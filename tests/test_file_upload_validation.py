"""Server-side file-upload guards (core/validators.py) — before this,
Document/Evidence/TrainingVideo/SupplierAgreement accepted any file
type or size at all via the API; the frontend's `accept="..."` on a
file input is cosmetic only and does nothing to a direct request."""

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


def make_member(tenant, username, role):
    user = User.objects.create_user(username, f'{username}@example.com', 'pass12345')
    Membership.objects.create(user=user, tenant=tenant, role=role)
    return user


class DocumentUploadValidationTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('fileuploadtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'upload_user', Membership.Role.USER)
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_rejects_a_disallowed_extension(self):
        resp = self.api.post(
            '/api/documents/',
            {'title': 'Malicious', 'file': SimpleUploadedFile('payload.exe', b'MZ...')},
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn('file', resp.data)

    def test_rejects_an_oversized_file(self):
        too_big = SimpleUploadedFile('big.pdf', b'x' * (26 * 1024 * 1024))
        resp = self.api.post(
            '/api/documents/', {'title': 'Too Big', 'file': too_big},
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn('file', resp.data)

    def test_accepts_a_valid_pdf_within_the_size_limit(self):
        resp = self.api.post(
            '/api/documents/',
            {'title': 'Fine', 'file': SimpleUploadedFile('policy.pdf', b'%PDF-1.4 real-enough content')},
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)


class EvidenceUploadValidationTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('evidenceuploadtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'ev_upload_user', Membership.Role.USER)
        from core.models import Risk
        with schema_context(self.tenant.schema_name):
            self.risk = Risk.objects.create(name='Some risk')
        self.risk_ct_id = ContentType.objects.get_for_model(Risk).id
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_rejects_a_disallowed_extension(self):
        resp = self.api.post(
            '/api/evidence/',
            {
                'title': 'Bad', 'content_type': self.risk_ct_id, 'object_id': self.risk.pk,
                'file': SimpleUploadedFile('script.sh', b'#!/bin/sh\necho hi'),
            },
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn('file', resp.data)

    def test_accepts_a_screenshot(self):
        resp = self.api.post(
            '/api/evidence/',
            {
                'title': 'Good', 'content_type': self.risk_ct_id, 'object_id': self.risk.pk,
                'file': SimpleUploadedFile('shot.png', b'fake-png-bytes'),
            },
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)


class TrainingVideoUploadValidationTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('videouploadtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'video_admin', Membership.Role.ADMIN)
        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    def test_rejects_a_non_video_extension(self):
        resp = self.api.post(
            '/api/training-videos/',
            {'title': 'Not a video', 'file': SimpleUploadedFile('notes.pdf', b'%PDF-1.4')},
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn('file', resp.data)

    def test_accepts_an_mp4(self):
        resp = self.api.post(
            '/api/training-videos/',
            {'title': 'Real video', 'file': SimpleUploadedFile('clip.mp4', b'fake-mp4-bytes')},
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
