const API_BASE = 'http://127.0.0.1:8000/api'
export const AUTH_TOKEN_STORAGE_KEY = 'auth_token'

export async function apiFetch(path, options = {}) {
  // Let the browser set Content-Type (with the multipart boundary) itself
  // when the body is FormData — only default to JSON otherwise.
  const headers =
    options.body instanceof FormData
      ? { ...options.headers }
      : { 'Content-Type': 'application/json', ...options.headers }

  const token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    if (response.status === 401) {
      // Token missing/expired/invalid — drop it and tell AuthContext (it
      // can't see localStorage changes on its own) so `user` clears and
      // ProtectedRoute redirects to login, instead of the app silently
      // staying in a "logged in" state that 401s on every request.
      localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
      window.dispatchEvent(new Event('auth:unauthorized'))
    }
    const body = await response.json().catch(() => null)
    // FastAPI's `detail` is a string for most errors, but a list of
    // per-field objects for 422 validation errors — fall back gracefully
    // instead of rendering "[object Object]" to the user.
    const detail = body?.detail
    let message
    if (typeof detail === 'string') {
      message = detail
    } else if (Array.isArray(detail)) {
      message = detail.map((item) => item?.msg || JSON.stringify(item)).join(' ')
    } else {
      message = `Request failed: ${response.status}`
    }
    const error = new Error(message)
    error.status = response.status
    throw error
  }

  return response.json()
}
