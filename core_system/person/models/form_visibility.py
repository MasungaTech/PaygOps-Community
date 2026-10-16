from shared.logger.loggers import Error
from shared.helpers.db_helpers import TypeClassBase
from payg_loan_system.offers.models import OfferType
from core_system.core_entities import db
from pony import orm


class FormVisibility(TypeClassBase):
    required = 1
    optional = 2
    present = 3


class FormVisibilityScope(TypeClassBase):
    client_and_lead = 1
    lead_only = 2
    client_only = 3

    _human_codes = {
        client_and_lead: "Clients and Leads",
        lead_only: "Leads",
        client_only: "Clients"
    }

    @classmethod
    def _lead_scopes(cls):
        return [cls.client_and_lead, cls.lead_only]

    @classmethod
    def _client_scopes(cls):
        return [cls.client_and_lead, cls.client_only]

class FormVisibilityRule(db.Entity):

    _table_ = "persondatasurvey"

    order = orm.Required(int)
    status = orm.Required(int, py_check=FormVisibility.valid)
    scope = orm.Required(int, py_check=FormVisibilityScope.valid)
    offer_type = orm.Optional(str, py_check=OfferType.ovalid)
    answer_for_each_lead = orm.Optional(bool, default=False)
    offers = orm.Set("Offer", table="offer_persondatasurvey")
    form = orm.Required('Form', column="survey_wrapper")

    def check_data_coherence(self):
        if not self.scope in self.form.allowed_scopes():
            raise Error(f'Scope {FormVisibilityScope.to_human(self.scope)} not allowed for form {self.form.name}')

    def before_update(self):
        self.check_data_coherence()

    def before_insert(self):
        self.check_data_coherence()
