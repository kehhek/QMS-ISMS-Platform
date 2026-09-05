from django.urls import path
from .views import (
    onboard_tenant, RegisterView, LoggingObtainAuthToken, LoginView, LogoutView,
    ChangePasswordView, ExpiredPasswordChangeView, PasswordResetRequestView, PasswordResetConfirmView,
)
from tenants.views import DemoRequestView

# No router/UserViewSet/GroupViewSet here anymore — see accounts/views.py
# for why (a cross-tenant user/group management leak, removed rather than
# re-scoped).

urlpatterns = [
    path('onboard/', onboard_tenant, name='tenant-onboard'),
    path('register/', RegisterView.as_view(), name='api-register'),
    path('demo-request/', DemoRequestView.as_view(), name='api-demo-request'),
    path('token/', LoggingObtainAuthToken.as_view(), name='api-token'),
    path('login/', LoginView.as_view(), name='api-login'),
    path('logout/', LogoutView.as_view(), name='api-logout'),
    path('password/change/', ChangePasswordView.as_view(), name='api-password-change'),
    path('password/change-expired/', ExpiredPasswordChangeView.as_view(), name='api-password-change-expired'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='api-password-reset-request'),
    path('password/reset-confirm/', PasswordResetConfirmView.as_view(), name='api-password-reset-confirm'),
]
