import React, { useEffect, useRef, useState } from 'react'
import { createThread, deriveThreadTitle, getActiveThread, isNewThreadCommand, loadThread, routeWakePhrase, saveThread, sendAgentMessage, setActiveThread, stripWakePhrase } from '../lib/nexusAgentDispatch'
import { speakHermesResponse, stopHermesSpeech } from '../lib/hermesSpeechSynthesis'

const endpoint = import.meta.env.VITE_NEXUS_VOICE_ENDPOINT || ''
const MAX_MS = 30000
const SILENCE_MS = 1100
const PREVIEW_MS = 1200
const COOLDOWN_MS = 900
const OWNER_KEY = 'nexus-voice-listener-owner'
const OWNER_TTL = 5000

function ownerId() { return `voice-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` }
function ownerIsOther(id) { try { const item = JSON.parse(localStorage.getItem(OWNER_KEY) || 'null'); return item && item.id !== id && item.expiresAt > Date.now() } catch { return false } }
function claim(id) { try { localStorage.setItem(OWNER_KEY, JSON.stringify({ id, expiresAt: Date.now() + OWNER_TTL })) } catch { /* browser policy */ } }
function release(id) { try { if (JSON.parse(localStorage.getItem(OWNER_KEY) || 'null')?.id === id) localStorage.removeItem(OWNER_KEY) } catch {} }

