import { useState } from 'react'
import ChatHeader from './ChatHeader'
import TabBar from './TabBar'
import MessageList from './MessageList'
import DebugPanel from './DebugPanel'
import ChatInput from './ChatInput'

export default function ChatWindow({ isOpen, windowMode, messages, debugLogs, loading, onClose, onCycleResize, onSend, onClearChat }) {
  const [activeTab, setActiveTab] = useState('chat')

  const stateClasses = isOpen
    ? 'pointer-events-auto opacity-100 translate-x-0 translate-y-0 scale-100'
    : 'pointer-events-none opacity-0 translate-x-[20%] translate-y-8 scale-95'

  let sizeClasses
  if (windowMode === 'full') {
    sizeClasses = 'inset-0 h-screen w-screen max-h-screen max-w-screen rounded-none origin-center'
  } else if (windowMode === 'half') {
    sizeClasses = [
      'bottom-[74px] right-5 h-[min(86vh,860px)] w-[min(50vw,860px)] rounded-2xl',
      'max-[900px]:bottom-[78px] max-[900px]:right-3 max-[900px]:h-[min(86vh,760px)] max-[900px]:w-[min(70vw,760px)] max-[900px]:rounded-[14px]',
      'max-[600px]:inset-0 max-[600px]:h-screen max-[600px]:w-screen max-[600px]:max-h-screen max-[600px]:max-w-screen max-[600px]:rounded-none max-[600px]:pb-[env(safe-area-inset-bottom)]',
    ].join(' ')
  } else {
    sizeClasses = [
      'bottom-[74px] right-5 h-[min(560px,72vh)] w-[min(380px,calc(100vw-40px))] rounded-2xl',
      'max-[900px]:bottom-[78px] max-[900px]:right-3 max-[900px]:h-[min(70vh,540px)] max-[900px]:w-[min(380px,calc(100vw-24px))] max-[900px]:rounded-[14px]',
      'max-[600px]:inset-0 max-[600px]:h-screen max-[600px]:w-screen max-[600px]:max-h-screen max-[600px]:max-w-screen max-[600px]:rounded-none max-[600px]:pb-[env(safe-area-inset-bottom)]',
    ].join(' ')
  }

  return (
    <div
      className={`chat-shell fixed z-[9999] flex min-h-0 flex-col overflow-hidden border border-slate-200/80 shadow-[0_32px_80px_-44px_rgba(2,6,23,0.7),0_18px_40px_-24px_rgba(15,23,42,0.45)] transition-all duration-300 ease-out origin-bottom-right motion-safe:animate-surface-in ${stateClasses} ${sizeClasses}`}
      onKeyDown={(e) => e.stopPropagation()}
      onKeyUp={(e) => e.stopPropagation()}
    >
      {/* Decorative blurs */}
      <div className="pointer-events-none absolute -right-14 -top-14 h-36 w-36 rounded-full bg-brand-500/15 blur-2xl" />
      <div className="pointer-events-none absolute -bottom-14 -left-12 h-32 w-32 rounded-full bg-violet-400/15 blur-2xl" />

      {/* Header */}
      <div className="relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-500 to-violet-400">
        <div className="pointer-events-none absolute inset-0 opacity-45" style={{ background: 'linear-gradient(120deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.02) 52%, rgba(255,255,255,0.12) 100%)' }} />
        <ChatHeader
          windowMode={windowMode}
          onClose={onClose}
          onCycleResize={onCycleResize}
          onClearChat={onClearChat}
        />
        <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      {/* Body */}
      <div className="chat-scrollbar min-h-0 flex-1 overflow-x-hidden overflow-y-auto bg-slate-50/60 px-4 py-4 max-[900px]:px-3.5 max-[900px]:py-3.5 max-[600px]:px-3 max-[600px]:py-3">
        <div className="min-w-0">
          {activeTab === 'chat' ? (
            <MessageList messages={messages} />
          ) : (
            <DebugPanel logs={debugLogs} />
          )}
        </div>
      </div>

      {/* Footer */}
      {activeTab === 'chat' && (
        <div className="border-t border-slate-200/80 bg-white/90 px-3 py-3 pb-[calc(12px+env(safe-area-inset-bottom))] backdrop-blur-sm sm:px-4 sm:py-4">
          <ChatInput onSubmit={onSend} disabled={loading} />
        </div>
      )}
    </div>
  )
}
