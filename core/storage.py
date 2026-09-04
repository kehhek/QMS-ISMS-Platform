"""Encryption at rest for uploaded evidence files.

Files are encrypted with Fernet (AES-128-CBC + HMAC, from the
`cryptography` package) before they touch disk, and transparently
decrypted on read. The key lives in EVIDENCE_ENCRYPTION_KEY, never in
the file itself or in the database.

This only protects file *content*. Filenames and directory structure
(evidence/%Y/%m/...) are still visible on disk — don't put anything
sensitive in a filename.
"""
import io

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage


def _get_fernet():
    # Imported lazily: `cryptography` needs a compiled extension that isn't
    # always available (e.g. no prebuilt wheel yet for a given Python build),
    # and nothing should fail to import core.models over it — only an actual
    # file save/read needs this.
    from cryptography.fernet import Fernet

    key = getattr(settings, 'EVIDENCE_ENCRYPTION_KEY', None)
    if not key:
        raise ImproperlyConfigured(
            'EVIDENCE_ENCRYPTION_KEY must be set to encrypt/decrypt evidence files.'
        )
    return Fernet(key)


class EncryptedFileSystemStorage(FileSystemStorage):
    def _save(self, name, content):
        fernet = _get_fernet()
        raw = content.read()
        encrypted = fernet.encrypt(raw)
        return super()._save(name, ContentFile(encrypted))

    def _open(self, name, mode='rb'):
        from cryptography.fernet import InvalidToken

        fernet = _get_fernet()
        f = super()._open(name, mode)
        try:
            encrypted = f.read()
        finally:
            f.close()
        try:
            decrypted = fernet.decrypt(encrypted)
        except InvalidToken:
            # Not encrypted (e.g. a file written before this storage was
            # wired up) — surface it as-is rather than failing outright.
            decrypted = encrypted
        return io.BytesIO(decrypted)
