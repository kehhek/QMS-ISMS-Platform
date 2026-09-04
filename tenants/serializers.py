from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Client, Membership

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

    class Meta:
        model = Membership
        fields = ('id', 'user', 'username', 'email', 'role', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')


class MembershipInviteSerializer(serializers.Serializer):
    """Add an existing user (by username) or invite a brand-new one (by
    username + email) to the current tenant with a role."""

    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=Membership.Role.choices, default=Membership.Role.USER)
