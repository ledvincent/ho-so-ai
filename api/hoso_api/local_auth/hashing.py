"""Password hashing for the explicit local checkpoint, not a deployment IdP.

OWASP Password Storage Cheat Sheet: scrypt N=2**17, r=8, p=1. No additional
dependency is needed. Two concurrent derivations bound memory consumption.
"""

import hashlib
import hmac
import secrets
from threading import BoundedSemaphore

SCRYPT_N = 2**17
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
HASH_BYTES = 32
_workers = BoundedSemaphore(2)


def derive_password(password: str, salt: bytes) -> bytes:
    if not isinstance(password, str) or not 1 <= len(password.encode("utf-8")) <= 1024:
        raise ValueError("Invalid password length.")
    if not isinstance(salt, bytes) or len(salt) != SALT_BYTES:
        raise ValueError("Invalid password salt.")
    with _workers:
        return hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
            dklen=HASH_BYTES, maxmem=256 * 1024 * 1024,
        )


def hash_password(password: str) -> tuple[bytes, bytes]:
    salt = secrets.token_bytes(SALT_BYTES)
    return salt, derive_password(password, salt)


def check_password(password: str, salt: bytes, expected: bytes) -> bool:
    return hmac.compare_digest(derive_password(password, salt), expected)
