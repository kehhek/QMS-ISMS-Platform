import re

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from tenants.models import Client, Domain


class TenantOnboardSerializer(serializers.Serializer):
    name = serializers.CharField()
    schema = serializers.CharField()
    domain = serializers.CharField()
    admin_username = serializers.CharField(default='admin')
    admin_email = serializers.EmailField(default='admin@example.com')
    # If omitted, a strong random password is generated and returned once
    # in the response — there's no reason for callers to hand us a weak one.
    admin_password = serializers.CharField(required=False, allow_blank=True)

    # Org branding, set on the new tenant at creation time.
    logo_url = serializers.URLField(required=False, allow_blank=True)
    primary_color = serializers.CharField(required=False, allow_blank=True, max_length=7)
    support_email = serializers.EmailField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)


class RegisterSerializer(serializers.Serializer):
    """Public self-service signup — the "Get started" flow from the home
    page. Creates a brand-new tenant, not just a user."""

    org_name = serializers.CharField(max_length=100)
    subdomain = serializers.CharField(max_length=50)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True, style={'input_type': 'password'})
    plan = serializers.ChoiceField(choices=Client.Plan.choices, default=Client.Plan.FREE)

    def validate_subdomain(self, value):
        slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
        if not slug:
            raise serializers.ValidationError('Enter a subdomain using letters, numbers, and hyphens.')
        schema_name = f"org_{slug.replace('-', '_')}"
        domain_name = f'{slug}.localhost'
        if Client.objects.filter(schema_name=schema_name).exists() or Domain.objects.filter(domain=domain_name).exists():
            raise serializers.ValidationError('That subdomain is already taken — try another.')
        return slug

    def validate_username(self, value):
        if get_user_model().objects.filter(username=value).exists():
            raise serializers.ValidationError('That username is already taken.')
        return value


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff', 'is_active')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')
