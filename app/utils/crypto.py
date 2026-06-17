"""Symmetric encryption + hashing for evidence at rest (ADR 0003).

Single place that reads the Fernet key(s) from config. Uses MultiFernet so the
primary key encrypts and any older keys can still decrypt — key rotation is then
a config change, not a data migration.

Honest threat model: this protects a stolen disk or backup. It does NOT protect
against an attacker who already has application + environment access, because they
hold the key. State that boundary accurately in any compliance pack.
"""
import hashlib
from flask import current_app
from cryptography.fernet import Fernet, MultiFernet


def sha256_hex(data: bytes) -> str:
    """Hex sha256 of the given bytes (always over plaintext)."""
    return hashlib.sha256(data).hexdigest()


def _get_multifernet() -> MultiFernet:
    primary = current_app.config.get('EVIDENCE_ENCRYPTION_KEY')
    if not primary:
        raise RuntimeError('EVIDENCE_ENCRYPTION_KEY is not configured')
    keys = [primary]
    old = current_app.config.get('EVIDENCE_ENCRYPTION_KEYS_OLD', '') or ''
    keys.extend(k.strip() for k in old.split(',') if k.strip())
    return MultiFernet([Fernet(k.encode() if isinstance(k, str) else k) for k in keys])


def encrypt_bytes(data: bytes) -> bytes:
    return _get_multifernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    """Decrypt; raises cryptography.fernet.InvalidToken if tampered or wrong key."""
    return _get_multifernet().decrypt(token)
