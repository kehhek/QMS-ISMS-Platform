import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

const ALL_ROLES = ['admin', 'auditor', 'user']
const GATEABLE_ENTITIES = [
  { value: 'workflow_step', label: 'Document approval (workflow step)' },
  { value: 'corrective_action', label: 'Corrective/Preventive Action (close)' },
]

function RoleCell({ roles }) {
  if (!Array.isArray(roles)) return <span>{String(roles)}</span>
  if (roles.length === 0) return <span className="empty-state" style={{ padding: 0 }}>none</span>
  return (
    <>
      {roles.map((r) => (
        <span
          key={r}
          className={`badge ${ALL_ROLES.includes(r) ? 'badge-neutral' : 'badge-warning'}`}
          style={{ marginRight: 4 }}
        >
          {r}
        </span>
      ))}
    </>
  )
}

function ApprovalGateRules({ token }) {
  const [rules, setRules] = useState([])
  const [error, setError] = useState(null)

  const load = () => {
    apiFetch('/approval-matrix-rules/', token)
      .then((data) => setRules(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => { if (token) load() }, [token]) // eslint-disable-line

  const ruleFor = (entityType) => rules.find((r) => r.entity_type === entityType)

  const saveRule = (entityType, changes) => {
    const existing = ruleFor(entityType)
    const req = existing
      ? apiFetch(`/approval-matrix-rules/${existing.id}/`, token, { method: 'PATCH', body: JSON.stringify(changes) })
      : apiFetch('/approval-matrix-rules/', token, {
          method: 'POST',
          body: JSON.stringify({ entity_type: entityType, required_role: 'admin', active: true, ...changes }),
        })
    req.then(() => { setError(null); load() }).catch((err) => setError(err.message))
  }

  return (
    <div style={{ marginTop: 24 }}>
      <h4>Additional Approval Gates (admin)</h4>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        An OPTIONAL extra sign-off gate layered on top of an existing signed action — off by
        default. When active, the named role must record an approval (below) before that action
        is allowed through.
      </p>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Active</th>
            <th>Required role</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {GATEABLE_ENTITIES.map((entity) => {
            const rule = ruleFor(entity.value)
            return (
              <tr key={entity.value}>
                <td>{entity.label}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={rule ? rule.active : false}
                    onChange={(e) => saveRule(entity.value, { active: e.target.checked })}
                  />
                </td>
                <td>
                  <select
                    value={rule ? rule.required_role : 'admin'}
                    onChange={(e) => saveRule(entity.value, { required_role: e.target.value })}
                  >
                    {ALL_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td>{!rule && <span className="empty-state" style={{ padding: 0 }}>not configured yet</span>}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function ApprovalRecords({ token }) {
  const [records, setRecords] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({
    entity_type: GATEABLE_ENTITIES[0].value, object_id: '', document_number: '', review_date: '', password: '',
  })
  // Open (not-yet-closed) CAPAs, fetched only when the entity picker is
  // set to corrective_action — lets the "Record ID" field become a
  // by-title dropdown instead of a raw number nobody looking at the
  // CAPA screen actually knows, which is exactly what made this gate
  // confusing to satisfy in practice.
  const [openCapas, setOpenCapas] = useState(null)

  const load = () => {
    apiFetch('/approval-records/', token)
      .then((data) => setRecords(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => { if (token) load() }, [token]) // eslint-disable-line

  useEffect(() => {
    if (!token || form.entity_type !== 'corrective_action') return
    apiFetch('/corrective-actions/', token)
      .then((data) => setOpenCapas(unwrapList(data).filter((c) => c.status !== 'closed')))
      .catch(() => setOpenCapas(null))
    // eslint-disable-next-line
  }, [token, form.entity_type])

  const submit = (e) => {
    e.preventDefault()
    apiFetch('/approval-records/', token, {
      method: 'POST',
      body: JSON.stringify({ ...form, object_id: Number(form.object_id), review_date: form.review_date || null }),
    })
      .then(() => {
        setForm({ ...form, object_id: '', document_number: '', review_date: '', password: '' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  return (
    <div style={{ marginTop: 24 }}>
      <h4>Record an Approval</h4>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Only the role named above for that gate can record one, and only with your own password —
        the same re-verify-at-signing pattern every other electronic signature in this app uses.
      </p>
      <form onSubmit={submit} className="toolbar">
        <select
          value={form.entity_type}
          onChange={(e) => setForm({ ...form, entity_type: e.target.value, object_id: '' })}
        >
          {GATEABLE_ENTITIES.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
        </select>
        {form.entity_type === 'corrective_action' ? (
          <select
            value={form.object_id}
            onChange={(e) => setForm({ ...form, object_id: e.target.value })}
            style={{ minWidth: 220 }}
            required
          >
            <option value="">
              {openCapas === null ? 'Loading open CAPAs…' : 'Choose a CAPA…'}
            </option>
            {(openCapas || []).map((c) => (
              <option key={c.id} value={c.id}>#{c.id} — {c.title}</option>
            ))}
          </select>
        ) : (
          <input
            placeholder="Record ID"
            type="number"
            value={form.object_id}
            onChange={(e) => setForm({ ...form, object_id: e.target.value })}
            style={{ width: 90 }}
            required
          />
        )}
        <input
          placeholder="Doc number (optional)"
          value={form.document_number}
          onChange={(e) => setForm({ ...form, document_number: e.target.value })}
        />
        <input
          type="date"
          value={form.review_date}
          onChange={(e) => setForm({ ...form, review_date: e.target.value })}
        />
        <input
          type="password"
          placeholder="Your password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
        <button type="submit" className="btn-primary">Record Approval</button>
      </form>
      {records.length === 0 ? (
        <p className="empty-state">No approvals recorded yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Action</th>
              <th>Record ID</th>
              <th>Approved By</th>
              <th>Doc #</th>
              <th>Review date</th>
              <th>Approved at</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id}>
                <td>{GATEABLE_ENTITIES.find((e) => e.value === r.entity_type)?.label || r.entity_type}</td>
                <td>{r.object_id}</td>
                <td>{r.approved_by_username}</td>
                <td>{r.document_number || '—'}</td>
                <td>{r.review_date || '—'}</td>
                <td>{new Date(r.approved_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function ApprovalMatrixPanel({ token }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!token) return
    apiFetch('/approval-matrix/', token).then(setRows).catch((err) => setError(err.message))
  }, [token])

  if (!token) return <p className="empty-state">Set a token above to view the approval matrix.</p>
  if (error) return <p className="error-text">{error}</p>
  if (!rows) return <p className="empty-state">Loading…</p>

  return (
    <div>
      <p className="panel-hint">
        Which tenant roles can create/edit/delete each record type. Read directly off the API's
        own permission wiring, so this can never drift out of sync with what's actually enforced.
        Read access (viewing) is generally open to any tenant member unless noted otherwise.
      </p>
      <table>
        <thead>
          <tr>
            <th>Record type</th>
            <th>Can write (create/edit/delete)</th>
            <th>Can read</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.record_type}>
              <td>{row.record_type}</td>
              <td><RoleCell roles={row.can_write} /></td>
              <td><RoleCell roles={row.can_read} /></td>
            </tr>
          ))}
        </tbody>
      </table>

      <ApprovalGateRules token={token} />
      <ApprovalRecords token={token} />
    </div>
  )
}
