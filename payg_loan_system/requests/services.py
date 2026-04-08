from shared.services.base_getter_service import BaseGetterService
from shared.services.sorter import Sorter
from shared.helpers.list_helpers import timePeriodHelper
from shared.helpers.pagination import Pagination
from payg_loan_system.requests.models import ActivationRequest, MentorRequest
from pony import orm


class MentorRequestSorter(Sorter):

    @classmethod
    def sort_by(cls, field_name):
        options = {
            'id': cls.by_id,
            'reception_time': cls.by_reception_time,
            'type': cls.by_type,
            'request_code': cls.by_request_code,
            'activation_days': cls.by_activation_days,
            'agent': cls.by_mentor,
            'client': cls.by_client,
            'device': cls.by_device
        }
        return options.get(field_name, cls.by_reception_time)

    def real_field_sort(field_name, desc=False):
        options = {
            'id': MentorRequest.id,
            'reception_time': MentorRequest.ReceptionTime,
            'type': MentorRequest.Type,
            'request_code': MentorRequest.RequestCode,
            'activation_days': MentorRequest.ActivationTimeAddedInDays,
            'agent': lambda mr: mr.user.full_name,
            'client': lambda mr: mr.client.full_name,
            'device': lambda mr: mr.Device.composed_serial
        }
        options_desc = {
            'agent': lambda mr: orm.desc(mr.user.full_name),
            'client': lambda mr: orm.desc(mr.client.full_name),
            'device': lambda mr: orm.desc(mr.Device.composed_serial)
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, MentorRequest.ReceptionTime))
        return options.get(field_name, MentorRequest.ReceptionTime)

    @staticmethod
    def by_reception_time(obj):
        return obj.ReceptionTime

    @staticmethod
    def by_type(obj):
        return obj.Type

    @staticmethod
    def by_request_code(obj):
        return obj.RequestCode

    @staticmethod
    def by_activation_days(obj):
        if obj.ActivationTimeAddedInDays is not None:
            return obj.ActivationTimeAddedInDays
        return -1

    @staticmethod
    def by_mentor(obj):
        return obj.user.full_name

    @staticmethod
    def by_client(obj):
        return obj.client.full_name

    @staticmethod
    def by_device(obj):
        return obj.Device


class ActivationRequestSorter(Sorter):

    @classmethod
    def sort_by(cls, field_name):
        options = {
            'id': cls.by_id,
            'reception_time': cls.by_reception_time,
            'request_code': cls.by_request_code,
            'client': cls.by_client,
            'device': cls.by_device,
            'activation_hours': cls.by_activation_hours,
            'credits_added': cls.by_credits_added
        }

        return options.get(field_name, cls.by_reception_time)

    @staticmethod
    def by_reception_time(obj):
        return obj.ReceptionTime

    @staticmethod
    def by_request_code(obj):
        return obj.RequestCode

    @staticmethod
    def by_activation_hours(obj):
        return obj.TimeActivatedInHours

    @staticmethod
    def by_client(obj):
        return obj.client.full_name

    @staticmethod
    def by_device(obj):
        return obj.Device

    @staticmethod
    def by_credits_added(obj):
        if obj.CreditsAdded is not None:
            return obj.CreditsAdded
        return 0


class ActivationRequestGetter(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user=None, **kwargs):
        return ActivationRequest.select()


class MentorRequestGetter(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user=None, **kwargs):
        return MentorRequest.select()


class GetterService:

    @staticmethod
    def filter(request, db_model, sort_type, current_user, clients=None, time_default=14, user=None, device=None):

        if request.method == 'POST':
            selected_time = request.form.get('time_filter', '')
        else:
            selected_time = request.args.get('time_filter', '')

        if db_model == ActivationRequest:
            sorter = ActivationRequestSorter
            getter = ActivationRequestGetter
        else:
            sorter = MentorRequestSorter
            getter = MentorRequestGetter

        params = 'time_filter={}'.format(selected_time)
        limit_time = timePeriodHelper(selected_time, time_default)

        if selected_time == '':
            selected_time = str(time_default)

        objects = getter.get_list(current_user).filter(lambda a: a.ReceptionTime >= limit_time)

        if clients:
            objects = objects.filter(lambda req: req.client in clients)

        if device:
            objects = objects.filter(lambda req: req.Device == device)

        if user:
            objects = objects.filter(lambda req: req.user == user)

        pagination = Pagination.generate(request, params)
        pagination.sort = request.args.get('sort', sort_type)
        pagination.objects = sorter.sort(objects, pagination.sort)

        return pagination, selected_time
