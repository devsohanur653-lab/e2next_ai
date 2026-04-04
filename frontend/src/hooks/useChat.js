import { useState, useCallback, useRef, useEffect } from 'react'
import { sendChatMessage } from '../utils/api'
import { getOrCreateSessionId, resetSession } from '../utils/session'

const STORAGE_KEY = 'e2next_ai_messages'

function loadSavedMessages() {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch {}
  return []
}

function saveMessages(messages) {
  try {
    const clean = messages.filter((m) => !m.loading)
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(clean))
  } catch {}
}

export function useChat() {
  const [messages, setMessages] = useState(loadSavedMessages)
  const [loading, setLoading] = useState(false)
  const [debugLogs, setDebugLogs] = useState([])
  const sessionIdRef = useRef(getOrCreateSessionId())

  useEffect(() => {
    saveMessages(messages)
  }, [messages])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loading) return

    const userMsg = { role: 'user', text: text.trim() }
    const botMsg = { role: 'bot', text: 'Thinking...', loading: true }

    setMessages((prev) => [...prev, userMsg, botMsg])
    setLoading(true)

    try {
      const response = await sendChatMessage(text.trim(), sessionIdRef.current)

      if (response?.session_id) {
        sessionIdRef.current = response.session_id
        sessionStorage.setItem('e2next_ai_session_id', response.session_id)
      }

      const reply = response?.reply || 'No response received.'
      const toolsCalled = response?.tools_called || []

      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'bot',
          text: reply,
          loading: false,
          toolsCalled,
        }
        return updated
      })

      setDebugLogs((prev) => [
        ...prev,
        {
          question: text.trim(),
          reply,
          toolsCalled,
          timestamp: new Date().toISOString(),
        },
      ])
    } catch (err) {
      const errorText =
        err?.message ||
        err?.responseJSON?.exception ||
        err?.responseJSON?.message ||
        'Something went wrong. Please try again.'

      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'bot',
          text: `${errorText}`,
          loading: false,
          error: true,
        }
        return updated
      })

      setDebugLogs((prev) => [
        ...prev,
        { question: text.trim(), error: errorText, timestamp: new Date().toISOString() },
      ])
    } finally {
      setLoading(false)
    }
  }, [loading])

  const clearChat = useCallback(() => {
    setMessages([])
    setDebugLogs([])
    resetSession()
    sessionIdRef.current = getOrCreateSessionId()
    try { sessionStorage.removeItem(STORAGE_KEY) } catch {}
  }, [])

  return { messages, loading, debugLogs, sendMessage, clearChat }
}
