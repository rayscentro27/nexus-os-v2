import React, { useState } from 'react';
import {
  FileText,
  Search,
  CheckCircle2,
  Download,
  ChevronRight,
  ShieldCheck,
  FolderKanban
} from 'lucide-react';
import { StatusBadge } from '../components/common/StatusBadge';
import { TruthBadge } from '../components/common/TruthBadge';
import { DOCUMENTS_DATA } from '../data/mockData';
import { useNexus } from '../context/NexusContext';
import { DocumentItem, TruthClass } from '../types';

interface EnrichedDocument extends DocumentItem {
  projectId?: string;
  projectName?: string;
  truthClass: TruthClass;
  scopeSummary: string;
}

const NEXUS_DOCUMENTS: EnrichedDocument[] = [
  {
    id: 'doc-holiday-spec',
    name: 'Printify_6afa4814536c7c3c520f7865_Mug_Unit_Cost_Spec.json',
    size: '48 KB',
    client: 'Holiday Commerce Pilot',
    category: 'Financial',
    status: 'Verified',
    uploadedDate: 'Today · 08:10 AM',
    reviewer: { name: 'Commerce Agent', avatar: 'CM' },
    format: 'pdf',
    projectId: 'proj_98ef515bccee4b58',
    projectName: 'The 6:12 AM Quiet Ritual',
    truthClass: 'VERIFIED',
    scopeSummary:
      'Verified Printify product 6afa4814536c7c3c520f7865 (Variant 104692: 15oz white glossy ceramic mug). Base cost $6.13, first-item US shipping $7.09, additional shipping $2.99. Staged retail $24.00 (PROPOSED).',
  },
  {
    id: 'doc-holiday-stage-a',
    name: 'StageA_Holiday_Mug_H1_Distribution_Brief.docx',
    size: '215 KB',
    client: 'Holiday Commerce Pilot',
    category: 'Marketing',
    status: 'Needs Review',
    uploadedDate: 'Today · 12m ago',
    reviewer: { name: 'Ray Davis', avatar: 'RD' },
    format: 'docx',
    projectId: 'proj_98ef515bccee4b58',
    projectName: 'The 6:12 AM Quiet Ritual',
    truthClass: 'PROPOSED',
    scopeSummary:
      'Stage A interest-capture publication packet for Holiday Mug H1. Includes UTM waitlist URLs and copy hooks; live checkout remains BLOCKED pending Stripe test credential.',
  },
  {
    id: 'doc-trading-r1',
    name: 'Trading_R1_Wick_Sequence_Breakout_v1_Manifest.pdf',
    size: '412 KB',
    client: 'Trading R1 Core',
    category: 'Research',
    status: 'Verified',
    uploadedDate: 'Today · 07:00 AM',
    reviewer: { name: 'Risk Guardrail', avatar: 'RG' },
    format: 'pdf',
    projectId: 'proj_trading_r1_wick',
    projectName: 'Trading R1 Core · Wick Sequence Breakout v1',
    truthClass: 'PAPER',
    scopeSummary:
      'Certification manifest locking EUR_USD H1 strategy execution strictly to OANDA Practice paper mode with 0.75% max risk per trade and continuous receipt parity.',
  },
  ...DOCUMENTS_DATA.map(d => ({
    ...d,
    projectId: d.client.toLowerCase().includes('goclear') ? 'proj_goclear_pilot' : undefined,
    projectName: d.client.toLowerCase().includes('goclear')
      ? 'GoClear Institutional Clearing Pilot'
      : undefined,
    truthClass: 'DEMO' as TruthClass,
    scopeSummary:
      'Sample governance agreement template staged for sandbox validation and legal workflow verification.',
  })),
];

