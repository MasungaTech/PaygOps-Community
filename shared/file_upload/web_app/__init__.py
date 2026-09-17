from flask import Blueprint

file_upload = Blueprint('file_upload', __name__)

from . import views
