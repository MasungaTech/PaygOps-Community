from constants import AVAILABLE_ICONS
from core_system.person.models.form_visibility import FormVisibilityScope
from payg_loan_system.offers.models import Offer
from datetime import datetime
from pony import orm
from core_system.core_entities import db
from survey_system.models.ordered_question import OrderedQuestion
from shared.helpers import date_helper
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.model.cached_model import CachedModelMixin
from shared.helpers.dict_helpers import insert_after_key, rename_key
from shared.helpers.form_helpers import value_to_bool
import config

ENTERPRISE_FEATURES_ENABLED = getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False)

if ENTERPRISE_FEATURES_ENABLED:
    from mobile_sync_system.factories.survey_factory import SurveyFactory
else:
    class SurveyFactory:
        """Stub for SurveyFactory when enterprise features are disabled."""
        @staticmethod
        def map_server_to_mobile_core(server_obj):
            return {}



class Form(db.Entity, ModelDefinitionMixin):

    _table_ = 'surveywrapper'

    name = orm.Required(str, index=True)
    icon = orm.Optional(str, py_check=lambda i: not i or i in AVAILABLE_ICONS)
    is_system = orm.Required(bool, default=False)
    for_leads = orm.Required(bool, default=False)
    for_clients = orm.Required(bool, default=False)
    for_interactions = orm.Required(bool, default=False)
    restrict_editing = orm.Required(bool, default=False)

    visibility_rules = orm.Set('FormVisibilityRule')
    # Interaction topics live in the enterprise after_sales_system module.
    # Only define the relation when enterprise features are enabled so Pony
    # doesn't require the InteractionTopic entity in OSS mode.
    if ENTERPRISE_FEATURES_ENABLED:
        interaction_topics = orm.Set('InteractionTopic')
    versions = orm.Set('FormVersion')

    modifiedDate = orm.Required(datetime, default=datetime.now, index=True, volatile=True)

    def before_update(self):
        now = datetime.now()
        self.modifiedDate = now
        # We actually need to update the form versions to update their cache
        # This makes it that the name, restricted status, etc. are updated on mobile
        # There are only a few version for each form so low performance impact
        for version in self.versions:
            version.modifiedDate = now

    def get_link(self):
        from flask import url_for
        return url_for('forms_blueprint.view_form', form_id=self.id)

    def get_display_id(self):
        return str(self.name)

    @property
    def last_version_number(self):
        return orm.max((v.version for v in self.versions)) or 0

    @property
    def last_version(self):
        return self.versions.select(lambda v: v.version == self.last_version_number).first()

    @property
    def nb_answers(self):
        return orm.select(a for a in db.SurveyAnswer if a.surveyAnswered.form == self).count()

    @property
    def applicable_offers(self):
        
        offers = []
        for rule in self.visibility_rules:
            specified_offers = []
            offers_for_type = []
            if rule.offers:
                specified_offers = rule.offers
            if rule.offer_type:
                offers_for_type = orm.select(offer for offer in Offer if offer.type == rule.offer_type)
            to_add = list(offers_for_type) + list(set(specified_offers) - set(offers_for_type))
            offers.extend(to_add)
        return offers

    def allowed_scopes(self):
        if self.for_leads:
            if self.for_clients:
                return FormVisibilityScope.to_list()
            return [FormVisibilityScope.lead_only]
        if self.for_clients:
            return [FormVisibilityScope.client_only]
        return []

    def allowed_scopes_human(self):
        return {s: FormVisibilityScope.to_human(s) for s in self.allowed_scopes()}

    @classmethod
    def get_model_definition(cls, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "This is the ID of the Form."
                },
                'icon': {
                    "description": "This is name of the icon of the form.",
                    "type": "string",
                    "example": "done",
                    "value": lambda o: o.icon
                },
                'name': {
                    "description": "This is the name of the form.",
                    "type": "string",
                    "example": "My Form",
                    "value": lambda o: o.name
                },
                'for_leads': {
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.for_leads,
                    "description": "This the availability of this form for leads."
                },
                'for_clients': {
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.for_clients,
                    "description": "This the availability of this form for clients."
                },
                'for_interactions': {
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.for_interactions,
                    "description": "This the availability of this form for interactions."
                },
                'restrict_editing': {
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.restrict_editing,
                    "description": "This the property to determine whether to restrict editing of a form associated with a lead in a restricted status."
                },
                'versions': {
                    "type": "array",
                    "itemsModel": FormVersion,
                    "value": lambda o: [v.get_serialized_object() for v in o.versions],
                }
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": ["name", "icon", "for_leads", "for_clients", "for_interactions", "versions", "restrict_editing"],
            "view_required": [],
            "view_allowed": None
        }


