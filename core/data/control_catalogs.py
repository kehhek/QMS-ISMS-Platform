"""Standard control catalogs, loaded into a tenant by
`manage.py seed_control_catalogs` (ISO 27001 + SOC 2, auto-seeded on
registration) or on-demand per framework via
ControlViewSet.seed_framework (HIPAA/GDPR/PCI DSS/NIST CSF — see
CATALOGS_BY_FRAMEWORK below, and control_mappings.py for how these
frameworks' controls cross-reference each other).

ISO27001_CONTROLS: all 93 controls of ISO/IEC 27001:2022 Annex A —
37 Organizational (A.5), 8 People (A.6), 14 Physical (A.7), and
34 Technological (A.8) controls. Titles match the published standard.

SOC2_CONTROLS: the 33 Common Criteria (CC1–CC9) from the AICPA Trust
Services Criteria. Unlike ISO 27001, SOC 2 doesn't publish a single
fixed numbered "control list" — a report is built from the Trust
Services Criteria the auditor and entity agree to test. The Common
Criteria are the right default catalog to seed here regardless: they
back the Security category, which is the one category mandatory in
every SOC 2 report (Availability, Confidentiality, Processing
Integrity, and Privacy are each opt-in on top of it).

HIPAA_CONTROLS: the 21 standards of the HIPAA Security Rule (45 CFR
§164.308 Administrative, §164.310 Physical, §164.312 Technical,
§164.314 Organizational, §164.316 Policies/Documentation safeguards).

GDPR_CONTROLS: the Articles most relevant to an ISMS/security program —
not the full regulation (which covers many non-security legal topics),
but the security, accountability, and breach-response provisions a
compliance platform actually tracks.

PCI_DSS_CONTROLS: the 12 top-level requirements of PCI DSS v4.0.

NIST_CSF_CONTROLS: the 22 categories across NIST Cybersecurity
Framework 2.0's 6 functions (Govern, Identify, Protect, Detect,
Respond, Recover) — CSF 2.0 (April 2024) added Govern as a full
function, unlike CSF 1.1.
"""

