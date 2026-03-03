"""
Security utilities.

Responsibilities:
- Password hashing and verification (argon2)
- Constant-time comparisons where needed

Non-responsibilities:
- No RBAC decisions
- No session/auth token issuance (handled in services)
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Tuned defaults (reasonable for team internal apps).
# You can tighten these later based on your infra and latency tolerance.
_PH = PasswordHasher(
    time_cost=2,      # iterations
    memory_cost=102400,  # 100 MiB
    parallelism=8,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using Argon2id.

    Args:
        plain_password: plaintext password

    Returns:
        Argon2 hash string.
    """
    if not plain_password or len(plain_password) < 8:
        # Keep policy minimal here; UI/services can enforce richer policies.
        raise ValueError("Password must be at least 8 characters long.")
    return _PH.hash(plain_password)


def verify_password(password_hash: str, plain_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2 hash.

    Returns:
        True if matches, False otherwise.
    """
    try:
        return _PH.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False