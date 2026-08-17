import re
from pony import orm
from survey_system.models.question import Question

def not_empty(value):
    return value not in ['', None, [], {}]

def cleanJSONDict(obj):
    if isinstance(obj, dict):
        return {key.replace('q', ''): cleanJSONDict(val) for key, val in obj.items() if not_empty(cleanJSONDict(val))}
    if isinstance(obj, list):
        return [cleanJSONDict(d) for d in obj if not_empty(cleanJSONDict(d))]
    return obj

def is_valid_url(url):
    regex = ("((http|https)://)(www.)?" +
             "[a-zA-Z0-9@:%._\\+~#?&//=]" +
             "{2,256}\\.[a-z]" +
             "{2,6}\\b([-a-zA-Z0-9@:%" +
             "._\\+~#?&//=]*)")
    return url is not None and bool(re.search(regex, url))

def get_missing_questions(request_data):        
    if type(request_data) != dict: 
        return False
    
    answers = request_data.get("answers")
    if not answers:
        return False
    
    question_names = set(q.get("question_name") for q in answers if type(q) == dict)
    db_question_names = set(
        item
        for q in orm.select(
            q for q in Question
            if q.name in question_names or q.slug in question_names
        )
        for item in (q.name, q.slug)
    )
    return question_names - db_question_names 
