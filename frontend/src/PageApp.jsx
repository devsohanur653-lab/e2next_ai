import ChatHeader from './components/ChatHeader'
import TabBar from './components/TabBar'
import MessageList from './components/MessageList'
import DebugPanel from './components/DebugPanel'
import ChatInput from './components/ChatInput'
import { useChat } from './hooks/useChat'
import { useState } from 'react'

export default function PageApp() {
  const { messages, loading, debugLogs, sendMessage, clearChat } = useChat()
  const [activeTab, setActiveTab] = useState('chat')

  return (
    <div className="chat-shell relative flex h-full w-full flex-col overflow-hidden rounded-none border-0 shadow-none sm:rounded-2xl sm:border sm:border-slate-200/80 sm:shadow-[0_32px_80px_-44px_rgba(2,6,23,0.7),0_18px_40px_-24px_rgba(15,23,42,0.45)]">
      {/* Decorative blurs */}
      <div className="pointer-events-none absolute -right-14 -top-14 h-44 w-44 rounded-full bg-brand-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-14 -left-12 h-40 w-40 rounded-full bg-violet-400/10 blur-3xl" />
      <div className="pointer-events-none absolute left-1/2 top-1/3 h-32 w-32 -translate-x-1/2 rounded-full bg-brand-300/5 blur-3xl" />

      {/* Header */}
      <div className="relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-500 to-violet-400">
        <div className="pointer-events-none absolute inset-0 opacity-45" style={{ background: 'linear-gradient(120deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.02) 52%, rgba(255,255,255,0.12) 100%)' }} />
        <ChatHeader
          windowMode="page"
          onClose={() => {}}
          onCycleResize={() => {}}
          onClearChat={clearChat}
          pageMode
        />
        <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      {/* Body */}
      <div className="chat-scrollbar min-h-0 flex-1 overflow-x-hidden overflow-y-auto bg-gradient-to-b from-slate-50/80 to-white px-4 py-5 sm:px-6 md:px-8 lg:px-12">
        <div className="mx-auto min-w-0 max-w-3xl">
          {activeTab === 'chat' ? (
            <MessageList messages={messages} />
          ) : (
            <DebugPanel logs={debugLogs} />
          )}
        </div>
      </div>

      {/* Footer */}
      {activeTab === 'chat' && (
        <div className="border-t border-slate-200/80 bg-white/95 px-4 py-4 backdrop-blur-md sm:px-6 sm:py-5 md:px-8 lg:px-12">
          <div className="mx-auto max-w-3xl">
            <ChatInput onSubmit={sendMessage} disabled={loading} />
          </div>
        </div>
      )}
    </div>
  )
}
