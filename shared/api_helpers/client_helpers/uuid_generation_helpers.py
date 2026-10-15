import random


def generate_uuid():
    return ''.join(random.choice('0123456789abcdef') for i in range(8)) + '-' + ''\
           .join(random.choice('0123456789abcdef') for i in range(8)) + '-' + ''\
           .join(random.choice('0123456789abcdef') for i in range(8))