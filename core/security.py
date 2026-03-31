import hashlib
import os
from typing import Any, Optional, Dict

from dotenv import load_dotenv

try:
    # Fernet provides authenticated symmetric encryption (encrypt/decrypt with a key)
    from cryptography.fernet import Fernet, InvalidToken  # type: ignore
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore
    InvalidToken = Exception  # type: ignore


# Load .env next to this module so encryption can work in dev.
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))


def _get_fernet() -> Optional[Any]:
    """
    Returns a Fernet instance if `DATA_ENCRYPTION_KEY` exists.
    Fernet key is a base64-encoded 32-byte key.
    """
    if Fernet is None:
        return None
    key = os.getenv("DATA_ENCRYPTION_KEY")
    if not key:
        return None
    # Fernet expects bytes
    return Fernet(key.encode("utf-8"))


def require_fernet():
    f = _get_fernet()
    if f is None:
        raise RuntimeError("DATA_ENCRYPTION_KEY not configured or cryptography not available")
    return f


def hash_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    norm = str(value).strip()
    if not norm:
        return None
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def generate_salt(length: int = 16) -> str:
    return os.urandom(length).hex()


def hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = generate_salt()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${{dk.hex()}}"


def verify_password(stored: str, provided: str) -> bool:
    try:
        salt, hash_hex = stored.split("$", 1)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", provided.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return dk.hex() == hash_hex


def generate_session_id() -> str:
    import uuid

    return uuid.uuid4().hex


def encrypt_value(value: Optional[str], *, require_key: bool = False) -> Optional[str]:
    if value is None:
        return None
    norm = str(value).strip()
    if norm == "":
        return ""

    f = _get_fernet()
    if f is None:
        if require_key:
            raise RuntimeError(
                "Encryption is not ready. Ensure DATA_ENCRYPTION_KEY is set and `cryptography` is installed."
            )
        # fallback: store plaintext (keeps existing behavior)
        return norm

    return f.encrypt(norm.encode("utf-8")).decode("utf-8")


def decrypt_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)

    f = _get_fernet()
    if f is None:
        return value

    try:
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Legacy plaintext value or wrong key -> return as-is
        return value


def mask_cccd(cccd_full: Optional[str]) -> str:
    if not cccd_full:
        return ""
    s = str(cccd_full).strip()
    # Keep digits only for masking consistency (but do not reformat)
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return ""
    if len(digits) <= 4:
        return digits[0] + ("*" * max(0, len(digits) - 2)) + digits[-1]
    # e.g. 12 digits -> 3 first, 3 last, middle masked
    return f"{digits[:3]}{'*' * (len(digits) - 6)}{digits[-3:]}"


def tenant_doc_to_ui(tenant_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert raw Mongo tenant document (possibly encrypted/legacy plaintext)
    into a template-friendly dict.
    """
    cccd_full = decrypt_value(tenant_doc.get("cccd")) or ""
    phone_full = decrypt_value(tenant_doc.get("phone")) or ""
    return {
        "id": str(tenant_doc.get("_id")),
        "full_name": tenant_doc.get("full_name"),
        "phone": phone_full,
        "cccd": mask_cccd(cccd_full),
        "cccd_full": cccd_full,
        # keep other fields if needed later
        "gender": tenant_doc.get("gender"),
        "birth_year": tenant_doc.get("birth_year"),
        "rental_status": tenant_doc.get("rental_status", "Đã kết thúc"),
    }