ISO27001_CONTROLS = [
    # A.5 Organizational controls (37)
    ('A.5.1', 'Policies for information security'),
    ('A.5.2', 'Information security roles and responsibilities'),
    ('A.5.3', 'Segregation of duties'),
    ('A.5.4', 'Management responsibilities'),
    ('A.5.5', 'Contact with authorities'),
    ('A.5.6', 'Contact with special interest groups'),
    ('A.5.7', 'Threat intelligence'),
    ('A.5.8', 'Information security in project management'),
    ('A.5.9', 'Inventory of information and other associated assets'),
    ('A.5.10', 'Acceptable use of information and other associated assets'),
    ('A.5.11', 'Return of assets'),
    ('A.5.12', 'Classification of information'),
    ('A.5.13', 'Labelling of information'),
    ('A.5.14', 'Information transfer'),
    ('A.5.15', 'Access control'),
    ('A.5.16', 'Identity management'),
    ('A.5.17', 'Authentication information'),
    ('A.5.18', 'Access rights'),
    ('A.5.19', 'Information security in supplier relationships'),
    ('A.5.20', 'Addressing information security within supplier agreements'),
    ('A.5.21', 'Managing information security in the ICT supply chain'),
    ('A.5.22', 'Monitoring, review and change management of supplier services'),
    ('A.5.23', 'Information security for use of cloud services'),
    ('A.5.24', 'Information security incident management planning and preparation'),
    ('A.5.25', 'Assessment and decision on information security events'),
    ('A.5.26', 'Response to information security incidents'),
    ('A.5.27', 'Learning from information security incidents'),
    ('A.5.28', 'Collection of evidence'),
    ('A.5.29', 'Information security during disruption'),
    ('A.5.30', 'ICT readiness for business continuity'),
    ('A.5.31', 'Legal, statutory, regulatory and contractual requirements'),
    ('A.5.32', 'Intellectual property rights'),
    ('A.5.33', 'Protection of records'),
    ('A.5.34', 'Privacy and protection of PII'),
    ('A.5.35', 'Independent review of information security'),
    ('A.5.36', 'Compliance with policies, rules and standards for information security'),
    ('A.5.37', 'Documented operating procedures'),

    # A.6 People controls (8)
    ('A.6.1', 'Screening'),
    ('A.6.2', 'Terms and conditions of employment'),
    ('A.6.3', 'Information security awareness, education and training'),
    ('A.6.4', 'Disciplinary process'),
    ('A.6.5', 'Responsibilities after termination or change of employment'),
    ('A.6.6', 'Confidentiality or non-disclosure agreements'),
    ('A.6.7', 'Remote working'),
    ('A.6.8', 'Information security event reporting'),

    # A.7 Physical controls (14)
    ('A.7.1', 'Physical security perimeters'),
    ('A.7.2', 'Physical entry'),
    ('A.7.3', 'Securing offices, rooms and facilities'),
    ('A.7.4', 'Physical security monitoring'),
    ('A.7.5', 'Protecting against physical and environmental threats'),
    ('A.7.6', 'Working in secure areas'),
    ('A.7.7', 'Clear desk and clear screen'),
    ('A.7.8', 'Equipment siting and protection'),
    ('A.7.9', 'Security of assets off-premises'),
    ('A.7.10', 'Storage media'),
    ('A.7.11', 'Supporting utilities'),
    ('A.7.12', 'Cabling security'),
    ('A.7.13', 'Equipment maintenance'),
    ('A.7.14', 'Secure disposal or re-use of equipment'),

    # A.8 Technological controls (34)
    ('A.8.1', 'User endpoint devices'),
    ('A.8.2', 'Privileged access rights'),
    ('A.8.3', 'Information access restriction'),
    ('A.8.4', 'Access to source code'),
    ('A.8.5', 'Secure authentication'),
    ('A.8.6', 'Capacity management'),
    ('A.8.7', 'Protection against malware'),
    ('A.8.8', 'Management of technical vulnerabilities'),
    ('A.8.9', 'Configuration management'),
    ('A.8.10', 'Information deletion'),
    ('A.8.11', 'Data masking'),
    ('A.8.12', 'Data leakage prevention'),
    ('A.8.13', 'Information backup'),
    ('A.8.14', 'Redundancy of information processing facilities'),
    ('A.8.15', 'Logging'),
    ('A.8.16', 'Monitoring activities'),
    ('A.8.17', 'Clock synchronization'),
    ('A.8.18', 'Use of privileged utility programs'),
    ('A.8.19', 'Installation of software on operational systems'),
    ('A.8.20', 'Networks security'),
    ('A.8.21', 'Security of network services'),
    ('A.8.22', 'Segregation of networks'),
    ('A.8.23', 'Web filtering'),
    ('A.8.24', 'Use of cryptography'),
    ('A.8.25', 'Secure development life cycle'),
    ('A.8.26', 'Application security requirements'),
    ('A.8.27', 'Secure system architecture and engineering principles'),
    ('A.8.28', 'Secure coding'),
    ('A.8.29', 'Security testing in development and acceptance'),
    ('A.8.30', 'Outsourced development'),
    ('A.8.31', 'Separation of development, test and production environments'),
    ('A.8.32', 'Change management'),
    ('A.8.33', 'Test information'),
    ('A.8.34', 'Protection of information systems during audit testing'),
]

assert len(ISO27001_CONTROLS) == 93

