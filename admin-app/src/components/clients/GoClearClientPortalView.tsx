import React, { useState } from 'react';
import {
  ShieldCheck,
  Building2,
  CheckCircle2,
  Clock,
  ArrowRight,
  Upload,
  Download,
  FileText,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  Sparkles,
  PhoneCall,
  Lock,
  EyeOff,
  UserCheck
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';
import { ClientItem } from '../../types';

interface GoClearClientPortalViewProps {
  client: ClientItem;
  onExitPreview: () => void;
}

export const GoClearClientPortalView: React.FC<GoClearClientPortalViewProps> = ({
  client,
  onExitPreview
}) => {
  const { sendMessage } = useNexus();
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([
    'Articles of Organization',
    'IRS EIN Confirmation Letter'
  ]);
  const [isUploading, setIsUploading] = useState(false);

  const roadmapSteps = [
    {
      step: '01',
      title: 'Corporate Foundation & Entity Verification',
      status: 'COMPLETED',
      detail: 'State certificate in good standing, commercial address, registered agent active.'
    },
    {
      step: '02',
      title: 'Commercial Tradelines & Credit File Building',
      status: 'IN_PROGRESS',
      progress: 75,
      detail: '3 of 4 Tier-1 vendor tradelines reporting to Experian Business & Dun & Bradstreet.'
    },
    {
      step: '03',
      title: 'Tier-1 Vendor Credit Facilities',
      status: 'NEXT_GATE',
      detail: 'Opening $15,000 - $35,000 revolving lines with Uline, Grainger, and Quill.'
    },
    {
      step: '04',
      title: 'Institutional Non-Dilutive Growth Capital',
      status: 'SCHEDULED',
      detail: 'SBA 7(a) Express / State innovation voucher submission upon Phase 2 completion.'
    }
  ];

  const fundingMatches = [
    {
      id: 'match-1',
      productName: 'Tier-1 Commercial Vendor Revolver',
      institution: 'GoClear Preferred Vendor Network',
      potentialAmount: '$35,000',
      fitStatus: 'CURRENT MATCH',
      fitColor: 'text-emerald-700 bg-emerald-50 border-emerald-200',
      requirementsMet: 'Entity > 6 mos, EIN verified, Good Standing',
      nextAction: 'Confirm primary ordering point of contact'
    },
    {
      id: 'match-2',
      productName: 'Regional Commercial Equipment Facility',
      institution: 'Apex Regional Capital Bank',
      potentialAmount: '$75,000',
      fitStatus: 'NEAR MATCH',
      fitColor: 'text-blue-700 bg-blue-50 border-blue-200',
      requirementsMet: 'Clean corporate file, no tax liens',
      nextAction: 'Upload past 3 months business bank statements'
    },
    {
      id: 'match-3',
      productName: 'SBA Community Advantage Growth Line',
      institution: 'Federal SSBCI Partner Lender',
      potentialAmount: '$150,000',
      fitStatus: 'PATH TO ELIGIBILITY',
      fitColor: 'text-amber-800 bg-amber-50 border-amber-200',
      requirementsMet: 'NAICS 541512 eligible; entity active',
      nextAction: 'Complete 90-day deposit continuity milestone'
    }
  ];

  const handleSimulateUpload = (docName: string) => {
    setIsUploading(true);
    setTimeout(() => {
      setUploadedDocs(prev => [...prev, docName]);
      setIsUploading(false);
      sendMessage(`Client document uploaded: "${docName}" for ${client.name}. Notification sent to GoClear onboarding team.`);
    }, 1000);
  };

  const handleDownloadReport = () => {
    sendMessage(`Generated and downloaded GoClear Capital Readiness Summary for ${client.name}.`);
  };

  return (
    <div className="w-full space-y-4 pb-8">
      {/* Simulation Watermark Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-950 to-slate-900 text-white rounded-xl p-3 sm:p-4 flex flex-wrap items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-500/20 border border-blue-400/40 flex items-center justify-center">
            <EyeOff className="w-4 h-4 text-blue-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-black uppercase tracking-wider text-blue-400">
                GoClear Client View Simulation
              </span>
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                PROTECTED VIEW
              </span>
            </div>
            <p className="text-xs text-slate-300 font-medium">
              Internal underwriting profit margins, confidential handoff gates, and raw algorithmic scores are strictly hidden from this preview.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onExitPreview}
          className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-bold transition-all cursor-pointer border border-white/20 flex items-center gap-1.5"
        >
          <span>Exit Client Preview</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Client Header / Brand Stage */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center shadow-lg shadow-blue-500/10 font-black text-xl">
            {client.company.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
                {client.company}
              </h1>
              <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">
                Client Portal Active
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium pt-0.5">
              Capital Readiness &amp; Funding Facility Dashboard · Managed via GoClear Advisory
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleDownloadReport}
            className="px-3 py-2 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-bold flex items-center gap-1.5 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Readiness Report</span>
          </button>
          <button
            type="button"
            onClick={() => sendMessage(`Client clicked "Contact GoClear Advisor" regarding ${client.name}.`)}
            className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-black flex items-center gap-1.5 shadow-sm cursor-pointer"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>Contact Advisor</span>
          </button>
        </div>
      </div>

      {/* Bankability Health Scorecard Quad */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-1">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Corporate Entity</span>
          <div className="flex items-center gap-1.5 text-slate-900 font-black text-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Good Standing</span>
          </div>
          <span className="text-[10px] text-slate-500 font-medium block">State records verified active</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-1">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Dun &amp; Bradstreet</span>
          <div className="flex items-center gap-1.5 text-slate-900 font-black text-sm">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span>PAYDEX Score: 80</span>
          </div>
          <span className="text-[10px] text-emerald-600 font-bold block">Prime Commercial Grade</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-1">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Commercial Banking</span>
          <div className="flex items-center gap-1.5 text-slate-900 font-black text-sm">
            <Building2 className="w-4 h-4 text-indigo-600" />
            <span>6+ Months History</span>
          </div>
          <span className="text-[10px] text-slate-500 font-medium block">Positive deposit continuity</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-1">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Funding Eligibility</span>
          <div className="flex items-center gap-1.5 text-slate-900 font-black text-sm">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>3 Active Matches</span>
          </div>
          <span className="text-[10px] text-slate-500 font-medium block">Up to $260,000 potential</span>
        </div>
      </div>

      {/* Main Two-Column Client Stage */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* LEFT COLUMN: Roadmap & Curated Opportunities (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Funding Roadmap */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                Your GoClear Capital Roadmap
              </h2>
              <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                Phase 2 of 4 Active
              </span>
            </div>

            <div className="space-y-3">
              {roadmapSteps.map((step, idx) => (
                <div
                  key={step.step}
                  className={`p-3 rounded-xl border text-xs transition-all ${
                    step.status === 'COMPLETED'
                      ? 'bg-slate-50 border-slate-200 text-slate-600'
                      : step.status === 'IN_PROGRESS'
                      ? 'bg-blue-50/60 border-blue-200 shadow-2xs text-slate-900'
                      : 'bg-white border-slate-100 text-slate-400'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                        {step.step}
                      </span>
                      <strong className="text-xs font-extrabold">{step.title}</strong>
                    </div>
                    {step.status === 'COMPLETED' && (
                      <span className="text-[10px] font-black text-emerald-600 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Complete
                      </span>
                    )}
                    {step.status === 'IN_PROGRESS' && (
                      <span className="text-[10px] font-black text-blue-700 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        In Progress
                      </span>
                    )}
                    {step.status === 'NEXT_GATE' && (
                      <span className="text-[10px] font-bold text-slate-400">Next Step</span>
                    )}
                    {step.status === 'SCHEDULED' && (
                      <span className="text-[10px] font-bold text-slate-400">Scheduled</span>
                    )}
                  </div>
                  <p className="text-[11px] pt-1 pl-7 text-slate-600 font-medium">
                    {step.detail}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Curated Matches */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div>
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                  Pre-Screened Funding Matches
                </h2>
                <span className="text-[10px] text-slate-500 font-medium">
                  Verified against your corporate credit file and bankability profile
                </span>
              </div>
            </div>

            <div className="space-y-3">
              {fundingMatches.map(match => (
                <div
                  key={match.id}
                  className="p-3.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white transition-all space-y-2 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="text-[10px] text-slate-400 font-bold uppercase block">{match.institution}</span>
                      <strong className="text-sm font-black text-slate-900 block">{match.productName}</strong>
                    </div>
                    <div className="text-right">
                      <span className="text-base font-black text-slate-900 font-mono block">{match.potentialAmount}</span>
                      <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded border ${match.fitColor}`}>
                        {match.fitStatus}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[11px]">
                    <div className="text-slate-600 font-medium">
                      <strong>Requirements Met:</strong> {match.requirementsMet}
                    </div>
                    <div className="text-blue-700 font-bold flex items-center gap-1">
                      <span>Next: {match.nextAction}</span>
                      <ArrowRight className="w-3 h-3" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Document Verification & Secure Uploads (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                Document Verification Center
              </h2>
              <span className="text-[10px] font-bold text-slate-400">
                {uploadedDocs.length} of 4 Ready
              </span>
            </div>

            <div className="space-y-2 text-xs">
              {[
                { name: 'Articles of Organization', required: true },
                { name: 'IRS EIN Confirmation Letter', required: true },
                { name: 'Last 3 Months Business Bank Statements', required: true },
                { name: 'Commercial Lease / Address Proof', required: false }
              ].map(doc => {
                const isUploaded = uploadedDocs.includes(doc.name);
                return (
                  <div
                    key={doc.name}
                    className="p-3 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between gap-2"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className={`w-4 h-4 ${isUploaded ? 'text-emerald-600' : 'text-slate-400'}`} />
                      <div>
                        <strong className="text-slate-900 text-xs block">{doc.name}</strong>
                        <span className="text-[10px] text-slate-400 font-medium">
                          {doc.required ? 'Required for underwriting' : 'Optional supplementary'}
                        </span>
                      </div>
                    </div>

                    {isUploaded ? (
                      <span className="text-[10px] font-black text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        Verified
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleSimulateUpload(doc.name)}
                        disabled={isUploading}
                        className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-bold flex items-center gap-1 cursor-pointer"
                      >
                        <Upload className="w-3 h-3" />
                        <span>Upload</span>
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 text-xs space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-slate-800">
                <Lock className="w-3.5 h-3.5 text-blue-600" />
                <span>Bank-Grade Encryption</span>
              </div>
              <p className="text-[10px] text-slate-500 font-medium">
                All uploaded documents are stored in secure AES-256 encrypted vaults and transmitted solely to authorized underwriting partners.
              </p>
            </div>
          </div>

          {/* Dedicated Advisor Contact Card */}
          <div className="bg-gradient-to-br from-slate-900 to-blue-950 text-white rounded-xl p-4 sm:p-5 shadow-sm space-y-3">
            <span className="text-[10px] font-black uppercase tracking-wider text-blue-400 block">
              Dedicated Advisory Support
            </span>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center font-black text-white text-sm">
                GO
              </div>
              <div>
                <h3 className="text-xs font-black text-white">GoClear Capital Advisory Desk</h3>
                <span className="text-[10px] text-slate-300 font-medium">
                  Assigned Underwriting Specialist
                </span>
              </div>
            </div>

            <p className="text-[11px] text-slate-300 font-medium leading-relaxed">
              Have questions about your tier-1 tradelines or bankability score? Our team reviews requirements daily to expedite your loan approvals.
            </p>

            <button
              type="button"
              onClick={() => sendMessage(`Schedule consultation requested for ${client.name}.`)}
              className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs text-center cursor-pointer transition-colors"
            >
              Request 15-Minute Strategy Review
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
