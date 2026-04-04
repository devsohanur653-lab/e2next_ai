import { useState } from 'react'
import ChatToggle from './components/ChatToggle'
import ChatWindow from './components/ChatWindow'
import { useChat } from './hooks/useChat'
import { useResize } from './hooks/useResize'

export default function App() {
  const [isOpen, setIsOpen] = useState(false)
  const { messages, loading, debugLogs, sendMessage, clearChat } = useChat()
  const { mode, cycleMode } = useResize()

  return (
    <>
      <ChatToggle isOpen={isOpen} onToggle={() => setIsOpen(!isOpen)} />
      <ChatWindow
        isOpen={isOpen}
        windowMode={mode}
        messages={messages}
        debugLogs={debugLogs}
        loading={loading}
        onClose={() => setIsOpen(false)}
        onCycleResize={cycleMode}
        onSend={sendMessage}
        onClearChat={clearChat}
      />
    </>
  )
}
