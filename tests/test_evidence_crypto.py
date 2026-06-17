"""Tests for evidence encryption-at-rest and integrity (Phase 2 m6)."""
import os
import pytest
from cryptography.fernet import InvalidToken

from app.utils import crypto, evidence_store


def test_sha256_is_over_plaintext():
    data = b'hello evidence'
    assert crypto.sha256_hex(data) == crypto.sha256_hex(b'hello evidence')
    assert crypto.sha256_hex(data) != crypto.sha256_hex(b'tampered')


def test_save_encrypts_and_roundtrips(app):
    with app.app_context():
        data = b'compliance evidence body'
        meta = evidence_store.save_evidence_file(data, 'report.pdf')
        try:
            # on-disk bytes are NOT the plaintext
            path = evidence_store.storage_path(meta['storage_name'])
            with open(path, 'rb') as f:
                on_disk = f.read()
            assert on_disk != data
            # storage name is not the user's filename (no traversal / collisions)
            assert meta['storage_name'] != 'report.pdf'
            assert '/' not in meta['storage_name'] and '..' not in meta['storage_name']
            # hash is over the plaintext
            assert meta['content_hash'] == crypto.sha256_hex(data)
            assert meta['size'] == len(data)
            # decrypt returns the original
            assert evidence_store.load_evidence_file(meta['storage_name']) == data
        finally:
            evidence_store.delete_evidence_file(meta['storage_name'])


def test_tampered_file_fails_integrity(app):
    with app.app_context():
        meta = evidence_store.save_evidence_file(b'original', 'a.txt')
        path = evidence_store.storage_path(meta['storage_name'])
        try:
            with open(path, 'wb') as f:
                f.write(b'corrupted-ciphertext')
            with pytest.raises(InvalidToken):
                evidence_store.load_evidence_file(meta['storage_name'])
        finally:
            evidence_store.delete_evidence_file(meta['storage_name'])
