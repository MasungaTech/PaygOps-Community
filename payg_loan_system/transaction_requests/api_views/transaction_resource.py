import uuid
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, DocumentedResource, get_error_example
from flask_restful import request
from werkzeug.exceptions import BadRequest, NotFound
from pony.orm import db_session
from shared.api_helpers.server_helpers.jwt_and_schema_verification import check_permissions_for_user, verify
from core_system.users.services.current_user_service import get_current_api_user
from payg_loan_system.transaction_requests.services.get_transaction_request_service import \
    GetTransactionRequestService
from payg_loan_system.transaction_requests.models import TransactionRequest
from messages_system.services.message_service import MessageService
from shared.logger.loggers import Error
from shared.services.audit_log_service import AuditLogService


PUT_SCHEMA = {
    "properties": {
        "sent_to_client": {
            "type": "boolean",
            "description": "Flag indicating if the result of the request must be sent to the client",
            "example": True,
        }
    },
    "required": []
}


class TransactionResource(DocumentedResource):

    service = None
    ALLOWED_API_CALLER = ["post"]
    API_CALLER_GENERATORS = {
        "post": {
            "uuid": lambda: str(uuid.uuid1())
        }
    }

    @classmethod
    def get_meta(cls):
        return {
            'get': {
                "tags": ['Transactions'],
                "permissions": ['ViewActions'],
                "summary": "GET " + cls.__name__.replace('Resource', '') + " Information",
                "parameters": [{
                    "in": "path",
                    "name": "uuid",
                    "description": "The uuid of the transaction",
                    "required": True,
                    "example": "123e4567-e89b-12d3-a456-426614174000",
                    "schema": {
                        "type": "string",
                        "format": "uuid",
                    }
                }, {
                    "in": "query",
                    "name": "human_answer",
                    "description": "Flag indicating if the human readable result of the transaction is requested or not",
                    "required": False,
                    "schema": {
                        "type": "boolean",
                        "example": True
                    }
                }],
                "responses": {
                    200: {
                        "description": "Returns the " + cls.__name__.replace('Resource', '') + " information",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        TransactionRequest.get_model_schema(service=cls.service),
                                        TransactionRequest.get_model_schema(service=cls.service, human_answer=True),
                                    ]
                                },
                                "examples": {
                                    "human_answer == false": {
                                        "summary": "",
                                        "value": TransactionRequest.get_model_example(service=cls.service),
                                    },
                                    "human_answer == true":  {
                                        "summary": "",
                                        "value": TransactionRequest.get_model_example(service=cls.service, human_answer=True)
                                    }
                                }
                            }
                        },
                    },
                    404: {
                        "description": "Transaction Not Found",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(message="Transaction Not Found")
                            }
                        },
                    },
                }
            },
            'post': {
                "tags": ['Transactions'],
                "permissions": cls.service.permissions,
                "summary": "ADD " + cls.__name__.replace('Resource', ''),
                "parameters": [{
                    "in": "path",
                    "name": "uuid",
                    "description": "The uuid of the transaction",
                    "required": True,
                    "example": "123e4567-e89b-12d3-a456-426614174000",
                    "schema": {
                        "type": "string",
                        "format": "uuid"
                    }
                }],
                "requestBody": {
                    "description": cls.service.description,
                    "schema": cls.service.schema
                },
                "responses": {
                    200: {
                        "description": "Returns the " + cls.__name__.replace('Resource', '') + " information",
                        "content": {
                            "application/json": {
                                "schema": TransactionRequest.get_model_schema(service=cls.service, human_answer=True),
                                "example": TransactionRequest.get_model_example(service=cls.service, human_answer=True)
                            }
                        },
                    },
                    400: {
                        "description": "Badly formated request",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(code=400, message='Invalid contract reference')
                            }
                        }
                    },
                }
            },
            'put': {
                "tags": ['Transactions'],
                "permissions": cls.service.permissions,
                "summary": "SEND RESULT of " + cls.__name__.replace('Resource', '') + " to client",
                "parameters": [{
                    "in": "path",
                    "name": "uuid",
                    "description": "The uuid of the transaction",
                    "required": True,
                    "example": "123e4567-e89b-12d3-a456-426614174000",
                    "schema": {
                        "type": "string",
                        "format": "uuid",
                    }
                }],
                "requestBody": {
                    "description": "Allows for sending the result of the request to the affected client/lead by sms",
                    "schema": PUT_SCHEMA
                },
                "responses": {
                    200: {
                        "description": "Send request processed",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "properties": {
                                        "success": {
                                            "type": "boolean",
                                            "description": "Flag indicating whather the send request was process successfully",
                                            "example": True
                                        },
                                        "sent_to_client": {
                                            "type": "string",
                                            "description": "Text send as sms to the client/lead",
                                            "example": "This is the sms body sent to the client"
                                        }
                                    }
                                }
                            }
                        },
                    },
                    400: {
                        "description": "Badly formated request",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(code=400, message='Invalid contract reference')
                            }
                        }
                    },
                    404: {
                        "description": "Transaction not found",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(code=404, message='Invalid transaction uuid')
                            }
                        }
                    },
                }
            }
        }
    
    def get(self, uuid):
        return verify()(self.get_core)(uuid)

    def post(self, uuid):
        with db_session:
            user = get_current_api_user()
        data = request.json
        return verify(schema=self.service.schema)(self.post_core)(user, uuid, data)

    def put(self, uuid):
        with db_session:
            user = get_current_api_user()
        data = request.json
        return verify(schema=PUT_SCHEMA)(self.put_core)(user, uuid, data)

    @db_session
    def get_core(self, uuid):
        return GetTransactionRequestService.get_transaction_request_answer(
            get_current_api_user(),
            uuid,
            request.args.get('human_answer')
        )

    @classmethod
    def post_core(cls, user, uuid, data):
        schema = cls.service.get_relevant_subschema(data)
        params = {k: data.get(k, s.get('default')) for k, s in schema['properties'].items()}
        assert user, "User required for transactions"
        this_transaction = cls.service.create(
            user=user,
            uuid=uuid,
            **params)
        with db_session:
            return GetTransactionRequestService.get_transaction_request_answer(
                user.reload(), 
                this_transaction.uuid, 
                True
            )

    @classmethod
    @db_session
    def put_core(cls, user, uuid, data):
        transaction = TransactionRequest.get(uuid=uuid)
        if not transaction:
            raise NotFound("Transaction not found")
        check_permissions_for_user(user, cls.service.permissions, person=transaction._get_affected_person())
        response = {'success': True}
        if 'sent_to_client' in data:
            sent_to_client = data.pop('sent_to_client')
            if sent_to_client:
                if not transaction.message_for_client:
                    raise Error('The transaction answer has no messages for clients')
                if not transaction.client:
                    raise Error('The transaction has no associated client')
                sms = MessageService.send_answer_to_person(transaction.message_for_client, transaction.client.person)
                if sms != 0:
                    response['sent_to_client'] = sms.to_dict()
                    # Body is LongUnicode and not included in to_dict
                    response['sent_to_client'].update({'Body': sms.Body})
                else:
                    response['success'] = False
        for unknown in data:
            raise BadRequest('Unkown or non-editable property %s' % unknown)
        AuditLogService.store_audit_log_data(user=user, data=data, object=transaction, action='edit')
        return response
