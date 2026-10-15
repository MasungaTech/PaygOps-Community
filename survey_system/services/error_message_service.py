

from messages_system.services.message_service import MessageService


class SurveyAnswerErrorMessageService:

    @classmethod
    def get_human_readable_error(cls, error):
        # Related to the survey answer
        if 'INSUFFICIENT_PERMISSION' in str(error):
            return MessageService.get_message({'status': str(error), 'permission': error.data.get('permission')})
        if 'INVALID_FORM_ID' in str(error):
            return 'Invalid Form ID. '
        if 'FORM_CAN_HAVE_ONLY_ONE_SUBJECT' in str(error):
            return 'The form can only have one subject, please choose either client or user. '
        if 'INVALID_CLIENT_ID' in str(error):
            return 'Invalid Client ID. '
        if 'INVALID_USER_ID' in str(error):
            return 'Invalid User ID. '
        if 'INVALID_LEAD_ID' in str(error):
            return 'Invalid LEAD ID. '
        if 'CLIENT_AND_LEAD_ARE_DIFFERENT_PERSONS' in str(error):
            return 'The Client and Lead are different persons.  '
        if 'FORM_SUBJECT_REQUIRED' in str(error):
            return 'The form needs at least one subject, please choose either client or user. '
        if 'USER_JOURNEY_RUN_DISABLED_IN_FEATURE_TOGGLES' in str(error):
            return 'User journey editor is disabled. Please enable User Journey Editor in Feature Toggles to run this journey. '
        if 'INVALID_DISCUSSED_TOPIC_ID' in str(error):
            return 'Invalid Discussed Topic ID. '

        # Related to the individual answer to a question
        question_name = cls._get_variable_from_error(error, 'question_name')
        if 'EMPTY_ANSWER' in str(error):
            return f'The answer to the question {question_name} is empty. '
        if 'INVALID_QUESTION_TYPE' in str(error):
            return f'The question {question_name} is of a type that is not supported. '
        if 'ANSWER_TOO_SHORT' in str(error):
            min_value = cls._get_variable_from_error(error, 'min_value')
            return f'The answer provided to the question {question_name} is too short. ' \
                   f'It should be at least {min_value} character long. '
        if 'ANSWER_TOO_LONG' in str(error):
            max_value = cls._get_variable_from_error(error, 'max_value')
            return f'The answer provided to the question {question_name} is too long. ' \
                   f'It should be at most {max_value} character long. '
        if 'VALUE_TOO_LOW' in str(error):
            min_value = cls._get_variable_from_error(error, 'min_value')
            return f'The value for the answer to the question {question_name} is too low. ' \
                   f'It should be at least {min_value}. '
        if 'VALUE_TOO_HIGH' in str(error):
            max_value = cls._get_variable_from_error(error, 'max_value')
            return f'The value for the answer provided to the question {question_name} is too high. ' \
                   f'It should be at most {max_value}. '
        if 'VALUE_NOT_INTEGER' in str(error):
            return f'The value for the answer provided to question {question_name} is not an integer. '
        if 'INVALID_QUESTION_CHOICE' in str(error):
            return f'The answer provided to question {question_name} is not a valid choice for that question. '
        if 'INVALID_PICTURE_ID' in str(error):
            return f'The answer provided to question {question_name} is not a valid picture ID, ' \
                   f'make sure that the picture was created properly. '
        if 'INVALID_SIGNATURE_ID' in str(error):
            return f'The answer provided to question {question_name} is not a valid signature ID, ' \
                   f'make sure that the signature was created properly. '
        raise error

    @classmethod
    def _get_variable_from_error(cls, error, variable):
        return error.args[1].get(variable) if len(error.args) > 1 else ''