export const DocumentsPage: React.FC = () => {
  const { sendMessage, navigateToObject, setIsNovaDrawerOpen } = useNexus();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedDocId, setSelectedDocId] = useState<string>(NEXUS_DOCUMENTS[0].id);

  const filteredDocs = NEXUS_DOCUMENTS.filter(doc => {
    const matchesSearch =
      doc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.client.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (doc.projectName || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCat = selectedCategory === 'All' || doc.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  const activeDoc =
    filteredDocs.find(d => d.id === selectedDocId) || filteredDocs[0] || NEXUS_DOCUMENTS[0];

  const verifiedCount = NEXUS_DOCUMENTS.filter(d => d.status === 'Verified').length;
  const needsSignatureOrReview = NEXUS_DOCUMENTS.filter(
    d => d.status === 'Needs Signature' || d.status === 'Needs Review'
  ).length;

  return (
    <div className="space-y-4 pb-10">
      {/* Header with accurate counts (no fabricated 247 / 84 counts) */}
      <div className="bg-white rounded-xl p-4 border border-slate-200/80 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
              Documents &amp; Operational Artifacts
            </h1>
            <TruthBadge truth="VERIFIED" label="Indexed Manifest" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Project specs, Printify cost verification proofs, campaign briefs, and sample governance templates.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-slate-500">Indexed Artifacts: </span>
            <strong className="text-slate-900">{NEXUS_DOCUMENTS.length}</strong>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200">
            <span className="text-emerald-700">Verified: </span>
            <strong className="text-emerald-900">{verifiedCount}</strong>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200">
            <span className="text-amber-700">Needs Review: </span>
            <strong className="text-amber-900">{needsSignatureOrReview}</strong>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left List */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden flex flex-col">
          <div className="p-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2 bg-slate-50/50">
            <div className="relative flex-1 min-w-[160px]">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Search artifacts, projects, clients..."
                className="w-full pl-8 pr-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-hidden focus:border-blue-500"
              />
            </div>

            <div className="flex items-center gap-1 text-xs flex-wrap">
              {['All', 'Financial', 'Marketing', 'Research', 'Legal'].map(cat => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-2.5 py-1 rounded-md font-medium cursor-pointer ${
                    selectedCategory === cat
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-600 hover:bg-slate-200/60'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase border-b border-slate-100">
                <tr>
                  <th className="py-2 px-3">Artifact</th>
                  <th className="py-2 px-3">Category</th>
                  <th className="py-2 px-3">Truth</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDocs.map(doc => {
                  const isSelected = activeDoc.id === doc.id;
                  return (
                    <tr
                      key={doc.id}
                      onClick={() => setSelectedDocId(doc.id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? 'bg-blue-50/70' : 'hover:bg-slate-50'
                      }`}
                    >
                      <td className="py-2.5 px-3">
                        <div className="font-medium text-slate-900 truncate max-w-[230px]">
                          {doc.name}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {doc.projectName || doc.client}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-slate-700">{doc.category}</td>
                      <td className="py-2.5 px-3">
                        <TruthBadge truth={doc.truthClass} />
                      </td>
                      <td className="py-2.5 px-3">
                        <StatusBadge status={doc.status} size="sm" />
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <ChevronRight
                          className={`w-4 h-4 inline ${
                            isSelected ? 'text-blue-600' : 'text-slate-300'
                          }`}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Inspector */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
          <div className="pb-3 border-b border-slate-100">
            <div className="flex items-center justify-between gap-2">
              <TruthBadge truth={activeDoc.truthClass} size="sm" />
              <StatusBadge status={activeDoc.status} size="sm" />
            </div>
            <h2 className="text-sm font-semibold text-slate-900 mt-2 break-all">
              {activeDoc.name}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {activeDoc.client} · {activeDoc.uploadedDate} · {activeDoc.size}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-slate-700">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              Document Scope &amp; Provenance
            </div>
            <p className="text-slate-600 leading-relaxed">{activeDoc.scopeSummary}</p>
          </div>

          {activeDoc.projectId && (
            <button
              type="button"
              onClick={() => navigateToObject('projects', activeDoc.projectId, 'project')}
              className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <FolderKanban className="w-3.5 h-3.5" />
              Open Linked Project ({activeDoc.projectName})
            </button>
          )}

          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              onClick={() => {
                sendMessage(`Summarize artifact ${activeDoc.name}.`);
                setIsNovaDrawerOpen(true);
              }}
              className="flex-1 py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Ask Nova
            </button>
            <button
              type="button"
              onClick={() => sendMessage(`Prepare export for "${activeDoc.name}".`)}
              className="py-2 px-3 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