export default function NexusWakeVoice({ onDispatched }) {
  const idRef = useRef(ownerId()), streamRef = useRef(null), audioRef = useRef(null), analyserRef = useRef(null), rafRef = useRef(null), recorderRef = useRef(null), cooldownRef = useRef(null)
  const chunksRef = useRef([]), startedRef = useRef(0), lastSoundRef = useRef(0), speakingRef = useRef(false), persistentRef = useRef(false), previewAtRef = useRef(0), sequenceRef = useRef(0), previewAbortRef = useRef(null), followUpRef = useRef(null), wakeStateRef = useRef('WAKE_IDLE')
  const [enabled, setEnabled] = useState(false), [capturing, setCapturing] = useState(false), [partial, setPartial] = useState(''), [status, setStatus] = useState(''), [notice, setNotice] = useState(''), [otherOwner, setOtherOwner] = useState(false)

  useEffect(() => () => { stopHermesSpeech(); stopCapture(); stopListening(); release(idRef.current) }, [])
  useEffect(() => { const onStorage = event => { if (event.key === OWNER_KEY) setOtherOwner(ownerIsOther(idRef.current)) }; window.addEventListener('storage', onStorage); return () => window.removeEventListener('storage', onStorage) }, [])

  function setWakeState(next) { wakeStateRef.current = next }
  function armCooldown() { clearTimeout(cooldownRef.current); setWakeState('COOLDOWN'); cooldownRef.current = setTimeout(() => { if (persistentRef.current) setWakeState('WAKE_IDLE') }, COOLDOWN_MS) }
  function stopCapture() { cancelAnimationFrame(rafRef.current); clearTimeout((stopCapture).silenceTimer); previewAbortRef.current?.abort(); if (recorderRef.current?.state === 'recording') recorderRef.current.stop(); recorderRef.current = null; speakingRef.current = false; setCapturing(false) }
  function stopListening() { clearTimeout(cooldownRef.current); stopCapture(); streamRef.current?.getTracks().forEach(track => track.stop()); streamRef.current = null; audioRef.current?.close?.(); audioRef.current = null; setWakeState('WAKE_IDLE'); if (persistentRef.current) release(idRef.current); persistentRef.current = false }
  function scheduleStop() { clearTimeout((stopCapture).silenceTimer); (stopCapture).silenceTimer = setTimeout(() => { if (speakingRef.current) finishUtterance() }, SILENCE_MS) }

  async function preview(blob, sequence) {
    // Persistent listening deliberately sends no rolling preview STT. It
    // records one bounded utterance and performs one final local STT call;
    // Quick Voice retains its explicit preview behavior.
    if (persistentRef.current || !endpoint || !blob.size) return
    const previewEndpoint = endpoint.replace(/\/v1\/voice\/transcribe\/?$/, '/v1/voice/preview')
    const controller = new AbortController(); previewAbortRef.current = controller
    try { const response = await fetch(previewEndpoint, { method: 'POST', credentials: 'include', headers: { 'Content-Type': blob.type || 'audio/webm', 'X-Nexus-Voice-Session': `wake-${idRef.current}`, 'X-Nexus-Voice-Preview-Sequence': String(sequence) }, body: blob, signal: controller.signal }); const payload = await response.json(); if (response.ok && payload.text && sequence >= sequenceRef.current) setPartial(payload.text) } catch { /* final transcription remains authoritative */ }
  }

  async function finalize(blob) {
    if (!endpoint || !blob.size) { setStatus('Ready'); return }
    setWakeState('ROUTING')
    setStatus('Thinking…')
    try {
      setWakeState('THINKING')
      const response = await fetch(endpoint, { method: 'POST', credentials: 'include', headers: { 'Content-Type': blob.type || 'audio/webm', 'X-Nexus-Voice-Session': `wake-${idRef.current}` }, body: blob })
      const payload = await response.json(); if (!response.ok) throw new Error(payload.error || 'Voice transcription unavailable')
      const text = String(payload.text || '').trim(); setPartial(text)
      const explicitAgent = routeWakePhrase(text); const followUp = !explicitAgent && followUpRef.current && followUpRef.current.expiresAt > Date.now() ? followUpRef.current.agent : null; const agent = explicitAgent || followUp
      if (!agent) { setStatus('Say “Hey Nexus”, “Hey Nova”, or “Hey Alpha”'); return }
      const message = stripWakePhrase(text); if (!message && !isNewThreadCommand(text)) { setStatus(`Heard ${agent === 'hermes' ? 'Nexus' : agent}; waiting for a request`); return }
      let id = getActiveThread(agent); let thread = id ? loadThread(agent, id) : null
      const fresh = isNewThreadCommand(text)
      if (fresh || !thread) { thread = createThread(agent, fresh ? deriveThreadTitle(text) : 'New conversation'); id = thread.id; setActiveThread(agent, id) }
      const body = fresh ? deriveThreadTitle(text) : message
      if (!body || body === 'New conversation') { saveThread(thread); setStatus(`New ${agent} chat ready`); onDispatched?.({ agent, conversationId: id, text: '' }); return }
      const now = new Date().toISOString(); const user = { id: `${Date.now()}-voice`, role: 'user', text: body, createdAt: now }; const recentHistory = (thread.messages || []).slice(-10).map(item => ({ role: item.role === 'assistant' ? 'assistant' : 'user', content: item.text }))
      thread = { ...thread, title: thread.messages?.length ? thread.title : body.slice(0, 48), updatedAt: now, messages: [...(thread.messages || []), user] }; saveThread(thread)
      const reply = await sendAgentMessage({ agent, conversationId: id, text: body, recentHistory }); thread = { ...thread, updatedAt: new Date().toISOString(), messages: [...thread.messages, reply] }; saveThread(thread)
      if (agent === 'hermes') speakHermesResponse(reply?.text || reply?.content || '')
      followUpRef.current = { agent, conversationId: id, expiresAt: Date.now() + 20000 }; window.dispatchEvent(new CustomEvent('nexus:voice-thread-update', { detail: { agent, conversationId: id } })); onDispatched?.({ agent, conversationId: id, text: body }); setStatus(`${agent === 'hermes' ? 'Nexus / Hermes' : agent[0].toUpperCase() + agent.slice(1)} responded`)
    } catch (error) { setStatus(error?.message || 'Voice error'); setNotice('Quick Voice failed; no external action was performed.') }
  }

  function finishUtterance() { if (!recorderRef.current || recorderRef.current.state !== 'recording') return; recorderRef.current.stop() }
  function beginRecorder() {
    if (speakingRef.current || !streamRef.current || !['WAKE_IDLE', 'FOLLOW_UP_READY'].includes(wakeStateRef.current)) return
    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm'; const recorder = new MediaRecorder(streamRef.current, { mimeType: mime }); chunksRef.current = []; sequenceRef.current = 0; previewAtRef.current = 0; startedRef.current = Date.now(); speakingRef.current = true; setCapturing(true); setStatus('Listening…')
    recorder.ondataavailable = event => { if (!event.data.size) return; chunksRef.current.push(event.data); const elapsed = Date.now() - startedRef.current; if (elapsed - previewAtRef.current >= PREVIEW_MS) { previewAtRef.current = elapsed; const sequence = ++sequenceRef.current; void preview(new Blob(chunksRef.current, { type: recorder.mimeType }), sequence) } }
    recorder.onstop = () => { recorderRef.current = null; speakingRef.current = false; setCapturing(false); setWakeState('FINALIZING'); const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' }); void finalize(blob).finally(() => { if (!persistentRef.current) stopListening(); else armCooldown() }) }
    recorderRef.current = recorder; recorder.start(500); scheduleStop()
  }
  function sampleVoice() { if (!analyserRef.current) return; const data = new Uint8Array(analyserRef.current.fftSize); analyserRef.current.getByteTimeDomainData(data); let sum = 0; for (const value of data) { const delta = (value - 128) / 128; sum += delta * delta } const rms = Math.sqrt(sum / data.length); if (rms > 0.035 && ['WAKE_IDLE', 'FOLLOW_UP_READY', 'CAPTURING'].includes(wakeStateRef.current)) { lastSoundRef.current = Date.now(); if (!speakingRef.current) beginRecorder(); else scheduleStop() } if (speakingRef.current && Date.now() - lastSoundRef.current > SILENCE_MS) finishUtterance(); if (Date.now() - startedRef.current > MAX_MS && speakingRef.current) finishUtterance(); rafRef.current = requestAnimationFrame(sampleVoice) }
  async function startListening(persistent = true) {
    if (otherOwner || ownerIsOther(idRef.current)) { setOtherOwner(true); return }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { setStatus('This browser does not provide private microphone capture'); return }
    if (!endpoint) { setStatus('Voice endpoint is not configured'); return }
    try { claim(idRef.current); persistentRef.current = persistent; setWakeState('WAKE_IDLE'); const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } }); streamRef.current = stream; const AudioContextCtor = window.AudioContext || window.webkitAudioContext; const context = new AudioContextCtor(); const source = context.createMediaStreamSource(stream); const analyser = context.createAnalyser(); analyser.fftSize = 512; source.connect(analyser); audioRef.current = context; analyserRef.current = analyser; setEnabled(persistent); setOtherOwner(false); setNotice('Private local VAD active. One utterance at a time; persistent listening sends one final local STT request after silence.'); lastSoundRef.current = Date.now(); rafRef.current = requestAnimationFrame(sampleVoice) } catch (error) { release(idRef.current); persistentRef.current = false; setWakeState('WAKE_IDLE'); setStatus(error?.message || 'Microphone permission was not granted') }
  }
  function toggle() { if (enabled) { stopListening(); setEnabled(false); setStatus('Voice Listening off'); setNotice('') } else void startListening(true) }
  function quick() { if (capturing) return; void startListening(false).then(() => { setStatus('Listening… say a wake phrase'); setTimeout(() => { if (!speakingRef.current) beginRecorder() }, 150) }) }
  function takeover() { stopListening(); setOtherOwner(false); void startListening(true) }

  return <section className="nx2-wake-voice" data-testid="nx2-wake-voice"><div className="nx2-wake-controls"><button type="button" className={`nx2-voice-listening-toggle ${enabled ? 'active' : ''}`} onClick={toggle} aria-pressed={enabled}>{enabled ? '● Voice Listening ON' : '○ Voice Listening OFF'}</button>{!enabled && <button type="button" className="nx2-quick-voice" onClick={quick} aria-label="Start one quick private voice conversation">🎙 Quick Voice</button>}</div>{enabled && <div className="nx2-wake-indicator" role="status">● Listening locally for: <b>Hey Nexus</b> · <b>Hey Nova</b> · <b>Hey Alpha</b><button type="button" onClick={toggle}>Turn Listening Off</button></div>}{otherOwner && <div className="nx2-wake-conflict" role="status">Voice listening active in another Nexus window. <button type="button" onClick={takeover}>Take over Voice</button></div>}{status && <div className="nx2-wake-status" role="status">{capturing ? 'Listening…' : status}{partial && capturing ? ` ${partial}` : ''}</div>}{notice && <small className="nx2-wake-notice">{notice}</small>}</section>
}
