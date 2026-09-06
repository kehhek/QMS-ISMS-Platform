import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { onAuthExpired } from './api'
import { readStoredToken, writeStoredToken, clearStoredToken } from './tokenStorage'
import LoginForm from './LoginForm'
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
import IsmsCalendarPanel from './IsmsCalendarPanel'
import AccessRegisterPanel from './AccessRegisterPanel'
import ApprovalMatrixPanel from './ApprovalMatrixPanel'
import SecurityAwarenessPanel from './SecurityAwarenessPanel'
import AssetsPanel from './AssetsPanel'
import NonconformancesPanel from './NonconformancesPanel'
import PolicyPanel from './PolicyPanel'
import SopPanel from './SopPanel'
import WorkInstructionPanel from './WorkInstructionPanel'
import UserGroupsPanel from './UserGroupsPanel'
import AuditorAccessPanel from './AuditorAccessPanel'
import IntegrationsPanel from './IntegrationsPanel'

const TABS = [
  { key: 'dashboard', label: 'Dashboard', Component: DashboardPanel },
  { key: 'calendar', label: 'ISMS Calendar', Component: IsmsCalendarPanel },
  { key: 'documents', label: 'Documents', Component: DocumentsPanel },
  { key: 'policies', label: 'Policies', Component: PolicyPanel },
  { key: 'sops', label: 'SOPs', Component: SopPanel },
  { key: 'work-instructions', label: 'Work Instructions', Component: WorkInstructionPanel },
  { key: 'workflows', label: 'Approvals', Component: WorkflowsPanel },
  { key: 'signatures', label: 'Signatures', Component: SignaturesPanel },
  { key: 'risks', label: 'Risks', Component: RisksPanel },
  { key: 'assets', label: 'Assets', Component: AssetsPanel },
  { key: 'suppliers', label: 'Suppliers', Component: SupplierPanel },
  { key: 'controls', label: 'Controls', Component: ControlsPanel },
  { key: 'incidents', label: 'Incidents', Component: IncidentsPanel },
  { key: 'nonconformances', label: 'Nonconformances', Component: NonconformancesPanel },
  { key: 'capa', label: 'Corrective Actions', Component: CorrectiveActionsPanel },
  { key: 'audits', label: 'Audits', Component: AuditsPanel },
  { key: 'awareness', label: 'Security Awareness', Component: SecurityAwarenessPanel },
  { key: 'evidence', label: 'Evidence', Component: EvidencePanel },
  { key: 'audit-log', label: 'Audit Log', Component: AuditLogPanel },
  { key: 'auditor-access', label: 'Auditor Access', Component: AuditorAccessPanel },
  { key: 'integrations', label: 'Integrations', Component: IntegrationsPanel },
  { key: 'members', label: 'Members', Component: MembersPanel },
  { key: 'user-groups', label: 'User Groups', Component: UserGroupsPanel },
  { key: 'access-register', label: 'Access Register', Component: AccessRegisterPanel },
  { key: 'approval-matrix', label: 'Approval Matrix', Component: ApprovalMatrixPanel },
  { key: 'org-settings', label: 'Org Settings', Component: TenantSettingsPanel },
]

// Purely a presentation grouping for the sidebar — TABS above stays the
// single source of truth for what each key renders; this just says how
// to organize the same keys into sections instead of one flat 20-item row.
const NAV_GROUPS = [
  { label: 'Overview', keys: ['dashboard', 'calendar'] },
  { label: 'Documents & Approvals', keys: ['documents', 'policies', 'sops', 'work-instructions', 'workflows', 'signatures'] },
  { label: 'Risk & Assets', keys: ['risks', 'assets', 'suppliers'] },
  { label: 'Compliance', keys: ['controls', 'integrations', 'incidents', 'nonconformances', 'capa', 'audits', 'awareness'] },
  { label: 'Evidence & Records', keys: ['evidence', 'audit-log', 'auditor-access'] },
  { label: 'Administration', keys: ['members', 'user-groups', 'access-register', 'approval-matrix', 'org-settings'] },
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

  const activeTab = TABS.find((t) => t.key === activeKey)
  const ActiveComponent = activeTab.Component

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
      <aside className="app-sidebar">
        <div className="app-sidebar-brand">QMS/ISMS Console</div>
        <nav>
          {NAV_GROUPS.map((group) => (
            <div className="sidebar-group" key={group.label}>
              <div className="sidebar-group-label">{group.label}</div>
              {group.keys.map((key) => {
                const tab = TABS.find((t) => t.key === key)
                return (
                  <button
                    key={key}
                    className={`sidebar-link${activeKey === key ? ' active' : ''}`}
                    onClick={() => setActiveKey(key)}
                  >
                    {tab.label}
                  </button>
                )
              })}
              {/* Not a tab — /trust is a public, unauthenticated page (no
                  token, nothing to render inside the console shell), so it
                  opens in a new tab instead of swapping the active panel. */}
              {group.label === 'Administration' && (
                <a href="/trust" target="_blank" rel="noreferrer" className="sidebar-link">
                  Trust Center ↗
                </a>
              )}
            </div>
          ))}
        </nav>
      </aside>

      <div className="app-main">
        <div className="app-topbar">
          <h1>{activeTab.label}</h1>
          <button onClick={handleLogout}>Log out</button>
        </div>
        <div className="panel">
          <ActiveComponent token={token} />
        </div>
      </div>
    </div>
  )
}
