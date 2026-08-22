import React, { useEffect, useRef, useState } from 'react'

const MAX_MS = 30000
const endpoint = import.meta.env.VITE_NEXUS_VOICE_ENDPOINT || ''
const STATE_LABELS = {
  REQUESTING_PERMISSION: 'Microphone permission…',
  LISTENING: 'Listening…',
  PROCESSING: 'Processing…',
  TRANSCRIBED: 'Transcript received',
  DONE: 'Transcript received',
  ERROR: 'Error'
}

export default function VoicePushToTalk({ onTranscript, disabled = false }) {
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const startedRef = useRef(0)
  const [state, setState] = useState('IDLE')
  const [error, setError] = useState('')
  const [transcript, setTranscript] = useState('')
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => () => {
    clearInterval(timerRef.current)
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }, [])

  async function start() {
    if (disabled || recorderRef.current?.state === 'recording' || state === 'REQUESTING_PERMISSION' || state === 'PROCESSING') return
    setError('')
    setTranscript('')
    if (!endpoint) { setState('ERROR'); setError('Admin voice transport is not configured; local-only STT is not exposed to this browser.'); return }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { setState('ERROR'); setError('This browser does not provide microphone capture.'); return }
    try {
      setState('REQUESTING_PERMISSION')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm'
      const recorder = new MediaRecorder(stream, { mimeType: mime })
      chunksRef.current = []
      recorder.ondataavailable = event => { if (event.data.size) chunksRef.current.push(event.data) }
      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop())
        clearInterval(timerRef.current)
        setState('PROCESSING')
        try {
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
          const headers = { 'Content-Type': blob.type || 'audio/webm', 'X-Nexus-Voice-Session': `admin-${Date.now()}` }
          const response = await fetch(endpoint, { method: 'POST', headers, credentials: 'include', body: blob })
          const payload = await response.json()
          if (!response.ok) throw new Error(payload.error || 'voice-transcription-unavailable')
          setTranscript(payload.text || '')
          setState('TRANSCRIBED')
          if (payload.text && onTranscript) await onTranscript(payload.text, payload)
          setState('DONE')
        } catch (caught) { setState('ERROR'); setError(caught?.message || 'Voice transcription failed.') }
      }
      recorderRef.current = recorder
      startedRef.current = Date.now()
      recorder.start()
      setState('LISTENING')
      timerRef.current = setInterval(() => {
        const next = Date.now() - startedRef.current
        setElapsed(next)
        if (next >= MAX_MS) stop()
      }, 100)
    } catch (caught) { setState('ERROR'); setError(caught?.message || 'Microphone permission was not granted.') }
  }

  function stop() {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  return <div className="nexus-voice-ptt" data-voice-state={state}>
      <button type="button" className="hermes-chip nexus-voice-button" onPointerDown={start} onPointerUp={stop} onPointerCancel={stop} onKeyDown={event => { if ((event.key === 'Enter' || event.key === ' ') && !event.repeat) { event.preventDefault(); start() } }} onKeyUp={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); stop() } }} aria-label="Press and hold to talk" aria-pressed={state === 'LISTENING'} disabled={disabled || state === 'PROCESSING' || state === 'REQUESTING_PERMISSION'}>
        🎙️
      </button>
    <small className="nexus-voice-state" role="status">{STATE_LABELS[state] || ''}{state === 'LISTENING' ? ` ${(elapsed / 1000).toFixed(1)}s` : ''}</small>
    {transcript && <div className="nexus-voice-transcript"><strong>Transcript:</strong> {transcript}</div>}
    {error && <div className="nexus-voice-error" role="status">{error}</div>}
  </div>
}
