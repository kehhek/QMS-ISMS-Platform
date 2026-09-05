"""User Groups — org-structure labels (department/team), NOT a
permissions boundary. Role (Membership.role) still decides what someone
can do; a group's only payoff is filtering the Members list."""

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
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


class UserGroupTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('usergrouptest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'ug_admin', Membership.Role.ADMIN)
        self.alice = make_member(self.tenant, 'ug_alice', Membership.Role.USER)
        self.bob = make_member(self.tenant, 'ug_bob', Membership.Role.USER)

    def test_non_admin_cannot_create_a_group(self):
        api = APIClient()
        api.force_authenticate(user=self.alice)
        resp = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_a_group(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        resp = api.post(
            '/api/tenant/user-groups/', {'name': 'Quality Team', 'description': 'QMS owners'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['member_count'], 0)

    def test_duplicate_group_name_in_the_same_tenant_is_rejected_cleanly(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        resp = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('name', resp.data)

    def test_same_group_name_is_fine_in_a_different_tenant(self):
        other_tenant = make_tenant('usergrouptest2')
        other_admin = make_member(other_tenant, 'ug_admin2', Membership.Role.ADMIN)

        api = APIClient()
        api.force_authenticate(user=self.admin)
        first = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(first.status_code, 201)

        api.force_authenticate(user=other_admin)
        second = api.post(
            '/api/tenant/user-groups/', {'name': 'Quality Team'},
            format='json', HTTP_HOST=f'{other_tenant.schema_name}.localhost',
        )
        self.assertEqual(second.status_code, 201)

    def test_add_and_remove_members(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        create = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        group_id = create.data['id']

        add = api.post(
            f'/api/tenant/user-groups/{group_id}/add-member/', {'username': 'ug_alice'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(add.status_code, 200, add.data)
        self.assertEqual(add.data['member_count'], 1)
        self.assertEqual(add.data['members'][0]['username'], 'ug_alice')

        remove = api.post(
            f'/api/tenant/user-groups/{group_id}/remove-member/', {'user': self.alice.pk},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(remove.status_code, 200)
        self.assertEqual(remove.data['member_count'], 0)

    def test_cannot_add_someone_who_is_not_a_member_of_this_tenant(self):
        outsider = User.objects.create_user('ug_outsider', 'o@example.com', 'pass12345')

        api = APIClient()
        api.force_authenticate(user=self.admin)
        create = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        group_id = create.data['id']

        resp = api.post(
            f'/api/tenant/user-groups/{group_id}/add-member/', {'username': outsider.username},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)

    def test_group_is_not_a_permissions_boundary(self):
        # Alice is a plain "user" role in a group — being in a group grants
        # her nothing beyond what her role already allows.
        api = APIClient()
        api.force_authenticate(user=self.admin)
        create = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        api.post(
            f'/api/tenant/user-groups/{create.data["id"]}/add-member/', {'username': 'ug_alice'},
            format='json', HTTP_HOST=self.host,
        )

        alice_api = APIClient()
        alice_api.force_authenticate(user=self.alice)
        # Still can't manage members/groups — that's an admin-only action,
        # unaffected by group membership.
        resp = alice_api.post(
            '/api/tenant/user-groups/', {'name': 'Another Team'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)

    def test_filtering_members_by_group(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        create = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        group_id = create.data['id']
        api.post(
            f'/api/tenant/user-groups/{group_id}/add-member/', {'username': 'ug_alice'},
            format='json', HTTP_HOST=self.host,
        )

        filtered = api.get(f'/api/tenant/members/?group={group_id}', HTTP_HOST=self.host)
        self.assertEqual(filtered.status_code, 200)
        usernames = [m['username'] for m in filtered.data['results']]
        self.assertEqual(usernames, ['ug_alice'])

        unfiltered = api.get('/api/tenant/members/', HTTP_HOST=self.host)
        self.assertEqual(unfiltered.data['count'], 3)  # admin + alice + bob

    def test_a_groups_id_from_another_tenant_matches_nothing(self):
        other_tenant = make_tenant('usergrouptest3')
        other_admin = make_member(other_tenant, 'ug_admin3', Membership.Role.ADMIN)

        api = APIClient()
        api.force_authenticate(user=other_admin)
        other_group = api.post(
            '/api/tenant/user-groups/', {'name': 'Other Tenant Team'},
            format='json', HTTP_HOST=f'{other_tenant.schema_name}.localhost',
        )

        api.force_authenticate(user=self.admin)
        resp = api.get(f'/api/tenant/members/?group={other_group.data["id"]}', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 0)

    def test_membership_serializer_reports_group_names(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        create = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        api.post(
            f'/api/tenant/user-groups/{create.data["id"]}/add-member/', {'username': 'ug_alice'},
            format='json', HTTP_HOST=self.host,
        )

        resp = api.get('/api/tenant/members/', HTTP_HOST=self.host)
        alice_row = next(m for m in resp.data['results'] if m['username'] == 'ug_alice')
        self.assertEqual(alice_row['groups'], ['Quality Team'])

        bob_row = next(m for m in resp.data['results'] if m['username'] == 'ug_bob')
        self.assertEqual(bob_row['groups'], [])

    def test_deleting_a_group_does_not_affect_membership_or_role(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        create = api.post('/api/tenant/user-groups/', {'name': 'Quality Team'}, format='json', HTTP_HOST=self.host)
        group_id = create.data['id']
        api.post(
            f'/api/tenant/user-groups/{group_id}/add-member/', {'username': 'ug_alice'},
            format='json', HTTP_HOST=self.host,
        )

        delete = api.delete(f'/api/tenant/user-groups/{group_id}/', HTTP_HOST=self.host)
        self.assertEqual(delete.status_code, 204)

        # Alice's actual tenant membership/role is untouched.
        self.assertTrue(Membership.objects.filter(user=self.alice, tenant=self.tenant, role='user').exists())
