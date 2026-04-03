from pony.orm import db_session
from core_system.core_entities import db
from flask import g
import hashlib


@db_session
def getCurrentUser():
    return db.User.get(id=g.user.id)


def isPasswordValidForUser(passwordToCheck, user):
    return encode_password(passwordToCheck) == user.password


def encode_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
