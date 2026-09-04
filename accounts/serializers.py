from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


class TenantOnboardSerializer(serializers.Serializer):
    name = serializers.CharField()
    schema = serializers.CharField()
    domain = serializers.CharField()
    admin_username = serializers.CharField(default='admin')
    admin_email = serializers.EmailField(default='admin@example.com')
    admin_password = serializers.CharField(default='admin')


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff', 'is_active')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')
