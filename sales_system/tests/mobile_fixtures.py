class MobileFixtures:
    @classmethod
    def incoming_data(cls):
        return {
            'statusId': 12,
            'name': 'john',
            'surname': 'cobra',
            'generatorCrmId': 1,
            'village': 2,
            'phoneNumber': '0001112224',
            'gender': 'male', #optional
            'generationDate': '2018-11-28T00:00:00.000Z', #optional
            'modifiedDate': '2018-11-28T11:22:33.444Z', #optional
            'homeUse': False, #optional
            'businessUse': True, #optional
            'mobileUuid': 'lead_2018-11-28T16:15:07Z_6', #optional
            '_rev': 'some_rev', #optional
        }
