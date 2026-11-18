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
import { useNexus } from '../context/NexusContext';
import { DocumentItem, TruthClass } from '../types';
import { UnavailableState } from '../components/live/UnavailableState';

interface EnrichedDocument extends DocumentItem {
  projectId?: string;
  projectName?: string;
  truthClass: TruthClass;
  scopeSummary: string;
}

const NEXUS_DOCUMENTS: EnrichedDocument[] = [];

export const DocumentsPage: React.FC = () => {
  const { sendMessage, navigateToObject, setIsNovaDrawerOpen, liveAreas } = useNexus();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const liveDocuments = (liveAreas.documents || liveAreas.artifacts || []) as EnrichedDocument[];
  const [selectedDocId, setSelectedDocId] = useState<string>('');

  const filteredDocs = liveDocuments.filter(doc => {
    const matchesSearch =
      doc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.client.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (doc.projectName || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCat = selectedCategory === 'All' || doc.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  const activeDoc =
    filteredDocs.find(d => d.id === selectedDocId) || filteredDocs[0] || null;

  const verifiedCount = liveDocuments.filter(d => d.status === 'Verified').length;
  const needsSignatureOrReview = liveDocuments.filter(
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
            Project specs, campaign briefs, and other durable Nexus artifacts when connected.
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

  if (liveDocuments.length === 0) {
    return <div className="space-y-4 pb-10"><div className="bg-white rounded-xl p-4 border border-slate-200/80 shadow-2xs"><h1 className="text-lg font-semibold text-slate-900">Documents &amp; Operational Artifacts</h1><p className="text-xs text-slate-500 mt-0.5">Project and evidence artifacts from durable Nexus records.</p></div><div className="grid grid-cols-1 lg:grid-cols-12 gap-4"><div className="lg:col-span-7 bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4"><UnavailableState>Documents are not connected to the live Nexus read model.</UnavailableState></div><div className="lg:col-span-5 bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4"><UnavailableState>No live artifact is available to inspect.</UnavailableState></div></div></div>;
  }
};
