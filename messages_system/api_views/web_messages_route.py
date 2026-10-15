from flask_restful import Resource, request
from pony import orm
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from shared.logger.loggers import LogAPI
from messages_system.models.sms_db import OutgoingSMS


log_api = LogAPI()


class WebAnswerResource(Resource):

    @verify(permissions=['ViewMessages'])
    @orm.db_session
    def get(self):
        sender_number = request.args.get('sender_number')
        # We get the messages that are destined to the sender_number and are not sent
        answers_body = orm.select(sms.Body for sms in OutgoingSMS if not sms.IsSent
                                    and sms.ToNumber == sender_number)[:]
        answers_body = [answer for answer in answers_body]
        # We mark the messages as sent immediately since they are displayed on the web interface
        answers = orm.select(sms for sms in OutgoingSMS if not sms.IsSent and sms.ToNumber == sender_number)
        # We mark them as sent
        for answer in answers:
            answer.IsSent = True
        return answers_body, 200
