import React, { useState } from 'react';
import {
  X,
  Printer,
  Copy,
  Check,
  Sparkles,
  ShieldCheck,
  FileText,
  DollarSign,
  AlertTriangle,
  Building2,
  TrendingUp,
  Download,
  Share2,
  ExternalLink
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';

export interface DossierData {
  id: string;
  referenceCode: string;
  title: string;
  department: string;
  preparedBy: string;
  canonicalNotebook: string;
  date: string;
  classification: string;
  status: string;
  executiveSummary: string;
  strategicValue: string;
  marketEvidence: {
    sourcesCount: number;
    questionnaireComplete: boolean;
    citations: string[];
    targetAudience: string;
    verifiedDemand: string;
  };
  financials: {
    entryCost: string;
    capitalRequired: string;
    projectedMonthlyRevenue: string;
    breakEvenTimeline: string;
    maxDrawdownLimit: string;
    projectedROI: string;
  };
  bankabilityScorecard: {
    entityType: string;
    goodStanding: boolean;
    einVerified: boolean;
    dunsNumber: string;
    paydexScore: number;
    recommendedNAICS: string;
    naicsJustification: string;
  };
  risksAndMitigations: Array<{
    risk: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH';
    mitigation: string;
  }>;
  signOff: {
    authority: string;
    status: 'PENDING_RAY' | 'APPROVED_BY_RAY' | 'RE_ANALYSIS_REQUESTED';
    signedAt?: string;
    notes?: string;
  };
}

interface ExecutiveDossierModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: DossierData;
}

