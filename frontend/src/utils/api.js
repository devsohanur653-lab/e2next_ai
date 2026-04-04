const API_METHOD = 'e2next_ai.api.chat'

function getCsrfToken() {
  // www page sets window.csrf_token via Jinja
  if (window.csrf_token) return window.csrf_token
  // Frappe desk sets it on frappe.csrf_token
  if (window.frappe && window.frappe.csrf_token) return window.frappe.csrf_token
  // Cookie fallback
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  return match ? match[1] : ''
}

export function frappeCall(method, args = {}) {
  // Use frappe.call if available (desk/widget mode)
  if (window.frappe && window.frappe.call) {
    return new Promise((resolve, reject) => {
      window.frappe.call({
        method,
        args,
        callback(r) {
          resolve(r.message)
        },
        error(err) {
          reject(err)
        },
      })
    })
  }

  // Direct fetch fallback (www page mode)
  return fetch(`/api/method/${method}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Frappe-CSRF-Token': getCsrfToken(),
    },
    body: JSON.stringify(args),
  }).then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json()
  }).then((data) => data.message)
}

export function sendChatMessage(message, sessionId) {
  return frappeCall(API_METHOD, {
    message,
    session_id: sessionId || null,
  })
}
