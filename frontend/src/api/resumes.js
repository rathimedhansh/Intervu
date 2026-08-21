import { apiFetch } from './client'

export function uploadResume(file) {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch('/resumes/', {
    method: 'POST',
    body: formData,
  })
}

export function getResume(resumeId) {
  return apiFetch(`/resumes/${resumeId}`)
}

export function listResumes() {
  return apiFetch('/resumes/')
}
