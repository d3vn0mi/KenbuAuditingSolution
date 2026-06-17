"""Filesystem storage for evidence artifacts, encrypted at rest.

Files live under <instance>/evidence/, named by a random UUID (never the user's
filename — avoids path traversal and collisions). The plaintext is hashed BEFORE
encryption so the integrity hash proves what was uploaded; on load we decrypt and
the caller can re-hash to verify.
"""
import os
import uuid
from flask import current_app
from . import crypto


def _evidence_dir():
    path = current_app.config.get('EVIDENCE_DIR') or os.path.join(
        current_app.instance_path, 'evidence')
    os.makedirs(path, exist_ok=True)
    return path


def storage_path(storage_name):
    # storage_name is a bare uuid hex (validated on creation); guard anyway.
    if os.path.sep in storage_name or '..' in storage_name:
        raise ValueError('invalid storage name')
    return os.path.join(_evidence_dir(), storage_name)


def save_evidence_file(data: bytes, original_filename: str) -> dict:
    """Hash (plaintext) -> encrypt -> write. Returns metadata for the version row."""
    content_hash = crypto.sha256_hex(data)
    storage_name = uuid.uuid4().hex
    token = crypto.encrypt_bytes(data)
    with open(storage_path(storage_name), 'wb') as f:
        f.write(token)
    return {
        'storage_name': storage_name,
        'content_hash': content_hash,
        'size': len(data),
        'original_filename': original_filename,
    }


def load_evidence_file(storage_name: str) -> bytes:
    """Return decrypted plaintext; raises InvalidToken if tampered."""
    with open(storage_path(storage_name), 'rb') as f:
        token = f.read()
    return crypto.decrypt_bytes(token)


def delete_evidence_file(storage_name: str):
    path = storage_path(storage_name)
    if os.path.exists(path):
        os.remove(path)
