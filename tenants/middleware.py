from django.db import connection


class TenantSessionScopeMiddleware:
    """Sets a Postgres session variable (app.current_tenant_id) identifying
    the current tenant, for Row-Level Security policies to key off — see
    the RLS policy on tenants_membership (migration 0004).

    This is defense-in-depth on top of schema-based isolation, which is
    already the primary isolation mechanism: every tenant's QMS/ISMS data
    (Document, Risk, Audit, Control, Incident, ...) lives in a completely
    separate Postgres schema, not just separate rows in a shared table.
    RLS only matters here for the few tables that *are* shared across
    every tenant (accounts.User, tenants.Membership) because a bug in
    application-level permission checks could otherwise leak rows across
    tenants from those shared tables.

    Important caveat: Postgres RLS is never enforced against a superuser
    role, full stop — FORCE ROW LEVEL SECURITY doesn't change that. The
    default dev DATABASES config connects as the `postgres` superuser, so
    right now this plumbing is correctly wired but inert. It only takes
    effect once the app connects as a non-superuser role with the right
    grants.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(connection, 'tenant', None)
        tenant_id = getattr(tenant, 'id', None)
        with connection.cursor() as cursor:
            cursor.execute('SET app.current_tenant_id = %s', [str(tenant_id) if tenant_id else ''])
        try:
            return self.get_response(request)
        finally:
            # Reset rather than leave set — connections can be reused
            # across requests (persistent connections, connection pooling).
            with connection.cursor() as cursor:
                cursor.execute("SET app.current_tenant_id = ''")
