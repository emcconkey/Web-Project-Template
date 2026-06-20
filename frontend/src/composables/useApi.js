// Thin fetch wrapper. Base URL is read at RUNTIME from window.__APP_CONFIG__
// (injected by /config.js — see frontend/public/config.js and the nginx
// startup script), so one built image serves every environment. Empty base →
// relative paths through the Vite dev proxy. Every request sends
// credentials:'include' so the Flask session cookie travels.

const baseUrl = window.__APP_CONFIG__?.API_BASE_URL || ''

async function request(path, options = {}) {
  const res = await fetch(`${baseUrl}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.message || `Request failed (${res.status})`)
  }
  return data
}

export function useApi() {
  return {
    get: (path) => request(path, { method: 'GET' }),
    post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  }
}
