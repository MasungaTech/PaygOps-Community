def format_thousands(amount):
    return "{:,}".format(amount)

def round_if_exists(number, decimals=2):
    if number is None:
        return number
    return round(number, decimals)

def round_if_needed(number, decimals=2):
    if number % 1: # The number is not whole
        return round(number, decimals)
    return round(number, 0)

def float_if_exists(number):
    if number is not None:
        return float(number)
    return number