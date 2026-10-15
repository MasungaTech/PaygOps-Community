from flask import Blueprint

message = Blueprint('message',
                    __name__,
                    template_folder='templates',
                    static_folder='static')

from . import list_message, add_message_manually, custom_messages
