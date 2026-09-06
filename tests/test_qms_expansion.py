"""Asset Register, CAPA workflow depth (root cause + signed effectiveness
verification at close), Nonconformance intake, Access Review, and
Approval Matrix enforcement — the five features added on top of the
platform's existing (read-only) Access Register and Approval Matrix
reference views."""

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


def make_member(tenant, username, role, password='pass12345'):
    user = User.objects.create_user(username, f'{username}@example.com', password)
    Membership.objects.create(user=user, tenant=tenant, role=role)
    return user


class AssetTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('assettest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'asset_user', Membership.Role.USER)
        self.admin = make_member(self.tenant, 'asset_admin', Membership.Role.ADMIN)

    def test_any_member_can_create_an_asset(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/assets/', {'name': 'Laptop Fleet', 'asset_type': 'hardware', 'sensitivity': 'internal'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        # Defaults to the creator as owner when none given.
        self.assertEqual(resp.data['owner'], self.user.pk)

    def test_create_sets_asset_id_and_status(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/assets/',
            {
                'asset_id': 'AST-014', 'name': 'Prod DB Server', 'asset_type': 'hardware',
                'sensitivity': 'confidential', 'status': 'under_maintenance',
            },
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['asset_id'], 'AST-014')
        self.assertEqual(resp.data['status'], 'under_maintenance')

    def test_status_defaults_to_active(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post('/api/assets/', {'name': 'New Laptop'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['status'], 'active')
        self.assertEqual(resp.data['asset_id'], '')

    def test_plain_user_cannot_edit_an_asset(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Asset
            asset = Asset.objects.create(name='Prod DB', asset_type='data')

        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.patch(f'/api/assets/{asset.pk}/', {'name': 'Renamed'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_edit_an_asset(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Asset
            asset = Asset.objects.create(name='Prod DB', asset_type='data')

        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.patch(f'/api/assets/{asset.pk}/', {'name': 'Renamed'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)

    def test_only_admin_can_delete_an_asset(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Asset
            asset = Asset.objects.create(name='Old Server', asset_type='hardware')

        auditor = make_member(self.tenant, 'asset_auditor', Membership.Role.AUDITOR)
        api = APIClient()
        api.force_authenticate(user=auditor)
        denied = api.delete(f'/api/assets/{asset.pk}/', HTTP_HOST=self.host)
        self.assertEqual(denied.status_code, 403)

        api.force_authenticate(user=self.admin)
        allowed = api.delete(f'/api/assets/{asset.pk}/', HTTP_HOST=self.host)
        self.assertEqual(allowed.status_code, 204)

    def test_risk_can_link_to_an_asset(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Asset
            asset = Asset.objects.create(name='Customer DB', asset_type='data')

        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/risks/', {'name': 'DB breach', 'likelihood': 3, 'impact': 5, 'asset': asset.pk},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['asset'], asset.pk)
        self.assertEqual(resp.data['asset_name'], 'Customer DB')


class AssetReviewTests(TestCase):
    """Dated, attributed evidence that an asset was actually looked at
    (ISO 27001 A.5.9) — same pattern as AccessReview sitting on top of
    the Access Register."""

    def setUp(self):
        self.tenant = make_tenant('assetreviewtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'assetrev_admin', Membership.Role.ADMIN)
        self.plain_user = make_member(self.tenant, 'assetrev_user', Membership.Role.USER)
        with schema_context(self.tenant.schema_name):
            from core.models import Asset
            self.asset = Asset.objects.create(name='Prod DB Server', asset_type='hardware')

    def test_asset_has_no_last_review_before_one_is_recorded(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.get(f'/api/assets/{self.asset.pk}/', HTTP_HOST=self.host)
        self.assertIsNone(resp.data['last_review'])

    def test_plain_user_cannot_record_a_review(self):
        api = APIClient()
        api.force_authenticate(user=self.plain_user)
        resp = api.post(f'/api/assets/{self.asset.pk}/review/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_record_a_review_and_it_shows_as_last_review(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            f'/api/assets/{self.asset.pk}/review/',
            {'outcome': 'confirmed', 'notes': 'Still in service'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['last_review']['outcome'], 'confirmed')
        self.assertEqual(resp.data['last_review']['reviewed_by_username'], 'assetrev_admin')
        self.assertIsNotNone(resp.data['last_review']['reviewed_at'])

    def test_a_second_review_replaces_last_review_but_keeps_history(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        api.post(
            f'/api/assets/{self.asset.pk}/review/', {'outcome': 'confirmed'}, format='json', HTTP_HOST=self.host,
        )
        second = api.post(
            f'/api/assets/{self.asset.pk}/review/',
            {'outcome': 'needs_update', 'notes': 'Owner changed teams'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(second.data['last_review']['outcome'], 'needs_update')

        with schema_context(self.tenant.schema_name):
            from core.models import AssetReview
            self.assertEqual(AssetReview.objects.filter(asset=self.asset).count(), 2)

    def test_invalid_outcome_is_rejected(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            f'/api/assets/{self.asset.pk}/review/', {'outcome': 'not-a-real-outcome'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)

    def test_review_history_endpoint_is_admin_auditor_only(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        api.post(f'/api/assets/{self.asset.pk}/review/', {'outcome': 'confirmed'}, format='json', HTTP_HOST=self.host)

        denied = APIClient()
        denied.force_authenticate(user=self.plain_user)
        resp = denied.get('/api/asset-reviews/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

        allowed = api.get('/api/asset-reviews/', HTTP_HOST=self.host)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.data['count'], 1)


class CorrectiveActionWorkflowTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('capaworkflow')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'capa_user', Membership.Role.USER, password='RealPassword123')

        with schema_context(self.tenant.schema_name):
            from core.models import CorrectiveAction
            self.capa = CorrectiveAction.objects.create(title='Fix the thing')

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_direct_patch_to_closed_is_rejected(self):
        resp = self.api.patch(
            f'/api/corrective-actions/{self.capa.pk}/', {'status': 'closed'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)
        with schema_context(self.tenant.schema_name):
            from core.models import CorrectiveAction
            self.assertNotEqual(CorrectiveAction.objects.get(pk=self.capa.pk).status, CorrectiveAction.Status.CLOSED)

    def test_other_status_transitions_still_work_via_plain_patch(self):
        resp = self.api.patch(
            f'/api/corrective-actions/{self.capa.pk}/', {'status': 'investigation', 'root_cause': 'Bad config'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'investigation')
        self.assertEqual(resp.data['root_cause'], 'Bad config')

    def test_close_without_password_is_rejected(self):
        resp = self.api.post(f'/api/corrective-actions/{self.capa.pk}/close/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_close_with_correct_password_signs_and_closes(self):
        resp = self.api.post(
            f'/api/corrective-actions/{self.capa.pk}/close/',
            {'password': 'RealPassword123', 'effectiveness_notes': 'Verified via re-test.'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'closed')
        self.assertEqual(resp.data['effectiveness_notes'], 'Verified via re-test.')
        self.assertIsNotNone(resp.data['closed_date'])

        with schema_context(self.tenant.schema_name):
            from core.models import ElectronicSignature
            from django.contrib.contenttypes.models import ContentType
            sig = ElectronicSignature.objects.get(
                content_type=ContentType.objects.get_for_model(self.capa), object_id=self.capa.pk,
            )
            self.assertEqual(sig.meaning, ElectronicSignature.Meaning.VERIFIED)
            self.assertTrue(sig.verify())

    def test_closing_an_already_closed_capa_is_rejected(self):
        self.api.post(
            f'/api/corrective-actions/{self.capa.pk}/close/',
            {'password': 'RealPassword123'}, format='json', HTTP_HOST=self.host,
        )
        resp = self.api.post(
            f'/api/corrective-actions/{self.capa.pk}/close/',
            {'password': 'RealPassword123'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)


class NonconformanceTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('nonconftest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'nc_user', Membership.Role.USER)
        self.admin = make_member(self.tenant, 'nc_admin', Membership.Role.ADMIN)

    def test_anyone_can_report_one(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/nonconformances/', {'title': 'Mislabeled box', 'description': 'Found on line 3'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['reported_by_username'], 'nc_user')

    def test_plain_user_cannot_triage(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Nonconformance
            nc = Nonconformance.objects.create(title='Something wrong')

        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(f'/api/nonconformances/{nc.pk}/close_no_action/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_close_with_no_action(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Nonconformance
            nc = Nonconformance.objects.create(title='Minor thing')

        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            f'/api/nonconformances/{nc.pk}/close_no_action/',
            {'closure_reason': 'Not a real issue'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'closed_no_action')
        self.assertEqual(resp.data['closure_reason'], 'Not a real issue')

    def test_admin_can_escalate_to_a_capa(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Nonconformance
            nc = Nonconformance.objects.create(title='Recurring defect', description='Happens every batch')

        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(f'/api/nonconformances/{nc.pk}/escalate/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'escalated')
        self.assertIsNotNone(resp.data['resulting_capa'])

        with schema_context(self.tenant.schema_name):
            from core.models import CorrectiveAction
            capa = CorrectiveAction.objects.get(pk=resp.data['resulting_capa'])
            self.assertIn('Recurring defect', capa.title)


class ApprovalMatrixGateTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('gatetest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'gate_admin', Membership.Role.ADMIN, password='RealPassword123')
        self.user = make_member(self.tenant, 'gate_user', Membership.Role.USER, password='RealPassword123')

        with schema_context(self.tenant.schema_name):
            from core.models import CorrectiveAction
            self.capa = CorrectiveAction.objects.create(title='Gated CAPA')

    def test_close_works_normally_with_no_rule_configured(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            f'/api/corrective-actions/{self.capa.pk}/close/', {'password': 'RealPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_configured_rule_blocks_close_until_approved(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        rule_resp = api.post(
            '/api/approval-matrix-rules/',
            {'entity_type': 'corrective_action', 'required_role': 'admin', 'active': True},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(rule_resp.status_code, 201, rule_resp.data)

        api.force_authenticate(user=self.user)
        blocked = api.post(
            f'/api/corrective-actions/{self.capa.pk}/close/', {'password': 'RealPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(blocked.status_code, 403)

        api.force_authenticate(user=self.admin)
        approval = api.post(
            '/api/approval-records/',
            {'entity_type': 'corrective_action', 'object_id': self.capa.pk, 'password': 'RealPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(approval.status_code, 201, approval.data)

        api.force_authenticate(user=self.user)
        allowed = api.post(
            f'/api/corrective-actions/{self.capa.pk}/close/', {'password': 'RealPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(allowed.status_code, 200, allowed.data)

    def test_wrong_role_cannot_record_approval(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        api.post(
            '/api/approval-matrix-rules/',
            {'entity_type': 'corrective_action', 'required_role': 'admin', 'active': True},
            format='json', HTTP_HOST=self.host,
        )

        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/approval-records/',
            {'entity_type': 'corrective_action', 'object_id': self.capa.pk, 'password': 'RealPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)

    def test_wrong_password_cannot_record_approval(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        api.post(
            '/api/approval-matrix-rules/',
            {'entity_type': 'corrective_action', 'required_role': 'admin', 'active': True},
            format='json', HTTP_HOST=self.host,
        )
        resp = api.post(
            '/api/approval-records/',
            {'entity_type': 'corrective_action', 'object_id': self.capa.pk, 'password': 'totally-wrong'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)

    def test_duplicate_approval_record_is_rejected(self):
        with schema_context(self.tenant.schema_name):
            from core.models import ApprovalMatrixRule
            ApprovalMatrixRule.objects.create(entity_type='corrective_action', required_role='admin', active=True)

        api = APIClient()
        api.force_authenticate(user=self.admin)
        first = api.post(
            '/api/approval-records/',
            {'entity_type': 'corrective_action', 'object_id': self.capa.pk, 'password': 'RealPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(first.status_code, 201)

        second = api.post(
            '/api/approval-records/',
            {'entity_type': 'corrective_action', 'object_id': self.capa.pk, 'password': 'RealPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(second.status_code, 400)

    def test_workflow_step_rejection_is_never_gated(self):
        with schema_context(self.tenant.schema_name):
            from core.models import ApprovalMatrixRule
            ApprovalMatrixRule.objects.create(entity_type='workflow_step', required_role='admin', active=True)
            from core.models import Document
            document = Document.objects.create(title='Gated Doc')

        api = APIClient()
        api.force_authenticate(user=self.admin)
        workflow = api.post(
            '/api/workflows/',
            {'document': document.pk, 'new_steps': [{'order': 1, 'approver_role': 'admin'}]},
            format='json', HTTP_HOST=self.host,
        )
        step_id = workflow.data['steps'][0]['id']

        # Rejecting is never gated — only approving is.
        resp = api.post(
            f'/api/workflow-steps/{step_id}/decide/',
            {'decision': 'rejected', 'password': 'RealPassword123'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)


class AccessReviewTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('accessreviewtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'ar_admin', Membership.Role.ADMIN)
        self.plain_user = make_member(self.tenant, 'ar_user', Membership.Role.USER)

    def test_non_admin_cannot_record_a_review(self):
        membership = Membership.objects.get(user=self.plain_user, tenant=self.tenant)
        api = APIClient()
        api.force_authenticate(user=self.plain_user)
        resp = api.post(f'/api/tenant/members/{membership.pk}/review/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_confirm_access(self):
        membership = Membership.objects.get(user=self.plain_user, tenant=self.tenant)
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            f'/api/tenant/members/{membership.pk}/review/',
            {'outcome': 'confirmed', 'notes': 'Still needs access'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['last_review']['outcome'], 'confirmed')

        self.plain_user.refresh_from_db()
        self.assertTrue(self.plain_user.is_active)

    def test_admin_can_suspend_access_which_deactivates_the_account(self):
        membership = Membership.objects.get(user=self.plain_user, tenant=self.tenant)
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            f'/api/tenant/members/{membership.pk}/review/',
            {'outcome': 'suspended', 'notes': 'No longer with the company'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)

        self.plain_user.refresh_from_db()
        self.assertFalse(self.plain_user.is_active)

    def test_suspended_account_is_immediately_blocked_from_the_api(self):
        # force_authenticate bypasses real token authentication entirely
        # (it just attaches the user to the request), so it would never
        # exercise TokenAuthentication's own is_active check — a real
        # token, sent as a real Authorization header, is required here.
        from rest_framework.authtoken.models import Token
        token = Token.objects.create(user=self.plain_user)

        membership = Membership.objects.get(user=self.plain_user, tenant=self.tenant)
        api = APIClient()
        api.force_authenticate(user=self.admin)
        api.post(
            f'/api/tenant/members/{membership.pk}/review/',
            {'outcome': 'suspended'}, format='json', HTTP_HOST=self.host,
        )

        suspended_api = APIClient()
        resp = suspended_api.get(
            '/api/documents/', HTTP_HOST=self.host, HTTP_AUTHORIZATION=f'Token {token.key}',
        )
        self.assertEqual(resp.status_code, 401)

    def test_access_review_history_is_restricted_to_admin_and_auditor(self):
        api = APIClient()
        api.force_authenticate(user=self.plain_user)
        resp = api.get('/api/tenant/access-reviews/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

        api.force_authenticate(user=self.admin)
        resp = api.get('/api/tenant/access-reviews/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)

    def test_invalid_outcome_is_rejected(self):
        membership = Membership.objects.get(user=self.plain_user, tenant=self.tenant)
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            f'/api/tenant/members/{membership.pk}/review/',
            {'outcome': 'not-a-real-outcome'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)
