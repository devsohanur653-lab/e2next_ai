export default function DebugPanel({ logs }) {
  if (logs.length === 0) {
    return <p className="rounded-lg bg-brand-50 px-4 py-3 text-xs text-slate-700">No debug data yet. Send a message to see tool execution details.</p>
  }

  return (
    <div className="flex flex-col gap-3">
      {logs.map((log, i) => (
        <div key={i} className="min-w-0 overflow-x-auto rounded-lg bg-gray-100 p-2 text-[11px]">
          <div className="mb-1 font-semibold text-slate-800">Q: {log.question}</div>
          {log.error ? (
            <div className="text-red-600">Error: {log.error}</div>
          ) : (
            <>
              {log.toolsCalled?.length > 0 && (
                <div className="mb-1">
                  <span className="font-semibold text-slate-600">Tools: </span>
                  {log.toolsCalled.map((tc, j) => (
                    <span key={j} className="mr-2">
                      <span className="font-semibold text-brand-600">{tc.tool}</span>
                      <span className="text-slate-500"> ({tc.query_time_ms}ms)</span>
                    </span>
                  ))}
                </div>
              )}
              <div className="text-slate-600 truncate">{log.reply?.substring(0, 200)}{log.reply?.length > 200 ? '...' : ''}</div>
            </>
          )}
          <div className="mt-1 text-[9px] text-slate-400">{log.timestamp}</div>
        </div>
      ))}
    </div>
  )
}
