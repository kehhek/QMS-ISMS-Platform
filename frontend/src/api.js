const API_BASE = '/api'

export function apiFetch(path, token, options = {}) {
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...(options.headers || {}),
    },
  }).then(async (r) => {
    const data = await r.json().catch(() => null)
    if (!r.ok) {
      const message = (data && (data.detail || JSON.stringify(data))) || r.statusText
      throw new Error(message)
    }
    return data
  })
}

// DRF's PageNumberPagination wraps list responses as
// {count, next, previous, results}; unwrap so callers always get an array.
export function unwrapList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}
