import React from 'react'

export default function ThreadSelector({
  threadId,
  threadOptions,
  onChangeThreadId,
  onStartSession,
  sessionId,
  loading,
  error,
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Thread
          </span>
          <select
            className="h-9 min-w-[220px] rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-800 transition-colors hover:border-slate-400 focus:border-slate-500"
            value={threadId}
            onChange={(e) => onChangeThreadId(e.target.value)}
            disabled={loading}
          >
            {threadOptions.map(({ id, label }) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
          <button
            className="h-9 rounded-lg bg-slate-800 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-50 disabled:hover:bg-slate-800"
            onClick={onStartSession}
            disabled={loading}
            type="button"
          >
            {loading ? 'Starting…' : 'Start Session'}
          </button>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Session</span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
              sessionId
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-slate-100 text-slate-500'
            }`}
          >
            {sessionId ? (
              <span className="font-mono truncate max-w-[140px] inline-block" title={sessionId}>
                {sessionId}
              </span>
            ) : (
              '—'
            )}
          </span>
        </div>
      </div>
      {error ? (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      ) : (
        <p className="mt-1.5 text-xs text-slate-500">
          Pick a thread, then start a session to begin chatting.
        </p>
      )}
    </div>
  )
}
