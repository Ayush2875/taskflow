"""
auth.py
-------
Password hashing (bcrypt, called directly) and JWT creation/verification
(python-jose). Kept separate from main.py so the token/crypto logic is
easy to find and test in isolation.

NOTE on the hashing library choice: an earlier version of this used
passlib's CryptContext wrapper around bcrypt, which is the pattern most
tutorials show. It crashed at runtime with a `ValueError: password cannot
be longer than 72 bytes` coming from passlib's own internal self-test —
not from any real password. This is a known, unresolved incompatibility
between passlib (largely unmaintained) and recent bcrypt releases (bcrypt
5.x here). Calling the `bcrypt` package directly avoids passlib's broken
compatibility shim entirely and is the currently-recommended approach.

SECRET_KEY is read from an environment variable, never hardcoded — same
pattern as USE_REAL_LLM elsewhere in this project. A dev-only fallback is
provided so the app still runs locally without extra setup, but it prints
a loud warning so it's never mistaken for something safe to ship.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

if SECRET_KEY == "dev-only-insecure-secret-change-me":
    print(
        "WARNING: JWT_SECRET_KEY is not set — using an insecure default. "
        "Set the JWT_SECRET_KEY environment variable before deploying this anywhere real."
    )


def hash_password(password: str) -> str:
    # bcrypt works on bytes, and has a real (not buggy) 72-byte input limit —
    # truncate deliberately rather than letting bcrypt raise on long input.
    password_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")  # store as a string in the DB


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jose.JWTError if the token is invalid, tampered with, or expired."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

