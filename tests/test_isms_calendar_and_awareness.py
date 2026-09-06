"""ISMS Calendar (overdue/upcoming across Audit/CorrectiveAction/Risk/
TrainingRecord), the Approval Matrix reference view, and Security
Awareness training records (ISO 27001 A.6.3)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone
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


class IsmsCalendarTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('calendartest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'cal_user', Membership.Role.USER)

        today = timezone.localdate()
        with schema_context(self.tenant.schema_name):
            from core.models import Audit, CorrectiveAction, Risk, TrainingRecord

            Audit.objects.create(title='Overdue Audit', status=Audit.Status.PLANNED, scheduled_date=today - timedelta(days=3))
            Audit.objects.create(title='Upcoming Audit', status=Audit.Status.PLANNED, scheduled_date=today + timedelta(days=3))
            # Completed audits shouldn't show up even if their date is in the past.
            Audit.objects.create(title='Done Audit', status=Audit.Status.COMPLETED, scheduled_date=today - timedelta(days=10))

            CorrectiveAction.objects.create(title='Overdue CAPA', status=CorrectiveAction.Status.OPEN, due_date=today - timedelta(days=1))
            CorrectiveAction.objects.create(title='Closed CAPA', status=CorrectiveAction.Status.CLOSED, due_date=today - timedelta(days=1))

            Risk.objects.create(name='Upcoming Risk', status=Risk.Status.OPEN, target_date=today + timedelta(days=1))

            TrainingRecord.objects.create(user=self.user, title='Overdue Training', due_date=today - timedelta(days=2))
            TrainingRecord.objects.create(
                user=self.user, title='Done Training', due_date=today - timedelta(days=2),
                status=TrainingRecord.Status.COMPLETED,
            )

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_calendar_splits_overdue_and_upcoming_and_excludes_closed_items(self):
        resp = self.api.get('/api/isms-calendar/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)

        overdue_titles = {e['title'] for e in resp.data['overdue']}
        upcoming_titles = {e['title'] for e in resp.data['upcoming']}

        self.assertIn('Overdue Audit', overdue_titles)
        self.assertIn('Overdue CAPA', overdue_titles)
        self.assertIn('Overdue Training — cal_user', overdue_titles)
        self.assertIn('Upcoming Risk', upcoming_titles)
        self.assertIn('Upcoming Audit', upcoming_titles)

        # Completed/closed items never appear, regardless of date.
        all_titles = overdue_titles | upcoming_titles
        self.assertNotIn('Done Audit', all_titles)
        self.assertNotIn('Closed CAPA', all_titles)
        self.assertNotIn('Done Training — cal_user', all_titles)

        # Sorted soonest-first within each bucket.
        overdue_dates = [e['date'] for e in resp.data['overdue']]
        self.assertEqual(overdue_dates, sorted(overdue_dates))
        upcoming_dates = [e['date'] for e in resp.data['upcoming']]
        self.assertEqual(upcoming_dates, sorted(upcoming_dates))


class CalendarEventTests(TestCase):
    """Custom ISMS Calendar entries — the one kind of date nothing else
    in the schema implies, and the only calendar source that's ever
    directly created/edited/deleted as itself."""

    def setUp(self):
        self.tenant = make_tenant('calendareventtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'ce_user', Membership.Role.USER)
        self.admin = make_member(self.tenant, 'ce_admin', Membership.Role.ADMIN)

    def test_plain_user_cannot_create_a_custom_event(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/calendar-events/', {'title': 'Board review', 'date': str(timezone.localdate())},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_a_custom_event(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            '/api/calendar-events/', {'title': 'Board review', 'date': str(timezone.localdate())},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['created_by_username'], 'ce_admin')

    def test_plain_user_can_still_read_custom_events(self):
        with schema_context(self.tenant.schema_name):
            from core.models import CalendarEvent
            CalendarEvent.objects.create(title='Board review', date=timezone.localdate())

        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.get('/api/calendar-events/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)

    def test_a_custom_event_appears_on_the_isms_calendar(self):
        today = timezone.localdate()
        with schema_context(self.tenant.schema_name):
            from core.models import CalendarEvent
            CalendarEvent.objects.create(title='Overdue custom thing', date=today - timedelta(days=1))
            CalendarEvent.objects.create(title='Upcoming custom thing', date=today + timedelta(days=1))

        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.get('/api/isms-calendar/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)

        overdue_kinds = {(e['kind'], e['title']) for e in resp.data['overdue']}
        upcoming_kinds = {(e['kind'], e['title']) for e in resp.data['upcoming']}
        self.assertIn(('custom', 'Overdue custom thing'), overdue_kinds)
        self.assertIn(('custom', 'Upcoming custom thing'), upcoming_kinds)

    def test_admin_can_edit_and_delete_a_custom_event(self):
        with schema_context(self.tenant.schema_name):
            from core.models import CalendarEvent
            event = CalendarEvent.objects.create(title='Original', date=timezone.localdate())

        api = APIClient()
        api.force_authenticate(user=self.admin)
        edit = api.patch(
            f'/api/calendar-events/{event.pk}/', {'title': 'Renamed'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(edit.status_code, 200)
        self.assertEqual(edit.data['title'], 'Renamed')

        delete = api.delete(f'/api/calendar-events/{event.pk}/', HTTP_HOST=self.host)
        self.assertEqual(delete.status_code, 204)


class ApprovalMatrixTests(TestCase):
    def test_matrix_reflects_real_viewset_permissions(self):
        tenant = make_tenant('matrixtest')
        user = make_member(tenant, 'matrix_user', Membership.Role.USER)

        api = APIClient()
        api.force_authenticate(user=user)
        resp = api.get('/api/approval-matrix/', HTTP_HOST=f'{tenant.schema_name}.localhost')
        self.assertEqual(resp.status_code, 200)

        rows = {row['record_type']: row for row in resp.data}
        # Documents: admin + user can write (not auditor) — matches DocumentViewSet.allowed_roles.
        self.assertEqual(set(rows['Documents']['can_write']), {'admin', 'user'})
        # Audits: admin + auditor only — matches AuditViewSet.allowed_roles.
        self.assertEqual(set(rows['Audits']['can_write']), {'admin', 'auditor'})
        # Tenant members/roles: admin only.
        self.assertEqual(rows['Tenant members & roles']['can_write'], ['admin'])


class TrainingRecordTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('trainingtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'train_admin', Membership.Role.ADMIN)
        self.trainee = make_member(self.tenant, 'train_user', Membership.Role.USER)
        self.other_user = make_member(self.tenant, 'train_other', Membership.Role.USER)

    def test_admin_can_assign_training_to_a_user(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            '/api/training-records/', {'user': self.trainee.pk, 'title': 'Annual Awareness'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_plain_user_cannot_assign_training(self):
        api = APIClient()
        api.force_authenticate(user=self.trainee)
        resp = api.post(
            '/api/training-records/', {'user': self.other_user.pk, 'title': 'Should fail'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)

    def test_trainee_can_mark_their_own_record_complete(self):
        with schema_context(self.tenant.schema_name):
            from core.models import TrainingRecord
            record = TrainingRecord.objects.create(user=self.trainee, title='Annual Awareness')

        api = APIClient()
        api.force_authenticate(user=self.trainee)
        resp = api.post(f'/api/training-records/{record.pk}/complete/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'completed')
        self.assertIsNotNone(resp.data['completed_date'])

    def test_user_cannot_complete_someone_elses_training_record(self):
        with schema_context(self.tenant.schema_name):
            from core.models import TrainingRecord
            record = TrainingRecord.objects.create(user=self.trainee, title='Annual Awareness')

        api = APIClient()
        api.force_authenticate(user=self.other_user)
        resp = api.post(f'/api/training-records/{record.pk}/complete/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_complete_anyone_s_training_record(self):
        with schema_context(self.tenant.schema_name):
            from core.models import TrainingRecord
            record = TrainingRecord.objects.create(user=self.trainee, title='Annual Awareness')

        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(f'/api/training-records/{record.pk}/complete/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)


class TrainingVideoTests(TestCase):
    """Uploading/publishing a security awareness video and tracking who's
    watched it — a video's "who's watched this" is just its
    TrainingRecord assignments, same pattern as everything else in this
    ISMS (Access Review sits on top of the Access Register, Approval
    Records sit on top of the Approval Matrix, etc.)."""

    def setUp(self):
        self.tenant = make_tenant('trainingvideotest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'video_admin', Membership.Role.ADMIN)
        self.user1 = make_member(self.tenant, 'video_user1', Membership.Role.USER)
        self.user2 = make_member(self.tenant, 'video_user2', Membership.Role.USER)

    def _upload(self, actor):
        from django.core.files.uploadedfile import SimpleUploadedFile

        api = APIClient()
        api.force_authenticate(user=actor)
        return api, api.post(
            '/api/training-videos/',
            {
                'title': 'September 2026 Awareness', 'period': 'September 2026',
                'file': SimpleUploadedFile('video.mp4', b'fake mp4 bytes', content_type='video/mp4'),
            },
            format='multipart', HTTP_HOST=self.host,
        )

    def test_admin_can_upload_a_video(self):
        api, resp = self._upload(self.admin)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['file'], f'/api/training-videos/{resp.data["id"]}/stream/')
        self.assertEqual(resp.data['pending_count'], 0)

    def test_plain_user_cannot_upload_a_video(self):
        api, resp = self._upload(self.user1)
        self.assertEqual(resp.status_code, 403)

    def test_publishing_assigns_every_active_member_and_is_idempotent(self):
        api, video = self._upload(self.admin)
        video_id = video.data['id']

        first = api.post(f'/api/training-videos/{video_id}/publish/', HTTP_HOST=self.host)
        self.assertEqual(first.status_code, 200, first.data)
        # admin + user1 + user2 = 3 active members.
        self.assertEqual(first.data['assigned_count'], 3)

        second = api.post(f'/api/training-videos/{video_id}/publish/', HTTP_HOST=self.host)
        self.assertEqual(second.data['assigned_count'], 0)
        self.assertEqual(second.data['already_assigned_count'], 3)

        with schema_context(self.tenant.schema_name):
            from core.models import TrainingRecord
            self.assertEqual(TrainingRecord.objects.filter(video_id=video_id).count(), 3)

    def test_plain_user_cannot_publish(self):
        api, video = self._upload(self.admin)
        user_api = APIClient()
        user_api.force_authenticate(user=self.user1)
        resp = user_api.post(f'/api/training-videos/{video.data["id"]}/publish/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_watch_flow_start_then_complete_updates_status_and_counts(self):
        api, video = self._upload(self.admin)
        video_id = video.data['id']
        api.post(f'/api/training-videos/{video_id}/publish/', HTTP_HOST=self.host)

        user1_api = APIClient()
        user1_api.force_authenticate(user=self.user1)
        listing = user1_api.get('/api/training-videos/', HTTP_HOST=self.host)
        my_record_id = listing.data['results'][0]['my_record_id']
        self.assertEqual(listing.data['results'][0]['my_status'], 'assigned')

        start = user1_api.post(f'/api/training-records/{my_record_id}/start/', HTTP_HOST=self.host)
        self.assertEqual(start.data['status'], 'in_progress')

        complete = user1_api.post(f'/api/training-records/{my_record_id}/complete/', HTTP_HOST=self.host)
        self.assertEqual(complete.data['status'], 'completed')
        self.assertIsNotNone(complete.data['completed_date'])

        counts = api.get('/api/training-videos/', HTTP_HOST=self.host).data['results'][0]
        self.assertEqual(counts['completed_count'], 1)
        self.assertEqual(counts['pending_count'], 2)  # admin + user2 still pending

    def test_cannot_start_someone_elses_training_record(self):
        api, video = self._upload(self.admin)
        api.post(f'/api/training-videos/{video.data["id"]}/publish/', HTTP_HOST=self.host)

        with schema_context(self.tenant.schema_name):
            from core.models import TrainingRecord
            other_record = TrainingRecord.objects.get(video_id=video.data['id'], user=self.user1)

        user2_api = APIClient()
        user2_api.force_authenticate(user=self.user2)
        resp = user2_api.post(f'/api/training-records/{other_record.pk}/start/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_streaming_the_video_round_trips_the_uploaded_bytes(self):
        api, video = self._upload(self.admin)
        resp = api.get(video.data['file'], HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        content = b''.join(resp.streaming_content)
        self.assertEqual(content, b'fake mp4 bytes')

    def test_filtering_training_records_by_video(self):
        api, video = self._upload(self.admin)
        video_id = video.data['id']
        api.post(f'/api/training-videos/{video_id}/publish/', HTTP_HOST=self.host)

        with schema_context(self.tenant.schema_name):
            from core.models import TrainingRecord
            TrainingRecord.objects.create(user=self.admin, title='Unrelated cycle')  # no video

        resp = api.get(f'/api/training-records/?video={video_id}', HTTP_HOST=self.host)
        self.assertEqual(resp.data['count'], 3)
        self.assertTrue(all(r['video'] == video_id for r in resp.data['results']))


class AccessRegisterTests(TestCase):
    def test_membership_listing_includes_access_register_fields(self):
        tenant = make_tenant('accessregtest')
        admin = make_member(tenant, 'reg_admin', Membership.Role.ADMIN)
        make_member(tenant, 'reg_user', Membership.Role.USER)

        api = APIClient()
        api.force_authenticate(user=admin)
        resp = api.get('/api/tenant/members/', HTTP_HOST=f'{tenant.schema_name}.localhost')
        self.assertEqual(resp.status_code, 200)

        row = next(r for r in resp.data['results'] if r['username'] == 'reg_user')
        self.assertIn('is_active', row)
        self.assertIn('last_login', row)
        self.assertIn('date_joined', row)
        self.assertIn('created_at', row)  # when access was granted
        self.assertTrue(row['is_active'])


class OverdueDigestTaskTests(TestCase):
    """core.tasks.send_overdue_isms_digest — replaces the old
    'run-audit-every-minute' no-op placeholder with something real."""

    def test_sends_a_digest_only_to_tenants_with_overdue_items(self):
        connection.set_schema_to_public()

        overdue_tenant = make_tenant('digestoverdue')
        admin = make_member(overdue_tenant, 'digest_admin', Membership.Role.ADMIN)
        admin.email = 'digest_admin@example.com'
        admin.save()
        make_member(overdue_tenant, 'digest_user', Membership.Role.USER)  # not admin/auditor — shouldn't be emailed

        with schema_context(overdue_tenant.schema_name):
            from core.models import Audit
            Audit.objects.create(
                title='Way Overdue Audit', status=Audit.Status.PLANNED,
                scheduled_date=timezone.localdate() - timedelta(days=5),
            )

        quiet_tenant = make_tenant('digestquiet')
        quiet_admin = make_member(quiet_tenant, 'quiet_admin', Membership.Role.ADMIN)
        quiet_admin.email = 'quiet_admin@example.com'
        quiet_admin.save()
        # No overdue items in this tenant at all.

        from core.tasks import send_overdue_isms_digest
        sent_count = send_overdue_isms_digest()
        self.assertEqual(sent_count, 1)

        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['digest_admin@example.com'])
        self.assertIn('Way Overdue Audit', mail.outbox[0].body)


class DemoRequestTests(TestCase):
    PLATFORM_HOST = 'platform.localhost'

    def setUp(self):
        connection.set_schema_to_public()
        public_tenant, _ = Client.objects.get_or_create(schema_name='public', defaults={'name': 'Platform'})
        Domain.objects.get_or_create(domain=self.PLATFORM_HOST, defaults={'tenant': public_tenant, 'is_primary': True})

    def test_anyone_can_submit_a_demo_request(self):
        api = APIClient()
        resp = api.post('/api/accounts/demo-request/', {
            'name': 'Jane Prospect', 'email': 'jane@example.com', 'company': 'Acme',
            'message': 'Interested in the enterprise plan.',
        }, format='json', HTTP_HOST=self.PLATFORM_HOST)
        self.assertEqual(resp.status_code, 201, resp.data)

        from tenants.models import DemoRequest
        self.assertTrue(DemoRequest.objects.filter(email='jane@example.com').exists())

    @override_settings(DEMO_REQUEST_NOTIFY_EMAIL='sales@example.com')
    def test_a_notification_email_is_sent_when_configured(self):
        api = APIClient()
        resp = api.post('/api/accounts/demo-request/', {
            'name': 'Jane Prospect', 'email': 'jane@example.com', 'company': 'Acme',
        }, format='json', HTTP_HOST=self.PLATFORM_HOST)
        self.assertEqual(resp.status_code, 201, resp.data)

        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['sales@example.com'])
        self.assertIn('Jane Prospect', mail.outbox[0].subject)

    def test_no_email_attempted_when_notify_address_is_unset(self):
        # Default settings leave DEMO_REQUEST_NOTIFY_EMAIL blank.
        api = APIClient()
        resp = api.post('/api/accounts/demo-request/', {
            'name': 'No Notify Co', 'email': 'nn@example.com',
        }, format='json', HTTP_HOST=self.PLATFORM_HOST)
        self.assertEqual(resp.status_code, 201, resp.data)

        from django.core import mail
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_required_fields_rejected(self):
        api = APIClient()
        resp = api.post('/api/accounts/demo-request/', {'name': 'No Email'}, format='json', HTTP_HOST=self.PLATFORM_HOST)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('email', resp.data)