class FormVersion(db.Entity, ModelDefinitionMixin, CachedModelMixin):

    _table_ = 'survey'

    name = orm.Optional(str, index=True) # Should not be used
    icon = orm.Optional(str) # should not be used

    form = orm.Optional(Form, column="wrapper")
    isSystem = orm.Required(bool, default=False) #should not be used
    updateDate = orm.Required(datetime, default=datetime.now)
    version = orm.Required(int, default=1)

    updatedBy = orm.Optional('User', column="updatedby")

    modifiedDate = orm.Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = orm.Optional(str)

    # FKs
    if ENTERPRISE_FEATURES_ENABLED:
        interactionTopic = orm.Set('InteractionTopic')
    questions = orm.Set('OrderedQuestion')
    answers = orm.Set('SurveyAnswer')

    # Cached data
    cached_data = orm.Optional(orm.Json, volatile=True)


    # Parameters
    PARAMETERS = [
        {
            "name": "for_export",
            "in": "query",
            "description": "Exclude IDs from the response to make it easy to export to another platform. ",
            "required": False,
            "schema": {
                "type": "string",
                "enum": ["true", "false", "True", "False"],
                "default": "false",
            },
            "examples": {
                'false': {
                    "value": "false",
                    "summary": "Regular"
                },
                'true': {
                    "value": "true",
                    "summary": "For export"
                }
            },
        }
    ]

    def update_cached_data(self):
        if not self.cached_data:
            self.cached_data = {}
        self.cached_data['mobile_object'] = SurveyFactory.map_server_to_mobile_core(self)

    @property
    def is_editable(self):
        return self.is_latest and not self.form.is_system

    @property
    def is_latest(self):
        return self.version == self.form.last_version_number

    @property
    def in_settings(self):
        return bool((self.form.visibility_rules.count() or self.form.interaction_topics.count()) and self.form.versions.count() == 1)

    @staticmethod
    @orm.db_session
    def in_system(survey_name):
        return FormVersion.exists(lambda s: s.form.name == survey_name)

    def getQuestions(self):
        return orm.select(Q for Q in OrderedQuestion if not Q.isSubQuestion and Q.survey == self).order_by(lambda Q: Q.order)

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
    
    def after_insert(self):
        self.update_cached_data()

    def before_update(self):
        self.modifiedDate = datetime.now()
        self.form.modifiedDate = datetime.now()
        self.update_cached_data()

    @classmethod
    def get_model_definition(cls, new_models=True, for_export=False, **kwargs):
        description = {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "This is the ID of the Form Version."
                },
                "uuid": {
                    "description": "The UUID of the Form Version.",
                    "type": "string",
                    "example": "123e4567-e89b-12d3-a456-426614174000",
                    "value": lambda o: o.mobile_uuid
                },
                'questions': {
                    "description": "Questions in the form versison.",
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": OrderedQuestion.get_model_schema(new_models=new_models, for_export=for_export)['properties']
                    },
                    "example": [OrderedQuestion.get_model_example(new_models=new_models, for_export=for_export)],
                    "value": lambda o: [q.get_serialized_object(new_models=new_models, for_export=for_export) for q in o.questions.order_by(lambda q: q.order)]
                },
                "form": {
                    "description": "The ID of the base form to which this form version belongs.",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.form.id
                },
                "version": {
                    "description": "The version number of this Form Version.",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.version
                },
                "updated_by": {
                    "description": "The ID of the user that last edited the Form Version.",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.updatedBy.id if o.updatedBy else None
                },
                "update_date": {
                    "description": "The date that the Form Version was last edited.",
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00.000Z",
                    "value": lambda o: o.updateDate
                }
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": ["questions"],
            "bulk_edit_allowed": ["id", "questions"],
            "bulk_edit_required": ["id"],
            "bulk_view_allowed": [],
            "bulk_view_required": [],
            "view_required": [],
            "view_allowed": None
        }
        if new_models:
            description['properties'] = insert_after_key(description['properties'], 'id', {
                'name': {
                    "description": "This is the name of the form.",
                    "type": "string",
                    "example": "My Form",
                    "value": lambda o: o.form.name
                },
                'icon': {
                    "description": "This is name of the icon of the form. It should use Google Material Symbols.",
                    "type": "string",
                    "example": "done",
                    "value": lambda o: o.form.icon
                }
            })
            description['properties'] = insert_after_key(description['properties'], 'version', {
                'for_leads': {
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.form.for_leads,
                    "description": "This the availability of this form for leads."
                },
                'for_clients': {
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.form.for_clients,
                    "description": "This the availability of this form for clients."
                },
                'for_interactions': {
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.form.for_interactions,
                    "description": "This the availability of this form for interactions."
                },
            })
            description['properties'] = rename_key(description['properties'], 'for_leads', 'available_for_leads')
            description['properties'] = rename_key(description['properties'], 'for_clients', 'available_for_clients')
            description['properties'] = rename_key(description['properties'], 'for_interactions', 'available_for_interactions')
            description['properties'] = rename_key(description['properties'], 'form', 'form_id')
            del description['properties']['version']
            description['edit_allowed'] = ['name', 'icon', 'available_for_leads', 'available_for_clients', 'available_for_interactions']
            description['create_allowed'] = description['edit_allowed'] + ['questions', 'form_id']
            for_export = value_to_bool(for_export)
            if for_export:
                del description['properties']['id']
                del description['properties']['form_id']
                del description['properties']['updated_by']
                del description['properties']['update_date']
        return description
