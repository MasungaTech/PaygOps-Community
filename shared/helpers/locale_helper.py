import locale
import json
from config import CURRENT_DIR
import os

def get_all_available_currencies_from_installed_locales():
    currencies = {}
    locales = locale.locale_alias
    for indx in locales:
        loc = locales[indx]
        try:
            locale.setlocale(locale.LC_ALL, loc)
        except Exception as e:
            print("Exception: "+str(e)+". Locale string: "+str(loc))
            continue
        locale_conv = locale.localeconv()
        currency_name = locale_conv.get('int_curr_symbol', '').strip()
        currency_symbol = locale_conv.get('currency_symbol', '')
        if currency_name:
            currencies[currency_name] = currency_symbol
        
    return currencies

def get_all_available_currencies_from_json():
    currencies = {}
    file_path = os.path.join(CURRENT_DIR+'/shared/helpers/', "iso-4217-currency-codes.json")
    with open(file_path) as json_file:
        data = json.load(json_file)
        for currency in data:
            currency_code = currency.get("Alphabetic_Code")
            currency_name = currency.get("Currency")
            if currency_code:
                currencies[currency_code] = currency_name + " (" + currency_code + ")"
    return currencies