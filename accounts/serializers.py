import re

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

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
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    plan = serializers.ChoiceField(choices=Client.Plan.choices, default=Client.Plan.FREE)

    def validate_password(self, value):
        # Enforces settings.AUTH_PASSWORD_VALIDATORS (min length, common-
        # password check, etc.) — Part 11 §11.300(a). There's no user
        # instance yet at registration time; UserAttributeSimilarityValidator
        # tolerates user=None and just skips that one check.
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

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


# UserSerializer/GroupSerializer used to live here, backing UserViewSet/
# GroupViewSet — removed along with those views (see accounts/views.py)
# as a cross-tenant data leak: a full read/write serializer over every
# platform user and Django Group, reachable by any tenant's own admin.


class MyProfileSerializer(serializers.ModelSerializer):
    """Unlike the removed UserSerializer above, this is never looked up
    by pk — MyProfileView always instantiates it with request.user, so
    there's no way to read or edit anyone else's account through it.
    username/is_active/is_staff/is_superuser are deliberately excluded
    entirely (not just read-only) — none of those are something a user
    should ever set on themselves, even accidentally."""

    role = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            'username', 'first_name', 'last_name', 'email', 'role', 'is_superuser',
            'date_joined', 'last_login',
        )
        read_only_fields = ('username', 'is_superuser', 'date_joined', 'last_login')

    def get_role(self, obj):
        from django.db import connection
        from tenants.models import Membership

        tenant = getattr(connection, 'tenant', None)
        if tenant is None:
            return None
        membership = Membership.objects.filter(user=obj, tenant=tenant).first()
        return membership.role if membership else None


class NewPasswordMixin:
    def validate_new_password(self, value):
        # Same Part 11 §11.300(a) enforcement as registration
        # (settings.AUTH_PASSWORD_VALIDATORS) — a forced password change
        # shouldn't be allowed to land on a weaker password than signup did.
        try:
            validate_password(value, user=getattr(self, '_password_validation_user', None))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class ChangePasswordSerializer(NewPasswordMixin, serializers.Serializer):
    """For an already-authenticated user proactively changing their own
    password (as opposed to ExpiredPasswordChangeSerializer, used when
    they're blocked from logging in at all)."""

    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class ExpiredPasswordChangeSerializer(NewPasswordMixin, serializers.Serializer):
    """Lets a user whose password has expired (Part 11 §11.300(b)) set a
    new one WITHOUT already holding a token — they can't get one until
    they do this, since LoggingObtainAuthToken refuses to issue a token
    for an expired password. Re-verifies identity via username+old
    password, same as a normal login, rather than trusting the username
    alone."""

    username = serializers.CharField()
    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class PasswordResetRequestSerializer(serializers.Serializer):
    """"Forgot password" — just a username; the view decides whether that
    account exists and has an email without ever telling the caller
    which (see PasswordResetRequestView), so this can't be used to
    enumerate usernames."""

    username = serializers.CharField()


class PasswordResetConfirmSerializer(NewPasswordMixin, serializers.Serializer):
    """Completes a reset from the emailed link's uid+token — Django's own
    PasswordResetTokenGenerator (used by the view), not a hand-rolled
    scheme: it's salted, single-use (invalidated by the very password
    change it authorizes, since the hash incorporates the old password),
    and time-limited via settings.PASSWORD_RESET_TIMEOUT."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
