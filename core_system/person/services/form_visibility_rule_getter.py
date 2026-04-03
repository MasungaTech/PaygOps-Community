from survey_system.models.survey_answer import SurveyAnswer
from payg_loan_system.offers.models import Offer
from core_system.person.models.form_visibility import FormVisibilityRule, FormVisibility, FormVisibilityScope
from pony import orm


class FormVisibilityRuleGetterService:

    @classmethod
    def get_forms(cls, client=None, lead=None, required=False, always_shown=False, include_offer_list=None, for_mobile=False):
        assert (client or lead) and not (client and lead), "You need to provide either a lead or a client"

        specific_scope = FormVisibilityScope.lead_only if lead else FormVisibilityScope.client_only

        # 1. Determine applicable offers
        offers = set()
        if client and not isinstance(client, bool):
            offers.update(contract.offer for contract in client.contracts)
        if lead and not isinstance(lead, bool):
            offers.add(lead.offer)
        if include_offer_list:
            offers.update(include_offer_list)

        offer_ids = {o.id for o in offers if o is not None}
        offer_types = {o.type for o in offers if o is not None}

        # 2. Select all rules with valid scope
        configs = FormVisibilityRule.select(
            lambda config: config.scope in [specific_scope, FormVisibilityScope.client_and_lead]
        )

        # 3. Filter rules by offer_type and offer restrictions
        if not for_mobile:
            configs = configs.filter(
                lambda config:
                    # Include if no offer_type restriction or one of the offers matches
                    (not config.offer_type or config.offer_type in offer_types)
                    and (
                        not config.offers
                        or orm.exists(o for o in config.offers if o.id in offer_ids)
                    )
            )

        # 4. Filter based on status
        if always_shown:
            configs = configs.filter(lambda c: c.status != FormVisibility.present)
        elif required:
            configs = configs.filter(lambda c: c.status == FormVisibility.required)

        # 5. Return the forms in order
        return [config.form for config in configs.order_by(FormVisibilityRule.order)]


    @classmethod
    def get_all_person_surveys(cls):
        return FormVisibilityRule.select().order_by(lambda survey: survey.order)
    
    @classmethod
    def get_all_forms_to_be_answered_again(cls, lead=None):
        configs = FormVisibilityRule.select(lambda config: config.answer_for_each_lead)

        # Filter out forms that have already been answered by the lead
        if lead:
            lead_answers = orm.select(sa.surveyAnswered.form.id for sa in SurveyAnswer if sa.lead_answering.id == lead.id)
            # Exclude the forms that the lead has already answered
            return [config.form for config in configs.order_by(FormVisibilityRule.order) if config.form.id not in lead_answers]
        return [config.form for config in configs.order_by(FormVisibilityRule.order)]

    @classmethod
    def get_answers_for_client(cls, client):
        client_data_forms = cls.get_forms(client=client)
        return cls._get_answers_list_for_person_and_forms(client.person, client_data_forms)

    @classmethod
    def get_client_data_answers_id_for_client(cls, client):
        client_data_surveys = cls.get_answers_for_client(client)
        return {survey.surveyAnswered.form.name: survey.id for survey in client_data_surveys}

    @classmethod
    def get_answers_for_lead(cls, lead):
        lead_data_forms = cls.get_forms(lead=lead)
        return cls._get_answers_list_for_person_and_forms(lead.person, lead_data_forms, lead=lead)

    @classmethod
    def get_lead_data_answers_id_for_lead(cls, lead):
        lead_data_surveys = cls.get_answers_for_lead(lead)
        return {survey.surveyAnswered.form.name: survey.id for survey in lead_data_surveys}


    @classmethod
    def _get_answers_list_for_person_and_forms(cls, person, forms, lead=None):
        # First, get answers for the given person
        answers = SurveyAnswer.select().filter(lambda sa: sa.personAnswering == person)

        # If no lead is provided, return answers for the given forms and only include the last answers
        if not lead:
            return answers.filter(lambda sa: sa.is_last_answer and sa.surveyAnswered.form in forms)

        # Initialize the list to store answers that meet the criteria
        selected_answers = []

        for form in forms:
            this_forms_answers = []
            # Get the visibility rule for the current form (answer_for_each_lead)
            answer_for_each_lead = orm.exists(rule for rule in form.visibility_rules if rule.form == form and rule.answer_for_each_lead)
            # Check if this form has the 'answer_for_each_lead' rule set to True or False
            if answer_for_each_lead:
                # If answer_for_each_lead is True, include all answers for this form from the given lead
                lead_answers = answers.filter(lambda sa: sa.surveyAnswered.form == form and sa.lead_answering == lead)
                # Add answers for the given lead, even if it's not the last answer
                this_forms_answers.extend(lead_answers[:])
            else:
                # If answer_for_each_lead is False, include the last answer for the given lead
                lead_answers = answers.filter(lambda sa: sa.surveyAnswered.form == form and sa.lead_answering == lead)
                this_forms_answers.extend(lead_answers[:])
                # For forms with answer_for_each_lead = False, also include answers from other leads
                other_lead_answers = answers.filter(lambda sa: sa.surveyAnswered.form == form)
                this_forms_answers.extend(other_lead_answers[:])
            if this_forms_answers:
                # If we did get forms, we just get the last one
                this_forms_answers.sort(key=lambda sa: sa.started, reverse=True)
                selected_answers.extend([this_forms_answers[0]])

        # Convert the list of selected answers into a query object
        return SurveyAnswer.select().filter(lambda sa: sa in selected_answers)


    @classmethod
    def get_answered_forms(cls, person):
        return [sa.surveyAnswered.form for sa in person.surveyAnswered]

    @classmethod
    def get_answered_forms_by_lead(cls, lead):
        forms_to_be_answerd_again = cls.get_all_forms_to_be_answered_again(lead=lead)
        return [sa.surveyAnswered.form for sa in lead.person.surveyAnswered if sa.surveyAnswered.form not in forms_to_be_answerd_again]

    @classmethod
    def get_not_answered_surveys(cls, client=None, lead=None):
        shown_forms = cls.get_forms(client=client, lead=lead, always_shown=True)
        if lead:
            forms_to_be_answerd_again = cls.get_all_forms_to_be_answered_again(lead=lead)
        else:
            forms_to_be_answerd_again = []
        answered = cls.get_answered_forms((client or lead).person)
        return [s.last_version for s in shown_forms if (s not in answered or (s in forms_to_be_answerd_again))]
