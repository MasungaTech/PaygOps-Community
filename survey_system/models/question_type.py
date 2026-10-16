from shared.helpers.db_helpers import TypeClassBase

class QuestionType(TypeClassBase):
    group = 0
    yes_no = 1
    text = 2
    numeric = 3
    choice_text = 4
    choice_numeric = 5
    picture = 6
    long_text = 7
    checkbox = 8
    date = 9
    note = 10
    gps = 11
    url = 12
    signature = 13
    gps_surface = 14
    regex = 15
    l0_entity = 16
    date_time = 17

    _human_codes = {
        text: 'Text',
        numeric: 'Numeric',
        long_text: 'Long Text',
        url: 'Url',
        gps: 'GPS',
        date: 'Date',
        gps_surface: 'Surface Mapping',

        picture: 'Picture',
        checkbox: 'Checkbox',
        signature: 'Signature',

        yes_no: 'Boolean',
        choice_text: 'Choice Text',
        choice_numeric: 'Choice Numeric',

        note: 'Note',
        regex: 'RegEx',
        l0_entity: 'L0 Entity',
        date_time: 'Date Time',
    }

    _input_type = {
        text: 'text',
        url: 'url',
        numeric: 'number',
        gps: 'gps',
        long_text: 'textarea',
        date: 'datepicker',
        date_time: 'datetimepicker',
        checkbox: 'checkbox',
        picture: 'picture',
        signature: 'signature',
        gps_surface: 'gps_surface',
        regex: 'regex',
        l0_entity: 'l0_entity'
    }

    @classmethod
    def _get_options_list(cls):
        return cls.keys()+['integer']
    

class PictureType(TypeClassBase):
    generic = 'generic'
    face_picture = 'face_picture'
    id_credit_card_picture = 'id_credit_card_picture'
    passport_picture = 'passport_picture'
    a4_landscape_picture = 'a4_landscape_picture'
    a4_portrait_picture = 'a4_portrait_picture'

    _human_codes = {
        generic: 'Generic',
        face_picture: 'Face Picture',
        id_credit_card_picture: 'ID/Credit Card Picture',
        passport_picture : 'Passport Picture',
        a4_landscape_picture: 'A4 Document Picture (Lanscape)',
        a4_portrait_picture: 'A4 Document Picture (Portrait)',
    }


    @classmethod
    def _get_options_list(cls):
        return cls.keys()
