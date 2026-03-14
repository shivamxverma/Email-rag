import React, { useState } from 'react'
import ThreadSelector from './components/ThreadSelector.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import ChatInput from './components/ChatInput.jsx'
import DebugPanel from './components/DebugPanel.jsx'
import { ask, startSession } from './api.js'

function makeId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

// 15 threads with clear labels (backend uses thread_id, e.g. T-001)
const THREAD_OPTIONS = [
  { id: 'T-001', label: 'General correspondence & forecasts' },
  { id: 'T-002', label: 'Demand – Ken Lay stock sales / donations' },
  { id: 'T-003', label: 'Schedule crawler – hourahead failure' },
  { id: 'T-004', label: 'Enron mentions' },
  { id: 'T-005', label: 'Schedule crawler – hourahead (codesite)' },
  { id: 'T-006', label: 'Entouch newsletter' },
  { id: 'T-007', label: 'General (no subject)' },
  { id: 'T-008', label: 'Lunch' },
  { id: 'T-009', label: 'Hey' },
  { id: 'T-010', label: 'Meeting' },
  { id: 'T-011', label: 'Hi' },
  { id: 'T-012', label: 'Organizational announcement' },
  { id: 'T-013', label: 'Organizational changes' },
  { id: 'T-014', label: 'Congratulations' },
  { id: 'T-015', label: 'APB checkout' },
]

export default function App() {
  const [threadId, setThreadId] = useState(THREAD_OPTIONS[0].id)
  const [sessionId, setSessionId] = useState('')
  const [searchOutsideThread, setSearchOutsideThread] = useState(false)

  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [startError, setStartError] = useState('')
  const [askError, setAskError] = useState('')

  const [debug, setDebug] = useState({
    rewrite: '',
    retrieved: [],
    traceId: '',
  })

  async function onStartSession() {
    setLoading(true)
    setStartError('')
    setAskError('')
    try {
      const data = await startSession({ thread_id: threadId })
      setSessionId(data.session_id)
      setMessages([])
      setDebug({ rewrite: '', retrieved: [], traceId: '' })
    } catch (e) {
      setStartError(e?.message || 'Failed to start session')
    } finally {
      setLoading(false)
    }
  }

  async function onSend(text) {
    if (!sessionId) return
    setAskError('')
    setMessages((prev) => [...prev, { id: makeId(), role: 'user', text }])
    setLoading(true)
    try {
      const data = await ask({
        session_id: sessionId,
        text,
        search_outside_thread: searchOutsideThread,
      })

      const answerText = (data.answer != null && data.answer !== '') ? String(data.answer).trim() : 'No response from the assistant. Please try again.'
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: 'assistant',
          text: answerText,
          citations: Array.isArray(data.citations) ? data.citations : [],
        },
      ])

      setDebug({
        rewrite: data.rewrite ?? '',
        retrieved: Array.isArray(data.retrieved) ? data.retrieved : [],
        traceId: data.trace_id ?? '',
      })
    } catch (e) {
      console.error('Ask failed:', e)
      let errMsg = [e?.message, e?.toString?.(), String(e)].find((m) => m != null && String(m).trim() !== '')
      if (!errMsg) errMsg = 'Request failed. Is the backend running? Run: uvicorn app.main:app --port 8000'
      const isSessionNotFound =
        errMsg.includes('Session not found') ||
        errMsg.includes('start a new session') ||
        (errMsg.includes('400') && errMsg.toLowerCase().includes('session'))
      if (isSessionNotFound) {
        setSessionId('')
        setAskError('')
      } else {
        setAskError(errMsg)
      }
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: 'assistant',
          text: isSessionNotFound
            ? 'Session expired. Please choose a thread and click Start Session again.'
            : `Error: ${errMsg}`,
          citations: [],
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const chatDisabled = loading || !sessionId

  return (
    <div className="mx-auto flex h-full max-w-4xl flex-col gap-4 p-4 md:p-6">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-lg font-semibold text-slate-800">Email Thread RAG</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Chat over a selected email thread with optional search outside the thread.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="md:col-span-2">
          <ThreadSelector
            threadId={threadId}
            threadOptions={THREAD_OPTIONS}
            onChangeThreadId={setThreadId}
            onStartSession={onStartSession}
            sessionId={sessionId}
            loading={loading}
            error={startError}
          />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Retrieval
          </span>
          <label className="mt-2 flex cursor-pointer items-center gap-3">
            <input
              type="checkbox"
              checked={searchOutsideThread}
              onChange={(e) => setSearchOutsideThread(e.target.checked)}
              disabled={loading}
              className="h-4 w-4 rounded border-slate-300 text-slate-800 focus:ring-slate-400"
            />
            <span className="text-sm font-medium text-slate-700">
              Search outside thread
            </span>
          </label>
          <p className="mt-1 text-xs text-slate-500">
            When on, retrieval can use messages from other threads.
          </p>
        </div>
      </div>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Chat</h2>
          <span className="text-xs text-slate-500">
            {askError ? (
              <span className="text-red-600">{askError}</span>
            ) : sessionId ? (
              searchOutsideThread ? 'Outside thread ON' : 'Outside thread only'
            ) : (
              'Start a session to chat'
            )}
          </span>
        </div>
        <ChatWindow messages={messages} loading={loading} />
      </section>

      <ChatInput disabled={chatDisabled} onSend={onSend} />

      <DebugPanel
        rewrite={debug.rewrite}
        retrieved={debug.retrieved}
        traceId={debug.traceId}
      />
    </div>
  )
}
