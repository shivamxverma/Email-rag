import React, { useState } from 'react'

export default function DebugPanel({ rewrite, retrieved, traceId }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50 transition-colors"
      >
        <span className="text-sm font-semibold text-slate-800">Debug Panel</span>
        <span className="text-slate-400">
          {open ? (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          )}
        </span>
      </button>
      {open && (
        <div className="border-t border-slate-200 p-4 pt-3">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="md:col-span-2">
              <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Rewrite query
              </label>
              <div className="mt-1.5 min-h-[2.5rem] rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800">
                {rewrite ? (
                  <div className="whitespace-pre-wrap font-mono text-xs">{rewrite}</div>
                ) : (
                  <span className="text-slate-400">—</span>
                )}
              </div>
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Trace ID
              </label>
              <div className="mt-1.5 rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs text-slate-800 break-all">
                {traceId || '—'}
              </div>
            </div>
            <div className="md:col-span-3">
              <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Retrieved documents
              </label>
              <div className="mt-1.5 overflow-hidden rounded-lg border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500">
                    <tr>
                      <th className="px-3 py-2.5 font-medium">message_id</th>
                      <th className="px-3 py-2.5 font-medium w-24">score</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white">
                    {retrieved?.length ? (
                      retrieved.map((r, idx) => (
                        <tr
                          key={`${r.message_id}-${idx}`}
                          className="border-t border-slate-100 hover:bg-slate-50/50"
                        >
                          <td className="px-3 py-2 font-mono text-xs text-slate-800 truncate max-w-[200px]">
                            {r.message_id}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs text-slate-600">
                            {typeof r.score === 'number'
                              ? r.score.toFixed(4)
                              : String(r.score)}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr className="border-t border-slate-100">
                        <td className="px-3 py-3 text-slate-400 text-xs" colSpan={2}>
                          —
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
