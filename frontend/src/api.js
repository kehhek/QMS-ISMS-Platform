const API_BASE = '/api'

function authHeaders(token, extra) {
  return {
    ...(token ? { Authorization: `Token ${token}` } : {}),
    ...(extra || {}),
  }
}

async function handleResponse(r) {
  const data = await r.json().catch(() => null)
  if (!r.ok) {
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
