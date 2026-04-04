import { useEffect, useRef } from 'react'
import BotIcon from './BotIcon'
import MessageBubble from './MessageBubble'

export default function MessageList({ messages }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col gap-5">
      {/* Welcome message */}
      {messages.length === 0 && (
        <div className="motion-safe:animate-fade-rise flex flex-col items-center gap-4 py-8 text-center sm:py-12">
          <BotIcon size={56} className="h-14 w-14" />
          <div className="flex flex-col gap-1.5">
            <h3 className="text-lg font-bold text-slate-800 sm:text-xl">Welcome to E2Next AI</h3>
            <p className="max-w-md text-sm text-slate-500">
              Your ERPNext assistant. Ask me anything about your business data &mdash; sales, inventory, accounts, and more.
            </p>
          </div>
          <div className="mt-2 flex flex-wrap justify-center gap-2">
            <span className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700">Sales Summary</span>
            <span className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700">Stock Balance</span>
            <span className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700">Outstanding Invoices</span>
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div className="motion-safe:animate-fade-rise flex w-full items-start gap-2.5">
          <BotIcon size={34} className="mt-0.5 h-[34px] w-[34px] shrink-0" />
          <p className="chat-card w-fit max-w-[calc(100%-3rem)] whitespace-pre-line rounded-[18px_18px_18px_4px] px-5 py-3.5 text-sm leading-relaxed break-words text-slate-800">
            Hello! I'm E2Next AI, your ERPNext assistant. Ask me anything about your business data.
          </p>
        </div>
      )}

      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}

      <div ref={bottomRef} />
    </div>
  )
}
