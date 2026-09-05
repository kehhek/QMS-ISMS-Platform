from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Client, Membership, DemoRequest, AccessReview, UserGroup, UserGroupMember

User = get_user_model()


class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = (
            'schema_name', 'name', 'logo_url', 'primary_color',
            'support_email', 'website', 'on_trial', 'paid_until', 'created_on',
        )
        read_only_fields = ('schema_name', 'on_trial', 'paid_until', 'created_on')


class AccessReviewSerializer(serializers.ModelSerializer):
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, default=None)

    class Meta:
        model = AccessReview
        fields = ('id', 'membership', 'reviewed_by', 'reviewed_by_username', 'reviewed_at', 'outcome', 'notes')
        read_only_fields = fields


class UserGroupMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserGroupMember
        fields = ('id', 'user', 'username', 'added_at')
        read_only_fields = fields


class UserGroupSerializer(serializers.ModelSerializer):
    members = UserGroupMemberSerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = UserGroup
        fields = ('id', 'name', 'description', 'members', 'member_count', 'created_at')
        read_only_fields = ('members', 'member_count', 'created_at')


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
    # Access review: the last completed review, if any — the evidence
    # ISO 27001 A.5.18 actually asks for, not just the register itself.
    last_review = serializers.SerializerMethodField()
    # Org-structure labels (see UserGroup's docstring) — display only,
    # never a permissions check.
    groups = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = (
            'id', 'user', 'username', 'email', 'role', 'created_at',
            'is_active', 'last_login', 'date_joined', 'last_review', 'groups',
        )
        read_only_fields = ('id', 'user', 'created_at')

    def get_last_review(self, obj):
        review = obj.reviews.first()  # AccessReview.Meta.ordering = ['-reviewed_at']
        if not review:
            return None
        return AccessReviewSerializer(review).data

    def get_groups(self, obj):
        return list(
            UserGroup.objects.filter(tenant=obj.tenant, members__user=obj.user).values_list('name', flat=True)
        )


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
