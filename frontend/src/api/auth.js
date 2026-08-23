import { apiFetch } from './client'

export function signup(name, email, password) {
  return apiFetch('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
}

export function login(email, password) {
  return apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function getCurrentUser() {
  return apiFetch('/auth/me')
}

export function forgotPassword(email) {
  return apiFetch('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export function resetPassword(token, newPassword) {
  return apiFetch('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  })
}
