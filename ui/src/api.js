async function jsonFetch(path, body) {
  let res
  try {
    res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch (e) {
    const msg = e?.message || String(e) || 'Network error. Is the backend running on port 8000?'
    throw new Error(msg)
  }

  const text = await res.text().catch(() => '')

  if (!res.ok) {
    let message = text || res.statusText || `Request failed (${res.status})`
    try {
      const err = JSON.parse(text)
      if (err.detail) message = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch (_) {
      if (text) message = text
    }
    if (!message || !String(message).trim()) message = `Request failed (${res.status}). Check the backend.`
    // Normalize session-not-found so the UI can show a friendly message and clear session
    if (res.status === 400 && (message.includes('Session not found') || message.includes('start a new session'))) {
      message = 'Session not found. The server may have restarted. Please start a new session from the thread selector.'
    }
    throw new Error(message)
  }

  try {
    return JSON.parse(text)
  } catch (_) {
    const hint = text ? text.slice(0, 150) : 'empty response'
    throw new Error(`Invalid response from server (${res.status}). ${hint}`)
  }
}

export function startSession({ thread_id }) {
  return jsonFetch('/start_session', { thread_id })
}

export function ask({ session_id, text, search_outside_thread }) {
  return jsonFetch('/ask', { session_id, text, search_outside_thread })
}

