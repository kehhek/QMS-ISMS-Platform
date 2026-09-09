import React, { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'

// A real, styled dialog — not the browser's native window.prompt(), which
// never masks a password field (it's always plain, visible text) and
// looks like something out of 2005 next to the rest of this app. This is
// a drop-in replacement at call sites: `await requestInput({...})`
// resolves to `{ [fieldName]: value }` on confirm, or `null` on cancel —
// the same "one call, get an answer" ergonomics as window.prompt(), just
// backed by a real React dialog instead of the browser chrome.
function PromptDialog({ title, message, fields, confirmLabel, danger, onSubmit, onCancel }) {
  const [values, setValues] = useState(() => Object.fromEntries(fields.map((f) => [f.name, ''])))
  const firstInputRef = useRef(null)

  useEffect(() => {
    firstInputRef.current?.focus()
    const onKeyDown = (e) => { if (e.key === 'Escape') onCancel() }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
    // eslint-disable-next-line
  }, [])

  const missingRequired = fields.some((f) => f.required && !values[f.name])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (missingRequired) return
    onSubmit(values)
  }

  return (
    <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel() }}>
      <form className="modal-dialog" onSubmit={handleSubmit}>
        <h3 className="modal-title">{title}</h3>
        {message && <p className="modal-message">{message}</p>}
        {fields.map((f, i) => (
          <div className="modal-field" key={f.name}>
            <label className="modal-field-label" htmlFor={`prompt-dialog-${f.name}`}>{f.label}</label>
            {f.type === 'textarea' ? (
              <textarea
                id={`prompt-dialog-${f.name}`}
                ref={i === 0 ? firstInputRef : undefined}
                rows={3}
                value={values[f.name]}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                required={f.required}
              />
            ) : (
              <input
                id={`prompt-dialog-${f.name}`}
                ref={i === 0 ? firstInputRef : undefined}
                type={f.type || 'text'}
                autoComplete={f.type === 'password' ? 'current-password' : 'off'}
                value={values[f.name]}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                required={f.required}
              />
            )}
          </div>
        ))}
        <div className="modal-actions">
          <button type="button" onClick={onCancel}>Cancel</button>
          <button type="submit" className={danger ? 'btn-danger' : 'btn-primary'} disabled={missingRequired}>
            {confirmLabel || 'Confirm'}
          </button>
        </div>
      </form>
    </div>
  )
}

/**
 * Mounts a PromptDialog on demand and resolves once the user acts on it.
 * @param {{
 *   title: string, message?: string, confirmLabel?: string, danger?: boolean,
 *   fields: Array<{name: string, label: string, type?: 'text'|'password'|'textarea', required?: boolean}>,
 * }} options
 * @returns {Promise<Record<string, string> | null>} field values, or null if cancelled.
 */
export function requestInput(options) {
  return new Promise((resolve) => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)

    const cleanup = (result) => {
      root.unmount()
      container.remove()
      resolve(result)
    }

    root.render(
      <PromptDialog
        {...options}
        onSubmit={(values) => cleanup(values)}
        onCancel={() => cleanup(null)}
      />,
    )
  })
}

// The specific, recurring case: re-entering your password as a 21 CFR
// Part 11 §11.200 electronic signature, optionally alongside a notes
// field (e.g. CAPA effectiveness verification) — every signing call site
// in the app wants exactly this shape.
export function requestSignature({ title, message, notesField, confirmLabel, danger }) {
  const fields = [{ name: 'password', label: 'Password', type: 'password', required: true }]
  if (notesField) fields.push({ name: notesField.name, label: notesField.label, type: 'textarea' })
  return requestInput({
    title,
    message: message || 'This is your electronic signature — it will be permanently recorded.',
    fields,
    confirmLabel,
    danger,
  })
}
