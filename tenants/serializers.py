from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Client, Membership, DemoRequest

User = get_user_model()


class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = (
            'schema_name', 'name', 'logo_url', 'primary_color',
            'support_email', 'website', 'on_trial', 'paid_until', 'created_on',
        )
        read_only_fields = ('schema_name', 'on_trial', 'paid_until', 'created_on')


class MembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    # Access-register fields: when access was granted (created_at, already
    # present) alongside whether the account is active and when it was
    # last actually used — "who has access to what, and are they still
    # using it" is the point of an access register, not just the role.
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    last_login = serializers.DateTimeField(source='user.last_login', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)

    class Meta:
        model = Membership
        fields = (
            'id', 'user', 'username', 'email', 'role', 'created_at',
            'is_active', 'last_login', 'date_joined',
        )
        read_only_fields = ('id', 'user', 'created_at')


class DemoRequestSerializer(serializers.ModelSerializer):
    """Public, unauthenticated create — the home page's "Request a demo"
    form. No read access exposed here; a platform admin reviews these
    via the Django admin."""

    class Meta:
        model = DemoRequest
        fields = ('id', 'name', 'email', 'company', 'message', 'created_at')
        read_only_fields = ('id', 'created_at')


class MembershipInviteSerializer(serializers.Serializer):
    """Add an existing user (by username) or invite a brand-new one (by
    username + email) to the current tenant with a role."""

    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=Membership.Role.choices, default=Membership.Role.USER)
