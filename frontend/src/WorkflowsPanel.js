import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'

const ROLE_OPTIONS = ['admin', 'auditor', 'user']

export default function WorkflowsPanel({ token }) {
  const [workflows, setWorkflows] = useState([])
  const [documents, setDocuments] = useState([])
  const [error, setError] = useState(null)
  const [documentId, setDocumentId] = useState('')
  const [steps, setSteps] = useState([{ order: 1, approver_role: 'admin' }])

  const load = () => {
    apiFetch('/workflows/', token)
      .then((data) => setWorkflows(unwrapList(data)))
      .catch((err) => setError(err.message))
    apiFetch('/documents/', token)
      .then((data) => {
        const docs = unwrapList(data)
        setDocuments(docs)
        if (docs.length && !documentId) setDocumentId(String(docs[0].id))
      })
      .catch(() => setDocuments([]))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const addStep = () => setSteps([...steps, { order: steps.length + 1, approver_role: 'admin' }])
  const updateStepRole = (i, role) =>
    setSteps(steps.map((s, idx) => (idx === i ? { ...s, approver_role: role } : s)))

  const createWorkflow = (e) => {
    e.preventDefault()
    apiFetch('/workflows/', token, {
      method: 'POST',
      body: JSON.stringify({ document: Number(documentId), new_steps: steps }),
    })
      .then(() => {
        setSteps([{ order: 1, approver_role: 'admin' }])
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const decide = (stepId, decision) => {
    apiFetch(`/workflow-steps/${stepId}/decide/`, token, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    })
      .then(() => {
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view workflows.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}

      <form onSubmit={createWorkflow} className="panel" style={{ marginBottom: 20, padding: 14 }}>
        <div style={{ marginBottom: 10 }}>
          <span className="field-label">Document:</span>
          <select value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>{d.title} ({d.status})</option>
            ))}
          </select>
        </div>
        <div style={{ marginBottom: 10, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
          <span className="field-label">Approval steps (in order):</span>
          {steps.map((s, i) => (
            <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              {i + 1}.
              <select value={s.approver_role} onChange={(e) => updateStepRole(i, e.target.value)}>
                {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </span>
          ))}
          <button type="button" onClick={addStep}>+ Add Step</button>
        </div>
        <button type="submit" className="btn-primary">Start Approval Workflow</button>
      </form>

      {workflows.length === 0 ? (
        <p className="empty-state">No approval workflows yet.</p>
      ) : (
        workflows.map((wf) => (
          <div key={wf.id} className="workflow-card">
            <div className="workflow-card-header">
              <strong>{documents.find((d) => d.id === wf.document)?.title || `Document #${wf.document}`}</strong>
              <StatusBadge value={wf.status} />
            </div>
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Required role</th>
                  <th>Status</th>
                  <th>Decided by</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {wf.steps.map((step) => (
                  <tr key={step.id}>
                    <td>{step.order}</td>
                    <td>{step.approver_username || step.approver_role}</td>
                    <td><StatusBadge value={step.status} /></td>
                    <td>{step.decided_by_username || '—'}</td>
                    <td>
                      {step.status === 'pending' && (
                        <>
                          <button onClick={() => decide(step.id, 'approved')} style={{ marginRight: 4 }}>
                            Approve
                          </button>
                          <button onClick={() => decide(step.id, 'rejected')}>Reject</button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  )
}
