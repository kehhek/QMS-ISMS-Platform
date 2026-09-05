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

async function handleResponse(r) {
  const data = await r.json().catch(() => null)
  if (!r.ok) {
    if (r.status === 401) {
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    }
    const message = (data && (data.detail || JSON.stringify(data))) || r.statusText
    throw new Error(message)
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

// For following DRF pagination's `next`/`previous` links, which are full
// URLs (including host), not paths relative to API_BASE.
export function apiFetchUrl(url, token) {
  return fetch(url, { headers: authHeaders(token) }).then(handleResponse)
}

// DRF's PageNumberPagination wraps list responses as
// {count, next, previous, results}; unwrap so callers always get an array.
export function unwrapList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}
