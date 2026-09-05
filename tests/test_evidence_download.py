"""EvidenceViewSet.download — a proper authenticated stream of the
decrypted file, replacing exposure of the storage backend's own URL
(local disk's /media/ has no auth check at all; a private S3 object
can't be handed out as a plain link either)."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from tenants.models import Client, Domain, Membership

User = get_user_model()


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


class EvidenceDownloadTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('evdownload')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = User.objects.create_user('ev_user', 'ev@example.com', 'pass12345')
        Membership.objects.create(user=self.user, tenant=self.tenant, role=Membership.Role.USER)

        with schema_context(self.tenant.schema_name):
            from core.models import Document, Evidence
            self.document = Document.objects.create(title='Doc for evidence')
            self.evidence = Evidence.objects.create(
                title='Proof',
                file=SimpleUploadedFile('proof.txt', b'this is the real evidence content'),
                content_type=ContentType.objects.get_for_model(Document),
                object_id=self.document.pk,
                uploaded_by=self.user,
            )

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_the_api_serializer_points_at_the_download_action_not_a_storage_url(self):
        resp = self.api.get('/api/evidence/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        entry = resp.data['results'][0]
        self.assertEqual(entry['file'], f'/api/evidence/{self.evidence.pk}/download/')

    def test_download_returns_the_original_decrypted_content(self):
        resp = self.api.get(f'/api/evidence/{self.evidence.pk}/download/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        content = b''.join(resp.streaming_content)
        self.assertEqual(content, b'this is the real evidence content')
        self.assertIn('attachment', resp['Content-Disposition'])

    def test_download_requires_tenant_membership(self):
        outsider = User.objects.create_user('ev_outsider', 'o@example.com', 'pass12345')
        api = APIClient()
        api.force_authenticate(user=outsider)
        resp = api.get(f'/api/evidence/{self.evidence.pk}/download/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_download_requires_authentication(self):
        api = APIClient()
        resp = api.get(f'/api/evidence/{self.evidence.pk}/download/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 401)
