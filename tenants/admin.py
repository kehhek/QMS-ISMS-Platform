from django.contrib import admin
from .models import Client, Domain, Membership, DemoRequest


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


@admin.register(DemoRequest)
class DemoRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'email', 'company', 'message')
