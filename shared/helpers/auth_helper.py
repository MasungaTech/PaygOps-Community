import hashlib
import re

from flask import g
from pony.orm import db_session
from werkzeug.security import check_password_hash, generate_password_hash

from core_system.core_entities import db

LEGACY_HASH_PATTERN = re.compile(r'^[0-9a-f]{64}$')
PASSWORD_HASH_METHOD = 'pbkdf2:sha256:600000'


@db_session
def getCurrentUser():
    return db.User.get(id=g.user.id)


def legacy_sha256(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def is_legacy_password_hash(stored_hash):
    return bool(stored_hash and LEGACY_HASH_PATTERN.match(stored_hash))


def encode_password(password):
    return generate_password_hash(password, method=PASSWORD_HASH_METHOD)


def encode_plaintext_password(plaintext_password):
    """Store a plaintext password for web login.

    The login form SHA-256s the typed password before POST, so plaintext
    passwords (reset email, env setup, autogen) must be hashed the same way
    before the salted encode step.
    """
    return encode_password(legacy_sha256(plaintext_password))


def verify_password(stored_hash, password_to_check):
    if is_legacy_password_hash(stored_hash):
        return stored_hash == legacy_sha256(password_to_check)
    return check_password_hash(stored_hash, password_to_check)


def upgrade_password_hash_if_legacy(user, password_to_check):
    if is_legacy_password_hash(user.password):
        user.password = encode_password(password_to_check)


def authenticate_password(password_to_check, user):
    if not user or not verify_password(user.password, password_to_check):
        return False
    upgrade_password_hash_if_legacy(user, password_to_check)
    return True


def isPasswordValidForUser(passwordToCheck, user):
    return verify_password(user.password, passwordToCheck)


def verify_api_key_password(user, plaintext_password):
    inner_hash = legacy_sha256(plaintext_password)
    if authenticate_password(inner_hash, user):
        return True
    return authenticate_password(plaintext_password, user)
