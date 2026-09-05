const TOKEN_STORAGE_KEY = 'mtp_token'

export function readStoredToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || ''
  } catch {
    // Private browsing / storage disabled — fall back to session-only.
    return ''
  }
}

export function writeStoredToken(token) {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } catch {
    // ignore
  }
}

export function clearStoredToken() {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    // ignore
  }
}
