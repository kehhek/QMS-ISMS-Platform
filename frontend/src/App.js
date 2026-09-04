import React, { useState } from 'react'
import RoleManager from './RoleManager'
import DocumentsPanel from './DocumentsPanel'
import RisksPanel from './RisksPanel'
import AuditsPanel from './AuditsPanel'
import CorrectiveActionsPanel from './CorrectiveActionsPanel'

const TABS = [
  { key: 'documents', label: 'Documents', Component: DocumentsPanel },
  { key: 'risks', label: 'Risks', Component: RisksPanel },
  { key: 'audits', label: 'Audits', Component: AuditsPanel },
  { key: 'capa', label: 'Corrective Actions', Component: CorrectiveActionsPanel },
  { key: 'roles', label: 'Roles & Users', Component: RoleManager },
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
