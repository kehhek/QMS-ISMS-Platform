import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context, get_tenant_model

from tenants.models import Membership
from tenants.utils import generate_password


class Command(BaseCommand):
    help = 'Seed sample QMS/ISMS demo data (Documents, Risks, Audits, CAPA, Memberships) into one or more tenant schemas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            action='append',
            dest='schemas',
            help='Tenant schema to seed. Repeatable. Defaults to every non-public tenant.',
        )

    def handle(self, *args, **options):
        Client = get_tenant_model()
        schemas = options['schemas']
        if not schemas:
            schemas = list(
                Client.objects.exclude(schema_name='public').values_list('schema_name', flat=True)
            )

        if not schemas:
            self.stdout.write(self.style.WARNING('No tenant schemas found to seed.'))
            return

        for schema in schemas:
            tenant = Client.objects.get(schema_name=schema)
            self.seed_memberships(schema, tenant)
            self.seed_schema(schema)

    def seed_memberships(self, schema, tenant):
        """Demo accounts exercising each of the three roles, scoped to this
        tenant. Usernames are schema-prefixed since accounts.User is a
        SHARED_APP model — one global user pool across every tenant."""
        User = get_user_model()
        demo_members = [
            (f'{schema}-auditor', f'auditor@{schema}.example.com', Membership.Role.AUDITOR),
            (f'{schema}-user', f'user@{schema}.example.com', Membership.Role.USER),
        ]
        for username, email, role in demo_members:
            with schema_context(tenant.schema_name):
                user, created = User.objects.get_or_create(username=username, defaults={'email': email})
                if created:
                    user.set_password(generate_password())
                    user.save()
                Membership.objects.get_or_create(user=user, tenant=tenant, defaults={'role': role})

        member_count = Membership.objects.filter(tenant=tenant).count()
        self.stdout.write(self.style.SUCCESS(f'Schema "{schema}": {member_count} tenant memberships.'))

    def seed_schema(self, schema):
        from core.models import Document, Risk, Control, Incident, Audit, CorrectiveAction

        with schema_context(schema):
            documents = [
                dict(
                    title='Information Security Policy',
                    content='Top-level ISMS policy defining scope, objectives, and management commitment.',
                    version=2,
                    status=Document.Status.APPROVED,
                ),
                dict(
                    title='Document Control Procedure',
                    content='QMS procedure describing how controlled documents are created, reviewed, and retired.',
                    version=1,
                    status=Document.Status.APPROVED,
                ),
                dict(
                    title='Access Control Policy',
                    content='Defines rules for granting, reviewing, and revoking system access.',
                    version=1,
                    status=Document.Status.IN_REVIEW,
                ),
                dict(
                    title='Incident Response Plan',
                    content='Draft procedure for detecting, reporting, and responding to security incidents.',
                    version=1,
                    status=Document.Status.DRAFT,
                ),
            ]
            created_docs = {}
            for doc in documents:
                obj, _ = Document.objects.get_or_create(title=doc['title'], defaults=doc)
                created_docs[doc['title']] = obj

            # Demonstrate document versioning: approving this doc via .save()
            # triggers Document.save()'s automatic DocumentRevision snapshot.
            access_policy = created_docs.get('Access Control Policy')
            if access_policy and access_policy.status != Document.Status.APPROVED:
                access_policy.status = Document.Status.APPROVED
                access_policy.content += '\n\nApproved after security review.'
                access_policy.save()

            risks = [
                dict(name='Unpatched servers', description='Servers missing critical security patches.', likelihood=3, impact=4),
                dict(name='Phishing', description='Employees targeted by phishing campaigns.', likelihood=4, impact=3),
                dict(name='Vendor data breach', description='Third-party processor suffers a data breach.', likelihood=2, impact=5),
            ]
            for risk in risks:
                Risk.objects.get_or_create(name=risk['name'], defaults=risk)

            unpatched_risk = Risk.objects.filter(name='Unpatched servers').first()
            phishing_risk = Risk.objects.filter(name='Phishing').first()

            controls = [
                dict(
                    identifier='A.8.8', name='Management of technical vulnerabilities',
                    description='Patch management and vulnerability scanning.',
                    status=Control.Status.PARTIAL, owner='Infra Team',
                    risk_names=['Unpatched servers'],
                ),
                dict(
                    identifier='A.6.3', name='Information security awareness, education and training',
                    description='Regular phishing-awareness training for all staff.',
                    status=Control.Status.IMPLEMENTED, owner='People Team',
                    risk_names=['Phishing'],
                ),
            ]
            for control in controls:
                risk_names = control.pop('risk_names', [])
                obj, _ = Control.objects.get_or_create(identifier=control['identifier'], defaults=control)
                risk_map = {'Unpatched servers': unpatched_risk, 'Phishing': phishing_risk}
                obj.risks.set([risk_map[n] for n in risk_names if risk_map.get(n)])

            Incident.objects.get_or_create(
                title='Phishing email reported by staff',
                defaults=dict(
                    description='An employee reported a phishing email impersonating IT support.',
                    severity=Incident.Severity.MEDIUM,
                    status=Incident.Status.RESOLVED,
                    related_risk=phishing_risk,
                ),
            )

            # Demonstrate a risk under active treatment.
            unpatched = Risk.objects.filter(name='Unpatched servers').first()
            if unpatched and unpatched.status != Risk.Status.MITIGATING:
                unpatched.status = Risk.Status.MITIGATING
                unpatched.owner = 'Infra Team'
                unpatched.treatment_plan = 'Deploy automated patch management across all production servers.'
                unpatched.target_date = datetime.date.today() + datetime.timedelta(days=45)
                unpatched.save()

            today = datetime.date.today()
            audits = [
                dict(
                    title='Q1 Internal ISMS Audit',
                    scope='Access control, incident response, and asset management.',
                    audit_type=Audit.AuditType.INTERNAL,
                    status=Audit.Status.COMPLETED,
                    auditor='J. Rivera',
                    scheduled_date=today - datetime.timedelta(days=60),
                    completed_date=today - datetime.timedelta(days=55),
                    findings='No major nonconformities. Two minor observations on access review cadence.',
                    related_titles=['Access Control Policy', 'Information Security Policy'],
                ),
                dict(
                    title='ISO 27001 Certification Audit',
                    scope='Full ISMS scope per Statement of Applicability.',
                    audit_type=Audit.AuditType.CERTIFICATION,
                    status=Audit.Status.PLANNED,
                    auditor='External — Certification Body',
                    scheduled_date=today + datetime.timedelta(days=45),
                    completed_date=None,
                    findings='',
                    related_titles=['Information Security Policy', 'Document Control Procedure'],
                ),
            ]
            created_audits = {}
            for audit in audits:
                related_titles = audit.pop('related_titles', [])
                obj, _ = Audit.objects.get_or_create(title=audit['title'], defaults=audit)
                created_audits[audit['title']] = obj
                if related_titles:
                    obj.related_documents.set(
                        [created_docs[t] for t in related_titles if t in created_docs]
                    )

            capa_items = [
                dict(
                    title='Increase access review frequency',
                    description='Move access reviews from quarterly to monthly following the audit observation.',
                    action_type=CorrectiveAction.ActionType.CORRECTIVE,
                    status=CorrectiveAction.Status.IN_PROGRESS,
                    owner='J. Rivera',
                    audit=created_audits.get('Q1 Internal ISMS Audit'),
                    due_date=today + datetime.timedelta(days=30),
                ),
                dict(
                    title='Deploy automated patch management',
                    description='Roll out automated OS patching to close the unpatched-servers risk.',
                    action_type=CorrectiveAction.ActionType.PREVENTIVE,
                    status=CorrectiveAction.Status.OPEN,
                    owner='Infra Team',
                    risk=unpatched,
                    due_date=today + datetime.timedelta(days=45),
                ),
            ]
            for capa in capa_items:
                CorrectiveAction.objects.get_or_create(title=capa['title'], defaults=capa)

            self.stdout.write(self.style.SUCCESS(
                f'Seeded schema "{schema}": '
                f'{Document.objects.count()} documents, {Risk.objects.count()} risks, '
                f'{Control.objects.count()} controls, {Incident.objects.count()} incidents, '
                f'{Audit.objects.count()} audits, {CorrectiveAction.objects.count()} corrective actions.'
            ))
