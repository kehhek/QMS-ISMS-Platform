const API_BASE = '/api'

// A stale/revoked token means every call starts 401ing. Broadcasting this
// (rather than each of a dozen panels handling it separately) lets App.js
// react once, in one place, by logging the user out back to the login form.
const AUTH_EXPIRED_EVENT = 'mtp:auth-expired'

export function onAuthExpired(handler) {
  window.addEventListener(AUTH_EXPIRED_EVENT, handler)
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handler)
}

function authHeaders(token, extra) {
  return {
    ...(token ? { Authorization: `Token ${token}` } : {}),
    ...(extra || {}),
  }
}

// DRF validation errors come back as {field: ["message", ...], ...} — not
// a {detail} — so the old fallback of JSON.stringify(data) showed the raw
// JSON verbatim (e.g. {"title":["This field may not be blank."]}) instead
// of a readable message. Render field-level errors as "field: message".
export function formatApiError(data, fallback) {
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  if (Array.isArray(data)) return data.join(' ')
  if (typeof data === 'object') {
    const parts = Object.entries(data).map(([field, messages]) => {
      const text = Array.isArray(messages) ? messages.join(' ') : messages
      return field === 'non_field_errors' ? text : `${field}: ${text}`
    })
    if (parts.length) return parts.join(' — ')
  }
  return fallback
}

async function handleResponse(r) {
  const data = await r.json().catch(() => null)
  if (!r.ok) {
    if (r.status === 401) {
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    }
    throw new Error(formatApiError(data, r.statusText))
  }
  return data
}

export function apiFetch(path, token, options = {}) {
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: authHeaders(token, {
      // FormData sets its own multipart Content-Type (with boundary) —
      // setting it manually here would break the upload.
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {}),
    }),
  }).then(handleResponse)
}

// For following DRF pagination's `next`/`previous` links. DRF builds these
// as full absolute URLs (scheme+host+path) from whatever Host header
// reached Django — in dev that's host.docker.internal (the CRA proxy
// rewrites Host to its target when forwarding), a name the browser itself
// can't resolve at all, so fetching the link verbatim fails outright.
// Every other call in this app goes through a same-origin relative path
// instead (see downloadFile's comment on raw URLs) — drop the scheme+host
// here too and keep only path+query, so this follows the exact same
// same-origin route (through the dev proxy / prod's own reverse proxy)
// as every other request, regardless of what host DRF happened to see.
export function apiFetchUrl(url, token) {
  const parsed = new URL(url, window.location.origin)
  return fetch(parsed.pathname + parsed.search, { headers: authHeaders(token) }).then(handleResponse)
}

// DRF's PageNumberPagination wraps list responses as
// {count, next, previous, results}; unwrap so callers always get an array.
export function unwrapList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

// Downloads a file from an authenticated API endpoint (CSV export, PDF
// report, evidence). A plain <a href> doesn't carry the Authorization
// header and — through the dev proxy — can be intercepted as an SPA
// navigation instead of reaching the API; fetching as a blob sidesteps
// both problems, the same pattern EvidencePanel's download() established.
export function downloadFile(path, token, filename) {
  return fetch(`${API_BASE}${path}`, { headers: authHeaders(token) })
    .then(async (r) => {
      if (!r.ok) {
        const data = await r.json().catch(() => null)
        throw new Error(formatApiError(data, `Download failed (${r.status})`))
      }
      return r.blob()
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    })
}
