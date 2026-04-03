from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from survey_system.models.forms import FormVersion
from survey_system.services.form_version_edit_service import FormVersionEditService
from survey_system.services.form_getter_service import FormVersionGetterService
from constants import INTEGER_OPTIONAL_OPTIONS_STRING


class FormVersionAPIAll(BaseAPIResourceAll):
    LIST_SERVICE = FormVersionGetterService
    LIST_PERMISSION = 'ViewForms'
    ADD_SERVICE = FormVersionEditService
    ADD_PERMISSION = 'AddForms'

    MODEL = FormVersion
    TAG = 'Custom Forms'
    OBJECT_NAME = 'Form Versions'

    EXTRA_LIST_PARAMS = {
        'form_id': {
            'in': 'query',
            'name': 'form_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering all the versions of one specific form'
        }
    }


class FormVersionAPI(BaseAPIResourceIndividual):
    GET_SERVICE = FormVersionGetterService
    GET_PERMISSION = 'ViewForms'
    EDIT_SERVICE = FormVersionEditService
    EDIT_PERMISSION = 'EditForms'
    DELETE_SERVICE = FormVersionEditService
    DELETE_PERMISSION = 'DeleteForms'

    MODEL = FormVersion
    TAG = 'Custom Forms'
    OBJECT_NAME = 'Form Versions'