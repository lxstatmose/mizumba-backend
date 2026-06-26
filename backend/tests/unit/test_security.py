from app.core.security import (
    TokenType,
    create_access_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    password_hash = hash_password("password123")

    assert password_hash != "password123"
    assert verify_password("password123", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_contains_expected_claims() -> None:
    token = create_access_token("user-id")
    payload = decode_token(token)

    assert payload["sub"] == "user-id"
    assert payload["type"] == TokenType.ACCESS.value
    assert payload["jti"]


def test_hash_token_is_stable_and_not_plaintext() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != "abc"
