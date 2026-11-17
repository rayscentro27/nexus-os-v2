/** Data shapes returned by the live Nexus Research Room API. */
export interface RoomSource {
  source_id: string
  room_id: string
  source_type: string
  title?: string
  content_or_url?: string
  requested_url?: string
  resolved_url?: string
  canonical_url?: string
  domain?: string
  page_title?: string
  retrieved_at?: string
  retrieval_status?: string
  content_hash?: string
  content_type?: string
  extracted_text?: string
  source_provenance?: Record<string, unknown>
  retrieval_error?: string
  created_at?: string
  [key: string]: unknown
}

export interface Citation {
  citation_id: number
  source_id: string
  source_title: string
  url?: string
  domain?: string
  excerpt?: string
  retrieval_status?: string
  content_hash?: string
}

export interface RoomMessage {
  message_id: string
  room_id: string
  timestamp?: string
  author: string
  content: string
  source_refs?: string[]
  citations?: Citation[]
  metadata?: Record<string, unknown>
}

export interface RoomThread {
  thread_id: string
  room_id: string
  title: string
  created_at?: string
  updated_at?: string
}

export interface ResearchRoom {
  room_id: string
  title: string
  status?: string
  created_at?: string
  updated_at?: string
  sources?: RoomSource[]
  messages?: RoomMessage[]
  threads?: RoomThread[]
  active_thread_id?: string
  preliminary_score?: number | null
  score_state?: string
  score_basis?: Record<string, unknown>
  promoted_project_id?: string
  promotion_status?: string
  [key: string]: unknown
}