SOC2_CONTROLS = [
    # CC1: Control Environment (5)
    ('CC1.1', 'The entity demonstrates a commitment to integrity and ethical values'),
    ('CC1.2', 'The board of directors demonstrates independence from management and exercises oversight of internal control'),
    ('CC1.3', 'Management establishes, with board oversight, structures, reporting lines, and appropriate authorities and responsibilities'),
    ('CC1.4', 'The entity demonstrates a commitment to attract, develop, and retain competent individuals'),
    ('CC1.5', 'The entity holds individuals accountable for their internal control responsibilities'),

    # CC2: Communication and Information (3)
    ('CC2.1', 'The entity obtains or generates and uses relevant, quality information to support internal control'),
    ('CC2.2', 'The entity internally communicates information necessary to support the functioning of internal control'),
    ('CC2.3', 'The entity communicates with external parties regarding matters affecting internal control'),

    # CC3: Risk Assessment (4)
    ('CC3.1', 'The entity specifies objectives with sufficient clarity to enable identification and assessment of risks'),
    ('CC3.2', 'The entity identifies and analyzes risks to the achievement of its objectives'),
    ('CC3.3', 'The entity considers the potential for fraud in assessing risks'),
    ('CC3.4', 'The entity identifies and assesses changes that could significantly impact internal control'),

    # CC4: Monitoring Activities (2)
    ('CC4.1', 'The entity performs ongoing and/or separate evaluations of internal control components'),
    ('CC4.2', 'The entity evaluates and communicates internal control deficiencies in a timely manner'),

    # CC5: Control Activities (3)
    ('CC5.1', 'The entity selects and develops control activities that mitigate risks to an acceptable level'),
    ('CC5.2', 'The entity selects and develops general control activities over technology'),
    ('CC5.3', 'The entity deploys control activities through policies and procedures'),

    # CC6: Logical and Physical Access Controls (8)
    ('CC6.1', 'The entity implements logical access security software, infrastructure, and architectures over protected information assets'),
    ('CC6.2', 'The entity registers and authorizes new internal and external users prior to issuing system credentials'),
    ('CC6.3', 'The entity authorizes, modifies, or removes access based on roles, responsibilities, or the system design'),
    ('CC6.4', 'The entity restricts physical access to facilities and protected information assets'),
    ('CC6.5', 'The entity discontinues logical and physical protections over assets only after their ability to read or recover data has been diminished'),
    ('CC6.6', 'The entity implements logical access security measures to protect against threats from outside its system boundaries'),
    ('CC6.7', 'The entity restricts the transmission, movement, and removal of information to authorized users and processes'),
    ('CC6.8', 'The entity implements controls to prevent or detect and act upon the introduction of unauthorized or malicious software'),

    # CC7: System Operations (5)
    ('CC7.1', 'The entity uses detection and monitoring procedures to identify security events'),
    ('CC7.2', 'The entity monitors system components and the operation of controls to detect anomalies'),
    ('CC7.3', 'The entity evaluates security events to determine whether they represent a security incident'),
    ('CC7.4', 'The entity responds to identified security incidents'),
    ('CC7.5', 'The entity identifies, develops, and implements activities to recover from security incidents'),

    # CC8: Change Management (1)
    ('CC8.1', 'The entity authorizes, designs, develops, configures, documents, tests, approves, and implements changes to infrastructure, data, software, and procedures'),

    # CC9: Risk Mitigation (2)
    ('CC9.1', 'The entity identifies, selects, and develops risk mitigation activities for risks arising from potential business disruptions'),
    ('CC9.2', 'The entity assesses and manages risks associated with vendors and business partners'),
]

assert len(SOC2_CONTROLS) == 33

HIPAA_CONTROLS = [
    # Administrative Safeguards — §164.308 (9)
    ('164.308(a)(1)', 'Security Management Process'),
    ('164.308(a)(2)', 'Assigned Security Responsibility'),
    ('164.308(a)(3)', 'Workforce Security'),
    ('164.308(a)(4)', 'Information Access Management'),
    ('164.308(a)(5)', 'Security Awareness and Training'),
    ('164.308(a)(6)', 'Security Incident Procedures'),
    ('164.308(a)(7)', 'Contingency Plan'),
    ('164.308(a)(8)', 'Evaluation'),
    ('164.308(b)(1)', 'Business Associate Contracts and Other Arrangements'),

    # Physical Safeguards — §164.310 (4)
    ('164.310(a)(1)', 'Facility Access Controls'),
    ('164.310(b)', 'Workstation Use'),
    ('164.310(c)', 'Workstation Security'),
    ('164.310(d)(1)', 'Device and Media Controls'),

    # Technical Safeguards — §164.312 (5)
    ('164.312(a)(1)', 'Access Control'),
    ('164.312(b)', 'Audit Controls'),
    ('164.312(c)(1)', 'Integrity'),
    ('164.312(d)', 'Person or Entity Authentication'),
    ('164.312(e)(1)', 'Transmission Security'),

    # Organizational Requirements — §164.314 (1)
    ('164.314(a)(1)', 'Business Associate Contracts or Other Arrangements'),

    # Policies, Procedures, and Documentation — §164.316 (2)
    ('164.316(a)', 'Policies and Procedures'),
    ('164.316(b)(1)', 'Documentation'),
]

assert len(HIPAA_CONTROLS) == 21

GDPR_CONTROLS = [
    ('Art. 5', 'Principles relating to processing of personal data'),
    ('Art. 6', 'Lawfulness of processing'),
    ('Art. 12-14', 'Transparency and information to be provided to data subjects'),
    ('Art. 15', 'Right of access by the data subject'),
    ('Art. 17', 'Right to erasure ("right to be forgotten")'),
    ('Art. 24', 'Responsibility of the controller'),
    ('Art. 25', 'Data protection by design and by default'),
    ('Art. 28', 'Processor obligations'),
    ('Art. 30', 'Records of processing activities'),
    ('Art. 32', 'Security of processing'),
    ('Art. 33', 'Notification of a personal data breach to the supervisory authority'),
    ('Art. 34', 'Communication of a personal data breach to the data subject'),
    ('Art. 35', 'Data protection impact assessment'),
    ('Art. 37', 'Designation of the data protection officer'),
]

