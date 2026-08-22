import { FileCheck2, FileClock, FileX2, Info } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, SectionHeaderV2, StatusBadgeV2 } from '../components/primitives'
import InlineDocumentUpload from '../../components/client/InlineDocumentUpload'

export function DocumentsV2({ data }: { data: V2ViewData }) {
  const { documents } = data
  const pct = documents.requiredCount ? Math.round((documents.uploadedCount / documents.requiredCount) * 100) : 0

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2
        eyebrow="Workspace"
        title="Documents"
        subtitle="Every requirement Nexus uses to confirm funding readiness. Status reflects what GoClear review has verified — not just what was uploaded."
      />

      <div className="v2-card p-4">
        <div className="flex flex-wrap items-center gap-5">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-v2brand-tint text-v2brand flex items-center justify-center">
              <FileCheck2 size={28} />
            </div>
            <div>
              <div className="text-v2xl font-bold text-v2ink tracking-tight">
                {documents.uploadedCount}
                <span className="text-v2muted text-v2base font-semibold"> / {documents.requiredCount || 0} required</span>
              </div>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {documents.uploadedCount > 0 && <StatusBadgeV2 tone="emerald" dot>{documents.uploadedCount} uploaded</StatusBadgeV2>}
                {documents.missing.length > 0 && <StatusBadgeV2 tone="amber" dot>{documents.missing.length} needed</StatusBadgeV2>}
                {documents.processingCount > 0 && <StatusBadgeV2 tone="brand" dot>{documents.processingCount} processing</StatusBadgeV2>}
              </div>
            </div>
          </div>
          <div className="flex-1 min-w-[140px]">
            <div className="v2-progress h-2.5 w-full mt-2">
              <div style={{ width: `${pct}%` }} />
            </div>
            <div className="flex justify-between mt-1.5 text-[11px] font-medium text-v2muted">
              <span>{pct}% complete</span>
            </div>
          </div>
        </div>
        <div className="mt-4 rounded-xl bg-v2amber-tint border border-amber-100 px-3.5 py-3 flex items-start gap-2">
          <span className="w-5 h-5 rounded-full bg-white flex items-center justify-center mt-px">
            <Info size={12} className="text-v2amber-deep" />
          </span>
          <p className="text-[12.5px] leading-relaxed text-[#8A6420]">
            Storage-backed upload lands in the next checkpoint. Your full required document set is already reflected live here.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <CardV2>
            <SectionHeaderV2 eyebrow="Requirements" title="Document checklist" right={<span className="text-[11.5px] text-v2muted">{documents.requiredCount} items</span>} />
            <ul className="mt-3 divide-y divide-[#EEF2F9]">
              {documents.requirements.map((req) => (
                <li key={req.label} className="py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-[13px] font-semibold text-v2ink">{req.label}</div>
                      {req.whyItMatters && <div className="mt-0.5 text-[12px] leading-relaxed text-v2muted">{req.whyItMatters}</div>}
                    </div>
                    <StatusBadgeV2 tone={req.status === 'complete' ? 'emerald' : req.status === 'processing' ? 'brand' : req.status === 'attention' ? 'red' : 'amber'} dot>
                      {req.status === 'complete' ? 'Complete' : req.status === 'processing' ? 'Processing' : req.status === 'attention' ? 'Attention' : 'Needed'}
                    </StatusBadgeV2>
                  </div>
                </li>
              ))}
              {documents.requirements.length === 0 && <li className="py-4 text-[12.5px] text-v2muted">No document requirements yet.</li>}
            </ul>
          </CardV2>
        </div>

        <aside className="space-y-4">
          <CardV2>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-8 h-8 rounded-lg bg-v2emerald-tint text-[#0E8A65] flex items-center justify-center">
                <FileCheck2 size={16} />
              </span>
              <span className="text-v2base font-semibold text-v2ink">Verified</span>
            </div>
            <DocumentList items={documents.uploaded.slice(0, 5)} empty="No verified documents yet." dot="v2-dot--emerald" />
          </CardV2>
          <CardV2>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-8 h-8 rounded-lg bg-v2brand-tint text-v2brand flex items-center justify-center">
                <FileClock size={16} />
              </span>
              <span className="text-v2base font-semibold text-v2ink">Processing</span>
            </div>
            <DocumentList items={documents.underReview.slice(0, 5)} empty="Nothing processing right now." dot="v2-dot--amber" />
          </CardV2>
          <CardV2>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-8 h-8 rounded-lg bg-v2amber-tint text-v2amber-deep flex items-center justify-center">
                <FileX2 size={16} />
              </span>
              <span className="text-v2base font-semibold text-v2ink">Needed</span>
            </div>
            <DocumentList items={documents.missing.slice(0, 5)} empty="Nothing missing — great work." dot="v2-dot--red" />
          </CardV2>
          <InlineDocumentUpload compact label="Upload document" pageContext="client_v2_documents" track="documents" />
        </aside>
      </div>
    </div>
  )
}

function DocumentList({ items, empty, dot }: { items: string[]; empty: string; dot: string }) {
  if (items.length === 0) return <p className="text-[12.5px] text-v2muted">{empty}</p>
  return (
    <ul className="space-y-1.5">
      {items.map((title) => (
        <li key={title} className="flex items-center gap-2 text-[12.5px] font-medium text-v2ink">
          <span className={`v2-dot ${dot}`} />
          <span className="truncate">{title}</span>
        </li>
      ))}
    </ul>
  )
}
