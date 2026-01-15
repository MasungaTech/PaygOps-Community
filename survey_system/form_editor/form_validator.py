from shared.logger.loggers import Error
from survey_system.form_editor.question_validator import QuestionValidator


class FormValidator:
    def __init__(self, descriptor):
        self.descriptor = descriptor

    def is_valid(self, just_questions=False, questions_required=True):
        questions = self._extract_questions()

        if not just_questions and not self.descriptor.get('name'):
            raise Error('Name is required')
        
        if not questions and questions_required:
            raise Error('The form must have at least one question')
        for question in questions:
            question.is_valid()

        question_orders_are_not_repeated = self._question_orders_are_not_repeated(questions)

        if not question_orders_are_not_repeated:
            raise Error('Invalid')

    def _extract_questions(self):
        return list(map(lambda descriptor: QuestionValidator(descriptor), self.descriptor.get('questions', [])))

    @staticmethod
    def _question_orders_are_not_repeated(questions):
        question_orders = list(map(lambda question: question.order, questions))

        return len(question_orders) == len(set(question_orders))
