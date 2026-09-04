from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/tenant/', include('tenants.urls')),
]

if settings.DEBUG:
    # gunicorn (unlike `runserver`) never serves STATIC_URL on its own;
    # this dev-only fallback keeps admin CSS/JS working in Docker.
    urlpatterns += staticfiles_urlpatterns()
