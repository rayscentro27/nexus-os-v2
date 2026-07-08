import { useState, useCallback } from 'react'
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import { supabase, isSupabaseConfigured } from '../../lib/supabaseClient'

interface UploadFile {
  file: File
  progress: number
  status: 'pending' | 'uploading' | 'success' | 'error'
  error?: string
  path?: string
  metadataWritten?: boolean
  metadataWarning?: string
}

const ALLOWED_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/heic',
  'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

const MAX_SIZE = 10 * 1024 * 1024 // 10MB

function validateFile(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return 'File type not supported. Please upload PDF, JPEG, PNG, HEIC, TXT, or DOCX.'
  }
  if (file.size > MAX_SIZE) {
    return 'File too large. Maximum size is 10MB.'
  }
  return null
}

function guessCategory(mimeType: string, fileName: string): string {
  const lower = fileName.toLowerCase()
  if (/address|utility|proof.of.address/.test(lower)) return 'proof_of_address'
  if (/bank|statement/.test(lower)) return 'bank_statement'
  if (/id|passport|license|government|identification/.test(lower)) return 'identification'
  if (/ein|tax|formation|incorporation/.test(lower)) return 'business_formation'
  if (/revenue|income|p&l|profit/.test(lower)) return 'revenue_summary'
  if (mimeType === 'application/pdf') return 'document'
  if (mimeType.startsWith('image/')) return 'identification'
  return 'miscellaneous'
}

export function DocumentUploadZone({ onUploadComplete }: { onUploadComplete?: () => void }) {
  const [files, setFiles] = useState<UploadFile[]>([])
  const [isDragging, setIsDragging] = useState(false)

  async function writeDocumentMetadata(params: { userId: string; path: string; file: File; category: string }) {
    const { userId, path, file, category } = params
    const now = new Date().toISOString()
    const row = {
      id: `${userId}_${Date.now()}`,
      tenant_id: 'tenant_demo_goclear',
      client_id: userId,
      category,
      title: file.name,
      summary: `Client portal upload — ${file.name} (${file.type || 'unknown'}, ${(file.size / 1024).toFixed(0)}KB) stored at ${path}`,
      status: 'pending_review',
      priority: 'normal',
      risk_level: 'low',
      automation_level: 'manual',
      client_visible: true,
      approval_required: true,
      goclear_review_status: 'pending_review',
      source: 'client_portal_upload',
      source_concept: 'document_upload',
      recommended_next_action: 'Admin review uploaded document',
      created_at: now,
    }
    const { error } = await supabase!.from('client_documents').insert(row)
    if (error) {
      return { ok: false as const, warning: `Storage upload succeeded, but metadata insert failed: ${error.message}` }
    }
    return { ok: true as const }
  }

  const handleFiles = useCallback(async (fileList: FileList) => {
    const newFiles: UploadFile[] = Array.from(fileList).map(file => ({
      file,
      progress: 0,
      status: 'pending' as const,
    }))

    setFiles(prev => [...prev, ...newFiles])

    for (const uploadFile of newFiles) {
      const error = validateFile(uploadFile.file)
      if (error) {
        setFiles(prev => prev.map(f => f.file === uploadFile.file ? { ...f, status: 'error', error } : f))
        continue
      }

      try {
        setFiles(prev => prev.map(f => f.file === uploadFile.file ? { ...f, status: 'uploading' } : f))

        if (!isSupabaseConfigured || !supabase) {
          setFiles(prev => prev.map(f => f.file === uploadFile.file ? { ...f, status: 'error', error: 'Supabase not configured' } : f))
          continue
        }

        const { data: { user } } = await supabase.auth.getUser()
        if (!user) {
          setFiles(prev => prev.map(f => f.file === uploadFile.file ? { ...f, status: 'error', error: 'Not signed in' } : f))
          continue
        }

        const timestamp = Date.now()
        const sanitizedName = uploadFile.file.name.replace(/[^a-zA-Z0-9._-]/g, '_')
        const path = `${user.id}/${timestamp}_${sanitizedName}`

        const { error: uploadError } = await supabase!.storage
          .from('client-documents')
          .upload(path, uploadFile.file, {
            cacheControl: '3600',
            upsert: false,
          })

        if (uploadError) {
          setFiles(prev => prev.map(f => f.file === uploadFile.file ? { ...f, status: 'error', error: uploadError.message } : f))
          continue
        }

        const category = guessCategory(uploadFile.file.type, uploadFile.file.name)
        const metadataResult = await writeDocumentMetadata({ userId: user.id, path, file: uploadFile.file, category })

        if (metadataResult.ok) {
          setFiles(prev => prev.map(f => f.file === uploadFile.file ? { ...f, status: 'success', path, metadataWritten: true } : f))
        } else {
          setFiles(prev => prev.map(f => f.file === uploadFile.file ? { ...f, status: 'success', path, metadataWritten: false, metadataWarning: metadataResult.warning } : f))
        }
      } catch (err) {
        setFiles(prev => prev.map(f => f.file === uploadFile.file ? { ...f, status: 'error', error: 'Upload failed' } : f))
      }
    }

    onUploadComplete?.()
  }, [onUploadComplete])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files)
    }
  }, [handleFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleClick = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = true
    input.accept = ALLOWED_TYPES.join(',')
    input.onchange = (e) => {
      const target = e.target as HTMLInputElement
      if (target.files?.length) {
        handleFiles(target.files)
      }
    }
    input.click()
  }, [handleFiles])

  const removeFile = useCallback((file: File) => {
    setFiles(prev => prev.filter(f => f.file !== file))
  }, [])

  const statusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'uploading': return <Loader2 size={16} className="spin" />
      case 'success': return <CheckCircle2 size={16} className="text-green-600" />
      case 'error': return <AlertCircle size={16} className="text-red-600" />
      default: return <FileText size={16} />
    }
  }

  return (
    <div className="client-upload-zone">
      <div
        className={`client-upload-dropzone ${isDragging ? 'dragging' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
      >
        <Upload size={32} />
        <strong>Drop files here or click to upload</strong>
        <span>PDF, JPEG, PNG, HEIC, TXT, DOCX — Max 10MB</span>
      </div>

      {files.length > 0 && (
        <div className="client-upload-list">
          {files.map((f, i) => (
            <div key={i} className={`client-upload-item ${f.status}`}>
              {statusIcon(f.status)}
              <span className="client-upload-name">{f.file.name}</span>
              <span className="client-upload-size">{(f.file.size / 1024).toFixed(0)}KB</span>
              {f.status === 'uploading' && (
                <div className="client-upload-progress">
                  <div className="client-upload-progress-bar" style={{ width: '60%' }} />
                </div>
              )}
              {f.status === 'success' && f.metadataWritten === false && f.metadataWarning && (
                <span className="client-upload-warning">{f.metadataWarning}</span>
              )}
              {f.status === 'success' && f.metadataWritten === true && (
                <span className="client-upload-success">Saved and queued for review</span>
              )}
              {f.status === 'error' && <span className="client-upload-error">{f.error}</span>}
              {f.status === 'pending' && (
                <button className="client-upload-remove" onClick={(e) => { e.stopPropagation(); removeFile(f.file) }}>×</button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
