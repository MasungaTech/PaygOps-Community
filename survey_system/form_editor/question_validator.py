from os import stat
from survey_system.models.question import Question
from shared.logger.loggers import Error


class QuestionValidator:
    def __init__(self, descriptor):
        self.question = descriptor.get('question')
        self.order = self._to_int(descriptor.get('order'))
        self.minimum_answers = self._to_int(descriptor.get('min_answers'))
        self.maximum_answers = self._to_int(descriptor.get('max_answers'))
        self.protected = self._to_bool(descriptor.get('protected', True))

    def is_valid(self):
        self._answers_amounts_are_valid()
        self._order_is_valid()

    def _answers_amounts_are_valid(self):
        ref = Question.get(id=self.question).name
        if self.maximum_answers < self.minimum_answers:
            raise Error(f'Invalid number of answers allowed ([{self.minimum_answers}, {self.maximum_answers}]) in Question {ref}')
        if not (type(self.minimum_answers) is int and self.minimum_answers >= 0):
            raise Error(f'Invalid minimum answers "{self.minimum_answers}" in Question {ref}')
        if not (type(self.maximum_answers) is int and self.maximum_answers > 0):
            raise Error(f'Invalid maximum answers "{self.maximum_answers}" in Question {ref}')

    def _order_is_valid(self):
        if not(type(self.order) is int and self.order >= 0):
            raise Error(f'Invalid order number for question {Question.get(id=self.question).name}')
    
    @staticmethod
    def _to_int(val):
        try:
            return int(val)
        except (ValueError, TypeError):
            return val
  
    @staticmethod
    def _to_bool(value):
        return value in ['1', 1, True, 'true', 'True']
