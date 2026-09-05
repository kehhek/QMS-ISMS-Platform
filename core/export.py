"""CSV export for any ModelViewSet — one of the platform's seven original
pillars ("basic reports & export") that had never actually been built.
Reuses the viewset's own serializer and permission/queryset scoping, so
an export can never show more than the matching list endpoint already
would, and never drifts out of sync with what that endpoint returns."""

import csv

from django.http import HttpResponse
from rest_framework.decorators import action


class CsvExportMixin:
    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        rows = serializer.data

        if rows:
            field_names = list(rows[0].keys())
        else:
            field_names = list(self.get_serializer().get_fields().keys())

        filename = f'{getattr(self, "basename", "export")}.csv'
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.DictWriter(response, fieldnames=field_names, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            # M2M / nested fields serialize as lists (e.g. Control.risks,
            # Audit.related_documents) and nested objects serialize as
            # dicts (e.g. Membership.last_review) — flatten both to a
            # readable string rather than a raw Python repr in the cell.
            flat = {key: self._flatten_cell(value) for key, value in row.items()}
            writer.writerow(flat)
        return response

    @staticmethod
    def _flatten_cell(value):
        if isinstance(value, list):
            return ', '.join(str(v) for v in value)
        if isinstance(value, dict):
            return '; '.join(f'{k}={v}' for k, v in value.items())
        return value
