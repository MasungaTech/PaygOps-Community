from flask import request, send_file, jsonify, abort
from flask_login import login_required
from pony import orm
from shared.file_upload.web_app import file_upload
from shared.file_upload.services.stored_file_service import StoredFileService, StoredFileType


@login_required
@file_upload.route('/upload/picture/', methods=['POST'])
@file_upload.route('/upload/picture/<picture_uuid>', methods=['POST'])
@orm.db_session
def upload_picture(picture_uuid=None):
    picture = request.files.get('pic')
    picture_object = StoredFileService.create_with_file(picture, StoredFileType.PICTURE, picture_uuid)
    if picture_object:
        return picture_object.uuid
    return jsonify({'error': 'NO_PICTURE_UPLOADED'})


@login_required
@file_upload.route('/pictures/<picture_uuid>.jpg', methods=['GET'])
@orm.db_session
def download_picture(picture_uuid):
    file = StoredFileService.get_from_uuid(picture_uuid)
    if not file or not file.is_found():
        abort(404)
    if file.type != StoredFileType.PICTURE:
        return jsonify({'error': 'NOT_A_PICTURE'})
    if not file.available:
        return jsonify({'error': 'NOT_AVAILABLE'})
    filepath = file.get_file_path()
    return send_file(filepath)


@login_required
@file_upload.route('/pictures/thumbnail/<picture_uuid>.jpg', methods=['GET'])
@orm.db_session
def download_picture_thumbnail(picture_uuid):
    file = StoredFileService.get_from_uuid(picture_uuid)
    if not file or not file.is_found():
        abort(404)
    if file.type != StoredFileType.PICTURE:
        return jsonify({'error': 'NOT_A_PICTURE'})
    if not file.available:
        return jsonify({'error': 'NOT_AVAILABLE'})
    filepath = file.get_thumbnail_path()
    return send_file(filepath)
