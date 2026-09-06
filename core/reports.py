"""PDF reports — the other half of "basic reports & export" alongside
CsvExportMixin (core/export.py). CSV covers "hand a table to an
auditor"; this covers "hand a formatted summary to an auditor" for the
one report that's most obviously worth a real layout: control
implementation status by framework."""

from io import BytesIO

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from rest_framework.views import APIView

from tenants.permissions import HasTenantRole

from .models import Control, Evidence


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


class StatementOfApplicabilityReportView(APIView):
    """The one document every ISO 27001 certification audit demands
    (Clause 6.1.3d) — normally assembled by hand in a spreadsheet, kept
    in sync manually, and inevitably stale by the time the auditor asks
    for it. Every column here except "Justification" is pulled live at
    generation time: Applicable/Status straight off the Control,
    Reference is whatever Evidence is actually attached to it right now
    (see the Controls page's "View / Add" attachments). Justification
    (soa_justification on Control) is the one line an auditor expects an
    actual person to have written — shown as "—" if not yet filled in,
    which does NOT block generating the report; that's a gap to flag and
    close, not a reason a one-click report should fail.

    ?framework=iso27001|soc2 optional, defaults to every framework the
    tenant has controls in."""

    permission_classes = [HasTenantRole]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        tenant_name = getattr(tenant, 'name', 'This organization')
        framework_filter = request.query_params.get('framework')

        controls = Control.objects.order_by('framework', 'identifier')
        if framework_filter:
            controls = controls.filter(framework=framework_filter)
        controls = list(controls)

        control_ct = ContentType.objects.get_for_model(Control)
        evidence_by_control = {}
        for ev in Evidence.objects.filter(content_type=control_ct, object_id__in=[c.id for c in controls]):
            evidence_by_control.setdefault(ev.object_id, []).append(ev.title)

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
            leftMargin=0.4 * inch, rightMargin=0.4 * inch,
        )
        styles = getSampleStyleSheet()
        cell_style = styles['Normal'].clone('cell', fontSize=7.5, leading=9.5)

        applicable_count = sum(1 for c in controls if c.status != Control.Status.NOT_APPLICABLE)
        story = [
            Paragraph('Statement of Applicability', styles['Title']),
            Paragraph(tenant_name, styles['Heading2']),
            Paragraph(f'Generated {timezone.now().strftime("%Y-%m-%d %H:%M UTC")}', styles['Normal']),
            Spacer(1, 0.15 * inch),
            Paragraph(
                f'{len(controls)} controls in scope — {applicable_count} applicable, '
                f'{len(controls) - applicable_count} not applicable.',
                styles['Normal'],
            ),
            Spacer(1, 0.25 * inch),
        ]

        for framework_value, framework_label in Control.Framework.choices:
            framework_controls = [c for c in controls if c.framework == framework_value]
            if not framework_controls:
                continue

            story.append(Paragraph(framework_label, styles['Heading2']))
            story.append(Spacer(1, 0.1 * inch))

            table_data = [['ID', 'Name', 'Applicable', 'Status', 'Justification', 'Reference']]
            for c in framework_controls:
                applicable = c.status != Control.Status.NOT_APPLICABLE
                reference = ', '.join(evidence_by_control.get(c.id, [])) or '—'
                table_data.append([
                    c.identifier,
                    Paragraph(c.name, cell_style),
                    'Yes' if applicable else 'No',
                    Paragraph(c.get_status_display(), cell_style),
                    Paragraph(c.soa_justification or '—', cell_style),
                    Paragraph(reference, cell_style),
                ])

            table = Table(
                table_data,
                colWidths=[0.55 * inch, 1.7 * inch, 0.65 * inch, 0.9 * inch, 1.7 * inch, 1.6 * inch],
                repeatRows=1,
            )
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 7.5),
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
        response['Content-Disposition'] = 'attachment; filename="statement-of-applicability.pdf"'
        return response
