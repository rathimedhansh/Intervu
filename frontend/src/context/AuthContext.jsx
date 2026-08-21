import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getCurrentUser, login as apiLogin, signup as apiSignup } from '../api/auth'
import { AUTH_TOKEN_STORAGE_KEY } from '../api/client'

const AuthContext = createContext(null)

// Holds auth state for the whole app: the current user (null when logged
// out), and login/signup/logout actions. The JWT itself lives only in
// localStorage (read by api/client.js on every request) — never in
// component state — so a page refresh doesn't lose the session.
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
    if (!token) {
      setIsLoading(false)
      return
    }
    getCurrentUser()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  // api/client.js can't reach into this component's state directly, so it
  // signals a 401 via this event — keeps `user` in sync with the token it
  // already cleared from localStorage, instead of the UI staying "logged
  // in" (and every subsequent request silently 401ing) until a refresh.
  useEffect(() => {
    function handleUnauthorized() {
      setUser(null)
    }
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await apiLogin(email, password)
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const signup = useCallback(async (name, email, password) => {
    const data = await apiSignup(name, email, password)
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    // JWTs are stateless — there's nothing to invalidate server-side.
    // "Logging out" just means forgetting the token locally.
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
