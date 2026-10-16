from survey_system.models.question_type import QuestionType
from slugify import slugify


class SurveyAnswerAnswersGetterService:
    
    @classmethod
    def get_answers_with_questions(cls, survey_answer, questions=None, group=None, group_answers=None, use_names=False, mobile=False, new_format=False, slug_as_keys=False):
        if questions is None:
            questions = survey_answer.getQuestionsInOrder()

        if slug_as_keys:
            new_format = True
        if new_format:
            use_names = True

        answer_group = {}
        pairs = {}
            
        if group_answers is not None:
            if use_names:
                for q in questions:
                    answer_group[q.question.name] = ''
            else:
                for q in questions:
                    answer_group[q.id] = ''
        
        for index, question in enumerate(questions):
            if use_names:
                question_id = question.question.name
            else:
                question_id = question.id

            if group is None:
                pairs.update({question_id: []})
                thisQuestionAnswers = question.getAnswersInSurveyAnswer(survey_answer)
            else:
                thisQuestionAnswers = question.getAnswersInSubQuestion(survey_answer, group)

            for answer in thisQuestionAnswers:
                if question.getType() == QuestionType.group:
                    cls.get_answers_with_questions(
                        survey_answer=survey_answer,
                        questions=question.getSubQuestions(),
                        group=answer.grouping,
                        group_answers=pairs[question_id],
                        use_names=use_names,
                        new_format=new_format,
                        slug_as_keys=slug_as_keys
                    )
                else:
                    if group is None and question.getType() != QuestionType.group:
                        if question.getType() == QuestionType.choice_text and not use_names:
                            answer = answer.value_choice.id if answer.value_choice else None
                        elif question.getType() == QuestionType.choice_numeric and mobile and not use_names:
                            answer = answer.value_choice.id if answer.value_choice else None
                        elif answer.question.type in [QuestionType.picture, QuestionType.signature]:
                            answer = answer.getValue()
                            if answer:
                                answer = answer.uuid
                        elif question.getType() == QuestionType.gps:
                            lat, lon = answer.value_text.split(';')
                            if mobile:
                                answer = {
                                    "lat": lat,
                                    "lon": lon
                                }
                            else:
                                answer = {
                                    "gps_longitude": lon,
                                    "gps_latitude": lat
                                }
                        elif question.getType() == QuestionType.gps_surface: 
                            answer = answer.value_json
                        else:
                            answer = answer.getValue()
                        if new_format and question.maxAnswers < 2:
                            pairs[question_id] = answer
                        else:
                            pairs[question_id].append(answer)
                    elif group is not None:
                        if question.getType() == QuestionType.choice_text and not use_names:
                            answer = answer.value_choice.id if answer.value_choice else None
                        elif question.getType() == QuestionType.choice_numeric and mobile and not use_names:
                            answer = answer.value_choice.id if answer.value_choice else None
                        elif answer.question.type in [QuestionType.picture, QuestionType.signature]:
                            answer = answer.getValue()
                            if answer:
                                answer = answer.uuid
                        elif question.getType() == QuestionType.gps:
                            lat, lon = answer.value_text.split(';')
                            if mobile:
                                answer = {
                                    "lat": lat,
                                    "lon": lon
                                }
                            else:
                                answer = {
                                    "gps_longitude": lon,
                                    "gps_latitude": lat
                                }
                        else:
                            answer = answer.getValue()
                        answer_group[question_id] = answer
                    else:
                        answer = answer
                        if new_format and question.maxAnswers < 2:
                            pairs[question_id] = answer
                        else:
                            pairs[question_id].append(answer)
        if group is None:
            return cls.process_for_new_format(pairs, new_format, slug_as_keys)
        else:
            group_answers.append(cls.process_for_new_format(answer_group, new_format, slug_as_keys))
            return group_answers
        
    @classmethod
    def process_for_new_format(cls, answer_dict, new_format, slug_as_keys):
        if not new_format:
            return answer_dict
        if slug_as_keys:
            answers = {}
            for key, value in answer_dict.items():
                answers[slugify(key)] = value
        else:
            answers = []
            for key, value in answer_dict.items():
                answers.append({'question_name': key, 'answers': value})
        return answers