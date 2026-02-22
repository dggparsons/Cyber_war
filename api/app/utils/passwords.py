"""Password helpers."""
from __future__ import annotations

import secrets
import string

from werkzeug.security import check_password_hash, generate_password_hash


PASSWORD_ALPHABET = string.ascii_letters + string.digits + "-_"


def generate_random_password(length: int = 16) -> str:
    if length < 8:
        raise ValueError("Password length must be >= 8")
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)
