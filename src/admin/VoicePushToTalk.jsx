import React, { useEffect, useRef, useState } from 'react'

const MAX_MS = 30000
const PREVIEW_CADENCE_MS = 1200
const endpoint = import.meta.env.VITE_NEXUS_VOICE_ENDPOINT || ''
const previewEndpoint = endpoint.replace(/\/v1\/voice\/transcribe\/?$/, '/v1/voice/preview')
const STATE_LABELS = {
  REQUESTING_PERMISSION: 'Microphone permission…', LISTENING: 'Listening…', LIVE_PREVIEW: 'Live preview…', FINALIZING: 'Processing…', TRANSCRIPT_READY: 'Transcript ready for review', EDITING: 'Editing transcript', SENDING: 'Sending to Hermes…', DONE: 'Transcript sent', ERROR: 'Error'
}

export default function VoicePushToTalk({ onTranscript, disabled = false, sendLabel = 'Send to Hermes' }) {
  const recorderRef = useRef(null), streamRef = useRef(null), chunksRef = useRef([]), timerRef = useRef(null)
  const startedRef = useRef(0), recordingRef = useRef(false), previewSequenceRef = useRef(0), acceptedPreviewRef = useRef(0)
  const previewInFlightRef = useRef(false), previewQueuedRef = useRef(false), previewAbortRef = useRef(null), sessionRef = useRef('')
  const [state, setState] = useState('IDLE'), [error, setError] = useState(''), [previewNotice, setPreviewNotice] = useState('')
  const [partialTranscript, setPartialTranscript] = useState(''), [transcript, setTranscript] = useState(''), [elapsed, setElapsed] = useState(0)

  useEffect(() => () => { clearInterval(timerRef.current); previewAbortRef.current?.abort(); streamRef.current?.getTracks().forEach(track => track.stop()); if (recorderRef.current?.state === 'recording') recorderRef.current.stop() }, [])

  function clearRecording() { clearInterval(timerRef.current); streamRef.current?.getTracks().forEach(track => track.stop()); streamRef.current = null; recordingRef.current = false }

  async function requestPreview() {
    if (!previewEndpoint || !recordingRef.current || previewInFlightRef.current || !chunksRef.current.length) return
    if (Date.now() - startedRef.current < PREVIEW_CADENCE_MS) { previewQueuedRef.current = true; return }
    previewQueuedRef.current = false; previewInFlightRef.current = true
    const sequence = ++previewSequenceRef.current
    const blob = new Blob(chunksRef.current, { type: recorderRef.current?.mimeType || 'audio/webm' })
    const controller = new AbortController(); previewAbortRef.current = controller
    try {
      const response = await fetch(previewEndpoint, { method: 'POST', headers: { 'Content-Type': blob.type || 'audio/webm', 'X-Nexus-Voice-Session': sessionRef.current, 'X-Nexus-Voice-Preview-Sequence': String(sequence) }, credentials: 'include', body: blob, signal: controller.signal })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.error || 'live-preview-unavailable')
      if (sequence >= acceptedPreviewRef.current && payload.text) { acceptedPreviewRef.current = sequence; setPartialTranscript(payload.text); setState('LIVE_PREVIEW') }
    } catch (caught) { if (caught?.name !== 'AbortError' && recordingRef.current) setPreviewNotice('Live preview unavailable — final transcription will appear after release.') }
    finally { previewInFlightRef.current = false; previewAbortRef.current = null; if (previewQueuedRef.current && recordingRef.current) requestPreview() }
  }

  function schedulePreview() { if (!recordingRef.current) return; if (previewInFlightRef.current) { previewQueuedRef.current = true; return }; requestPreview() }

  async function start() {
    if (disabled || recordingRef.current || ['REQUESTING_PERMISSION', 'FINALIZING', 'TRANSCRIPT_READY', 'EDITING', 'SENDING'].includes(state)) return
    setError(''); setPreviewNotice(''); setPartialTranscript(''); setTranscript(''); setElapsed(0)
    if (!endpoint) { setState('ERROR'); setError('Admin voice transport is not configured; local-only STT is not exposed to this browser.'); return }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { setState('ERROR'); setError('This browser does not provide microphone capture.'); return }
    try {
      setState('REQUESTING_PERMISSION')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } }); streamRef.current = stream
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm'
      const recorder = new MediaRecorder(stream, { mimeType: mime }); chunksRef.current = []; previewSequenceRef.current = 0; acceptedPreviewRef.current = 0
      recorder.ondataavailable = event => { if (event.data.size) { chunksRef.current.push(event.data); schedulePreview() } }
      recorder.onstop = async () => {
        recordingRef.current = false; previewAbortRef.current?.abort(); clearRecording(); setState('FINALIZING')
        try {
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
          const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': blob.type || 'audio/webm', 'X-Nexus-Voice-Session': sessionRef.current }, credentials: 'include', body: blob }); const payload = await response.json()
          if (!response.ok) throw new Error(payload.error || 'voice-transcription-unavailable')
          setTranscript(payload.text || ''); setPartialTranscript(payload.text || ''); setState('TRANSCRIPT_READY')
        } catch (caught) { setState('ERROR'); setError(caught?.message || 'Voice transcription failed.') }
      }
      recorderRef.current = recorder; sessionRef.current = `admin-${Date.now()}`; startedRef.current = Date.now(); recordingRef.current = true; recorder.start(1000); setState('LISTENING')
      timerRef.current = setInterval(() => { const next = Date.now() - startedRef.current; setElapsed(next); if (next >= MAX_MS) stop() }, 100)
    } catch (caught) { clearRecording(); setState('ERROR'); setError(caught?.message || 'Microphone permission was not granted.') }
  }

  function stop() { if (recorderRef.current?.state === 'recording') recorderRef.current.stop() }
  async function sendReviewedTranscript() { const clean = transcript.trim(); if (!clean || !onTranscript || !['TRANSCRIPT_READY', 'EDITING'].includes(state)) return; setState('SENDING'); try { await onTranscript(clean); setState('DONE') } catch (caught) { setState('ERROR'); setError(caught?.message || 'Transcript could not be sent.') } }
  function retry() { previewAbortRef.current?.abort(); setTranscript(''); setPartialTranscript(''); setPreviewNotice(''); setError(''); setState('IDLE') }

  const review = transcript && ['TRANSCRIPT_READY', 'EDITING'].includes(state)
  return <div className="nexus-voice-ptt" data-voice-state={state}>
    <button type="button" className="hermes-chip nexus-voice-button" onPointerDown={start} onPointerUp={stop} onPointerCancel={stop} onKeyDown={event => { if ((event.key === 'Enter' || event.key === ' ') && !event.repeat) { event.preventDefault(); start() } }} onKeyUp={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); stop() } }} aria-label="Press and hold to talk" aria-pressed={recordingRef.current} disabled={disabled || ['FINALIZING', 'REQUESTING_PERMISSION', 'SENDING'].includes(state)}>🎙️</button>
    <small className="nexus-voice-state" role="status">{STATE_LABELS[state] || ''}{recordingRef.current ? ` ${(elapsed / 1000).toFixed(1)}s` : ''}</small>
    {(state === 'LISTENING' || state === 'LIVE_PREVIEW') && <div className="nexus-voice-partial" role="status" aria-live="polite" aria-atomic="true">{partialTranscript || 'Listening…'}</div>}
    {previewNotice && recordingRef.current && <div className="nexus-voice-notice" role="status">{previewNotice}</div>}
    {review && <div className="nexus-voice-review" role="region" aria-label="Transcript review"><strong>Transcript ready</strong><textarea aria-label="Edit transcript before sending" value={transcript} onFocus={() => setState('EDITING')} onChange={event => setTranscript(event.target.value)} rows={3} /><div className="nexus-voice-review-actions"><button type="button" onClick={retry}>Retry</button><button type="button" className="primary" onClick={sendReviewedTranscript} disabled={!transcript.trim()}>{sendLabel}</button></div></div>}
    {state === 'DONE' && <div className="nexus-voice-transcript"><strong>Sent transcript:</strong> {transcript}</div>}
    {error && <div className="nexus-voice-error" role="status">{error}</div>}
  </div>
}
