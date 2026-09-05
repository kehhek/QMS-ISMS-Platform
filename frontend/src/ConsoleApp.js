import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { onAuthExpired } from './api'
import { readStoredToken, writeStoredToken, clearStoredToken } from './tokenStorage'
import LoginForm from './LoginForm'
import RoleManager from './RoleManager'
import TenantSettingsPanel from './TenantSettingsPanel'
import MembersPanel from './MembersPanel'
import DashboardPanel from './DashboardPanel'
import DocumentsPanel from './DocumentsPanel'
import RisksPanel from './RisksPanel'
import SupplierPanel from './SupplierPanel'
import ControlsPanel from './ControlsPanel'
import IncidentsPanel from './IncidentsPanel'
import AuditsPanel from './AuditsPanel'
import CorrectiveActionsPanel from './CorrectiveActionsPanel'
import EvidencePanel from './EvidencePanel'
import WorkflowsPanel from './WorkflowsPanel'
import AuditLogPanel from './AuditLogPanel'
import SignaturesPanel from './SignaturesPanel'

const TABS = [
  { key: 'dashboard', label: 'Dashboard', Component: DashboardPanel },
  { key: 'documents', label: 'Documents', Component: DocumentsPanel },
  { key: 'workflows', label: 'Approvals', Component: WorkflowsPanel },
  { key: 'risks', label: 'Risks', Component: RisksPanel },
  { key: 'suppliers', label: 'Suppliers', Component: SupplierPanel },
  { key: 'controls', label: 'Controls', Component: ControlsPanel },
  { key: 'incidents', label: 'Incidents', Component: IncidentsPanel },
  { key: 'audits', label: 'Audits', Component: AuditsPanel },
  { key: 'capa', label: 'Corrective Actions', Component: CorrectiveActionsPanel },
  { key: 'evidence', label: 'Evidence', Component: EvidencePanel },
  { key: 'signatures', label: 'Signatures', Component: SignaturesPanel },
  { key: 'audit-log', label: 'Audit Log', Component: AuditLogPanel },
  { key: 'members', label: 'Members', Component: MembersPanel },
  { key: 'org-settings', label: 'Org Settings', Component: TenantSettingsPanel },
  { key: 'roles', label: 'Global Users (superuser)', Component: RoleManager },
]

export default function ConsoleApp() {
  const [token, setToken] = useState(readStoredToken)
  const [activeKey, setActiveKey] = useState('dashboard')
  const navigate = useNavigate()

  const handleLogin = (newToken) => {
    setToken(newToken)
    writeStoredToken(newToken)
  }

  const handleLogout = () => {
    setToken('')
    clearStoredToken()
    navigate('/')
  }

  useEffect(() => onAuthExpired(() => {
    setToken('')
    clearStoredToken()
  }), [])

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
