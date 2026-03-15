import React, { useEffect, useRef } from 'react'

// Match [msg: <id>] or [msg: <id>, page: n] in assistant answers
const CITATION_RE = /\[msg:\s*[^\]]+\]/g

function formatCitations(answerText, citationsFromApi) {
  if (!answerText || typeof answerText !== 'string') return { displayText: answerText || '', sources: [] }
  const seen = new Map()
  let num = 0
  const displayText = answerText.replace(CITATION_RE, (match) => {
    if (!seen.has(match)) {
      num += 1
      seen.set(match, num)
    }
    return `[${seen.get(match)}]`
  })
  const sources = Array.from(seen.entries()).map(([raw, n]) => {
    const pageMatch = raw.match(/page:\s*(\d+)/i)
    const idMatch = raw.match(/\[msg:\s*<?([^>\],]+)/)
    const id = (idMatch && idMatch[1]) ? idMatch[1].trim() : raw
    const short = id.length > 20 ? id.slice(0, 20) + '…' : id
    return { num: n, raw, short, page: pageMatch ? pageMatch[1] : null }
  })
  return { displayText, sources }
}

function MessageBubble({ role, text, citations }) {
  const isUser = role === 'user'
  const { displayText, sources } = !isUser && text
    ? formatCitations(text, citations)
    : { displayText: text || '', sources: [] }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[88%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-slate-800 text-white rounded-br-md'
            : 'bg-white text-slate-800 border border-slate-200 rounded-bl-md shadow-sm'
        }`}
      >
        <div className="whitespace-pre-wrap">{displayText}</div>
        {!isUser && sources.length > 0 ? (
          <div className="mt-3 border-t border-slate-100 pt-2.5">
            <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">Sources</p>
            <div className="flex flex-wrap gap-2">
              {sources.map(({ num, raw, short, page }) => (
                <span
                  key={`${num}-${short}`}
                  className="inline-flex items-center rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700"
                  title={raw}
                >
                  <span className="mr-1 font-semibold text-slate-600">[{num}]</span>
                  <span className="font-mono">{short}</span>
                  {page != null ? <span className="ml-1 text-slate-500">p.{page}</span> : null}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex gap-1 rounded-2xl rounded-bl-md bg-white border border-slate-200 px-4 py-3 shadow-sm">
        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:0ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
      </div>
    </div>
  )
}

export default function ChatWindow({ messages, loading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, loading])

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 shadow-sm">
      <div className="h-[50vh] min-h-[280px] overflow-y-auto scroll-thin space-y-4 pr-1">
        {messages.length === 0 && !loading ? (
          <div className="flex h-full min-h-[240px] flex-col items-center justify-center text-center text-slate-500">
            <svg
              className="mb-3 h-10 w-10 text-slate-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
            <p className="text-sm font-medium text-slate-600">No messages yet</p>
            <p className="mt-1 text-xs">
              Start a session above, then ask a question about the thread.
            </p>
          </div>
        ) : null}
        {messages.map((m, idx) => (
          <MessageBubble
            key={m.id ?? idx}
            role={m.role}
            text={m.text}
            citations={m.citations}
          />
        ))}
        {loading ? <TypingIndicator /> : null}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
