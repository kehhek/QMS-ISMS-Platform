"""Deleting anything is admin-only, platform-wide (see
tenants/permissions.py's _delete_requires_admin) — a stricter floor
underneath every ViewSet's own allowed_roles, not something each one
opts into separately. Exercised against a handful of representative
ViewSets rather than exhaustively all of them, since the enforcement
lives in one shared place (HasTenantRole/HasTenantRoleStrict), not
duplicated per view."""

from django.contrib.auth import get_user_model
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


class DeleteRequiresAdminTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('deleteadmintest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'del_admin', Membership.Role.ADMIN)
        self.auditor = make_member(self.tenant, 'del_auditor', Membership.Role.AUDITOR)
        self.plain_user = make_member(self.tenant, 'del_user', Membership.Role.USER)

    def _api_as(self, user):
        api = APIClient()
        api.force_authenticate(user=user)
        return api

    # Risk: allowed_roles = ['admin', 'user'] — 'user' can create/update
    # a risk but, since this session, never delete one.
    def test_plain_user_can_create_and_update_a_risk_but_not_delete_it(self):
        api = self._api_as(self.plain_user)
        create = api.post('/api/risks/', {'name': 'A risk'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(create.status_code, 201, create.data)
        risk_id = create.data['id']

        update = api.patch(f'/api/risks/{risk_id}/', {'owner': 'someone'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(update.status_code, 200, update.data)

        delete = api.delete(f'/api/risks/{risk_id}/', HTTP_HOST=self.host)
        self.assertEqual(delete.status_code, 403)

    def test_auditor_also_cannot_delete_a_risk(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Risk
            risk = Risk.objects.create(name='Another risk')

        api = self._api_as(self.auditor)
        resp = api.delete(f'/api/risks/{risk.pk}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_still_delete_a_risk(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Risk
            risk = Risk.objects.create(name='Admin-deletable risk')

        api = self._api_as(self.admin)
        resp = api.delete(f'/api/risks/{risk.pk}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 204)

    # CorrectiveAction: allowed_roles includes admin/auditor/user for
    # everything else, but delete is still admin-only now.
    def test_plain_user_cannot_delete_a_corrective_action(self):
        with schema_context(self.tenant.schema_name):
            from core.models import CorrectiveAction
            capa = CorrectiveAction.objects.create(title='A CAPA')

        api = self._api_as(self.plain_user)
        resp = api.delete(f'/api/corrective-actions/{capa.pk}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    # Document: uses AuditLoggingMixin's default perform_destroy with no
    # extra check of its own — proves the permission-layer fix covers
    # ViewSets that never had any explicit delete-time role check at all.
    def test_plain_user_cannot_delete_a_document(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Document
            document = Document.objects.create(title='A document')

        api = self._api_as(self.plain_user)
        resp = api.delete(f'/api/documents/{document.pk}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    # A superuser bypasses this the same way it bypasses every other
    # role check — not an admin Membership, but still allowed.
    def test_superuser_can_delete_without_any_membership(self):
        superuser = User.objects.create_superuser('del_super', 'super@example.com', 'pass12345')
        with schema_context(self.tenant.schema_name):
            from core.models import Risk
            risk = Risk.objects.create(name='Superuser-deletable risk')

        api = self._api_as(superuser)
        resp = api.delete(f'/api/risks/{risk.pk}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 204)
