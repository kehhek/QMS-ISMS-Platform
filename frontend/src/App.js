import React, { useState } from 'react'
import RoleManager from './RoleManager'
import TenantSettingsPanel from './TenantSettingsPanel'
import MembersPanel from './MembersPanel'
import DocumentsPanel from './DocumentsPanel'
import RisksPanel from './RisksPanel'
import ControlsPanel from './ControlsPanel'
import IncidentsPanel from './IncidentsPanel'
import AuditsPanel from './AuditsPanel'
import CorrectiveActionsPanel from './CorrectiveActionsPanel'
import EvidencePanel from './EvidencePanel'
import WorkflowsPanel from './WorkflowsPanel'
import AuditLogPanel from './AuditLogPanel'

const TABS = [
  { key: 'documents', label: 'Documents', Component: DocumentsPanel },
  { key: 'workflows', label: 'Approvals', Component: WorkflowsPanel },
  { key: 'risks', label: 'Risks', Component: RisksPanel },
  { key: 'controls', label: 'Controls', Component: ControlsPanel },
  { key: 'incidents', label: 'Incidents', Component: IncidentsPanel },
  { key: 'audits', label: 'Audits', Component: AuditsPanel },
  { key: 'capa', label: 'Corrective Actions', Component: CorrectiveActionsPanel },
  { key: 'evidence', label: 'Evidence', Component: EvidencePanel },
  { key: 'audit-log', label: 'Audit Log', Component: AuditLogPanel },
  { key: 'members', label: 'Members', Component: MembersPanel },
  { key: 'org-settings', label: 'Org Settings', Component: TenantSettingsPanel },
  { key: 'roles', label: 'Global Users (superuser)', Component: RoleManager },
]

export default function App() {
  const [token, setToken] = useState('')
  const [activeKey, setActiveKey] = useState('documents')

  const ActiveComponent = TABS.find((t) => t.key === activeKey).Component

  return (
    <div style={{ padding: 20, fontFamily: 'sans-serif' }}>
      <h1>QMS/ISMS Console (Frontend Stub)</h1>

      <div style={{ marginBottom: 16 }}>
        <input
          placeholder="API Token (from POST /api/accounts/token/)"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          style={{ width: 340 }}
        />
      </div>

      <nav style={{ marginBottom: 16, borderBottom: '1px solid #ccc', paddingBottom: 8 }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveKey(t.key)}
            style={{
              fontWeight: activeKey === t.key ? 'bold' : 'normal',
              marginRight: 8,
              textDecoration: activeKey === t.key ? 'underline' : 'none',
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <ActiveComponent token={token} />
    </div>
  )
}
