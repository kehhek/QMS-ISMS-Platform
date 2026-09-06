"""Cross-framework control mappings — the actual "this one control
satisfies 3 frameworks at once" differentiator. Represented as themed
groups rather than a flat pairs table: every (framework, identifier) in
the same group is treated as substantially satisfying the same
underlying requirement, so a customer already Implemented on one framework's
version of "access control" can see they're already most of the way to
another framework's version of the same thing.

This is a curated crosswalk, not an official/exhaustive one — real
compliance crosswalks (e.g. NIST's own CSF-to-800-53 mapping) are
maintained the same way: judgment calls about "substantially covers",
not a mechanical one-to-one translation. Identifiers here must match
core/data/control_catalogs.py exactly; core/tests exercise that they do.
"""

CONTROL_MAPPING_GROUPS = [
    {
        'theme': 'Access control & authentication',
        'controls': [
            ('iso27001', 'A.5.15'), ('iso27001', 'A.5.16'), ('iso27001', 'A.8.5'),
            ('soc2', 'CC6.1'), ('soc2', 'CC6.2'), ('soc2', 'CC6.3'),
            ('hipaa', '164.312(a)(1)'), ('hipaa', '164.312(d)'),
            ('pci_dss', 'Req. 7'), ('pci_dss', 'Req. 8'),
            ('nist_csf', 'PR.AA'),
        ],
    },
    {
        'theme': 'Encryption & data security',
        'controls': [
            ('iso27001', 'A.8.24'), ('soc2', 'CC6.7'),
            ('hipaa', '164.312(e)(1)'), ('gdpr', 'Art. 32'),
            ('pci_dss', 'Req. 3'), ('pci_dss', 'Req. 4'),
            ('nist_csf', 'PR.DS'),
        ],
    },
    {
        'theme': 'Incident response',
        'controls': [
            ('soc2', 'CC7.4'), ('hipaa', '164.308(a)(6)'),
            ('gdpr', 'Art. 33'), ('gdpr', 'Art. 34'),
            ('pci_dss', 'Req. 12'),
            ('nist_csf', 'RS.MA'), ('nist_csf', 'RS.CO'), ('nist_csf', 'RS.AN'),
        ],
    },
    {
        'theme': 'Risk assessment',
        'controls': [
            ('soc2', 'CC3.1'), ('soc2', 'CC3.2'),
            ('hipaa', '164.308(a)(1)'), ('gdpr', 'Art. 35'),
            ('nist_csf', 'ID.RA'),
        ],
    },
    {
        'theme': 'Security awareness & training',
        'controls': [
            ('iso27001', 'A.6.3'), ('soc2', 'CC1.4'),
            ('hipaa', '164.308(a)(5)'), ('pci_dss', 'Req. 12'),
            ('nist_csf', 'PR.AT'),
        ],
    },
    {
        'theme': 'Vendor & third-party / business associate management',
        'controls': [
            ('iso27001', 'A.5.19'), ('iso27001', 'A.5.20'), ('soc2', 'CC9.2'),
            ('hipaa', '164.308(b)(1)'), ('hipaa', '164.314(a)(1)'), ('gdpr', 'Art. 28'),
            ('nist_csf', 'GV.SC'),
        ],
    },
    {
        'theme': 'Change management',
        'controls': [
            ('iso27001', 'A.8.32'), ('soc2', 'CC8.1'), ('pci_dss', 'Req. 6'),
            ('nist_csf', 'PR.PS'),
        ],
    },
    {
        'theme': 'Logging & monitoring',
        'controls': [
            ('iso27001', 'A.8.15'), ('iso27001', 'A.8.16'),
            ('soc2', 'CC7.1'), ('soc2', 'CC7.2'),
            ('hipaa', '164.312(b)'), ('pci_dss', 'Req. 10'),
            ('nist_csf', 'DE.CM'), ('nist_csf', 'DE.AE'),
        ],
    },
    {
        'theme': 'Physical security',
        'controls': [
            ('iso27001', 'A.7.1'), ('iso27001', 'A.7.2'), ('soc2', 'CC6.4'),
            ('hipaa', '164.310(a)(1)'), ('pci_dss', 'Req. 9'),
        ],
    },
    {
        'theme': 'Asset management & inventory',
        'controls': [
            ('iso27001', 'A.5.9'), ('hipaa', '164.310(d)(1)'), ('nist_csf', 'ID.AM'),
        ],
    },
    {
        'theme': 'Business continuity & backup',
        'controls': [
            ('iso27001', 'A.5.29'), ('iso27001', 'A.5.30'), ('iso27001', 'A.8.13'),
            ('soc2', 'CC9.1'), ('hipaa', '164.308(a)(7)'),
            ('nist_csf', 'RC.RP'), ('nist_csf', 'RC.CO'),
        ],
    },
    {
        'theme': 'Malware protection',
        'controls': [
            ('iso27001', 'A.8.7'), ('soc2', 'CC6.8'), ('pci_dss', 'Req. 5'),
        ],
    },
    {
        'theme': 'Vulnerability management & security testing',
        'controls': [
            ('iso27001', 'A.8.8'), ('soc2', 'CC4.1'), ('soc2', 'CC4.2'), ('pci_dss', 'Req. 11'),
        ],
    },
    {
        'theme': 'Information security policy',
        'controls': [
            ('iso27001', 'A.5.1'), ('hipaa', '164.316(a)'),
            ('pci_dss', 'Req. 12'), ('nist_csf', 'GV.PO'),
        ],
    },
    {
        'theme': 'Data classification & handling',
        'controls': [
            ('iso27001', 'A.5.12'), ('gdpr', 'Art. 5'), ('gdpr', 'Art. 30'),
        ],
    },
    {
        'theme': 'Governance, roles & oversight',
        'controls': [
            ('iso27001', 'A.5.2'), ('gdpr', 'Art. 37'),
            ('nist_csf', 'GV.RR'), ('nist_csf', 'GV.OV'),
        ],
    },
]


def build_equivalents_index():
    """{(framework, identifier): [(other_framework, other_identifier, theme), ...]}
    — every other control in the same theme group(s), excluding itself.
    A control can appear in more than one group (e.g. encryption also
    touches data classification), so this is built once and reused
    rather than searched linearly per lookup."""
    index = {}
    for group in CONTROL_MAPPING_GROUPS:
        members = group['controls']
        for member in members:
            others = [(f, i, group['theme']) for f, i in members if (f, i) != member]
            index.setdefault(member, []).extend(others)
    return index


EQUIVALENTS_INDEX = build_equivalents_index()
