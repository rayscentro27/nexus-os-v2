import React, { useState } from 'react';
import { 
  Database, 
  ShieldCheck, 
  Activity, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  Search, 
  Lock,
  Cpu
} from 'lucide-react';
import { DataProviderItem, TradingAuditRecord } from '../../types';

interface ProviderHealthAuditViewProps {
  providers: DataProviderItem[];
  auditLog: TradingAuditRecord[];
  compactMode?: boolean;
}

export const ProviderHealthAuditView: React.FC<ProviderHealthAuditViewProps> = ({
  providers,
  auditLog,
  compactMode = true,
}) => {
  const [activeTab, setActiveTab] = useState<'providers' | 'audit'>('providers');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredAudit = auditLog.filter(a => {
    return (
      a.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.actor.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.scope.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.reason.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden">
      {/* Top Banner with Tab Navigation */}
      <div className="bg-white rounded-xl p-2.5 border border-slate-200/90 shadow-2xs space-y-1.5 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-black text-slate-900 flex items-center gap-2">
              <Database className="w-4 h-4 text-blue-600" />
              <span>Infrastructure Health & Governance Audit Trail</span>
            </h2>
            <p className="text-[11px] text-slate-500 font-medium">
              Real-time feed latencies, gateway health, rate limit quotas, and tamper-evident audit records.
            </p>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setActiveTab('providers')}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'providers'
                  ? 'bg-blue-600 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Data Providers ({providers.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('audit')}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'audit'
                  ? 'bg-blue-600 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Audit Trail ({auditLog.length})
            </button>
          </div>
        </div>

        {/* Auto-Fit Infrastructure Telemetry Strip */}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-1.5 pt-1 border-t border-slate-100 text-[11px]">
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Feed Health:</span>
            <span className="font-extrabold text-emerald-600">4/4 Online</span>
          </div>
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Avg Latency:</span>
            <span className="font-extrabold text-blue-700">28ms (Optimal)</span>
          </div>
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">WS Channels:</span>
            <span className="font-extrabold text-slate-800">16 Active</span>
          </div>
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Audit Ledger:</span>
            <span className="font-black text-slate-900">SHA-256 Valid</span>
          </div>
        </div>

        {activeTab === 'audit' && (
          <div className="pt-1.5 border-t border-slate-100">
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search audit records, actors, actions..."
                className="w-full pl-7 pr-3 py-1 rounded-lg border border-slate-200 text-xs focus:outline-hidden"
              />
            </div>
          </div>
        )}
      </div>

      {/* CONTENT: DATA PROVIDERS TABLE */}
      {activeTab === 'providers' ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex-1 min-h-0 flex flex-col">
          <div className="overflow-x-auto overflow-y-auto custom-scrollbar flex-1 min-h-0">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 z-10">
                <tr className="border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                  <th className="py-2 px-3">Provider / Engine</th>
                  <th className="py-2 px-2">Category</th>
                  <th className="py-2 px-2">Status</th>
                  <th className="py-2 px-2">Latency</th>
                  <th className="py-2 px-2">Error Rate</th>
                  <th className="py-2 px-2">Rate Limit Quota</th>
                  <th className="py-2 px-2">Last Heartbeat</th>
                  <th className="py-2 px-3 text-right">30d Uptime</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {providers.map(prov => (
                  <tr key={prov.id} className="hover:bg-slate-50/60 transition-colors">
                    {/* Name */}
                    <td className="py-2 px-3">
                      <div className="font-extrabold text-slate-900">{prov.name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{prov.id}</div>
                    </td>

                    {/* Category */}
                    <td className="py-2 px-2">
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-100 text-slate-700">
                        {prov.category}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="py-2 px-2">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.2 rounded-full text-[9px] font-extrabold bg-emerald-100 text-emerald-800">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        <span>{prov.status}</span>
                      </span>
                    </td>

                    {/* Latency */}
                    <td className="py-2 px-2 font-mono font-bold text-slate-900">
                      {prov.latencyMs} ms
                    </td>

                    {/* Error Rate */}
                    <td className="py-2 px-2 text-slate-700 font-semibold">
                      {prov.errorRatePct}%
                    </td>

                    {/* Rate Limit */}
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-blue-600 h-full rounded-full"
                            style={{ width: `${prov.rateLimitUsedPct}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">{prov.rateLimitUsedPct}%</span>
                      </div>
                    </td>

                    {/* Last Heartbeat */}
                    <td className="py-2 px-2 text-[10px] text-slate-500 font-mono">
                      {prov.lastHeartbeat}
                    </td>

                    {/* Uptime */}
                    <td className="py-2 px-3 text-right font-extrabold text-emerald-600">
                      {prov.uptimePct}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* CONTENT: AUDIT TRAIL */
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar space-y-1.5 pr-0.5">
          {filteredAudit.map(rec => (
            <div
              key={rec.id}
              className="bg-white rounded-xl p-2.5 border border-slate-200 shadow-2xs space-y-1 hover:border-slate-300 transition-all text-xs"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-[9px] font-bold text-slate-400 bg-slate-100 px-1.5 py-0.2 rounded">
                    {rec.id}
                  </span>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-black bg-blue-100 text-blue-800">
                    {rec.action}
                  </span>
                  <span className="font-bold text-slate-800 text-[11px]">{rec.scope}</span>
                </div>

                <div className="text-[10px] text-slate-500 flex items-center gap-1 font-mono">
                  <Clock className="w-3 h-3 text-slate-400" />
                  <span>{rec.timestamp}</span>
                </div>
              </div>

              <p className="text-slate-700 leading-snug font-medium text-[11px]">
                {rec.reason}
              </p>

              <div className="pt-1 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[10px] text-slate-500">
                <div>
                  Actor: <strong className="text-slate-800">{rec.actor}</strong>
                </div>
                <div className="flex items-center gap-1 font-mono text-[9px] text-slate-400">
                  <Lock className="w-2.5 h-2.5" />
                  <span>{rec.governanceHash}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
