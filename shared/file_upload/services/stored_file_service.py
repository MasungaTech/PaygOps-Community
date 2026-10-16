from datetime import datetime
from uuid import uuid1
from PIL import Image, ExifTags
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from constants import CONTENT_PATH
from shared.file_upload.model import StoredFile, StoredFileType
from shared.helpers.exif_gps import get_lat_lon, get_exif_data
from pony import orm
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from core_system.core_entities import db
import config
from azure.storage.blob import BlobServiceClient
from worker_app.worker_app import worker_app
from survey_system.services.survey_answer_data_service import SurveyAnswerDataService


CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net'


class StoredFileService(BaseGetterService):

    THUMBNAIL_SIZE = 512
    JPEG_PICTURE_EXTENSION = ['jpg', 'jpeg', 'JPG', 'JPEG']
    SUPPORTED_PICTURE_EXTENSION = JPEG_PICTURE_EXTENSION
    PK_NAME = 'uuid'

    @classmethod
    def get_filtered_objects(cls, current_user=None, type=None, threshold=None, **kwargs):
        files = StoredFile.select()
        if type:
            files = files.filter(lambda f: f.type == type)
        if threshold:
            files = files.filter(lambda l: not l.backup_time and l.modifiedDate < threshold)
        return files

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        return StoredFileService.create_without_file(
            type=StoredFileType.PICTURE,
            uuid=data['uuid']
        )

    @classmethod
    def _edit_from_data_and_user(cls, entity, data, user):
        entity.modifiedDate = datetime.now()
        return entity

    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids):
        all_pictures = cls.get_list(
            current_user,
            type=StoredFileType.PICTURE,
            for_sync=True
        )
        survey_answers = current_user.get_relevant_survey_answers_for_mobile(cached_ids)
        survey_answer_ids = orm.select(e.id for e in survey_answers)[:]
        cached_ids['surveyanswer'] = survey_answer_ids
        user_clients_ids = cached_ids['client']
        user_leads_ids = cached_ids['lead']
        survey_pics_ids = orm.select(answer.value_stored_file.id for answer in db.Answer if answer.surveyAnswer.id in survey_answer_ids and answer.value_stored_file != None)[:]
        leads_person_ids = orm.select(l.person.id for l in db.Lead if l.id in user_leads_ids)[:]
        cached_ids['lead_persons'] = leads_person_ids
        client_persons_ids = orm.select(c.person.id for c in db.Client if c.id in user_clients_ids)
        cached_ids['client_persons'] = client_persons_ids
        persons_ids = leads_person_ids + client_persons_ids
        return all_pictures.filter(lambda pic: pic.person.id in persons_ids or pic.id in survey_pics_ids)

    @classmethod
    def create_with_file(cls, file, type, uuid=None):
        if not file:
            return None

        if not uuid:
            uuid = cls._generate_file_uuid()

        original_filename = cls._get_original_filename(file)
        file_object = cls.create_without_file(type, uuid, original_filename)

        cls.upload_file(file_object, file)
        return file_object

    @classmethod
    def upload_file(cls, file_object, file):
        if config.IS_SECONDARY:
            raise Error('Upload is disabled on secondary')
        if file_object.available and file_object.is_found():
            raise Error('Picture already uploaded')
        filepath = file_object.get_file_path()
        file.save(filepath)
        if file_object.type == StoredFileType.PICTURE:
            thumb = cls._generate_picture_thumbnail(file_object)
            thumbpath = file_object.get_thumbnail_path()
            thumb.save(thumbpath)
            cls._get_gps_coordinates_from_picture(file_object)
        file_object.available = True
        worker_app.send_task(
            'worker_app.tasks.backup_file_to_azure.backup_file_now',
            args=([file_object.uuid])
        )

        for answer in file_object.answers:
            survey_answer_data = SurveyAnswerDataService.get_survey_answer_data_dict(answer.surveyAnswer, use_names=True)
            if SurveyAnswerDataService.check_if_all_picture_sign_uploaded(surveyAnswer=answer.surveyAnswer):
                add_hook_after_commit(db, 'custom_form_answered_uploaded', survey_answer_data)


    @classmethod
    def create_without_file(cls, type, uuid, original_filename=''):
        existing = StoredFileService.get_from_uuid(uuid)
        if existing:
            return existing

        if not type:
            type = StoredFileType.PICTURE

        if original_filename:
            extension = '.'+original_filename.split('.')[-1]
        else:
            extension = None
        if type == StoredFileType.PICTURE:
            if extension and extension.split('.')[1] not in cls.SUPPORTED_PICTURE_EXTENSION:
                raise Error('INVALID_FILE_EXTENSION')
            filename = uuid + '.jpg'
            thumbnail_filename = uuid + '_t.jpg'
        elif type == StoredFileType.FILE:
            if not extension:
                raise Error('ORIGINAL_FILENAME_NEEDED_FOR_FILES')
            filename = uuid + extension
            thumbnail_filename = None
        else:
            raise Error('INVALID_FILE_TYPE')

        file_object = StoredFile(
            uuid=uuid,
            type=type,
            available=False,
            original_filename=original_filename,
            filename=filename,
            thumbnail_filename=thumbnail_filename
        )

        return file_object

    @classmethod
    def get_from_uuid(cls, uuid):
        if not uuid:
            return None
        return StoredFile.get(uuid=uuid)

    @classmethod
    def get_from_id(cls, id):
        return StoredFile.get(id=id)

    @classmethod
    def get_from_filename(cls, filename):
        # strip extension if it exists
        uuid = filename.split('.')[0]
        return cls.get_from_uuid(uuid)

    @classmethod
    def get_all_pictures(cls):
        return orm.select(file for file in StoredFile if file.type == StoredFileType.PICTURE)

    @classmethod
    def _generate_picture_thumbnail(cls, picture):
        picture = cls._fix_picture_orientation(picture)
        max_size = (cls.THUMBNAIL_SIZE, cls.THUMBNAIL_SIZE)
        picture.thumbnail(max_size, Image.LANCZOS)
        return picture

    @classmethod
    def _fix_picture_orientation(cls, picture_object):
        image = Image.open(picture_object.get_file_path())
        orientation_tag = None
        for tag in ExifTags.TAGS.keys():
            if ExifTags.TAGS[tag] == 'Orientation':
                orientation_tag = tag

        if image._getexif():
            exif = dict(image._getexif().items())
            if orientation_tag in exif:
                if exif[orientation_tag] == 3:
                    image = image.rotate(180, expand=True)
                elif exif[orientation_tag] == 6:
                    image = image.rotate(270, expand=True)
                elif exif[orientation_tag] == 8:
                    image = image.rotate(90, expand=True)
        return image

    @classmethod
    def _generate_file_uuid(cls):
        return str(uuid1())

    @classmethod
    def _get_original_filename(cls, file):
        return file.filename

    @classmethod
    def _get_gps_coordinates_from_picture(cls, file_object):
        file = Image.open(file_object.get_file_path())
        exif_data = get_exif_data(file)
        lat_lon = get_lat_lon(exif_data)
        lat = lat_lon[0]
        lon = lat_lon[1]
        if lat and lon:
            file_object.picture_gpslat = lat
            file_object.picture_gpslon = lon
    
    @classmethod
    def backup_file_from_client_and_object(cls, blob_service_client, file_object, overwrite=False):
        # Create a blob client using the local file name as the name for the blob
        blob_client = blob_service_client.get_blob_client(container=config.WALE_CONTAINER_NAME, blob='files/'+file_object.filename)
        # Upload the created file
        with open(file_object.get_file_path(), "rb") as data:
            blob_client.upload_blob(data, overwrite=overwrite)
        # get file and update backup_time
        file_object.backup_time = datetime.now()
    
    @classmethod
    def backup_file(cls, file_object):
        # We do not need to backup if the file is not available or if it's testing
        if file_object.available and not config.IS_TEST_PLATFORM:
            blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING.format(
                account_name=config.WABS_ACCOUNT_NAME,
                account_key=config.WABS_ACCESS_KEY,
            ))
            print("Uploading to Azure Storage as blob: " + file_object.filename)
            cls.backup_file_from_client_and_object(blob_service_client, file_object)
