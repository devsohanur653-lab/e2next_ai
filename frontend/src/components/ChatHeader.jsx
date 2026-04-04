export default function ChatHeader({ windowMode, onClose, onCycleResize, onClearChat, pageMode }) {
  const modeLabels = { compact: 'Compact', half: 'Half Screen', full: 'Full Screen' }
  const nextLabels = { compact: 'Half Screen', half: 'Full Screen', full: 'Compact' }

  return (
    <div className="relative flex min-h-14 items-center justify-between px-4 pb-2.5 pt-3 text-white sm:px-5">
      <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-2.5">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="35"
          height="35"
          viewBox="0 0 1024 1024"
          className="h-8 w-8 shrink-0 rounded-full bg-white p-1.5 shadow-md motion-safe:animate-soft-float"
          style={{ fill: '#6d4fc2' }}
        >
          <path d="M738.3 287.6H285.7c-59 0-106.8 47.8-106.8 106.8v303.1c0 59 47.8 106.8 106.8 106.8h81.5v111.1c0 .7.8 1.1 1.4.7l166.9-110.6 41.8-.8h117.4l43.6-.4c59 0 106.8-47.8 106.8-106.8V394.5c0-59-47.8-106.9-106.8-106.9zM351.7 448.2c0-29.5 23.9-53.5 53.5-53.5s53.5 23.9 53.5 53.5-23.9 53.5-53.5 53.5-53.5-23.9-53.5-53.5zm157.9 267.1c-67.8 0-123.8-47.5-132.3-109h264.6c-8.6 61.5-64.5 109-132.3 109zm110-213.7c-29.5 0-53.5-23.9-53.5-53.5s23.9-53.5 53.5-53.5 53.5 23.9 53.5 53.5-23.9 53.5-53.5 53.5zM867.2 644.5V453.1h26.5c19.4 0 35.1 15.7 35.1 35.1v121.1c0 19.4-15.7 35.1-35.1 35.1h-26.5zM95.2 609.4V488.2c0-19.4 15.7-35.1 35.1-35.1h26.5v191.3h-26.5c-19.4 0-35.1-15.7-35.1-35.1zM561.5 149.6c0 23.4-15.6 43.3-36.9 49.7v44.9h-30v-44.9c-21.4-6.5-36.9-26.3-36.9-49.7 0-28.6 23.3-51.9 51.9-51.9s51.9 23.3 51.9 51.9z" />
        </svg>
        <h2 className="truncate text-xs font-semibold tracking-[0.01em] sm:text-base text-white/95">
          E2Next AI
        </h2>
      </div>

      <div className="ml-2 flex items-center gap-1.5">
        <button
          className="flex h-8 min-w-8 items-center justify-center rounded-md border border-white/20 bg-white/20 px-2 text-xs font-semibold text-white/90 shadow-sm transition-all duration-200 hover:bg-white/25 focus:outline-none"
          style={{ borderRadius: '0.375rem' }}
          title={`Clear chat history`}
          aria-label="Clear chat"
          onClick={onClearChat}
        >
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
          </svg>
        </button>

        {!pageMode && (
          <button
            className="flex h-8 min-w-8 items-center justify-center rounded-md border border-white/20 bg-white/20 px-2 text-xs font-semibold text-white/90 shadow-sm transition-all duration-200 hover:bg-white/25 focus:outline-none"
            style={{ borderRadius: '0.375rem' }}
            title={`Resize: ${modeLabels[windowMode]} (click for ${nextLabels[windowMode]})`}
            aria-label={`Resize to ${nextLabels[windowMode]}`}
            onClick={onCycleResize}
          >
            {windowMode === 'compact' && (
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <rect x="7" y="8" width="10" height="8" rx="2" />
              </svg>
            )}
            {windowMode === 'half' && (
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <rect x="4" y="5" width="16" height="14" rx="2" />
                <path d="M12 5v14" />
              </svg>
            )}
            {windowMode === 'full' && (
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <rect x="4" y="5" width="16" height="14" rx="2" />
                <path d="M8 8H6v2M16 8h2v2M8 16H6v-2M16 16h2v-2" />
              </svg>
            )}
          </button>
        )}

        {!pageMode && (
          <button
            className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-white/20 text-white transition-all duration-200 hover:scale-105 hover:bg-white/20 focus:outline-none"
            style={{ borderRadius: '9999px' }}
            aria-label="Close chatbot"
            onClick={onClose}
          >
            <svg viewBox="0 0 24 24" height="24" width="24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}
