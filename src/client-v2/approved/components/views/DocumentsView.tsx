import React, { useRef, useState } from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';
import { StatusBadge } from '../common/StatusBadge';
import vaultEmptyStateImg from '../../assets/images/vault_empty_state_1790436741637.jpg';
import { getNexusClientPortalBridge } from '../../integration/nexusClientPortalBridge';

export const DocumentsView: React.FC = () => {
  const { documents, uploadDocument, setActiveTab, openClydeWithPrompt, profile } = usePortal();
  const [isSimulatingUpload, setIsSimulatingUpload] = useState(false);
  const [docFilter, setDocFilter] = useState<'ALL' | 'REQUIRED' | 'VERIFIED' | 'ARCHIVED'>('ALL');
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const completedDocsCount = documents.filter((d) => d.status === 'verified').length;
  const totalDocsCount = documents.length;
  const progressPercent = Math.round((completedDocsCount / totalDocsCount) * 100);

  const filteredDocs = documents.filter((doc) => {
    if (docFilter === 'REQUIRED') return doc.status === 'required';
    if (docFilter === 'VERIFIED') return doc.status === 'verified';
    if (docFilter === 'ARCHIVED') return false; // currently 0 archived, triggers empty state
    return true;
  });

  const handleSimulatedUpload = (docId: string = 'doc-4') => {
    setIsSimulatingUpload(true);
    setTimeout(() => {
      uploadDocument(docId, 'Chase_Commercial_90Day_Statements_VanceLogistics.pdf');
      setIsSimulatingUpload(false);
    }, 900);
  };

  const handleLiveUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    uploadDocument('doc-4', file.name, file);
    event.target.value = '';
  };

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-50 border border-cyan-200 shrink-0 text-cyan-600">
            <GiantIcon type="vault" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-cyan-700 font-bold">
              <span>Secure Underwriting Vault</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">256-Bit Encrypted Repository</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Institutional Document Vault · {completedDocsCount} of {totalDocsCount} Cleared ({progressPercent}%)
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 w-36">
            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-teal-500 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="text-xs font-mono font-bold text-teal-700">{progressPercent}%</span>
          </div>
          <button
            onClick={() => setActiveTab('request-review')}
            className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
          >
            Submit to Underwriter →
          </button>
        </div>
      </div>

      {/* 2-Column Consolidated Workspace (Fits on screen without scrolling) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5 overflow-hidden">
        {/* Left: Upload Zone & HOLD Resolution (5 cols) */}
        <div className="lg:col-span-5 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span className="text-[10px] font-bold text-cyan-700 uppercase tracking-wider">
                Upload Repository
              </span>
              <span className="text-[10px] text-slate-400 font-mono">PDF, PNG, TIFF up to 50MB</span>
            </div>

            {/* Drag & Drop Surface */}
            <div className="mt-3 border-2 border-dashed border-cyan-200 hover:border-cyan-400 rounded-xl p-4 text-center bg-slate-50/70 hover:bg-white transition-all cursor-pointer">
              <div className="w-10 h-10 mx-auto rounded-lg bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600">
                <GiantIcon type="vault" size="sm" glow={false} />
              </div>
              <h4 className="text-xs font-bold text-slate-900 mt-2">
                Drag and drop underwriting files here
              </h4>
              <p className="text-[10px] text-slate-500 mt-0.5">
                Automated document extraction & OCR verification
              </p>
            </div>

            {/* HOLD Document Action Button */}
            <div className="mt-3 p-3 rounded-lg border border-rose-200 bg-rose-50/80">
              <div className="flex items-center justify-between">
                <StatusBadge status="Blocked" label="Blocked · Action Required" size="sm" />
                <span className="text-[10px] text-amber-700 font-mono font-bold">+8 Points</span>
              </div>
              <h4 className="text-xs font-bold text-slate-900 mt-1">
                90-Day Commercial Bank Statements
              </h4>
              <p className="text-[11px] text-slate-600 mt-0.5 leading-snug">
                Resolving this document addresses the primary readiness hold for {profile.companyName}.
              </p>
              <button
                disabled={isSimulatingUpload}
                onClick={() => getNexusClientPortalBridge()?.mode === 'live' ? uploadInputRef.current?.click() : handleSimulatedUpload('doc-4')}
                className="mt-2.5 w-full py-2 bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 text-white font-bold text-xs rounded-lg transition-all shadow-xs active:scale-95 cursor-pointer disabled:opacity-50 text-center"
              >
                {isSimulatingUpload ? 'Verifying OCR Cash Flow...' : 'Upload 90-Day Statements (Simulate Resolution)'}
              </button>
              <input ref={uploadInputRef} type="file" accept="application/pdf,image/jpeg,image/png,image/heic,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={handleLiveUpload} className="hidden" aria-label="Upload 90-day bank statements" />
            </div>
          </div>

          {/* Clyde Vault Tip (Clean Light Highlight) */}
          <div className="mt-2 p-2 rounded-lg border border-teal-200/80 bg-teal-50/50 text-slate-800 shadow-xs flex items-center justify-between text-xs">
            <div className="text-[11px] text-slate-600 leading-tight">
              <span className="text-teal-800 font-bold block">⚡ Clyde Vault Advisor</span>
              Underwriters look for average daily ledger balance &gt; $10k.
            </div>
            <button
              onClick={() => openClydeWithPrompt("What exact figures do underwriters look for on business bank statements?")}
              className="text-[10px] text-teal-700 font-bold hover:underline shrink-0 ml-2 cursor-pointer"
            >
              Ask Clyde →
            </button>
          </div>
        </div>

        {/* Right: Document Checklist & Status (7 cols) */}
        <div className="lg:col-span-7 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-slate-100 shrink-0 gap-2">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
                Institutional Document Checklist
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                ({completedDocsCount}/{totalDocsCount} Complete)
              </span>
            </div>

            {/* Filter pills */}
            <div className="flex items-center gap-1 p-0.5 bg-slate-100 border border-slate-200/80 rounded-lg text-[10px]">
              {(['ALL', 'REQUIRED', 'VERIFIED', 'ARCHIVED'] as const).map((filter) => {
                const count = filter === 'ALL'
                  ? totalDocsCount
                  : filter === 'REQUIRED'
                  ? documents.filter((d) => d.status === 'required').length
                  : filter === 'VERIFIED'
                  ? completedDocsCount
                  : 0;

                return (
                  <button
                    key={filter}
                    onClick={() => setDocFilter(filter)}
                    className={`px-2 py-0.5 rounded font-semibold transition-all cursor-pointer whitespace-nowrap ${
                      docFilter === filter
                        ? 'bg-white text-slate-900 font-bold shadow-xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    {filter === 'ALL' ? 'All' : filter === 'REQUIRED' ? 'Action Required' : filter === 'VERIFIED' ? 'Verified' : 'Archived'} ({count})
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pt-2 pr-1 scrollbar-thin">
            {filteredDocs.length === 0 ? (
              /* Professional Branded Empty-State Illustration & Guidance */
              <div className="h-full flex flex-col items-center justify-center p-4 text-center animate-fade-in bg-slate-50/60 rounded-xl border border-slate-200/80">
                <div className="relative w-36 h-28 sm:w-44 sm:h-32 rounded-xl overflow-hidden shadow-xs border border-slate-200 bg-white shrink-0 group">
                  <img
                    src={vaultEmptyStateImg}
                    alt="Empty Document Vault"
                    referrerPolicy="no-referrer"
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950/40 via-transparent to-transparent" />
                  <span className="absolute bottom-1.5 left-2 px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-white/95 text-teal-800 border border-teal-300 shadow-xs">
                    VAULT SECURE
                  </span>
                </div>

                <div className="max-w-md mt-3">
                  <h3 className="text-sm font-bold text-slate-900">
                    {docFilter === 'ARCHIVED'
                      ? 'No Archived Underwriting Records'
                      : 'No Documents Match this Filter'}
                  </h3>
                  <p className="mt-1 text-[11px] text-slate-600 leading-snug">
                    {docFilter === 'ARCHIVED'
                      ? `All historical files for ${profile.companyName} are currently in the live client-scoped vault. No archived or legacy files were returned.`
                      : 'There are currently no document files matching the selected criteria in this vault queue.'}
                  </p>

                  {/* Step-by-Step Guidance Box */}
                  <div className="mt-3 p-2.5 rounded-lg bg-white border border-slate-200 text-left text-[11px] space-y-1.5 shadow-xs">
                    <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider block">
                      Recommended Next Actions:
                    </span>
                    <div className="flex items-start gap-2 text-slate-700">
                      <span className="w-4 h-4 rounded-full bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">1</span>
                      <span>Upload your 90-day bank statements to resolve the primary cash flow hold.</span>
                    </div>
                    <div className="flex items-start gap-2 text-slate-700">
                      <span className="w-4 h-4 rounded-full bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">2</span>
                      <span>Ask Clyde Copilot to audit OCR data before institutional underwriters review.</span>
                    </div>
                    <div className="flex items-start gap-2 text-slate-700">
                      <span className="w-4 h-4 rounded-full bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">3</span>
                      <span>Switch filter back to view all active document verification tasks.</span>
                    </div>
                  </div>

                  {/* Direct Action Buttons */}
                  <div className="mt-3 flex items-center justify-center gap-2">
                    <button
                      onClick={() => setDocFilter('ALL')}
                      className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-slate-300 text-slate-700 text-xs font-semibold shadow-xs cursor-pointer active:scale-95 transition-all"
                    >
                      View All Documents
                    </button>
                    <button
                      onClick={() => handleSimulatedUpload('doc-4')}
                      className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold shadow-xs cursor-pointer active:scale-95 transition-all"
                    >
                      Upload Statements (+8 Pts) →
                    </button>
                    <button
                      onClick={() => openClydeWithPrompt("What documents do institutional commercial lenders require?")}
                      className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-teal-800 text-xs font-semibold shadow-xs cursor-pointer transition-colors"
                      title="Ask Clyde Document Guidelines"
                    >
                      Ask Clyde →
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              filteredDocs.map((doc) => {
                const isVerified = doc.status === 'verified';
                const isRequired = doc.status === 'required';
                const isReviewing = doc.status === 'reviewing';

                const badgeStatus = isVerified
                  ? 'Completed'
                  : isRequired
                  ? 'Blocked'
                  : isReviewing
                  ? 'In Progress'
                  : 'Pending';

                return (
                  <div
                    key={doc.id}
                    className={`p-2.5 rounded-lg border transition-all ${
                      isVerified
                        ? 'border-emerald-200 bg-emerald-50/70 hover:border-emerald-300'
                        : isRequired
                        ? 'border-rose-200 bg-rose-50/70 hover:border-rose-300'
                        : 'border-sky-200 bg-sky-50/70 hover:border-sky-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 text-[10px]">
                          <StatusBadge status={badgeStatus} size="sm" />
                          <span className="text-slate-300">·</span>
                          <span className="text-slate-600 font-semibold">{doc.category}</span>
                          <span className="text-slate-300">·</span>
                          <span className="text-amber-800 font-mono text-[9px] font-semibold">{doc.requiredFor}</span>
                        </div>

                        <h4 className="text-xs font-bold text-slate-900 mt-1 truncate">
                          {doc.title}
                        </h4>
                        <p className="text-[11px] text-slate-600 mt-0.5 line-clamp-1">
                          {doc.notes || doc.requiredFor}
                        </p>
                      </div>

                      <div className="shrink-0 flex items-center gap-2">
                        {isVerified ? (
                          <span className="text-xs font-mono font-bold text-emerald-700 flex items-center gap-1 bg-emerald-100/70 px-2 py-0.5 rounded border border-emerald-200">
                            ✓ Verified
                          </span>
                        ) : isReviewing ? (
                          <span className="text-xs font-mono font-bold text-sky-700 flex items-center gap-1 bg-sky-100/70 px-2 py-0.5 rounded border border-sky-200">
                            ⏳ In Review
                          </span>
                        ) : (
                          <button
                            onClick={() => handleSimulatedUpload(doc.id)}
                            className="px-2.5 py-1 rounded bg-teal-600 hover:bg-teal-700 text-white font-bold text-[10px] transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
                          >
                            Upload Statements
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
