"""Standard control catalogs, loaded into a tenant by
`manage.py seed_control_catalogs`.

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
