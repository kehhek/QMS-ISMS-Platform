import React, { useEffect, useState } from 'react'
import { onAuthExpired } from './api'
import LoginForm from './LoginForm'
import RoleManager from './RoleManager'
import TenantSettingsPanel from './TenantSettingsPanel'
import MembersPanel from './MembersPanel'
import DashboardPanel from './DashboardPanel'
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
  { key: 'dashboard', label: 'Dashboard', Component: DashboardPanel },
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
  const [activeKey, setActiveKey] = useState('dashboard')

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

  if (!token) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <LoginForm onLogin={handleLogin} />
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>QMS/ISMS Console</h1>
        <button onClick={handleLogout}>Log out</button>
      </div>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab${activeKey === t.key ? ' active' : ''}`}
            onClick={() => setActiveKey(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="panel">
        <ActiveComponent token={token} />
      </div>
    </div>
  )
}
