from django.contrib import admin
from .models import Client, Domain, Membership, DemoRequest, AccessReview, UserGroup, UserGroupMember


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'on_trial', 'paid_until', 'support_email')


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'created_at')
    list_filter = ('role', 'tenant')


@admin.register(AccessReview)
class AccessReviewAdmin(admin.ModelAdmin):
    list_display = ('membership', 'outcome', 'reviewed_by', 'reviewed_at')
    list_filter = ('outcome',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserGroupMemberInline(admin.TabularInline):
    model = UserGroupMember
    extra = 0
    readonly_fields = ('added_at',)


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'created_at')
    list_filter = ('tenant',)
    search_fields = ('name', 'description')
    inlines = [UserGroupMemberInline]


@admin.register(DemoRequest)
class DemoRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'email', 'company', 'message')
