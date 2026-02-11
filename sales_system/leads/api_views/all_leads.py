from constants import BOOLEAN_OPTIONAL_OPTIONS_STRING, INTEGER_OPTIONAL_OPTIONS_STRING, INTEGER_PATTERN
from sales_system.leads.models.lead import Lead
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.logger.loggers import LogAPI
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.add_lead_service import AddLeadService
from datetime import datetime, timedelta

log_api = LogAPI()


class AllLeadsResource(BaseAPIResourceAll):

    LIST_SERVICE = LeadGetterService
    ADD_SERVICE = AddLeadService
    LIST_PERMISSION = 'ViewLeads'
    ADD_PERMISSION = 'AddLeads'
    MODEL = Lead
    TAG = 'Leads'
    ALLOWED_API_CALLER = ["post"]

    EXTRA_LIST_PARAMS = {
        'include_subobjects': {
            'in': 'query',
            'name': 'include_subobjects',
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
            },
            'example': 'true',
            'allowEmptyValue': True,
            'description': 'Flag for including Lead sub-object (e.g. add-on) information or just the id/reference. It can only be used if `include_objects` is also `true`. **IMPORTANT:** When `true`, the use of pagination is compulsory with a maximum page size of 250. '
        },
        "special_data": {
            "name": "special_data",
            "description": "Include additional metrics. ",
            "in": "query",
            "required": False,
            'allowEmptyValue': True,
            "schema": {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
                "default": False
            },
            "examples": {
                'true': {
                    "value": "true",
                    "summary": "With additional metrics"
                },
                'false': {
                    "value": "false",
                    "summary": "Without additional metrics"
                }
            },
        },
        'lead_id': {
            'in': 'query',
            'name': 'lead_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering just an specific lead by id'
        },
        'contract_reference': {
            'in': 'query',
            'name': 'contract_reference',
            'schema': {
                'type': 'string',
            },
            'example': 'C0121234',
            'allowEmptyValue': True,
            'description': 'Allows for filtering just an specific lead by its future contract reference'
        },
        'custom_id': {
            "in": "query",
            "name": "custom_id",
            'schema': {
                'type': 'string',
            },
            'example': 'A12345678',
            'allowEmptyValue': True,
            'description': 'Allows to find a lead by custom ID'
        },
        'status_category': {
            'in': 'query',
            'name': 'status_category',
            'schema': {
                'oneOf': [
                    {
                        'type': 'string',
                        'enum': list(StatusCategory.to_dict().keys()),
                        'example': 'awaiting_payment'
                    },
                    {
                        'type': 'array',
                        'items': {
                            'type': 'string', 
                            'enum': list(StatusCategory.to_dict().keys()),
                        },
                        'example': ['awaiting_payment', 'awaiting_delivery']
                    }
                ]
            },
            'examples': {
                'single value': {
                    'value': 'awaiting_payment',
                    'summary': 'With status category awaiting payment'
                },
                'multiple values': {
                    'value': "['awaiting_payment', 'awaiting_delivery']",
                    'summary': 'With status categories awaiting payment and awaiting delivery'
                }
            },
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list by status category. '
        },

        'status': {
            'in': 'query',
            'name': 'status',
            'schema': {
                'oneOf': [
                    {
                        'type': 'string',
                        'example': 'interested'
                    },
                    {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'example': ['interested', 'completed']
                    }
                ]
            },
            'examples': {
                'single value': {
                    'value': 'interested',
                    'summary': 'With status interested'
                },
                'multiple values': {
                    'value': "['interested', 'completed']",
                    'summary': 'With statuses interested and completed'
                }
            },
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list by status. '
        },
        'status_ids': {
            'in': 'query',
            'name': 'status_ids',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING + [
                    {
                        'type': 'array',
                        'items': {
                            'oneOf': [
                                {
                                    'type': 'integer'
                                },
                                {
                                    'type': 'string',
                                    'pattern': INTEGER_PATTERN
                                }
                            ]
                        }
                    }
                ]
            },
            'examples': {
                'single value': {
                    'value': '12',
                    'summary': 'With status ID 12'
                },
                'multiple values': {
                    'value':"[12,13,14]",
                    'summary': 'With status IDs 12, 13 and 14'
                }
            },
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list by status IDs. '
        },
        'entity_id': {
            'in': 'query',
            'name': 'entity_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list by the operational entity of the leads. You can specify an operational entity of any level and get all the leads included in the sub-levels. '
        },
        'phone_number': {
            "in": "query",
            "name": "phone_number",
            'schema': {
                'type': 'string',
            },
            'example': '+23454665656',
            'allowEmptyValue': True,
            'description': 'Allows for filtering leads by phone number'
        },
        'client_group_id': {
            'in': 'query',
            'name': 'client_group_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list by the client group of the leads. '
        },
        'from_planned_delivery_date': {
            'in': 'query',
            'name': 'from_planned_delivery_date',
            'schema': {
                'type': 'string',
                'format': 'date-time'
            },
            'example': (datetime.now()+timedelta(days=1)).isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list to include those with planned delivery date AFTER the specified date. '
        },
        'to_planned_delivery_date': {
            'in': 'query',
            'name': 'to_planned_delivery_date',
            'schema': {
                'type': 'string',
                'format': 'date-time'
            },
            'example': datetime.now().isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list to include those with planned delivery date BEFORE the specified date. '
        },
        'from_status_change_date': {
            'in': 'query',
            'name': 'from_status_change_date',
            'schema': {
                'type': 'string',
                'format': 'date-time'
            },
            'example': (datetime.now()+timedelta(days=1)).isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list to include those with last status change AFTER the specified date. '
        },
        'to_status_change_date': {
            'in': 'query',
            'name': 'to_status_change_date',
            'schema': {
                'type': 'string',
                'format': 'date-time'
            },
            'example': datetime.now().isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering the lead list to include those with last status change BEFORE the specified date. '
        },
        'custom_data': {
            'in': 'query',
            'name': 'custom_data',
            "schema": {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
                "default": False
            },
            "examples": {
                'true': {
                    "value": "true",
                    "summary": "With custom data"
                },
                'false': {
                    "value": "false",
                    "summary": "Without custom data"
                }
            },
            'allowEmptyValue': True,
            'description': 'Include Custom data written by APIs. '
        },
    }
