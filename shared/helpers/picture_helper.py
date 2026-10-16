import os
import shutil
from PIL import Image, ImageOps, ExifTags
from config import RECEIPT_PICTURES_PATH, CONTENT_PATH, \
    ALLOWED_EXTENSIONS, PICTURE_PATH
from shared.helpers.exif_gps import get_lat_lon, get_exif_data


def getGPSCoordinatesFromPicture(image):
    exif_data = get_exif_data(image)
    lat = get_lat_lon(exif_data)[0]
    lon = get_lat_lon(exif_data)[1]
    if lat and lon:
        return [lat, lon]
    else:
        return None


def getPictureFullpath(upload_id, upload_folder=None):
    full_upload_folder = getPictureFolder(upload_folder)
    return os.path.join(full_upload_folder, upload_id + '.jpg')


def getPictureFolder(upload_folder=None):
    if upload_folder:
        return CONTENT_PATH + upload_folder + '/'
    else:
        return PICTURE_PATH


def getPicture(upload_id, upload_folder=None):
    if upload_id is not None and upload_id != '':
        picture_fullpath = getPictureFullpath(upload_id, upload_folder)
        return Image.open(picture_fullpath)
    else:
        return None


def storePicture(upload_id, upload_folder=None, fixOrientation=True):
    dest = getPictureFullpath(upload_id, upload_folder)
    src_path = os.path.join(CONTENT_PATH, upload_id + '.jpg')
    if not os.path.isfile(dest):
        if not os.path.isfile(src_path):
            return None
        else:
            shutil.move(src_path, dest)
    image = Image.open(dest)
    # To fix image rotation issue
    if fixOrientation:
        fixPictureOrientation(image)

    return image


def fixPictureOrientation(image):
    for orientation in ExifTags.TAGS.keys():
        if ExifTags.TAGS[orientation] == 'Orientation':
            break

    if image._getexif():
        exif = dict(image._getexif().items())

        if orientation in exif:
            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)
    return image


def allowed_file(f_name):
    return '.' in f_name and f_name.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def picture_uploaded(pic_id):
    picture_filename = pic_id + '.jpg'
    picture_fullpath = os.path.join(RECEIPT_PICTURES_PATH, picture_filename)

    thumbnail_filename = 'small/' + pic_id + '.jpg'
    thumbnail_fullpath = os.path.join(RECEIPT_PICTURES_PATH, thumbnail_filename)

    content_temp_path_for_pic = os.path.join(CONTENT_PATH, pic_id + '.jpg')
    if os.path.isfile(picture_fullpath):
        os.remove(picture_fullpath)

    shutil.move(content_temp_path_for_pic, picture_fullpath)
    image = Image.open(picture_fullpath)

    # To fix image rotation issue
    for orientation in ExifTags.TAGS.keys():
        if ExifTags.TAGS[orientation] == 'Orientation':
            break

    if image._getexif():
        exif = dict(image._getexif().items())

        if orientation in exif:
            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)

    # To make the thumbnail
    size = (512, 512)
    thumb = ImageOps.fit(image, size, Image.LANCZOS)
    thumb.save(thumbnail_fullpath)

    return os.path.isfile(picture_fullpath) and os.path.isfile(thumbnail_fullpath)
