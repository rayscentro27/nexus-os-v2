import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Plus, Search, BookOpen, ArrowUpRight, FileText, Video, Send, RefreshCw,
  ExternalLink, Globe, FileCheck, X, GitCompare
} from 'lucide-react'
import {
  listResearchRoomsLive, getResearchRoomLive, createResearchRoomLive,
  addResearchRoomSourceLive, askAlphaLive, scoreResearchRoomLive,
  promoteResearchRoomLive,
} from '../lib/researchRoomApi'
import './researchRoomWorkspace.css'

const unwrapRoom = (payload) => payload?.room || payload
const roomMessages = (room) => Array.isArray(room?.messages) ? room.messages : []
const roomSources = (room) => Array.isArray(room?.sources) ? room.sources : []

export default function ResearchRoomWorkspace() {
  const [rooms, setRooms] = useState([])
  const [selectedRoom, setSelectedRoom] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [researchActivity, setResearchActivity] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [chatInput, setChatInput] = useState('')
  const [sessionMessages, setSessionMessages] = useState([])
  const [sessionMessagesRoomId, setSessionMessagesRoomId] = useState(null)
  const [askingRoomId, setAskingRoomId] = useState(null)
  const [showNewRoom, setShowNewRoom] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newSource, setNewSource] = useState('')
  const [showAddSource, setShowAddSource] = useState(false)
  const [sourceType, setSourceType] = useState('URL')
  const [sourceTitle, setSourceTitle] = useState('')
  const [sourceContent, setSourceContent] = useState('')
  const [showPromote, setShowPromote] = useState(false)
  const [promoteObjective, setPromoteObjective] = useState('')
  const [promotion, setPromotion] = useState(null)
  const [citation, setCitation] = useState(null)
  const [sourceDetail, setSourceDetail] = useState(null)

  const refreshRooms = useCallback(async (selectId) => {
    setLoading(true)
    setError('')
    try {
      const payload = await listResearchRoomsLive({
        ...(statusFilter !== 'ALL' ? { status: statusFilter } : {}),
        ...(searchQuery.trim() ? { query: searchQuery.trim() } : {}),
      })
      const rows = Array.isArray(payload?.rooms) ? payload.rooms : []
      setRooms(rows)
      const nextId = selectId || selectedRoom?.room_id
      if (!nextId || !rows.some((room) => room.room_id === nextId)) {
        setSelectedRoom(null)
        if (!selectId && !selectedRoom && rows[0]?.room_id) await openRoom(rows[0].room_id)
      } else if (selectId) await openRoom(selectId)
    } catch (err) {
      setError(err?.message || 'Research Rooms are unavailable.')
      setRooms([])
      setSelectedRoom(null)
    } finally {
      setLoading(false)
    }
  }, [searchQuery, statusFilter, selectedRoom?.room_id])

  const openRoom = useCallback(async (roomId) => {
    if (!roomId) return
    setError('')
    try {
      const payload = await getResearchRoomLive(roomId)
      setSelectedRoom(unwrapRoom(payload))
    } catch (err) {
      setError(err?.message || 'This Research Room is unavailable.')
      setSelectedRoom(null)
    }
  }, [])

  useEffect(() => { refreshRooms() }, [statusFilter, searchQuery]) // eslint-disable-line react-hooks/exhaustive-deps

  const messages = useMemo(() => [
    ...roomMessages(selectedRoom),
    ...(sessionMessagesRoomId === selectedRoom?.room_id ? sessionMessages : []),
  ], [selectedRoom, sessionMessages, sessionMessagesRoomId])
  const sources = roomSources(selectedRoom)

  async function runAction(action) {
    if (busy) return
    setBusy(true)
    setError('')
    setNotice('')
    try { await action() } catch (err) { setError(err?.message || 'Research request failed.') }
    finally { setBusy(false) }
  }

  async function handleCreateRoom(event) {
    event.preventDefault()
    if (!newTitle.trim()) return
    await runAction(async () => {
      const payload = await createResearchRoomLive({ title: newTitle.trim() })
      const created = unwrapRoom(payload)
      const roomId = payload?.room_id || created?.room_id
      if (newSource.trim() && roomId) {
        await addResearchRoomSourceLive(roomId, { source_type: 'URL', content_or_url: newSource.trim() })
      }
      setNewTitle(''); setNewSource(''); setShowNewRoom(false)
      setSessionMessages([])
      setSessionMessagesRoomId(roomId || null)
      await refreshRooms(roomId)
    })
  }

  async function handleAddSource(event) {
    event.preventDefault()
    if (!selectedRoom || !sourceContent.trim()) return
    await runAction(async () => {
      await addResearchRoomSourceLive(selectedRoom.room_id, {
        source_type: sourceType, content_or_url: sourceContent.trim(), ...(sourceTitle.trim() ? { title: sourceTitle.trim() } : {}),
      })
      setSourceTitle(''); setSourceContent(''); setShowAddSource(false)
      await openRoom(selectedRoom.room_id)
      await refreshRooms(selectedRoom.room_id)
    })
  }

  async function handleAsk(event) {
    event.preventDefault()
    if (!selectedRoom || !chatInput.trim() || busy) return
    const question = chatInput.trim()
    const roomId = selectedRoom.room_id
    setChatInput('')
    setError('')
    setNotice('')
    setBusy(true)
    setResearchActivity('Checking room evidence; public search and page reading run automatically when needed…')
    setAskingRoomId(roomId)
    setSessionMessagesRoomId(roomId)
    setSessionMessages((current) => [...current, {
      message_id: `session-user-${Date.now()}`,
      author: 'RAY',
      content: question,
    }])
    try {
      const result = await askAlphaLive(roomId, question)
      const response = result?.alpha_message || result?.response || result?.data || result?.result || result?.structuredContent || result
      const answer = [
        result?.alpha_message?.content,
        result?.answer,
        result?.alpha_answer,
        response?.answer,
        result?.structuredContent?.answer,
        result?.message?.content,
        response?.message?.content,
        result?.content,
      ].find((value) => typeof value === 'string' && value.trim())
      if (!answer) throw new Error('Alpha did not return an answer.')
      setSessionMessages((current) => [...current, {
        ...(response && typeof response === 'object' && !Array.isArray(response) ? response : {}),
        message_id: `session-alpha-${Date.now()}`,
        author: 'ALPHA',
        content: answer,
        ...(Array.isArray(response?.citations) ? { citations: response.citations } : {}),
        ...(Array.isArray(response?.source_refs) ? { source_refs: response.source_refs } : {}),
      }])
    } catch (err) {
      setSessionMessages((current) => [...current, {
        message_id: `session-error-${Date.now()}`,
        author: 'SYSTEM',
        content: err?.message || 'Alpha could not answer this request.',
      }])
    } finally {
      setAskingRoomId(null)
      setBusy(false)
      setResearchActivity('')
    }
  }

  async function handleScore() {
    if (!selectedRoom) return
    await runAction(async () => {
      const result = await scoreResearchRoomLive(selectedRoom.room_id)
      const room = unwrapRoom(result)
      if (room?.room_id) setSelectedRoom(room)
      else await openRoom(selectedRoom.room_id)
      await refreshRooms(selectedRoom.room_id)
    })
  }

  async function handlePromote(event) {
    event.preventDefault()
    if (!selectedRoom || !promoteObjective.trim()) return
    await runAction(async () => {
      const result = await promoteResearchRoomLive(selectedRoom.room_id, promoteObjective.trim())
      setPromotion(result)
      setPromoteObjective(''); setShowPromote(false)
      await openRoom(selectedRoom.room_id)
      await refreshRooms(selectedRoom.room_id)
    })
  }

  function renderCitations(message) {
    const refs = Array.isArray(message.source_refs) ? message.source_refs : []
    const citations = Array.isArray(message.citations) ? message.citations : []
    return message.content?.split(/(\[\d+\])/g).map((part, index) => {
      const match = part.match(/^\[(\d+)\]$/)
      if (!match) return <span key={index}>{part}</span>
      const number = Number(match[1])
      const actual = citations.find((item) => Number(item.citation_id) === number)
      const sourceId = actual?.source_id || refs[number - 1]
      const source = sources.find((item) => item.source_id === sourceId)
      if (!source) return <span key={index}>{part}</span>
      const evidence = actual ? { ...source, ...actual } : source
      return <button key={index} type="button" className="rr-citation-chip" onClick={() => setCitation(evidence)} title="View returned source evidence">{number}</button>
    })
  }

  return (
    <div className="research-room-workspace" data-testid="research-room-workspace">
      <aside className="rr-sidebar" data-testid="research-rooms-sidebar">
        <div className="rr-sidebar-header"><h3>Research Rooms</h3><button type="button" className="rr-btn-new-room" onClick={() => setShowNewRoom(true)} data-testid="btn-new-room"><Plus size={13} /> New Research</button></div>
        <div className="rr-search-box"><Search size={13} /><input placeholder="Search rooms..." value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} /></div>
        <select aria-label="Room status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="ALL">All rooms</option><option value="ACTIVE">Active</option><option value="PROMOTED">Promoted</option><option value="ARCHIVED">Archived</option></select>
        <div className="rr-room-list" data-testid="research-room-list">
          {rooms.map((room) => <button type="button" key={room.room_id} className={`rr-room-item ${selectedRoom?.room_id === room.room_id ? 'active' : ''}`} onClick={() => { if (selectedRoom?.room_id !== room.room_id) { setSessionMessages([]); setSessionMessagesRoomId(null) } openRoom(room.room_id) }} data-testid={`room-item-${room.room_id}`}>
            <div className="rr-room-item-top"><span className={`rr-status-pill ${(room.status || 'unknown').toLowerCase()}`}>{room.status || 'UNKNOWN'}</span><span className="rr-score-badge">{room.preliminary_score ?? '—'}</span></div>
            <div className="rr-room-item-title">{room.title || 'Untitled Research Room'}</div>
            <div className="rr-room-item-meta"><span>{roomSources(room).length} sources</span><span>·</span><span>{room.updated_at ? new Date(room.updated_at).toLocaleString() : 'Activity unknown'}</span></div>
          </button>)}
          {!loading && rooms.length === 0 && <div style={{ padding: 20, textAlign: 'center', color: '#64748b', fontSize: 11 }}>{error ? 'Unable to load rooms.' : 'No Research Rooms returned.'}</div>}
          {loading && <div style={{ padding: 20, textAlign: 'center', color: '#64748b', fontSize: 11 }}>Loading live rooms…</div>}
        </div>
      </aside>

      {selectedRoom ? <main className="rr-main" data-testid="research-room-main">
        <div className="rr-main-header"><div className="rr-main-title-block"><h2>{selectedRoom.title || 'Research Room'}</h2><div className="rr-main-badges"><span className={`rr-status-pill ${(selectedRoom.status || 'unknown').toLowerCase()}`}>{selectedRoom.status || 'UNKNOWN'}</span><div className="rr-score-display" data-testid="preliminary-score-display"><span>Preliminary Score:</span><strong>{selectedRoom.preliminary_score ?? 'Score unavailable'}</strong></div>{selectedRoom.promotion_status && <span className="rr-status-pill promoted">{selectedRoom.promotion_status}</span>}</div></div>
          <div className="rr-actions-bar"><button type="button" className="rr-btn" onClick={handleScore} disabled={busy} data-testid="btn-score-room"><RefreshCw size={13} /> Score</button><button type="button" className="rr-btn" disabled title="Live room comparison is not exposed by the Research API" data-testid="btn-compare-rooms"><GitCompare size={13} /> Compare unavailable</button><button type="button" className="rr-btn rr-btn-promote" onClick={() => setShowPromote(true)} disabled={busy} data-testid="btn-promote-room"><ArrowUpRight size={13} /> Promote to Nova</button></div>
        </div>

        {error && <div role="alert" className="rr-error-banner">{error}</div>}{notice && <div role="status">{notice}</div>}{researchActivity && <div role="status" className="rr-research-activity" data-testid="research-activity-status">{researchActivity}</div>}
        <section className="rr-sources-section" data-testid="research-sources-panel"><div className="rr-sources-header"><div className="rr-sources-title"><BookOpen size={14} /><span>SOURCES ({sources.length})</span></div><button type="button" className="rr-btn-add-source-compact" onClick={() => setShowAddSource(true)} disabled={busy}><Plus size={12} /> Add Source</button></div>
          <div className="rr-source-cards-scroll">{sources.map((source, index) => <button type="button" key={source.source_id} className="rr-source-pill-card" onClick={() => setSourceDetail(source)} data-testid={`source-card-${source.source_id}`}><div className="rr-source-pill-icon">{source.source_type === 'URL' ? <Globe size={13} /> : source.source_type === 'YOUTUBE' ? <Video size={13} /> : <FileText size={13} />}</div><div className="rr-source-pill-content"><div className="rr-source-pill-title"><span className="rr-source-index-num">[{index + 1}]</span> {source.domain || source.page_title || source.title || 'Source title unavailable'}</div><div className="rr-source-pill-meta"><span className="rr-retrieval-status">{source.retrieval_status || 'UNKNOWN'}</span>{source.domain && <span className="rr-domain-tag">{source.domain}</span>}</div></div></button>)}{sources.length === 0 && <div className="rr-empty-sources-banner">No sources returned for this room.</div>}</div>
        </section>

        <section className="rr-threads-section" data-testid="persistent-threads-bar"><div className="rr-threads-bar"><span className="rr-threads-label">Conversation</span><span>Thread persistence coming next</span></div></section>
        <section className="rr-chat-workspace" data-testid="chat-workspace"><div className="rr-chat-messages" data-testid="chat-messages-container">
          {messages.map((message, index) => {
            const role = String(message.author || message.role || message.type || 'UNKNOWN').toUpperCase()
            const isUser = role === 'RAY' || role === 'USER'
            const isAlpha = role === 'ALPHA' || role === 'ASSISTANT'
            const isSystem = role === 'SYSTEM'
            const kind = isUser ? 'ray' : isAlpha ? 'alpha' : isSystem ? 'system' : 'nova'
            const label = isUser ? 'Ray' : isAlpha ? 'Alpha (Research Agent)' : role
            const content = message.content || message.answer || ''
            return <div key={message.message_id || `${message.timestamp || index}-${index}`} className={`rr-chat-msg ${kind}`} data-testid={`chat-message-${message.message_id || index}`}><div className="rr-chat-msg-header">{label}</div><div className="rr-chat-msg-content">{isAlpha ? renderCitations({ ...message, content }) : content}</div></div>
          })}
          {askingRoomId === selectedRoom.room_id && <div className="rr-chat-msg system" role="status" data-testid="alpha-loading-message"><div className="rr-chat-msg-header">Alpha</div><div className="rr-chat-msg-content">Thinking…</div></div>}
          {messages.length === 0 && <div className="rr-empty-sources-banner">No conversation messages returned.</div>}
        </div><div className="rr-composer-container"><div className="rr-mode-selector-bar" data-testid="research-mode-selector"><span className="rr-mode-label">Mode:</span><span className="rr-mode-btn active" data-testid="mode-btn-sources-plus-web"><BookOpen size={11} /> Sources + Web</span><span className="rr-mode-btn" data-testid="mode-btn-web-search"><Globe size={11} /> Public search available</span><button type="button" className="rr-mode-btn" disabled title="Deep Research is not enabled in conversational mode" data-testid="mode-btn-deep-research"><FileCheck size={11} /> Deep Research unavailable</button><span className="rr-mode-helper-text">Alpha searches and reads public sources when room evidence is insufficient. No background ingestion.</span></div><form onSubmit={handleAsk} className="rr-chat-composer" data-testid="chat-composer-form"><input placeholder="Ask Alpha about attached sources…" value={chatInput} onChange={(event) => setChatInput(event.target.value)} disabled={busy} data-testid="chat-composer-input"/><button type="submit" disabled={!chatInput.trim() || busy} className="rr-composer-send-btn" data-testid="chat-composer-submit"><Send size={13} /> Send</button></form></div></section>
      </main> : <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>{error || 'Select or create a Research Room to begin.'}</div>}

      {showNewRoom && <div className="rr-modal-backdrop" onClick={() => setShowNewRoom(false)}><div className="rr-modal" onClick={(event) => event.stopPropagation()} data-testid="new-room-modal"><div className="rr-modal-header-row"><h3>Create Research Room</h3><button type="button" className="rr-btn-icon-close" onClick={() => setShowNewRoom(false)}><X size={14} /></button></div><form onSubmit={handleCreateRoom}><div className="rr-form-group"><label>Room Title / Topic</label><input value={newTitle} onChange={(event) => setNewTitle(event.target.value)} required data-testid="input-new-room-title" /></div><div className="rr-form-group"><label>Initial Source URL (Optional)</label><textarea rows={3} value={newSource} onChange={(event) => setNewSource(event.target.value)} placeholder="Paste a URL" data-testid="input-new-room-content" /></div><div className="rr-modal-actions"><button type="button" className="rr-btn" onClick={() => setShowNewRoom(false)}>Cancel</button><button type="submit" className="rr-btn rr-btn-primary" disabled={busy} data-testid="btn-submit-create-room">Create Room</button></div></form></div></div>}

      {showAddSource && <div className="rr-modal-backdrop" onClick={() => setShowAddSource(false)}><div className="rr-modal" onClick={(event) => event.stopPropagation()} data-testid="add-source-modal"><div className="rr-modal-header-row"><h3>Add Source to Room</h3><button type="button" className="rr-btn-icon-close" onClick={() => setShowAddSource(false)}><X size={14} /></button></div><form onSubmit={handleAddSource}><div className="rr-form-group"><label>Source Type</label><select value={sourceType} onChange={(event) => setSourceType(event.target.value)} data-testid="select-source-type"><option value="URL">Web Page URL</option><option value="YOUTUBE">YouTube Video</option><option value="TEXT">Text / Notes</option><option value="EXISTING_RESEARCH">Existing Research</option></select></div><div className="rr-form-group"><label>Source Title (Optional)</label><input value={sourceTitle} onChange={(event) => setSourceTitle(event.target.value)} data-testid="input-source-title" /></div><div className="rr-form-group"><label>Content or URL</label><textarea rows={4} value={sourceContent} onChange={(event) => setSourceContent(event.target.value)} required data-testid="input-source-content" /></div><div className="rr-modal-actions"><button type="button" className="rr-btn" onClick={() => setShowAddSource(false)}>Cancel</button><button type="submit" className="rr-btn rr-btn-primary" disabled={busy} data-testid="btn-submit-add-source">Add Source</button></div></form></div></div>}

      {showPromote && <div className="rr-modal-backdrop" onClick={() => setShowPromote(false)}><div className="rr-modal" onClick={(event) => event.stopPropagation()} data-testid="promote-to-nova-modal"><div className="rr-modal-header-row"><h3>Promote Room to Nova</h3><button type="button" className="rr-btn-icon-close" onClick={() => setShowPromote(false)}><X size={14} /></button></div><p>Submit this room through the live promotion endpoint. Promotion does not create downstream directives in this UI.</p><form onSubmit={handlePromote}><div className="rr-form-group"><label>Requested Business Objective</label><textarea rows={3} value={promoteObjective} onChange={(event) => setPromoteObjective(event.target.value)} required data-testid="input-promote-objective" /></div><div className="rr-modal-actions"><button type="button" className="rr-btn" onClick={() => setShowPromote(false)}>Cancel</button><button type="submit" className="rr-btn rr-btn-promote" disabled={busy} data-testid="btn-confirm-promotion">Confirm Promotion</button></div></form></div></div>}

      {promotion && <div className="rr-modal-backdrop" onClick={() => setPromotion(null)}><div className="rr-modal" onClick={(event) => event.stopPropagation()} data-testid="promotion-banner"><div className="rr-modal-header-row"><h3>Promotion response</h3><button type="button" className="rr-btn-icon-close" onClick={() => setPromotion(null)}><X size={14} /></button></div><pre>{JSON.stringify(promotion, null, 2)}</pre></div></div>}

      {citation && <div className="rr-modal-backdrop" onClick={() => setCitation(null)}><div className="rr-modal rr-citation-modal" onClick={(event) => event.stopPropagation()} data-testid="citation-popover-modal"><div className="rr-modal-header-row"><h3>{citation.source_title || citation.page_title || citation.title || 'Source evidence'}</h3><button type="button" className="rr-btn-icon-close" onClick={() => setCitation(null)}><X size={14} /></button></div><div>{citation.domain || 'Domain unavailable'} {citation.url && <a href={citation.url} target="_blank" rel="noreferrer"><ExternalLink size={11} /> Open source</a>}</div><div className="rr-citation-excerpt-box"><label>Supporting excerpt</label><p>{citation.excerpt || citation.extracted_text || 'Excerpt unavailable from the backend.'}</p></div><div>Status: {citation.retrieval_status || 'UNKNOWN'} {citation.content_hash && <code>{citation.content_hash}</code>}</div></div></div>}

      {sourceDetail && <div className="rr-modal-backdrop" onClick={() => setSourceDetail(null)}><div className="rr-modal rr-source-detail-modal" onClick={(event) => event.stopPropagation()} data-testid="source-detail-modal"><div className="rr-modal-header-row"><h3>{sourceDetail.page_title || sourceDetail.title || 'Source details'}</h3><button type="button" className="rr-btn-icon-close" onClick={() => setSourceDetail(null)}><X size={14} /></button></div><div className="rr-source-detail-meta-grid"><div><label>Source Type</label><strong>{sourceDetail.source_type || 'UNKNOWN'}</strong></div><div><label>Retrieval Status</label><strong>{sourceDetail.retrieval_status || 'UNKNOWN'}</strong></div><div><label>Domain</label><strong>{sourceDetail.domain || 'UNKNOWN'}</strong></div><div><label>Retrieved</label><strong>{sourceDetail.retrieved_at || 'UNKNOWN'}</strong></div></div>{(sourceDetail.requested_url || sourceDetail.source_url || sourceDetail.resolved_url) && <p>Requested URL: <a href={sourceDetail.requested_url || sourceDetail.source_url || sourceDetail.resolved_url} target="_blank" rel="noreferrer">{sourceDetail.requested_url || sourceDetail.source_url || sourceDetail.resolved_url}</a></p>}{sourceDetail.content_hash && <p>Content hash: <code>{sourceDetail.content_hash}</code></p>}<div className="rr-source-detail-body"><label>Retrieved content</label><div className="rr-source-text-viewport">{sourceDetail.extracted_text || 'Source text is not included in the live room response.'}</div></div>{sourceDetail.source_provenance && <pre>{JSON.stringify(sourceDetail.source_provenance, null, 2)}</pre>}</div></div>}
    </div>
  )
}
