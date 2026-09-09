import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'
import { requestSignature } from './PromptDialog'

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
        // Full list, for resolving titles in the workflow cards below —
        // but only a Draft can actually be submitted for review (see
        // WorkflowViewSet.perform_create), so that's all the picker offers.
        const docs = unwrapList(data)
        setDocuments(docs)
        const draftDocs = docs.filter((d) => d.status === 'draft')
        if (draftDocs.length && !documentId) setDocumentId(String(draftDocs[0].id))
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

  const decide = async (stepId, decision) => {
    // 21 CFR Part 11 §11.200: signing requires re-entering your password
    // at the moment of signing — being logged in isn't enough on its own.
    const result = await requestSignature({
      title: decision === 'approved' ? 'Approve this step' : 'Reject this step',
      danger: decision === 'rejected',
      confirmLabel: decision === 'approved' ? 'Approve' : 'Reject',
    })
    if (!result) return
    apiFetch(`/workflow-steps/${stepId}/decide/`, token, {
      method: 'POST',
      body: JSON.stringify({ decision, password: result.password }),
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
        <p className="panel-hint">
          Starting a workflow here is "submit for review" — it moves the document to In review
          immediately and requires a real Draft; a rejected step sends it back to Draft for rework,
          and every approval requires re-entering your password as an electronic signature.
        </p>
        {documents.filter((d) => d.status === 'draft').length === 0 ? (
          <p className="empty-state">No Draft documents available to submit for review.</p>
        ) : (
          <div style={{ marginBottom: 10 }}>
            <span className="field-label">Document:</span>
            <select value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
              {documents.filter((d) => d.status === 'draft').map((d) => (
                <option key={d.id} value={d.id}>{d.title}</option>
              ))}
            </select>
          </div>
        )}
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
        <button type="submit" className="btn-primary" disabled={documents.filter((d) => d.status === 'draft').length === 0}>
          Submit for review
        </button>
        <ExportCsvButton token={token} path="/workflows/" filename="workflows.csv" />
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
                        <div className="cell-actions">
                          <button onClick={() => decide(step.id, 'approved')}>Approve</button>
                          <button onClick={() => decide(step.id, 'rejected')}>Reject</button>
                        </div>
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
