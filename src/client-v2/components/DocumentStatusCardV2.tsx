import { FileText, Upload } from 'lucide-react'
import type { V2DocumentView } from '../types/v2-models'
import { navigateV2 } from '../utils/navigate'
import { StatusBadgeV2 } from './primitives'

export function DocumentStatusCardV2({ documents }: { documents: V2DocumentView }) {
  const missing = documents.missing.slice(0, 3)
  const fullyClean = missing.length === 0 && documents.processingCount === 0
  return (
    <div className="v2-card p-4 flex flex-col">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-lg bg-v2brand-tint text-v2brand flex items-center justify-center">
            <FileText size={16} />
          </span>
          <span className="text-v2base font-semibold text-v2ink">Documents</span>
        </div>
        <button type="button" className="text-[12px] font-semibold text-v2brand hover:text-[#1157D6]" onClick={() => navigateV2('/client-v2/documents')}>
          Manage →
        </button>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <div className="text-[22px] font-bold text-v2ink tracking-tight">
          {documents.uploadedCount}
          <span className="text-v2muted text-[13px] font-semibold">/{documents.requiredCount || 0}</span>
        </div>
        <div className="v2-progress flex-1 h-2">
          <div style={{ width: `${documents.requiredCount ? Math.round((documents.uploadedCount / documents.requiredCount) * 100) : 0}%` }} />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {documents.processingCount > 0 && <StatusBadgeV2 tone="brand"> {documents.processingCount} processing</StatusBadgeV2>}
        {missing.length > 0 && <StatusBadgeV2 tone="amber">{missing.length} needed</StatusBadgeV2>}
        {fullyClean && <StatusBadgeV2 tone="emerald">All complete</StatusBadgeV2>}
      </div>

      {missing.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {missing.map((title) => (
            <li key={title} className="flex items-center justify-between gap-2 text-[12.5px]">
              <span className="text-v2ink truncate">{title}</span>
              <button
                type="button"
                onClick={() => navigateV2('/client-v2/documents')}
                className="flex items-center gap-1 text-[11.5px] font-semibold text-v2brand shrink-0"
              >
                <Upload size={12} /> Upload
              </button>
            </li>
          ))}
        </ul>
      )}

      {fullyClean && documents.uploadedCount > 0 && (
        <p className="mt-2 text-[12px] text-v2muted">Your document set is complete. Next review refresh will confirm.</p>
      )}
    </div>
  )
}