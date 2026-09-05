"""Starter policy templates a tenant can generate straight into their
Policy library (category="policy" Documents) instead of writing one from
scratch. Each is a genuine, usable first draft — Purpose/Scope/Policy
Statements/Roles/Review — referencing the ISO 27001 Annex A controls it
supports, so a generated policy slots directly into the rest of this
platform's control catalog and approval workflow. Generated as Draft;
still goes through the normal Workflow/electronic-signature approval
before it counts as "Approved" — this only removes the blank-page
problem, not the approval requirement.

See core/views.py's PolicyTemplateListView/PolicyTemplateGenerateView and
seed_control_catalogs.py's docstring for the analogous pattern this
follows (a bundled reference catalog, applied into a tenant on request).
"""

POLICY_TEMPLATES = [
    {
        'slug': 'information-security-policy',
        'title': 'Information Security Policy',
        'summary': 'The top-level ISMS policy — management commitment and the umbrella every other policy sits under.',
        'controls': 'A.5.1, A.5.2, A.5.4',
        'content': """PURPOSE
This policy states management's commitment to information security and defines the framework by
which [Organization Name] establishes, implements, maintains, and continually improves its
Information Security Management System (ISMS).

SCOPE
This policy applies to all employees, contractors, and third parties who access, process, or
store [Organization Name]'s information assets, across all systems, facilities, and locations.

POLICY STATEMENTS
- [Organization Name] is committed to protecting the confidentiality, integrity, and availability
  of information assets belonging to the organization, its customers, and its partners.
- Information security objectives are set, measured, and reviewed at least annually as part of
  management review.
- Every employee and contractor is responsible for protecting information assets and must
  complete security awareness training on hire and at least annually thereafter.
- This policy is supported by a set of subordinate policies (Access Control, Acceptable Use,
  Incident Response, Data Classification, and others) which together implement its commitments.
- Non-compliance with this policy may result in disciplinary action, up to and including
  termination of employment or contract.

ROLES & RESPONSIBILITIES
- Executive management: approves this policy and provides the resources needed for the ISMS.
- Information Security Owner: maintains this policy, coordinates the ISMS, and reports on its
  performance to management.
- All personnel: comply with this policy and report suspected security weaknesses or incidents.

REVIEW
This policy is reviewed at least annually, or after any significant change to the organization,
its risk environment, or applicable legal/regulatory requirements.""",
    },
    {
        'slug': 'access-control-policy',
        'title': 'Access Control Policy',
        'summary': 'Least-privilege access, provisioning/de-provisioning, and periodic access review.',
        'controls': 'A.5.15, A.5.16, A.5.17, A.5.18, A.8.2, A.8.3',
        'content': """PURPOSE
This policy defines the rules for granting, reviewing, and revoking access to [Organization
Name]'s information systems, in order to prevent unauthorized access to information and
information processing facilities.

SCOPE
This policy applies to all user, administrative, and service accounts across all systems that
store or process organizational information.

POLICY STATEMENTS
- Access is granted on the principle of least privilege: users are given the minimum access
  required to perform their job function, and no more.
- Access requests must be approved by the relevant system/data owner before being provisioned.
- Privileged (administrative) access is granted only where justified by role and is reviewed more
  frequently than standard user access.
- Access rights are reviewed at least every 6 months (see the platform's Access Register/Access
  Review feature) to confirm they remain appropriate; access no longer required is revoked
  promptly.
- Access is revoked immediately upon termination of employment or contract, and promptly upon a
  role change that no longer requires it.
- Shared/generic accounts are avoided; where unavoidable, their use is logged and attributable to
  an individual.
- Multi-factor authentication is required for all remote and administrative access.

ROLES & RESPONSIBILITIES
- System/data owners: approve access requests for the systems/data they own.
- IT/Administrators: provision, modify, and revoke access per approved requests.
- Managers: promptly notify IT of role changes or terminations affecting their reports' access.

REVIEW
This policy is reviewed at least annually and after any significant access-related incident.""",
    },
    {
        'slug': 'acceptable-use-policy',
        'title': 'Acceptable Use Policy',
        'summary': 'Rules for appropriate use of company systems, email, internet, and devices.',
        'controls': 'A.5.10, A.8.1',
        'content': """PURPOSE
This policy defines acceptable and unacceptable use of [Organization Name]'s information systems,
devices, and network, to protect the organization, its employees, and its customers.

SCOPE
This policy applies to all employees, contractors, and third parties using [Organization Name]'s
systems, devices, or network, whether on-site or remote.

POLICY STATEMENTS
- Company systems and devices are provided for business purposes; incidental personal use is
  permitted provided it does not interfere with work duties, consume excessive resources, or
  violate any other organizational policy or law.
- Users must not attempt to access data, systems, or accounts they are not authorized to access.
- Installation of unauthorized software is prohibited; only software approved by IT may be
  installed on company devices.
- Confidential or sensitive information must not be shared over unencrypted channels or with
  unauthorized parties (see the Data Classification & Handling Policy).
- Users must lock or log off devices when unattended and use strong, unique passwords/passphrases.
- Use of company systems to harass, discriminate against, or defame others is strictly prohibited.
- Users must promptly report lost/stolen devices and suspected security incidents.

ROLES & RESPONSIBILITIES
- All personnel: comply with this policy when using company systems and devices.
- IT: monitors for and investigates violations, and maintains approved software lists.

REVIEW
This policy is reviewed at least annually.""",
    },
    {
        'slug': 'data-classification-policy',
        'title': 'Data Classification & Handling Policy',
        'summary': 'How information is classified (Public/Internal/Confidential/Restricted) and handled accordingly.',
        'controls': 'A.5.12, A.5.13, A.8.10, A.8.11',
        'content': """PURPOSE
This policy defines how [Organization Name] classifies information according to its sensitivity
and the handling requirements that apply at each classification level.

SCOPE
This policy applies to all information created, received, stored, or transmitted by
[Organization Name], regardless of format or medium.

CLASSIFICATION LEVELS
- Public: information approved for public release; no handling restrictions.
- Internal: information for use within the organization; not for external distribution.
- Confidential: sensitive business information (e.g. contracts, financials, customer data);
  access limited to those with a business need, encrypted in transit and at rest.
- Restricted: highly sensitive information (e.g. credentials, cryptographic keys, regulated
  personal data); access limited to named individuals, encrypted at rest and in transit, and
  access logged.

POLICY STATEMENTS
- Information owners are responsible for classifying the information they own at creation and
  re-classifying it if circumstances change.
- Documents and records in this platform carry a classification field (see the Documents/
  Policies/SOPs pages) that must be set consistent with this policy.
- Confidential and Restricted information must not be sent by unencrypted email or stored on
  unapproved personal devices or cloud services.
- Information no longer needed is securely disposed of/deleted in line with the organization's
  retention schedule.

ROLES & RESPONSIBILITIES
- Information owners: classify and periodically re-review the information they own.
- All personnel: handle information according to its classification.

REVIEW
This policy is reviewed at least annually.""",
    },
    {
        'slug': 'incident-response-policy',
        'title': 'Incident Response Policy',
        'summary': 'Detection, reporting, escalation, and closure of information security incidents.',
        'controls': 'A.5.24, A.5.25, A.5.26, A.5.27',
        'content': """PURPOSE
This policy establishes a consistent, effective approach to detecting, reporting, and responding
to information security incidents at [Organization Name], to minimize their impact and prevent
recurrence.

SCOPE
This policy applies to any suspected or confirmed event that compromises the confidentiality,
integrity, or availability of [Organization Name]'s information or systems.

POLICY STATEMENTS
- All personnel must report suspected security incidents immediately upon discovery, using the
  Incidents module of this platform or the designated incident reporting channel.
- Reported incidents are triaged and assigned a severity level, then investigated, contained, and
  remediated by the incident response team.
- Incidents are tracked from open through resolution/closure, with corrective actions raised
  (see the Corrective Actions module) where root-cause remediation is required.
- Incidents involving personal data are assessed for breach notification obligations under
  applicable law, and escalated to management/legal without delay.
- A post-incident review is conducted for significant incidents to capture lessons learned and
  feed them back into the ISMS (updated risks, controls, or this policy itself).

ROLES & RESPONSIBILITIES
- All personnel: report suspected incidents promptly; do not attempt to investigate independently
  in ways that could destroy evidence.
- Incident response team: triage, investigate, contain, and remediate reported incidents.
- Management: is notified of significant incidents and approves external communications.

REVIEW
This policy is reviewed at least annually and after any significant incident.""",
    },
    {
        'slug': 'business-continuity-policy',
        'title': 'Business Continuity & Disaster Recovery Policy',
        'summary': 'Continuity of critical operations and recovery of systems/data after a disruption.',
        'controls': 'A.5.29, A.5.30, A.8.14',
        'content': """PURPOSE
This policy defines [Organization Name]'s approach to maintaining the continuity of critical
business functions and recovering information systems following a disruptive event.

SCOPE
This policy applies to all critical business processes, information systems, and facilities
required to deliver [Organization Name]'s products and services.

POLICY STATEMENTS
- Critical business processes and their supporting systems are identified and assessed for
  the impact of a disruption (a Business Impact Analysis), including target Recovery Time
  Objectives (RTO) and Recovery Point Objectives (RPO).
- Backups of critical data are taken on a defined schedule, stored securely (including off-site/
  redundant copies), and periodically tested for successful restoration.
- Disaster recovery and business continuity plans are documented, made available to relevant
  personnel, and tested at least annually.
- Following an activation of these plans, a post-event review is conducted and the plans updated
  with lessons learned.

ROLES & RESPONSIBILITIES
- Executive management: approves continuity plans and allocates resources for their maintenance.
- IT: maintains backup and recovery procedures and tests them on schedule.
- Process owners: maintain continuity plans for the critical processes they own.

REVIEW
This policy and its supporting plans are reviewed at least annually and after any activation.""",
    },
    {
        'slug': 'supplier-management-policy',
        'title': 'Supplier & Third-Party Management Policy',
        'summary': 'Security requirements and oversight for vendors and third parties.',
        'controls': 'A.5.19, A.5.20, A.5.21, A.5.22',
        'content': """PURPOSE
This policy defines the security requirements [Organization Name] applies when engaging
suppliers and other third parties who access, process, or store its information.

SCOPE
This policy applies to all suppliers, vendors, and third parties with access to [Organization
Name]'s information, systems, or facilities (see the Suppliers module of this platform).

POLICY STATEMENTS
- Suppliers with access to confidential or restricted information are assessed for security risk
  before onboarding, proportionate to the access/data involved.
- Security and confidentiality requirements are documented in supplier contracts, including the
  right to audit and requirements to notify [Organization Name] of security incidents affecting
  its data.
- Supplier access is provisioned per the Access Control Policy (least privilege) and reviewed
  periodically alongside internal access.
- Supplier performance and security posture are monitored on an ongoing basis, proportionate to
  the risk the relationship presents; issues are tracked to resolution.
- Supplier relationships are formally offboarded, including revocation of access and confirmation
  of data return/destruction, when the relationship ends.

ROLES & RESPONSIBILITIES
- Procurement/Business owners: assess and onboard suppliers per this policy.
- Information Security Owner: defines the security assessment criteria and reviews high-risk
  suppliers.

REVIEW
This policy is reviewed at least annually.""",
    },
    {
        'slug': 'password-authentication-policy',
        'title': 'Password & Authentication Policy',
        'summary': 'Password strength, MFA, and credential handling requirements.',
        'controls': 'A.5.17, A.8.5',
        'content': """PURPOSE
This policy defines the minimum requirements for passwords and authentication used to access
[Organization Name]'s systems.

SCOPE
This policy applies to all accounts (user, administrative, and service) on systems owned or
operated by [Organization Name].

POLICY STATEMENTS
- Passwords must meet the organization's configured minimum length and complexity requirements
  and must not be reused across systems.
- Multi-factor authentication (MFA) is required for all remote access, administrative access, and
  access to systems processing confidential or restricted information.
- Passwords must never be shared, written down in plaintext, or transmitted unencrypted.
- Default vendor passwords must be changed before a system is put into use.
- Accounts are locked out after a defined number of failed authentication attempts, and repeated
  failures are logged for review.
- Where technically supported, passwords are stored only as salted cryptographic hashes, never in
  plaintext or reversibly encrypted form.

ROLES & RESPONSIBILITIES
- All personnel: choose and protect passwords per this policy and enable MFA where offered.
- IT: enforces password/MFA requirements at the system level and monitors for lockout patterns
  that may indicate an attack.

REVIEW
This policy is reviewed at least annually.""",
    },
    {
        'slug': 'change-management-policy',
        'title': 'Change Management Policy',
        'summary': 'Controlled review, testing, and approval of changes to systems and infrastructure.',
        'controls': 'A.8.32',
        'content': """PURPOSE
This policy ensures that changes to [Organization Name]'s information systems and infrastructure
are made in a controlled manner that minimizes risk to confidentiality, integrity, and
availability.

SCOPE
This policy applies to changes to production systems, applications, infrastructure, and network
configuration.

POLICY STATEMENTS
- Changes are proposed, documented, and assessed for risk and impact before being scheduled.
- Changes are tested in a non-production environment where practicable before deployment.
- Changes require approval from an appropriate owner before being deployed to production,
  commensurate with their risk (routine changes may follow a lighter-weight approval than
  high-risk changes).
- A rollback plan is defined for changes before deployment.
- Emergency changes made outside the normal process are documented and formally reviewed/
  approved after the fact as soon as practicable.
- A record of changes made is maintained to support audit and incident investigation.

ROLES & RESPONSIBILITIES
- Change requester: documents and tests the proposed change.
- Change approver: reviews risk/impact and approves or rejects the change.
- IT/Engineering: implements approved changes and maintains the change record.

REVIEW
This policy is reviewed at least annually.""",
    },
    {
        'slug': 'risk-management-policy',
        'title': 'Risk Management Policy',
        'summary': 'How information security risks are identified, assessed, treated, and monitored.',
        'controls': 'A.5.1, Clause 6.1',
        'content': """PURPOSE
This policy defines [Organization Name]'s approach to identifying, assessing, treating, and
monitoring information security risks as part of its ISMS.

SCOPE
This policy applies to risks affecting the confidentiality, integrity, or availability of
[Organization Name]'s information assets, systems, and processes.

POLICY STATEMENTS
- Risks are identified and recorded in the organization's risk register (see the Risks module of
  this platform), including the asset(s) affected where applicable.
- Each risk is assessed for likelihood and impact, and assigned an owner responsible for its
  treatment.
- Risk treatment options (mitigate, accept, transfer, avoid) are decided and documented for each
  risk, along with the controls implemented to treat it.
- The risk register is reviewed at least quarterly, and immediately after any significant change
  to the organization, its systems, or its threat environment.
- Residual risk (remaining after treatment) is documented and formally accepted by an appropriate
  risk owner.

ROLES & RESPONSIBILITIES
- Risk owners: assess, treat, and monitor the risks assigned to them.
- Information Security Owner: maintains the risk register and reports on overall risk posture to
  management.
- Executive management: accepts residual risk where treatment does not eliminate it entirely.

REVIEW
This policy is reviewed at least annually.""",
    },
]

POLICY_TEMPLATES_BY_SLUG = {t['slug']: t for t in POLICY_TEMPLATES}

assert len(POLICY_TEMPLATES_BY_SLUG) == len(POLICY_TEMPLATES), 'duplicate policy template slug'
