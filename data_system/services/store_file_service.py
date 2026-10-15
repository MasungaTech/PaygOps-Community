import os
from uuid import uuid1
import config


def store_file(file):
    if file:
        extension = os.path.splitext(file.filename)[1]
        filename = str(uuid1())+extension
        filepath = os.path.join(config.CONTENT_PATH, filename)
        file.save(filepath)
        return filename
    else:
        return False