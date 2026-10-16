import random


class PasswordGenerator:

    PASS_LENGTH = 8
    PASS_CHARSET = 'abcdefghijklmnopqrstuvwxyz' \
                   'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                   '0123456789' '!@#?[]%*'

    @classmethod
    def generate_password(cls):
        return ''.join(random.choice(cls.PASS_CHARSET) for i in range(cls.PASS_LENGTH))
