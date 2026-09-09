import { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

// Shared list/create/edit/delete plumbing for a simple REST resource
// panel. Each panel still owns its own form fields and table columns —
// this only removes the load/create/edit/delete boilerplate that used to
// be duplicated (with edit+delete simply missing) across most panels,
// e.g. RisksPanel/IncidentsPanel/AuditsPanel/EvidencePanel previously
// only supported create+list.
export default function useCrudPanel(path, token, emptyForm) {
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)

  const load = () => {
    apiFetch(path, token)
      .then((data) => setItems(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const create = (payload) => {
    apiFetch(path, token, { method: 'POST', body: JSON.stringify(payload !== undefined ? payload : form) })
      .then(() => {
        setForm(emptyForm)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const startEdit = (item) => {
    setEditingId(item.id)
    setEditForm({ ...item })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditForm(null)
  }

  const saveEdit = (overrides) => {
    // Every current call site wires this up as `onClick={() => saveEdit()}`,
    // but `onClick={saveEdit}` (passing the function itself, not a call)
    // is an easy, natural-looking mistake given `overrides` is optional —
    // React then hands this a SyntheticEvent as `overrides`, and
    // spreading that into the PATCH body used to crash with
    // "JSON.stringify cannot serialize cyclic structures" (an event
    // object contains circular internal references). Guard against that
    // exact shape rather than trusting every caller to remember the
    // arrow-wrap.
    const safeOverrides = overrides && typeof overrides === 'object' && !overrides.nativeEvent ? overrides : undefined
    apiFetch(`${path}${editingId}/`, token, {
      method: 'PATCH',
      body: JSON.stringify(safeOverrides ? { ...editForm, ...safeOverrides } : editForm),
    })
      .then(() => {
        setEditingId(null)
        setEditForm(null)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const remove = (item, label) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Delete ${label || 'this item'}? This can't be undone.`)) return
    apiFetch(`${path}${item.id}/`, token, { method: 'DELETE' })
      .then(() => {
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  return {
    items, error, setError, load,
    form, setForm, create,
    editingId, editForm, setEditForm, startEdit, cancelEdit, saveEdit,
    remove,
  }
}