assert len(GDPR_CONTROLS) == 14

PCI_DSS_CONTROLS = [
    ('Req. 1', 'Install and Maintain Network Security Controls'),
    ('Req. 2', 'Apply Secure Configurations to All System Components'),
    ('Req. 3', 'Protect Stored Account Data'),
    ('Req. 4', 'Protect Cardholder Data with Strong Cryptography During Transmission'),
    ('Req. 5', 'Protect All Systems and Networks from Malicious Software'),
    ('Req. 6', 'Develop and Maintain Secure Systems and Software'),
    ('Req. 7', 'Restrict Access to System Components and Cardholder Data by Business Need to Know'),
    ('Req. 8', 'Identify Users and Authenticate Access to System Components'),
    ('Req. 9', 'Restrict Physical Access to Cardholder Data'),
    ('Req. 10', 'Log and Monitor All Access to System Components and Cardholder Data'),
    ('Req. 11', 'Test Security of Systems and Networks Regularly'),
    ('Req. 12', 'Support Information Security with Organizational Policies and Programs'),
]

assert len(PCI_DSS_CONTROLS) == 12

NIST_CSF_CONTROLS = [
    # Govern (6)
    ('GV.OC', 'Organizational Context'),
    ('GV.RM', 'Risk Management Strategy'),
    ('GV.RR', 'Roles, Responsibilities, and Authorities'),
    ('GV.PO', 'Policy'),
    ('GV.OV', 'Oversight'),
    ('GV.SC', 'Cybersecurity Supply Chain Risk Management'),

    # Identify (3)
    ('ID.AM', 'Asset Management'),
    ('ID.RA', 'Risk Assessment'),
    ('ID.IM', 'Improvement'),

    # Protect (5)
    ('PR.AA', 'Identity Management, Authentication, and Access Control'),
    ('PR.AT', 'Awareness and Training'),
    ('PR.DS', 'Data Security'),
    ('PR.PS', 'Platform Security'),
    ('PR.IR', 'Technology Infrastructure Resilience'),

    # Detect (2)
    ('DE.CM', 'Continuous Monitoring'),
    ('DE.AE', 'Adverse Event Analysis'),

    # Respond (4)
    ('RS.MA', 'Incident Management'),
    ('RS.AN', 'Incident Analysis'),
    ('RS.CO', 'Incident Response Reporting and Communication'),
    ('RS.MI', 'Incident Mitigation'),

    # Recover (2)
    ('RC.RP', 'Incident Recovery Plan Execution'),
    ('RC.CO', 'Incident Recovery Communication'),
]

assert len(NIST_CSF_CONTROLS) == 22

# Generic seeding target — ControlViewSet.seed_framework looks up its
# `?framework=` argument here rather than a long if/elif chain, and
# adding a 5th/6th framework later is just one more entry.
CATALOGS_BY_FRAMEWORK = {
    'iso27001': ISO27001_CONTROLS,
    'soc2': SOC2_CONTROLS,
    'hipaa': HIPAA_CONTROLS,
    'gdpr': GDPR_CONTROLS,
    'pci_dss': PCI_DSS_CONTROLS,
    'nist_csf': NIST_CSF_CONTROLS,
}


def seed_framework_into_current_schema(framework):
    """Loads one framework's catalog into whatever tenant schema is
    currently active on the connection — same idempotent get_or_create
    pattern as `manage.py seed_control_catalogs` (which only ever loads
    ISO 27001 + SOC 2, at registration). This is the on-demand path for
    the other four, called from ControlViewSet.seed_framework when a
    tenant decides to pursue an additional certification. Returns
    (added_count, total_count) for that framework in this schema."""
    from core.models import Control

    catalog = CATALOGS_BY_FRAMEWORK.get(framework)
    if catalog is None:
        raise ValueError(f'Unknown framework: {framework}')

    added = 0
    for identifier, name in catalog:
        _, created = Control.objects.get_or_create(framework=framework, identifier=identifier, defaults={'name': name})
        added += int(created)
    total = Control.objects.filter(framework=framework).count()
    return added, total
