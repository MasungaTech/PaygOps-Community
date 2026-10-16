from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.file_upload.model import StoredFile
from shared.logger.loggers import Error
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from flask import request, send_file
from core_system.core_entities import db
import config, os
from pony.orm import db_session
from shared.api_helpers.documented_resource import DocumentedResource, API_ERROR_SCHEMA, get_error_example
from shared.file_upload.services.stored_file_service import StoredFileService, StoredFileType

SCHEMA = {
    "properties": {
        "pic": {
            "type": "string",
            "description": "The file data encoded as multipart/form-data",
            "example": "FILE_ENCODED_AS_MULTIPART_FORM_DATA"
        },
    },
    "required": ["pic"]
}

class DownloadFileResource(DocumentedResource):

    META = {
        "get": {
            "summary": "Download Picture from PaygOps",
            "description": "Downloads a picture from PaygOps. ",
            "parameters": [{
                "name": "uuid",
                "in": "path",
                "description": "The UUID of the picture",
                "required": True,
                "example": "1234abcd-12ab-12ab-12ab-1234abcd1234",
                "schema": {
                    "type": "string"
                }
            }],
            "responses": {
                200: {
                    "description": "Returns the actual JPEG image. ",
                    "content": {
                        "image/jpeg": {}
                    }
                },
                404: {
                    "description": "The picture does not exists",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(message="Picture does not exists or you do not have the permission.")
                        }
                    }
                },
                410: {
                    "description": "The picture was taken but never uploaded",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(code=410, message="The picture was created but was never uploaded. Check that the mobile app fully synced in the background if the picture was taken while offline. ")
                        }
                    }
                }
            }
        }
    }

    @verify(permissions=['ViewForms'])
    @db_session
    def get(self, uuid):
        file_object = StoredFileService.get_from_uuid(uuid)
        if not file_object:
            return {
                'error': '404',
                'success': False,
                'error_message': 'Picture not found',
                'error_data': {}
            }, 404
        if not file_object.is_found():
            return {
                'error': '410',
                'success': False,
                'error_message': 'The picture was created but was never uploaded. Check that the mobile app fully synced in the background if the picture was taken while offline. ',
                'error_data': {}
            }, 410
        if config.is_test_platform() and not file_object.is_found():
            return send_file(os.path.join(config.IMG_STATIC_PATH, 'default_mentor.jpg'))
        directory = file_object.get_file_path()
        return send_file(directory)

class FileResource(BaseAPIResourceAll):

    LIST_SERVICE = StoredFileService
    LIST_PERMISSION = 'ViewForms'
    LIST_VARIABLE = 'uuid'
    LIST_VARIABLE_TYPE = 'string'
    LIST_VARIABLE_FORMAT = ''
    LIST_VARIABLE_EXAMPLES = [
        "8e1feded-27d7-43e0-9183-8ff66caf0d58",
        "5b086ffb-81d6-47bb-ad08-cc8d073c063f",
        "d34ad6f4-8e26-4d46-bfe5-ee8cdba544c6"
    ]
    MODEL = StoredFile
    TAG = 'Miscellaneous'

class UploadFileResource(DocumentedResource):

    META = {
        "post": {
            "summary": "Upload Picture to PaygOps",
            "description": "Uploads a picture to the platform and gets the UUID to reference it. ",
            "requestBody": {
                "description": "",
                "mime": "multipart/form-data",
                "schema": SCHEMA
            },
            "responses": {
                201 : {
                    "description": "File uploaded successfully. Returns UUID.",
                    "content": {
                        "text/plain": {
                            "example": "1234abcd-12ab-12ab-12ab-1234abcd1234"
                        }
                    }
                },
                400: {
                    "description": "Badly formated request",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(code=400, message='No file data')
                        }
                    }
                }
            }
        }
    }

    @verify(permissions=['AddForms'])
    @db_session
    def post(self):
        picture = request.files.get('pic')
        uuid = request.form.get('uuid')
        if uuid:
            picture_object = StoredFileService.get_from_uuid(uuid)
            if not picture_object:
                picture_object = StoredFileService.create_without_file(StoredFileType.PICTURE, uuid)
            if picture:
                StoredFileService.upload_file(picture_object, picture)

        else:
            if not picture:
                raise Error('No file data', code="NO_FILE_DATA")
            picture_object = StoredFileService.create_with_file(picture, StoredFileType.PICTURE)

        return picture_object.uuid
