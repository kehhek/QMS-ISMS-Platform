"""Per-tenant evidence encryption key derivation (core/storage.py) — each
tenant's files are encrypted under a key derived (via HKDF) from the
shared master key + that tenant's schema name, not the master key
directly, so one tenant's key material never helps decrypt another's."""

from django.db import connection
from django.test import TestCase
from django_tenants.utils import schema_context

from tenants.models import Client, Domain


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


class EvidenceEncryptionTests(TestCase):
    def test_a_file_round_trips_through_save_and_read(self):
        from core.storage import EncryptedFileSystemStorage
        from django.core.files.base import ContentFile

        tenant = make_tenant('enctest1')
        with schema_context(tenant.schema_name):
            storage = EncryptedFileSystemStorage()
            name = storage.save('evidence/test1.txt', ContentFile(b'top secret contents'))
            try:
                with storage.open(name) as f:
                    self.assertEqual(f.read(), b'top secret contents')
            finally:
                storage.delete(name)

    def test_the_bytes_on_disk_are_not_plaintext(self):
        from core.storage import EncryptedFileSystemStorage
        from django.core.files.base import ContentFile

        tenant = make_tenant('enctest2')
        with schema_context(tenant.schema_name):
            storage = EncryptedFileSystemStorage()
            name = storage.save('evidence/test2.txt', ContentFile(b'plaintext marker XYZ'))
            try:
                raw_path = storage.path(name)
                with open(raw_path, 'rb') as raw:
                    on_disk = raw.read()
                self.assertNotIn(b'plaintext marker XYZ', on_disk)
            finally:
                storage.delete(name)

    def test_different_tenants_derive_different_keys(self):
        from core.storage import _derive_key

        make_tenant('enctenanta')
        make_tenant('enctenantb')

        with schema_context('enctenanta'):
            key_a = _derive_key(connection.schema_name)
        with schema_context('enctenantb'):
            key_b = _derive_key(connection.schema_name)

        self.assertNotEqual(key_a, key_b)

    def test_a_file_encrypted_for_one_tenant_cannot_be_decrypted_as_another(self):
        from cryptography.fernet import Fernet, InvalidToken
        from core.storage import _derive_key

        make_tenant('enctenantc')
        make_tenant('enctenantd')

        with schema_context('enctenantc'):
            fernet_c = Fernet(_derive_key(connection.schema_name))
            token = fernet_c.encrypt(b'tenant c only')

        with schema_context('enctenantd'):
            fernet_d = Fernet(_derive_key(connection.schema_name))
            with self.assertRaises(InvalidToken):
                fernet_d.decrypt(token)

    def test_a_file_encrypted_under_the_old_global_master_key_still_reads_back(self):
        # Backward compatibility: files encrypted before per-tenant
        # derivation existed used the master key directly. The storage
        # backend must still be able to read those without a manual
        # re-encryption migration.
        from cryptography.fernet import Fernet
        from django.conf import settings
        from core.storage import EncryptedFileSystemStorage

        tenant = make_tenant('enclegacy')
        with schema_context(tenant.schema_name):
            legacy_fernet = Fernet(settings.EVIDENCE_ENCRYPTION_KEY)
            legacy_ciphertext = legacy_fernet.encrypt(b'encrypted the old way')

            storage = EncryptedFileSystemStorage()
            # Write the legacy ciphertext directly to disk, bypassing
            # _save's (new-scheme) encryption, to simulate a pre-existing file.
            from django.core.files.base import ContentFile
            name = storage.get_available_name('evidence/legacy.txt')
            path = storage.path(name)
            import os
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(legacy_ciphertext)

            try:
                with storage.open(name) as f:
                    self.assertEqual(f.read(), b'encrypted the old way')
            finally:
                storage.delete(name)
