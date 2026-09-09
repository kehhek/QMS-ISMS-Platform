import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch, onAuthExpired } from './api'
import { readStoredToken, writeStoredToken, clearStoredToken } from './tokenStorage'
import LoginForm from './LoginForm'
import AuthLayout from './AuthLayout'
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
import ProfilePanel from './ProfilePanel'

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
  // Not in any NAV_GROUPS — this is a personal account page (name, email,
  // password), not tenant content, so it lives next to Log out in the
  // topbar instead of the content sidebar. Still just a normal TABS
  // entry underneath, same activeKey mechanism as everything else.
  { key: 'profile', label: 'My Profile', Component: ProfilePanel },
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
  const [profile, setProfile] = useState(null)
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

  // Only fetched to decide what the sidebar shows (Administration is
  // admin/superuser only — a plain "user" role never sees it) — the
  // backend is still the actual enforcement; this just avoids showing a
  // menu that would 403 the moment they clicked into it.
  useEffect(() => {
    if (!token) { setProfile(null); return }
    apiFetch('/accounts/me/', token).then(setProfile).catch(() => setProfile(null))
  }, [token])

  const isAdmin = profile && (profile.role === 'admin' || profile.is_superuser)
  const visibleNavGroups = NAV_GROUPS.filter((group) => group.label !== 'Administration' || isAdmin)
  const administrationKeys = NAV_GROUPS.find((g) => g.label === 'Administration').keys

  // Defensive, not the real enforcement (the backend already 403s these
  // for a plain "user" role) — just avoids landing a non-admin on a
  // blank/erroring panel if activeKey was left pointing at one of these
  // from a previous, higher-privileged session in the same browser.
  useEffect(() => {
    if (profile && !isAdmin && administrationKeys.includes(activeKey)) {
      setActiveKey('dashboard')
    }
    // eslint-disable-next-line
  }, [profile, isAdmin, activeKey])

  const activeTab = TABS.find((t) => t.key === activeKey)
  const ActiveComponent = activeTab.Component

  if (!token) {
    return (
      <AuthLayout>
        <LoginForm onLogin={handleLogin} />
      </AuthLayout>
    )
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar-brand">QISMS</div>
        <nav>
          {visibleNavGroups.map((group) => (
            <div className="sidebar-group" key={group.label}>
              <div className="sidebar-group-label">{group.label}</div>
              {group.keys.map((key) => {
                const tab = TABS.find((t) => t.key === key)
                return (
                  <button
                    key={key}
                    className={`sidebar-link${key === 'dashboard' ? ' sidebar-link-dashboard' : ''}${activeKey === key ? ' active' : ''}`}
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
          <div className="cell-actions">
            <button onClick={() => setActiveKey('profile')}>My Profile</button>
            <button onClick={handleLogout}>Log out</button>
          </div>
        </div>
        <div className="panel">
          <ActiveComponent token={token} isAdmin={isAdmin} />
        </div>
      </div>
    </div>
  )
}
