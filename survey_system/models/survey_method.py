from shared.helpers.db_helpers import TypeClassBase


class SurveyMethod(TypeClassBase):
    in_person = 1  # The person is asked the question but doesn't see them directly, only voice
    phone = 2  # The person is asked questions over the phone
    sms = 3  # The person receives question by SMS and answers directly
    web_direct = 4  # The person directly answers via Web interface
    web_assisted = 5  # The person sees the Web interface but is assisted in entering information
    mobile_direct = 6  # The person answers question directly on the mobile app
    mobile_assisted = 7  # The person sees the mobile app but is assisted in entering information
    paper_direct = 8  # The person fills in a paper form
    paper_assisted = 9  # The person sees the paper form but is assisted in entering information

    _human_codes = {
        in_person: 'In Person',
        phone: 'Phone',
        sms: 'SMS',
        web_direct: "Web",
        web_assisted: "Web",
        mobile_direct: "Mobile",
        mobile_assisted: "Mobile",
        paper_direct: "Paper",
        paper_assisted: "Paper",
    }

    _METHOD_DICT = {
        'in_person': 1,
        'phone': 2,
        'sms': 3,
        'web_direct': 4,
        'web_assisted': 5,
        'mobile_direct': 6,
        'mobile_assisted': 7,
        'paper_direct': 8,
        'paper_assisted': 9
    }

    @classmethod
    def get_by_name(cls, method_name):
        return cls._METHOD_DICT.get(method_name)

    @classmethod
    def get_name_from_id(cls, method_id):
        return list(cls._METHOD_DICT.keys())[list(cls._METHOD_DICT.values()).index(method_id)]
