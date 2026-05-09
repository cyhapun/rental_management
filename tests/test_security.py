import os
import hashlib
import pytest

from core import security


def test_hash_value_none_and_empty():
    assert security.hash_value(None) is None
    assert security.hash_value("") is None
    assert security.hash_value("  abc  ") == hashlib.sha256(b"abc").hexdigest()


def test_generate_salt_length():
    salt = security.generate_salt()
    assert isinstance(salt, str)
    # default length=16 -> hex length 32
    assert len(salt) == 32


def test_hash_and_verify_password():
    pw = "mysecret123"
    hashed = security.hash_password(pw)
    assert isinstance(hashed, str)
    assert "$" in hashed
    assert security.verify_password(hashed, pw) is True
    assert security.verify_password(hashed, "wrong") is False


def test_hash_password_with_salt():
    salt = "a" * 32
    hashed = security.hash_password("pw", salt)
    assert hashed.startswith(salt + "$")
    assert security.verify_password(hashed, "pw")


def test_generate_session_id():
    sid = security.generate_session_id()
    assert isinstance(sid, str)
    assert len(sid) == 32


def test_encrypt_decrypt_no_key(monkeypatch):
    # Ensure no DATA_ENCRYPTION_KEY is present
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    # When Fernet/key not available, encrypt_value should fallback to plaintext
    assert security.encrypt_value("hello") == "hello"
    assert security.decrypt_value("hello") == "hello"
    assert security.encrypt_value("") == ""
    assert security.encrypt_value(None) is None
    assert security.decrypt_value(None) is None


def test_encrypt_decrypt_with_key(monkeypatch):
    # Skip if cryptography not installed in test environment
    pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", key.decode())

    s = "secret-token"
    enc = security.encrypt_value(s)
    assert enc != s
    dec = security.decrypt_value(enc)
    assert dec == s


def test_verify_password_malformed():
    assert security.verify_password("not-a-valid-hash", "pw") is False


def test_mask_cccd_examples():
    assert security.mask_cccd(None) == ""
    assert security.mask_cccd("") == ""
    assert security.mask_cccd("abc") == ""
    assert security.mask_cccd("1234") == "1**4"
    long_cccd = "012345678901"
    assert security.mask_cccd(long_cccd) == "012" + ("*" * (len(long_cccd) - 6)) + "901"


def test_tenant_doc_to_ui(monkeypatch):
    # Ensure decrypt_value is identity for this test by removing key
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    tenant = {
        "_id": "abc123",
        "full_name": "Nguyen Van A",
        "phone": "0123456789",
        "cccd": "012345678901",
        "gender": "M",
        "birth_year": 1990,
        "rental_status": "Đang thuê",
    }
    ui = security.tenant_doc_to_ui(tenant)
    assert ui["id"] == str(tenant["_id"]) 
    assert ui["full_name"] == tenant["full_name"]
    assert ui["phone"] == tenant["phone"]
    assert ui["cccd_full"] == tenant["cccd"]
    assert ui["cccd"] == security.mask_cccd(tenant["cccd"])
    assert ui["rental_status"] == "Đang thuê"
