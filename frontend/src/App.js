import React, { useEffect, useState } from 'react'
import { onAuthExpired } from './api'
import LoginForm from './LoginForm'
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

const TOKEN_STORAGE_KEY = 'mtp_token'

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

function readStoredToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || ''
  } catch {
    // Private browsing / storage disabled — fall back to session-only.
    return ''
  }
}

export default function App() {
  const [token, setToken] = useState(readStoredToken)
  const [activeKey, setActiveKey] = useState('documents')

  const handleLogin = (newToken) => {
    setToken(newToken)
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, newToken)
    } catch {
      // ignore — session-only if storage isn't available
    }
  }

  const handleLogout = () => {
    setToken('')
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    } catch {
      // ignore
    }
  }

  useEffect(() => onAuthExpired(handleLogout), [])

  const ActiveComponent = TABS.find((t) => t.key === activeKey).Component

  return (
    <div style={{ padding: 20, fontFamily: 'sans-serif' }}>
      <h1>QMS/ISMS Console</h1>

      {!token ? (
        <LoginForm onLogin={handleLogin} />
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <button onClick={handleLogout}>Log out</button>
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
        </>
      )}
    </div>
  )
}
