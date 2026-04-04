import { useState, useRef } from 'react'

export default function ChatInput({ onSubmit, disabled }) {
  const [text, setText] = useState('')
  const inputRef = useRef(null)

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSubmit(trimmed)
    setText('')
  }

  function handleKeyDown(e) {
    e.stopPropagation()
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e)
    }
  }

  const canSend = text.trim().length > 0 && !disabled

  return (
    <form
      className="group flex items-center gap-2.5 rounded-2xl border border-slate-200/90 bg-white px-3 py-2 shadow-[0_4px_20px_-8px_rgba(15,23,42,0.15)] transition-all duration-250 focus-within:border-brand-300 focus-within:shadow-[0_4px_24px_-8px_rgba(109,79,194,0.3)] focus-within:ring-2 focus-within:ring-brand-500/20 sm:px-4 sm:py-2.5"
      autoComplete="off"
      onSubmit={handleSubmit}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
      onKeyUp={(e) => e.stopPropagation()}
    >
      <input
        ref={inputRef}
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="h-10 w-full min-w-0 flex-1 border-none bg-transparent text-sm font-medium text-slate-800 placeholder:text-slate-400 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 sm:h-11 sm:text-base"
        placeholder={disabled ? 'Waiting for response...' : 'Ask about your business data...'}
        disabled={disabled}
        onKeyDown={handleKeyDown}
        onKeyUp={(e) => e.stopPropagation()}
      />

      <button
        type="submit"
        title="Send message"
        aria-label="Send message"
        disabled={!canSend}
        className={`flex h-10 items-center justify-center gap-1.5 rounded-xl border-0 px-4 text-sm font-semibold text-white shadow-md transition-all duration-200 focus:outline-none sm:h-11 sm:px-5 sm:text-sm ${
          canSend
            ? 'bg-gradient-to-br from-brand-500 to-brand-600 shadow-brand-500/30 hover:-translate-y-0.5 hover:from-brand-600 hover:to-brand-700 hover:shadow-lg hover:shadow-brand-500/40 active:translate-y-0 active:shadow-sm'
            : 'cursor-not-allowed bg-slate-300 shadow-none'
        }`}
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M22 2L11 13" />
          <path d="M22 2L15 22L11 13L2 9L22 2Z" />
        </svg>
        <span className="hidden sm:inline">Send</span>
      </button>
    </form>
  )
}
