import io
import csv
from datetime import datetime
import re
from pony.orm import flush, commit
from shared.logger.loggers import Error
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService
from core_system.phone_numbers.services.phone_number_finder import PhoneNumberFinder
from core_system.users.models.user_model import User
from core_system.client.models import Client
from sales_system.leads.models.lead import Lead
from messages_system.services.send_sms import SMSSend
from messages_system.services.notifications_service import NotificationsService
from messages_system.models.communications import CommunicationCampaign
from config import CONTROL_CHARS


class CommunicationsService():

    @classmethod
    def get_phones(cls, csv_file):
        rows = []
        valid_phones = []
        if csv_file.filename:
            rows = cls.import_csv_phone_list(csv_file)
            valid_phones = cls.validate_phones(rows)
        return rows, valid_phones

    @staticmethod
    def import_csv_phone_list(csv_file):

        try:
            csv_file = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            raise Error('Invalid file type. Please upload a text file.')
        if not csv_file:
            raise Error('The file is empty.')
        io_string = io.StringIO(csv_file)
        phones_file = csv.reader(io_string, delimiter=',', quotechar='"')
        try:
            next(phones_file)
        except csv.Error:
            io_string = io.StringIO(csv_file, newline='\r')
            phones_file = csv.reader(io_string, delimiter=',', quotechar='"')
            next(phones_file)
        try:
            rows = [row[0] for row in phones_file if len(row)]
        except IndexError as error:
            raise Error('File format is not correct.')
        return rows

    @staticmethod
    def validate_phones(phone_list):
        valid_phones = []
        for phone in phone_list:
            if phone[:2] == '00':
                phone = '+'+phone[2:]
            try:
                AddPhoneNumberService._is_phone_number_valid(phone)
            except Error:
                continue
            valid_phones.append(phone)
        return valid_phones

    @classmethod
    def send_campaign(cls, phones, leads_id, clients_id, content, user_id, name, filters):    
        for pattern, value in CONTROL_CHARS.items():
            content = re.sub(pattern, value, content)
        user = User.get(id=user_id)
        campaign = CommunicationCampaign(
            time=datetime.now(),
            name=name,
            user=user,
            content=content,
            criteria=filters,
            stats={'status': 'PROGRESS'},
            messages=[]
        )
        commit()
        result = {'phones': {}, 'leads': {}, 'clients': {}}

        clients = Client.select(lambda c: c.id in clients_id)
        result['clients'], out_for_delivery = cls._send_batch_objs(content=content, objects=clients, user=user)

        leads = Lead.select(lambda l: l.id in leads_id)
        result['leads'], sms = cls._send_batch_objs(content=content, objects=leads, user=user)
        out_for_delivery += sms

        result['phones'], sms = cls._send_batch_phones(content=content, phones=phones, user=user)
        out_for_delivery += sms

        flush()

        campaign.stats.update(result)
        campaign.stats.update({'status': 'COMPLETED'})
        campaign.messages = [sms.id for sms in out_for_delivery]

        return result

    @staticmethod
    def _send_batch_objs(content, objects, user=None):
        sms_sender = SMSSend
        result = {'total': 0, 'success': 0, 'failure': 0, 'nophone': 0}
        out_for_delivery = []
        if objects:
            for obj in objects:
                result['total'] += 1
                phone_number = PhoneNumberFinder.find_person_preferred_number(obj.person)
                if phone_number:
                    sms = sms_sender.SendMessage(phone_number, content, obj.person, user=user)
                    if sms:
                        out_for_delivery.append(sms)
                        result['success'] += 1
                    else:
                        result['failure'] += 1
                else:
                    NotificationsService.add_no_phone_notification(obj)
                    result['nophone'] += 1
        return result, out_for_delivery

    @staticmethod
    def _send_batch_phones(content, phones, user=None):
        sms_sender = SMSSend
        result = {'total': 0, 'success': 0, 'failure': 0}
        out_for_delivery = []
        if phones:
            for phone in phones:
                result['total'] += 1
                sms = sms_sender.SendMessage(phone, content, user=user)
                if sms:
                    out_for_delivery.append(sms)
                    result['success'] += 1
                else:
                    result['failure'] += 1
        return result, out_for_delivery
    