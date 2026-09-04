from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


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


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff', 'is_active')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')
