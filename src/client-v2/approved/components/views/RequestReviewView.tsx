import React, { useState } from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';

export const RequestReviewView: React.FC = () => {
  const { profile, requestUnderwritingReview, openClydeWithPrompt } = usePortal();
  const [underwriterNotes, setUnderwriterNotes] = useState('');
  const [facilityTarget, setFacilityTarget] = useState('$250,000 Prime Commercial Line of Credit');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError('');
    const ok = await requestUnderwritingReview(underwriterNotes);
    setIsSubmitting(false);
    if (ok) setIsSubmitted(true);
    else setSubmitError('The review request could not be saved. Your live client data was not changed.');
  };

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-teal-50 border border-teal-200 shrink-0 text-teal-600">
            <GiantIcon type="profile" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-teal-700 font-bold">
              <span>GoClear Credit Committee Concierge</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">Direct Underwriter Assignment</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Request Underwriting Review · Formal Credit Committee Audit
            </h1>
          </div>
        </div>

        <button
          onClick={() => openClydeWithPrompt("What happens during an institutional underwriting review?")}
          className="px-3.5 py-1.5 rounded-lg border border-slate-200 bg-white text-teal-800 font-bold text-xs hover:bg-slate-50 transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
        >
          Ask Clyde Audit Process →
        </button>
      </div>

      {isSubmitted ? (
        <div className="flex-1 rounded-xl border border-teal-200 bg-white p-6 text-center shadow-xs flex flex-col items-center justify-center">
          <div className="w-14 h-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600 mb-3">
            <svg className="w-8 h-8 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </div>

          <span className="text-xs font-bold uppercase tracking-wider text-teal-700">
            Dossier Dispatched
          </span>
          <h2 className="mt-1 text-xl font-bold text-slate-900">
            Underwriting Dossier In Active Review
          </h2>
          <p className="mt-1 text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
            Your file for <strong>{profile.companyName}</strong> has been submitted to the GoClear review queue. Review feedback and next steps will appear here when available.
          </p>

          <div className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-teal-50 border border-teal-200 text-teal-900 text-xs font-mono shadow-xs">
            <span>Dossier Reference: #GC-2026-9184-VL</span>
          </div>
        </div>
      ) : (
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5 overflow-hidden">
          {/* Dossier Preview (5 cols - Clean White Surface) */}
          <div className="lg:col-span-5 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
                <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
                  Compiled Dossier
                </span>
                <span className="text-[10px] font-mono text-emerald-700 font-bold">Ready to Dispatch</span>
              </div>

              <div className="mt-2.5 space-y-2 text-xs">
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-500">Borrower / Principal</div>
                  <div className="text-xs font-bold text-slate-900 mt-0.5">{profile.name}</div>
                  <div className="text-teal-700 text-[10px] font-semibold">{profile.role}</div>
                </div>

                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-500">Target Enterprise</div>
                  <div className="text-xs font-bold text-slate-900 mt-0.5">{profile.companyName}</div>
                  <div className="text-slate-600 text-[10px]">Delaware LLC · {profile.ein}</div>
                </div>

                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] text-slate-500">Readiness Score</div>
                    <div className="text-sm font-black text-teal-700 font-mono">
                      {profile.readinessPoints} / 1,000 Pts
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500">Underwriting Grade</div>
                    <div className="text-xs font-bold text-slate-900">Live readiness review</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Clean Light Non-Disclosure Highlight Box */}
            <div className="p-2.5 rounded-lg border border-teal-200/80 bg-teal-50/50 text-[11px] text-slate-700 shadow-xs">
              <span className="text-teal-900 font-bold block">🔒 Institutional Non-Disclosure</span>
              All financial documentation is encrypted under strict banking compliance protocols.
            </div>
          </div>

          {/* Submission Form (7 cols - Clean White Surface) */}
          <div className="lg:col-span-7 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs">
            <form onSubmit={handleSubmit} className="flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
                  <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
                    Application Parameters
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">Direct Committee Review</span>
                </div>

                <div className="mt-3 space-y-2.5">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Target Credit Program:
                    </label>
                    <select
                      value={facilityTarget}
                      onChange={(e) => setFacilityTarget(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 text-xs focus:outline-none focus:border-teal-500 focus:bg-white"
                    >
                      <option>$250,000 Prime Commercial Line of Credit</option>
                      <option>$125,000 Equipment & Fleet Lease Facility</option>
                      <option>$100,000 Revenue-Based Growth Facility</option>
                      <option>Comprehensive Multi-Facility Syndication</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Executive Notes & Capital Use:
                    </label>
                    <textarea
                      rows={3}
                      value={underwriterNotes}
                      onChange={(e) => setUnderwriterNotes(e.target.value)}
                      placeholder="Specify your capital allocation plan (e.g. freight fleet expansion, 90-day working capital reserve)..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 text-xs placeholder:text-slate-400 focus:outline-none focus:border-teal-500 focus:bg-white resize-none"
                    />
                  </div>
                </div>
              </div>

              {submitError && <p className="mt-2 text-xs text-rose-700" role="alert">{submitError}</p>}
              <button
                type="submit"
                disabled={isSubmitting}
                className="mt-3 w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs transition-all shadow-xs active:scale-95 disabled:opacity-50 cursor-pointer text-center"
              >
                {isSubmitting ? 'Transmitting Dossier...' : 'Submit Complete Dossier to Committee →'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
