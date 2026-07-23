import hashlib
from types import SimpleNamespace

from shared.helpers.auth_helper import (
    authenticate_password,
    encode_password,
    is_legacy_password_hash,
    legacy_sha256,
    verify_api_key_password,
    verify_password,
)


class TestPasswordHashing:

    def test_legacy_sha256_matches_hashlib(self):
        password = 'test1234'
        expected = hashlib.sha256(password.encode('utf-8')).hexdigest()
        assert legacy_sha256(password) == expected

    def test_is_legacy_password_hash(self):
        assert is_legacy_password_hash(legacy_sha256('test1234'))
        assert not is_legacy_password_hash(encode_password('test1234'))
        assert not is_legacy_password_hash('not-a-valid-hash')

    def test_encode_password_uses_unique_salts(self):
        first_hash = encode_password('same-password')
        second_hash = encode_password('same-password')
        assert first_hash != second_hash
        assert not is_legacy_password_hash(first_hash)

    def test_verify_password_accepts_legacy_and_salted_hashes(self):
        legacy_hash = legacy_sha256('secret')
        salted_hash = encode_password('secret')

        assert verify_password(legacy_hash, 'secret')
        assert not verify_password(legacy_hash, 'wrong')
        assert verify_password(salted_hash, 'secret')
        assert not verify_password(salted_hash, 'wrong')

    def test_authenticate_password_upgrades_legacy_hash(self):
        user = SimpleNamespace(password=legacy_sha256('test1234'))

        assert authenticate_password('test1234', user)
        assert not is_legacy_password_hash(user.password)
        assert verify_password(user.password, 'test1234')

    def test_authenticate_password_does_not_change_salted_hash(self):
        original_hash = encode_password('test1234')
        user = SimpleNamespace(password=original_hash)

        assert authenticate_password('test1234', user)
        assert user.password == original_hash

    def test_verify_api_key_password_supports_double_hashed_legacy_passwords(self):
        plaintext = 'api-password'
        user = SimpleNamespace(password=legacy_sha256(legacy_sha256(plaintext)))

        assert verify_api_key_password(user, plaintext)
        assert not is_legacy_password_hash(user.password)
        assert verify_password(user.password, legacy_sha256(plaintext))
