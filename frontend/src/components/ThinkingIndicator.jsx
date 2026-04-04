export default function ThinkingIndicator() {
  return (
    <div className="chat-card inline-flex w-fit rounded-[10px_10px_10px_3px] px-3 py-2" role="status" aria-live="polite" aria-label="Thinking">
      <div className="inline-flex items-center gap-1.5">
        <span className="relative inline-flex h-4 w-4 shrink-0 items-center justify-center">
          <span className="absolute inset-0 rounded-full border border-transparent border-t-[#4b89ff] border-r-[#4b89ff]/70 animate-thinking-pulse" />
          <svg viewBox="0 0 24 24" className="relative h-3 w-3 text-[#4b89ff] animate-thinking-spark" aria-hidden="true">
            <path fill="currentColor" d="M12 2.8c.52 3.22 1.6 5.66 3.22 7.28 1.62 1.62 4.06 2.7 7.28 3.22-3.22.52-5.66 1.6-7.28 3.22-1.62 1.62-2.7 4.06-3.22 7.28-.52-3.22-1.6-5.66-3.22-7.28-1.62-1.62-4.06-2.7-7.28-3.22 3.22-.52 5.66-1.6 7.28-3.22 1.62-1.62 2.7-4.06 3.22-7.28Z" />
          </svg>
        </span>
        <span className="text-[8px] font-semibold tracking-[0.12em] uppercase text-[#3a67c9]">Thinking</span>
      </div>
    </div>
  )
}
