from django.conf import settings
from django.conf.urls.static import static
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
    # gunicorn (unlike `runserver`) never serves STATIC_URL/MEDIA_URL on
    # its own; this dev-only fallback keeps admin CSS/JS and uploaded
    # evidence files working in Docker.
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # This backend is API-only — there's nothing at "/" (see the 404 you'd
    # otherwise get). Admin's "View site" link defaults to "/" on the
    # current host; in dev, point it at the actual React console instead.
    # Not set outside DEBUG since the real frontend origin in production
    # depends on deployment and isn't necessarily this same host.
    admin.site.site_url = 'http://localhost:3001/'
