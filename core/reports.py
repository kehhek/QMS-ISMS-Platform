"""PDF reports — the other half of "basic reports & export" alongside
CsvExportMixin (core/export.py). CSV covers "hand a table to an
auditor"; this covers "hand a formatted summary to an auditor" for the
one report that's most obviously worth a real layout: control
implementation status by framework."""

from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from rest_framework.views import APIView

from tenants.permissions import HasTenantRole

from .models import Control


class ControlsStatusReportView(APIView):
    """A one-shot PDF: implementation status counts by framework, then
    the full control list with status/owner — read-only, any tenant
    member (same visibility as ControlViewSet's own list endpoint)."""

    permission_classes = [HasTenantRole]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        tenant_name = getattr(tenant, 'name', 'This organization')

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
            leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph('Control Implementation Status Report', styles['Title']),
            Paragraph(tenant_name, styles['Heading2']),
            Paragraph(f'Generated {timezone.now().strftime("%Y-%m-%d %H:%M UTC")}', styles['Normal']),
            Spacer(1, 0.3 * inch),
        ]

        controls = list(Control.objects.order_by('framework', 'identifier'))
        cell_style = styles['Normal'].clone('cell', fontSize=8, leading=10)

        for framework_value, framework_label in Control.Framework.choices:
            framework_controls = [c for c in controls if c.framework == framework_value]
            if not framework_controls:
                continue

            story.append(Paragraph(framework_label, styles['Heading2']))

            counts = {}
            for c in framework_controls:
                counts[c.status] = counts.get(c.status, 0) + 1
            summary = ', '.join(
                f'{label}: {counts.get(value, 0)}' for value, label in Control.Status.choices if counts.get(value)
            )
            story.append(Paragraph(f'{len(framework_controls)} controls — {summary}', styles['Normal']))
            story.append(Spacer(1, 0.15 * inch))

            table_data = [['ID', 'Name', 'Status', 'Owner']]
            for c in framework_controls:
                # Plain strings in a reportlab Table don't wrap within the
                # column width — long SOC 2 control names (full sentences,
                # unlike ISO 27001's short titles) would overflow and
                # visually collide with the Status/Owner columns. Paragraph
                # flowables wrap correctly; ID/Owner stay plain since
                # they're always short.
                table_data.append([
                    c.identifier,
                    Paragraph(c.name, cell_style),
                    Paragraph(c.get_status_display(), cell_style),
                    c.owner or '—',
                ])

            table = Table(table_data, colWidths=[0.7 * inch, 4.0 * inch, 1.3 * inch, 1.0 * inch], repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.3 * inch))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="controls-status-report.pdf"'
        return response
