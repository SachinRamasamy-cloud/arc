import pytest
from pydantic import ValidationError

from foundation.config.settings import Settings
from foundation.crypto.security import (
    password_hash, password_matches, seal, signed_token, totp_code,
    totp_step, unseal, verify_signed,
)
from foundation.errors.public import PublicError


def test_passwords_are_hashed_and_verified():
    password = "foundation-test-passphrase"
    hashed = password_hash(password)
    assert password != hashed
    assert password_matches(hashed, password)
    assert not password_matches(hashed, "incorrect-passphrase")


def test_ciphertext_is_bound_to_its_purpose(settings):
    encrypted = seal("private-value", settings, "totp")
    assert unseal(encrypted, settings, "totp") == "private-value"
    with pytest.raises(PublicError):
        unseal(encrypted, settings, "mail")


@pytest.mark.parametrize("change", ["tamper", "purpose", "expired"])
def test_signed_tokens_reject_invalid_claims(settings, change):
    payload = {"purpose": "verify", "exp": 4102444800}
    if change == "expired":
        payload["exp"] = 0
    value = signed_token(payload, settings)
    if change == "tamper":
        value += "x"
    with pytest.raises(PublicError) as denied:
        verify_signed(value, settings, "reset" if change == "purpose" else "verify")
    assert denied.value.code == "INVALID_TOKEN"


def test_authenticator_matches_rfc_vector_and_rejects_replay():
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert totp_code(secret, at=59, digits=8) == "94287082"
    code = totp_code(secret, at=59)
    assert totp_step(secret, code, at=59) == 1
    assert totp_step(secret, code, last=1, at=59) is None


def test_unqualified_production_configuration_is_rejected(settings):
    with pytest.raises(ValidationError, match="Production blocked"):
        Settings(_env_file=None, env="production", secret_key=settings.secret_key, encryption_key=settings.encryption_key)