export const ExecutiveDossierModal: React.FC<ExecutiveDossierModalProps> = ({
  isOpen,
  onClose,
  data
}) => {
  const { sendMessage } = useNexus();
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'DOCUMENT' | 'MARKDOWN_PREVIEW'>('DOCUMENT');

  if (!isOpen) return null;

  const generateMarkdown = (): string => {
    return `# NEXUS OS EXECUTIVE DOSSIER
**Reference:** ${data.referenceCode}  
**Classification:** ${data.classification}  
**Prepared By:** ${data.preparedBy} (${data.department})  
**Canonical Notebook:** \`${data.canonicalNotebook}\`  
**Date:** ${data.date}  
**Subject:** ${data.title}  

---

## 1. EXECUTIVE SUMMARY & STRATEGIC VALUE
${data.executiveSummary}

**Strategic Alignment:**
${data.strategicValue}

---

## 2. MARKET EVIDENCE & VALIDATION
- **Verified Sources Analyzed:** ${data.marketEvidence.sourcesCount}
- **Target Customer / Audience:** ${data.marketEvidence.targetAudience}
- **Demand Evidence:** ${data.marketEvidence.verifiedDemand}
- **Key Citations:**
${data.marketEvidence.citations.map(c => `  - ${c}`).join('\n')}

---

## 3. FINANCIAL PROJECTIONS & CAPITAL STRUCTURE
| Metric | Specification |
|---|---|
| Entry Cost ($0 Entry Tier) | ${data.financials.entryCost} |
| Required Capital Deployment | ${data.financials.capitalRequired} |
| Projected 30-Day Velocity | ${data.financials.projectedMonthlyRevenue} |
| Target Break-Even Timeline | ${data.financials.breakEvenTimeline} |
| Max Drawdown / Capital at Risk Cap | ${data.financials.maxDrawdownLimit} |
| 12-Month Projected ROI | ${data.financials.projectedROI} |

---

## 4. BANKABILITY & NAICS COMPLIANCE SCORECARD
- **Entity Type:** ${data.bankabilityScorecard.entityType} (Good Standing: ${data.bankabilityScorecard.goodStanding ? 'YES' : 'NO'})
- **EIN / Tax ID:** ${data.bankabilityScorecard.einVerified ? 'Verified' : 'Pending'}
- **D&B D-U-N-S:** ${data.bankabilityScorecard.dunsNumber} (PAYDEX: ${data.bankabilityScorecard.paydexScore})
- **Accurate Primary NAICS:** \`${data.bankabilityScorecard.recommendedNAICS}\`
- **Classification Justification:** ${data.bankabilityScorecard.naicsJustification}

---

## 5. RISK MATRIX & MITIGATION BLUEPRINT
${data.risksAndMitigations.map(r => `### [${r.severity}] ${r.risk}\n**Mitigation:** ${r.mitigation}`).join('\n\n')}

---

## 6. STRATEGIC AUTHORITY SIGN-OFF GATE
- **Final Strategic Authority:** ${data.signOff.authority} (Ray Davis)
- **Gate Status:** ${data.signOff.status}
- **Recorded Timestamp:** ${data.signOff.signedAt || 'Pending Executive Review'}
- **Executive Stipulation:** ${data.signOff.notes || 'Awaiting formal authorization.'}

*Generated deterministically by Nexus OS Executive Console.*
`;
  };

  const handleCopyMarkdown = () => {
    const md = generateMarkdown();
    navigator.clipboard.writeText(md).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
      sendMessage(`Copied Executive Dossier (${data.referenceCode}) to clipboard as Markdown.`);
    });
  };

  const handlePrint = () => {
    window.print();
  };

  const handleSendToNova = () => {
    sendMessage(
      `Nova, give me a concise 30-second executive audio briefing on Dossier ${data.referenceCode}: ${data.title}. Focus on capital requirement (${data.financials.capitalRequired}) and risk mitigations.`
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 print:p-0">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity print:hidden"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div className="relative z-10 w-full max-w-4xl max-h-[92vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden print:max-h-none print:border-none print:shadow-none print:rounded-none">
        {/* Top Control Bar */}
        <div className="p-3 sm:p-4 bg-slate-900 text-white flex items-center justify-between shrink-0 print:hidden">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase tracking-wider text-blue-400">
                  Nexus Executive Dossier
                </span>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  {data.referenceCode}
                </span>
              </div>
              <h2 className="text-xs sm:text-sm font-black text-white truncate max-w-md">
                {data.title}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            <div className="hidden sm:flex items-center bg-slate-800 rounded-lg p-0.5 text-[10px] font-bold">
              <button
                type="button"
                onClick={() => setActiveTab('DOCUMENT')}
                className={`px-2 py-1 rounded cursor-pointer ${
                  activeTab === 'DOCUMENT'
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Executive Layout
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('MARKDOWN_PREVIEW')}
                className={`px-2 py-1 rounded cursor-pointer ${
                  activeTab === 'MARKDOWN_PREVIEW'
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Markdown Spec
              </button>
            </div>

            <button
              type="button"
              onClick={handleSendToNova}
              className="px-2.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[11px] font-bold flex items-center gap-1.5 cursor-pointer shadow-sm"
              title="Request Nova voice briefing on this dossier"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Nova Brief</span>
            </button>

            <button
              type="button"
              onClick={handleCopyMarkdown}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-[11px] font-bold flex items-center gap-1.5 cursor-pointer border border-slate-700"
              title="Copy markdown to clipboard"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy MD'}</span>
            </button>

            <button
              type="button"
              onClick={handlePrint}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-[11px] font-bold flex items-center gap-1.5 cursor-pointer border border-slate-700"
              title="Print or export as PDF"
            >
              <Printer className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Print / PDF</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body / Printable View */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-7 custom-scrollbar print:p-0 bg-white">
          {activeTab === 'MARKDOWN_PREVIEW' ? (
            <div className="space-y-3 font-mono text-xs bg-slate-900 text-slate-100 p-4 rounded-xl overflow-x-auto">
              <pre className="whitespace-pre-wrap">{generateMarkdown()}</pre>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6 text-slate-900 print:text-black">
              {/* Document Header */}
              <div className="border-b-2 border-slate-900 pb-4 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono uppercase tracking-wider text-slate-500">
                  <div className="flex items-center gap-2">
                    <span className="font-black text-slate-900">NEXUS OPERATING SYSTEM</span>
                    <span>·</span>
                    <span>OFFICIAL EXECUTIVE DOSSIER</span>
                  </div>
                  <div className="px-2 py-0.5 bg-rose-100 text-rose-900 font-bold border border-rose-300 rounded">
                    {data.classification}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 pt-1">
                  <div>
                    <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight leading-snug">
                      {data.title}
                    </h1>
                    <p className="text-xs text-slate-600 font-medium pt-0.5">
                      Originating Department: <strong>{data.department}</strong> · Prepared by: <strong>{data.preparedBy}</strong>
                    </p>
                  </div>

                  <div className="text-right text-[11px] text-slate-600 shrink-0 font-medium">
                    <div>Date: <strong>{data.date}</strong></div>
                    <div className="font-mono text-[10px] text-slate-500">Ref: {data.referenceCode}</div>
                  </div>
                </div>

                {/* Notebook reference & Principle badge */}
                <div className="pt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] bg-slate-50 p-2 rounded-lg border border-slate-200">
                  <div className="flex items-center gap-1.5 font-mono text-slate-700">
                    <FileText className="w-3.5 h-3.5 text-blue-600" />
                    <span>Canonical Notebook:</span>
                    <strong className="text-blue-900">{data.canonicalNotebook}</strong>
                  </div>
                  <div className="text-[10px] text-slate-500 font-bold">
                    OPERATING PRINCIPLE: WORKFLOW = AUTHORITY · AI = RECOMMENDER · RAY = DECIDER
                  </div>
                </div>
              </div>

              {/* Section 1: Executive Summary */}
              <div className="space-y-2">
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-blue-600 rounded-full" />
                  1. Executive Summary & Strategic Value
                </h2>
                <div className="p-3.5 bg-blue-50/50 rounded-xl border border-blue-200/80 text-xs sm:text-sm text-slate-800 leading-relaxed font-medium">
                  {data.executiveSummary}
                </div>
                <div className="text-xs text-slate-600 pl-1 font-medium">
                  <strong>Strategic Rationale:</strong> {data.strategicValue}
                </div>
              </div>

              {/* Section 2: Market & Empirical Evidence */}
              <div className="space-y-2">
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-cyan-600 rounded-full" />
                  2. Empirical Evidence & Market Validation
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Verified Sources</span>
                    <span className="text-base font-black text-slate-900">{data.marketEvidence.sourcesCount} Citations</span>
                    <span className="text-[10px] text-emerald-700 font-bold block pt-0.5">Fixed Questionnaire Complete</span>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Target Customer</span>
                    <span className="text-xs font-black text-slate-900 block truncate">{data.marketEvidence.targetAudience}</span>
                    <span className="text-[10px] text-slate-500 block pt-0.5">Validated Commercial Persona</span>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Demand Validation</span>
                    <span className="text-xs font-black text-slate-900 block truncate">{data.marketEvidence.verifiedDemand}</span>
                    <span className="text-[10px] text-blue-700 font-bold block pt-0.5">Empirical Signal</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 bg-white text-xs space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Source Traceability:</span>
                  <ul className="list-disc list-inside text-slate-700 space-y-0.5 text-[11px]">
                    {data.marketEvidence.citations.map((cite, idx) => (
                      <li key={idx} className="font-mono text-slate-600">{cite}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Section 3: Financial Projections */}
              <div className="space-y-2">
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-emerald-600 rounded-full" />
                  3. Financial Architecture & Capital Deployment
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  <div className="p-3 rounded-lg border border-slate-200 bg-emerald-50/40">
                    <span className="text-[10px] font-bold text-emerald-800 uppercase block">Cost-Free Option</span>
                    <span className="text-base font-black text-emerald-900">{data.financials.entryCost}</span>
                    <span className="text-[10px] text-emerald-700 block">Lowest-Cost Entry Tier</span>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-amber-50/40">
                    <span className="text-[10px] font-bold text-amber-800 uppercase block">Capital Required</span>
                    <span className="text-base font-black text-amber-900">{data.financials.capitalRequired}</span>
                    <span className="text-[10px] text-amber-700 block">Upfront Deployment</span>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-blue-50/40">
                    <span className="text-[10px] font-bold text-blue-800 uppercase block">Projected Monthly</span>
                    <span className="text-base font-black text-blue-900">{data.financials.projectedMonthlyRevenue}</span>
                    <span className="text-[10px] text-blue-700 block">Revenue Velocity Target</span>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Break-Even</span>
                    <span className="text-sm font-black text-slate-900">{data.financials.breakEvenTimeline}</span>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Drawdown Limit</span>
                    <span className="text-sm font-black text-rose-700">{data.financials.maxDrawdownLimit}</span>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Projected ROI</span>
                    <span className="text-sm font-black text-emerald-700">{data.financials.projectedROI}</span>
                  </div>
                </div>
              </div>

              {/* Section 4: Bankability & NAICS Scorecard */}
              <div className="space-y-2">
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full" />
                  4. Bankability & NAICS Governance Compliance
                </h2>
                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2.5 text-xs">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                    <div>
                      <span className="text-slate-500 block text-[10px]">Entity Type:</span>
                      <strong className="text-slate-900">{data.bankabilityScorecard.entityType}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Good Standing:</span>
                      <strong className="text-emerald-700">Verified Active</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">DUNS Number:</span>
                      <strong className="font-mono text-slate-900">{data.bankabilityScorecard.dunsNumber}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">PAYDEX Score:</span>
                      <strong className="text-blue-700">{data.bankabilityScorecard.paydexScore} / 100</strong>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-200/80">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-black uppercase text-indigo-900 bg-indigo-100 px-1.5 py-0.5 rounded">
                        Governed NAICS Code: {data.bankabilityScorecard.recommendedNAICS}
                      </span>
                      <span className="text-[10px] text-slate-500 font-bold">
                        Accurate Classification First · Funding Optimization Second
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-700 font-medium pt-1">
                      {data.bankabilityScorecard.naicsJustification}
                    </p>
                  </div>
                </div>
              </div>

              {/* Section 5: Risk Matrix */}
              <div className="space-y-2">
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-rose-600 rounded-full" />
                  5. Risk Matrix & Mitigation Blueprint
                </h2>
                <div className="space-y-1.5">
                  {data.risksAndMitigations.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg border border-slate-200 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                    >
                      <div className="flex items-start gap-2">
                        <span
                          className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded shrink-0 ${
                            item.severity === 'HIGH'
                              ? 'bg-rose-100 text-rose-800 border border-rose-300'
                              : item.severity === 'MEDIUM'
                              ? 'bg-amber-100 text-amber-800 border border-amber-300'
                              : 'bg-slate-100 text-slate-800 border border-slate-300'
                          }`}
                        >
                          {item.severity}
                        </span>
                        <div>
                          <strong className="text-slate-900 text-[11px] block">{item.risk}</strong>
                          <span className="text-[11px] text-slate-600 font-medium">{item.mitigation}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Section 6: Strategic Authority Sign-Off Block */}
              <div className="pt-3 border-t-2 border-slate-900">
                <div className="p-4 rounded-xl bg-slate-900 text-white space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="text-[9px] font-black uppercase tracking-wider text-amber-400 block">
                        Gate 6: Strategic Authority Sign-Off
                      </span>
                      <h3 className="text-sm font-black text-white">
                        Executive Decision by Ray Davis
                      </h3>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">
                        STATUS: {data.signOff.status}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-2 border-t border-slate-800">
                    <div>
                      <span className="text-[10px] text-slate-400 block">Stipulated Execution Conditions:</span>
                      <p className="text-slate-200 text-[11px] pt-0.5 font-medium">
                        {data.signOff.notes || 'Autonomous pipeline will strictly execute downstream actions only upon signed Ray Davis directive.'}
                      </p>
                    </div>
                    <div className="sm:text-right">
                      <span className="text-[10px] text-slate-400 block">Official Signature Stamp:</span>
                      <div className="font-mono text-xs font-bold text-amber-400 pt-0.5">
                        RAY DAVIS · CHIEF STRATEGIC OFFICER
                      </div>
                      <span className="text-[10px] text-slate-500 block font-mono">
                        {data.signOff.signedAt || 'PENDING HUMAN AUTHORIZATION'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 shrink-0 print:hidden text-xs">
          <div className="text-[11px] text-slate-500">
            Nexus OS Executive Dossier Engine · Connected to Durable Supabase Knowledge Packages
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopyMarkdown}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-bold cursor-pointer"
            >
              {copied ? 'Copied to Clipboard!' : 'Copy Markdown'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-bold hover:bg-slate-800 cursor-pointer"
            >
              Close Dossier
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
