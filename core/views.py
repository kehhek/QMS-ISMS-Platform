from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Document, DocumentRevision, Risk, Audit, CorrectiveAction
from .permissions import IsInGroupOrReadOnly
from .serializers import (
    DocumentSerializer, DocumentRevisionSerializer, RiskSerializer,
    AuditSerializer, CorrectiveActionSerializer,
)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsInGroupOrReadOnly]
    allowed_groups = ['DocumentOwners', 'QualityManagers']

    def perform_update(self, serializer):
        # Document.save() reads this to attribute the resulting DocumentRevision.
        if serializer.instance is not None:
            serializer.instance._revision_actor = self.request.user
        serializer.save()


class DocumentRevisionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentRevisionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DocumentRevision.objects.all()
        document_id = self.request.query_params.get('document')
        if document_id:
            qs = qs.filter(document_id=document_id)
        return qs


class RiskViewSet(viewsets.ModelViewSet):
    queryset = Risk.objects.all()
    serializer_class = RiskSerializer
    permission_classes = [IsInGroupOrReadOnly]
    allowed_groups = ['QualityManagers']


class AuditViewSet(viewsets.ModelViewSet):
    queryset = Audit.objects.all()
    serializer_class = AuditSerializer
    permission_classes = [IsInGroupOrReadOnly]
    allowed_groups = ['Auditors', 'QualityManagers']


class CorrectiveActionViewSet(viewsets.ModelViewSet):
    queryset = CorrectiveAction.objects.all()
    serializer_class = CorrectiveActionSerializer
    permission_classes = [IsInGroupOrReadOnly]
    allowed_groups = ['Auditors', 'QualityManagers']
