from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from tenants.models import Client, Domain, Membership
from tenants.utils import generate_password
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.models import Group
from .serializers import TenantOnboardSerializer, UserSerializer, GroupSerializer
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.views import APIView
from rest_framework.decorators import authentication_classes


@api_view(['POST'])
@permission_classes([IsAdminUser])
def onboard_tenant(request):
    """Endpoint to create a tenant from the public schema. Must be called from public and by an admin."""
    serializer = TenantOnboardSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    branding_fields = {
        k: data[k] for k in ('logo_url', 'primary_color', 'support_email', 'website') if k in data
    }
    client = Client(schema_name=data['schema'], name=data['name'], **branding_fields)
    client.save()
    Domain.objects.create(domain=data['domain'], tenant=client, is_primary=True)

    password = data.get('admin_password') or generate_password()
    password_was_generated = not data.get('admin_password')

    # create admin user inside tenant schema
    with schema_context(client.schema_name):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=data['admin_username'],
            defaults={'email': data['admin_email'], 'is_superuser': True, 'is_staff': True},
        )
        if created:
            user.set_password(password)
            user.save()
        Membership.objects.get_or_create(user=user, tenant=client, defaults={'role': Membership.Role.ADMIN})

    response = {'ok': True, 'schema': client.schema_name}
    if password_was_generated:
        response['generated_admin_password'] = password
    return Response(response, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return Response({'ok': True, 'username': user.username})
        return Response({'ok': False}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    authentication_classes = [SessionAuthentication]

    def post(self, request):
        logout(request)
        return Response({'ok': True})


class UserViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUser]
