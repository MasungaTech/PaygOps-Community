from core_system.client.services.client_getter_service import ClientGetterService
from datetime import datetime
from dateutil.relativedelta import relativedelta
from survey_system.services.other_services import QuestionService, AnswerStatsService


class ClientStatsServices:

    @classmethod
    def get_gender_split(cls, clients):
        male_count = clients.filter(lambda client: client.person.gender == 1).count()
        female_count = clients.filter(lambda client: client.person.gender == 2).count()
        other_count = clients.filter(lambda client: client.person.gender not in [1, 2]).count()
        return {
            'male': male_count,
            'female': female_count,
            'other': other_count
        }

    @classmethod
    def get_age_split(cls, clients):
        clients = clients.filter(lambda client: client.person.birthdate is not None
                                                and client.person.birthdate != datetime.min)
        now = datetime.now()
        birthday_25 = now - relativedelta(years=25)
        below_25 = clients.filter(lambda client: client.person.birthdate > birthday_25).count()
        birthday_35 = now - relativedelta(years=35)
        below_35 = clients.filter(lambda client: client.person.birthdate > birthday_35 and client.person.birthdate <= birthday_25).count()
        birthday_45 = now - relativedelta(years=45)
        below_45 = clients.filter(lambda client: client.person.birthdate > birthday_45 and client.person.birthdate <= birthday_35).count()
        birthday_55 = now - relativedelta(years=55)
        below_55 = clients.filter(lambda client: client.person.birthdate > birthday_55 and client.person.birthdate <= birthday_45).count()
        above_55 = clients.filter(lambda client: client.person.birthdate <= birthday_55).count()

        return {
            'below_25': below_25,
            '25_35': below_35,
            '35_45': below_45,
            '45_55': below_55,
            'above_55': above_55
        }

    @classmethod
    def get_ratio_of_business_clients(cls, clients):
        other_count = clients.filter(lambda client: client.person.businessUse == False).count()
        business_count = clients.filter(lambda client: client.person.businessUse == True).count()
        if other_count or business_count:
            return (business_count/(other_count+business_count)) * 100
        return 0

    @classmethod
    def get_average_household_size(cls, clients):
        CHILD_QUESTION_NAME = 'nb_child'
        ADULT_QUESTION_NAME = 'nb_adults'
        number_of_kids_question = QuestionService.get_questions_by_name(CHILD_QUESTION_NAME)
        number_of_adults_question = QuestionService.get_questions_by_name(ADULT_QUESTION_NAME)
        average_number_kids = AnswerStatsService.get_average_answer_from_questions_and_clients(
            questions=number_of_kids_question,
            clients=clients
        )
        average_number_adults = AnswerStatsService.get_average_answer_from_questions_and_clients(
            questions=number_of_adults_question,
            clients=clients
        )
        if average_number_adults and average_number_adults:
            return average_number_adults+average_number_kids
        return None

    @classmethod
    def get_number_current_clients(cls, clients):
        return ClientGetterService.filter_by_status(clients, 'active_contracts').count()

    @classmethod
    def get_total_clients_count(cls, clients):
        return clients.count()
