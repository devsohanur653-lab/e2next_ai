const SESSION_KEY = 'e2next_ai_session_id'

export function getOrCreateSessionId() {
  let id = sessionStorage.getItem(SESSION_KEY)
  if (!id) {
    id = `session_${Date.now()}_${crypto.randomUUID()}`
    sessionStorage.setItem(SESSION_KEY, id)
  }
  return id
}

export function resetSession() {
  sessionStorage.removeItem(SESSION_KEY)
}
