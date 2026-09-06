"""Encryption at rest for uploaded evidence files, on either local disk
or S3 — see EVIDENCE_STORAGE_BACKEND below for which one is active.

Files are encrypted with Fernet (AES-128-CBC + HMAC, from the
`cryptography` package) before they touch storage, and transparently
decrypted on read. There's one master key in EVIDENCE_ENCRYPTION_KEY,
but the key actually used to encrypt/decrypt a given file is derived
per-tenant from it via HKDF, keyed on the tenant's schema name — so a
compromised key for one tenant's files doesn't help decrypt any other
tenant's, and doesn't reveal the master key either (HKDF is one-way).
This is a meaningful step beyond "one key for everyone" without adding
a KMS or per-tenant secret storage to operate.

This only protects file *content*. Filenames and directory structure
(evidence/%Y/%m/...) are still visible to whatever holds the storage
credentials — don't put anything sensitive in a filename.
"""
import base64
import io

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import connection


def _master_key_bytes():
    key = getattr(settings, 'EVIDENCE_ENCRYPTION_KEY', None)
    if not key:
        raise ImproperlyConfigured(
            'EVIDENCE_ENCRYPTION_KEY must be set to encrypt/decrypt evidence files.'
        )
    key_bytes = key.encode() if isinstance(key, str) else key
    return base64.urlsafe_b64decode(key_bytes)


def _derive_key(schema_name):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    hkdf = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None,
        info=f'evidence-encryption:{schema_name}'.encode(),
    )
    derived = hkdf.derive(_master_key_bytes())
    return base64.urlsafe_b64encode(derived)


def _get_fernet():
    # Imported lazily: `cryptography` needs a compiled extension that isn't
    # always available (e.g. no prebuilt wheel yet for a given Python build),
    # and nothing should fail to import core.models over it — only an actual
    # file save/read needs this.
    from cryptography.fernet import Fernet

    schema_name = getattr(connection, 'schema_name', None) or 'public'
    return Fernet(_derive_key(schema_name))


def _get_legacy_fernet():
    """Pre-per-tenant-derivation behavior: the master key used directly,
    the same for every tenant. Only consulted as a read fallback, for
    files encrypted before this derivation scheme existed — never used
    to encrypt anything new."""
    from cryptography.fernet import Fernet

    key = getattr(settings, 'EVIDENCE_ENCRYPTION_KEY', None)
    return Fernet(key) if key else None


def encrypt_text(plaintext):
    """Encrypts a short string (e.g. a third-party API credential for
    Integration.encrypted_credentials) with the same per-tenant derived
    key as evidence files — a compromised key for one tenant doesn't
    help decrypt another's, and a credential is at least as sensitive as
    a file, so it gets the same protection rather than a separate,
    weaker scheme."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_text(ciphertext):
    return _get_fernet().decrypt(ciphertext.encode()).decode()


class EncryptedStorageMixin:
    """The encrypt-on-save / decrypt-on-open behavior, independent of
    where bytes actually end up (local disk vs. S3) — mixed into a real
    Storage backend below rather than duplicated per backend."""

    def _save(self, name, content):
        fernet = _get_fernet()
        raw = content.read()
        encrypted = fernet.encrypt(raw)
        return super()._save(name, ContentFile(encrypted))

    def _open(self, name, mode='rb'):
        from cryptography.fernet import InvalidToken

        f = super()._open(name, mode)
        try:
            encrypted = f.read()
        finally:
            f.close()

        try:
            decrypted = _get_fernet().decrypt(encrypted)
        except InvalidToken:
            legacy = _get_legacy_fernet()
            try:
                decrypted = legacy.decrypt(encrypted) if legacy else encrypted
            except InvalidToken:
                # Not encrypted under either scheme (e.g. a file written
                # before encryption was wired up at all) — surface it
                # as-is rather than failing outright.
                decrypted = encrypted
        return io.BytesIO(decrypted)


class EncryptedFileSystemStorage(EncryptedStorageMixin, FileSystemStorage):
    pass


def get_evidence_storage():
    """Returns the configured Evidence storage backend — S3 if
    AWS_STORAGE_BUCKET_NAME is set (production-appropriate: multiple app
    server replicas all need the same files, which local disk can't give
    them), local disk otherwise (the zero-config default for a single-
    container dev setup). Called lazily from core.models.Evidence's field
    definition rather than importing django-storages/boto3 at module load
    time — neither needs to exist at all unless S3 is actually configured.
    """
    if not getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None):
        return EncryptedFileSystemStorage()

    from storages.backends.s3boto3 import S3Boto3Storage

    class EncryptedS3Storage(EncryptedStorageMixin, S3Boto3Storage):
        pass

    return EncryptedS3Storage()
