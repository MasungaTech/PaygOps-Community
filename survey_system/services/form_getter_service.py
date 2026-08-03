from shared.services.base_getter_service import BaseGetterService
from survey_system.models.forms import Form, FormVersion


class FormGetterService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user, for_interactions=None, **kwargs):
        forms = Form.select()
        if for_interactions:
            forms = forms.filter(lambda f: f.for_interactions == True)
        return forms


class FormVersionGetterService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user, form_id=None, uuid=None, **kwargs):
        form_versions = FormVersion.select()
        if form_id:
            form_versions = form_versions.filter(lambda fv: fv.form.id == form_id)
        if uuid:
            form_versions = form_versions.filter(lambda fv: fv.mobile_uuid == uuid)
        return form_versions
