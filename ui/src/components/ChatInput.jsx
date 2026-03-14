import React, { useState } from 'react'

export default function ChatInput({ disabled, onSend }) {
  const [text, setText] = useState('')

  function submit(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    console.log('text', text)
    setText('')
  }

  return (
    <form onSubmit={submit} className="flex gap-2">
      <input
        className="h-11 flex-1 rounded-xl border border-slate-300 bg-white px-4 text-sm text-slate-800 placeholder:text-slate-400 transition-colors hover:border-slate-400 focus:border-slate-500"
        placeholder={disabled ? 'Start a session to chat…' : 'Ask a question about this thread…'}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
      />
      <button
        className="h-11 rounded-xl bg-slate-800 px-5 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-50 disabled:hover:bg-slate-800"
        disabled={disabled}
        type="submit"
      >
        Send
      </button>
    </form>
  )
}
