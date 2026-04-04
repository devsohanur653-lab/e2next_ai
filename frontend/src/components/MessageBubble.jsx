import { useState } from 'react'
import BotIcon from './BotIcon'
import ThinkingIndicator from './ThinkingIndicator'
import { renderMarkdown } from '../utils/markdown'

export default function MessageBubble({ message }) {
  const [expanded, setExpanded] = useState(false)
  const [showDebug, setShowDebug] = useState(false)

  const isUser = message.role === 'user'
  const isLoading = message.loading
  const isError = message.error

  const plainText = message.text || ''
  const shouldCollapse = !isUser && !isLoading && (plainText.length > 520 || plainText.split(/\n+/).filter(Boolean).length > 8)
  const hasTools = !isUser && message.toolsCalled?.length > 0

  if (isUser) {
    return (
      <div className="motion-safe:animate-fade-rise flex w-full flex-col items-end gap-1.5">
        <p className="w-fit max-w-[80%] whitespace-pre-line rounded-[18px_18px_4px_18px] bg-gradient-to-br from-brand-500 to-brand-600 px-5 py-3.5 text-sm leading-relaxed break-words text-white shadow-[0_8px_24px_-12px_rgba(109,79,194,0.6)]">
          {message.text}
        </p>
      </div>
    )
  }

  return (
    <div className="motion-safe:animate-fade-rise flex w-full items-start gap-2.5">
      <BotIcon size={34} className="mt-0.5 h-[34px] w-[34px] shrink-0" />
      <div className="flex min-w-0 max-w-[calc(100%-3rem)] flex-1 flex-col">
        {isLoading ? (
          <ThinkingIndicator />
        ) : (
          <div className="flex w-fit max-w-full flex-col items-start gap-2.5">
            <div className={`chat-card relative w-fit max-w-full whitespace-pre-line rounded-[18px_18px_18px_4px] px-5 py-3.5 text-sm leading-relaxed break-words ${isError ? 'border-red-200 bg-red-50 text-red-700' : 'text-slate-800'}`}>
              <div
                className={`overflow-x-auto ${shouldCollapse && !expanded ? 'max-h-48 overflow-y-hidden' : ''}`}
                dangerouslySetInnerHTML={{ __html: renderMarkdown(message.text) }}
              />
              {shouldCollapse && !expanded && (
                <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 rounded-b-[18px] bg-gradient-to-t from-white via-white/92 to-white/0" aria-hidden="true" />
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {shouldCollapse && (
                <button
                  type="button"
                  className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition-colors duration-200 hover:border-brand-200 hover:bg-brand-50 hover:text-brand-600"
                  onClick={() => setExpanded(!expanded)}
                >
                  {expanded ? 'Show less' : 'Read more'}
                </button>
              )}
              {hasTools && (
                <button
                  type="button"
                  className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition-colors duration-200 hover:border-brand-200 hover:bg-brand-50 hover:text-brand-600"
                  onClick={() => setShowDebug(!showDebug)}
                >
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
                  </svg>
                  {showDebug ? 'Hide tools' : `${message.toolsCalled.length} tool${message.toolsCalled.length > 1 ? 's' : ''} used`}
                </button>
              )}
            </div>

            {showDebug && hasTools && (
              <div className="mt-1 w-full rounded-xl border border-slate-200/80 bg-slate-50 p-3 text-xs text-slate-700">
                {message.toolsCalled.map((tc, i) => (
                  <div key={i} className="mb-1.5 flex items-baseline gap-1.5 last:mb-0">
                    <span className="rounded bg-brand-100 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-brand-700">{tc.tool}</span>
                    <span className="text-slate-400">{tc.query_time_ms}ms</span>
                    {tc.summary && <span className="text-slate-600">&mdash; {tc.summary}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
