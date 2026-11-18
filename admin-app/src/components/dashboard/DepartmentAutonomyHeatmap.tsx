import React, { useState } from 'react';
import {
  Activity,
  ShieldCheck,
  Lock,
  ArrowRight,
  Sparkles,
  RotateCw,
  AlertTriangle,
  Bot,
  ExternalLink,
  ChevronRight,
  Info
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';
import { DepartmentId } from '../../data/executiveCommandData';

export interface DepartmentHeatmapItem {
  id: DepartmentId;
  name: string;
  agentName: string;
  autonomyScore: number; // 0 - 100
  status: 'OPTIMAL' | 'ACTIVE_BOUNDED' | 'ATTENTION' | 'ISOLATED';
  hitlRule: string;
  lastHeartbeat: string;
  activeWorkload: string;
  driftPercent: number;
  routePage: string;
}

const HEATMAP_DEPARTMENTS: DepartmentHeatmapItem[] = [
  {
    id: 'research',
    name: 'Research',
    agentName: 'Research Heartbeat & Whisper',
    autonomyScore: 99.2,
    status: 'OPTIMAL',
    hitlRule: 'Universal FIFO direct to Supabase. Alpha review runs as analysis, not blocking gate.',
    lastHeartbeat: '12s ago',
    activeWorkload: '14 feeds polled · 26 NotebookLM extractions · 0 audio backlog',
    driftPercent: 0.0,
    routePage: 'research'
  },
  {
    id: 'development-labs',
    name: 'Development / Labs',
    agentName: 'Needles & Jeeves Experimenter',
    autonomyScore: 91.5,
    status: 'ISOLATED',
    hitlRule: 'Isolated sandbox only. Direct production deployment is strictly FORBIDDEN.',
    lastHeartbeat: '28s ago',
    activeWorkload: 'Kaggle benchmark evaluation · Open weights latency stress test',
    driftPercent: 0.2,
    routePage: 'development-labs'
  },
  {
    id: 'upgrade-control',
    name: 'Upgrade Control',
    agentName: 'Gatekeeper Certification Daemon',
    autonomyScore: 96.8,
    status: 'OPTIMAL',
    hitlRule: 'Automated 5-point verification. Certifies packages before Systems can touch them.',
    lastHeartbeat: '18s ago',
    activeWorkload: 'GoClear v1.0 Production Readiness verification (Audit complete)',
    driftPercent: 0.0,
    routePage: 'upgrade-control'
  },
  {
    id: 'systems',
    name: 'Systems',
    agentName: 'Systems Recovery Guardian',
    autonomyScore: 98.7,
    status: 'OPTIMAL',
    hitlRule: 'Self-healing bounded. Arbitrary shell & destructive operations disabled.',
    lastHeartbeat: '6s ago',
    activeWorkload: '4 Nodes synced · Lease manager heartbeat active · 0 stale leases',
    driftPercent: 0.0,
    routePage: 'systems'
  },
  {
    id: 'trading',
    name: 'Trading Engine',
    agentName: 'Mercury Quant Fleet',
    autonomyScore: 95.0,
    status: 'ACTIVE_BOUNDED',
    hitlRule: 'Paper trading & tournaments autonomous. Live capital deployment requires Ray sign-off.',
    lastHeartbeat: '9s ago',
    activeWorkload: 'Forex London Breakout & Multi-Broker Slippage model active in sandbox',
    driftPercent: 0.0,
    routePage: 'trading-engine'
  },
  {
    id: 'marketing',
    name: 'Marketing',
    agentName: 'Mira Demand Agent',
    autonomyScore: 93.4,
    status: 'ACTIVE_BOUNDED',
    hitlRule: 'Autonomous content drafting. Outbound commercial messaging requires human sign-off.',
    lastHeartbeat: '45s ago',
    activeWorkload: 'GoClear B2B outreach messaging synthesis · SEO pipeline listener',
    driftPercent: 0.1,
    routePage: 'marketing'
  },
  {
    id: 'finance',
    name: 'Finance',
    agentName: 'Clyde & Unit Economics Desk',
    autonomyScore: 97.1,
    status: 'OPTIMAL',
    hitlRule: 'AI recommends funding & unit models. Commitments & applications require Ray/Client.',
    lastHeartbeat: '15s ago',
    activeWorkload: 'GoClear Working Capital DSCR model & Chase Ink eligibility check',
    driftPercent: 0.0,
    routePage: 'finance'
  }
];

export const DepartmentAutonomyHeatmap: React.FC = () => {
  const { setCurrentPage } = useNexus();
  const [filter, setFilter] = useState<'ALL' | 'OPTIMAL' | 'ATTENTION_BOUNDED'>('ALL');
  const [selectedDept, setSelectedDept] = useState<DepartmentHeatmapItem | null>(null);

  const filteredDepts = HEATMAP_DEPARTMENTS.filter(d => {
    if (filter === 'OPTIMAL') return d.status === 'OPTIMAL';
    if (filter === 'ATTENTION_BOUNDED') return d.status !== 'OPTIMAL';
    return true;
  });

  const getStatusColor = (status: DepartmentHeatmapItem['status']) => {
    switch (status) {
      case 'OPTIMAL':
        return {
          pill: 'bg-emerald-100 text-emerald-800 border-emerald-300',
          dot: 'bg-emerald-500',
          cardBorder: 'hover:border-emerald-300'
        };
      case 'ACTIVE_BOUNDED':
        return {
          pill: 'bg-blue-100 text-blue-800 border-blue-300',
          dot: 'bg-blue-500',
          cardBorder: 'hover:border-blue-300'
        };
      case 'ISOLATED':
        return {
          pill: 'bg-purple-100 text-purple-900 border-purple-300',
          dot: 'bg-purple-500',
          cardBorder: 'hover:border-purple-300'
        };
      case 'ATTENTION':
      default:
        return {
          pill: 'bg-amber-100 text-amber-900 border-amber-300',
          dot: 'bg-amber-500',
          cardBorder: 'hover:border-amber-300'
        };
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden flex flex-col h-full select-none">
      {/* Header Bar */}
      <div className="px-3 py-2 bg-slate-900 text-white flex items-center justify-between gap-2 shrink-0 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <div>
            <span className="text-xs font-black uppercase tracking-wider text-white">
              7-Department Autonomy Heatmap Grid
            </span>
            <p className="text-[9px] text-slate-400">
              Real-time autonomy fidelity, drift tracking &amp; human-in-the-loop invariants
            </p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 text-[9px] font-mono">
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`px-2 py-0.5 rounded cursor-pointer transition-colors ${
              filter === 'ALL'
                ? 'bg-slate-700 text-white font-bold'
                : 'bg-slate-800/60 text-slate-400 hover:text-white'
            }`}
          >
            All 7 Depts
          </button>
          <button
            type="button"
            onClick={() => setFilter('OPTIMAL')}
            className={`px-2 py-0.5 rounded cursor-pointer transition-colors ${
              filter === 'OPTIMAL'
                ? 'bg-emerald-600 text-white font-bold'
                : 'bg-slate-800/60 text-slate-400 hover:text-white'
            }`}
          >
            Optimal (96%+)
          </button>
          <button
            type="button"
            onClick={() => setFilter('ATTENTION_BOUNDED')}
            className={`px-2 py-0.5 rounded cursor-pointer transition-colors ${
              filter === 'ATTENTION_BOUNDED'
                ? 'bg-blue-600 text-white font-bold'
                : 'bg-slate-800/60 text-slate-400 hover:text-white'
            }`}
          >
            Bounded &amp; Sandbox
          </button>
        </div>
      </div>

      {/* Grid Content */}
      <div className="flex-1 min-h-0 p-2.5 overflow-y-auto custom-scrollbar space-y-2">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
          {filteredDepts.map(dept => {
            const colors = getStatusColor(dept.status);
            const isSelected = selectedDept?.id === dept.id;

            return (
              <div
                key={dept.id}
                onClick={() => setSelectedDept(dept)}
                className={`p-2.5 rounded-xl border bg-slate-50/50 hover:bg-white transition-all cursor-pointer flex flex-col justify-between gap-2 ${colors.cardBorder} ${
                  isSelected ? 'border-blue-500 bg-white ring-2 ring-blue-400/30 shadow-xs' : 'border-slate-200'
                }`}
              >
                <div>
                  {/* Top Bar of Card */}
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="font-black text-xs text-slate-900 truncate">
                      {dept.name}
                    </span>
                    <span className={`text-[8px] font-black uppercase px-1.5 py-0.2 rounded border font-mono ${colors.pill}`}>
                      {dept.status}
                    </span>
                  </div>

                  {/* Active Agent & Autonomy Score */}
                  <div className="flex items-center justify-between text-[10px] text-slate-600 mb-1.5">
                    <span className="font-mono text-[9px] text-slate-500 truncate flex items-center gap-1">
                      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot} animate-pulse`} />
                      {dept.agentName}
                    </span>
                  </div>

                  {/* Visual Autonomy Bar */}
                  <div className="space-y-0.5 mb-2">
                    <div className="flex items-center justify-between text-[9px] font-mono">
                      <span className="text-slate-500">Unprompted Autonomy:</span>
                      <strong className="text-slate-900 tabular-nums">{dept.autonomyScore}%</strong>
                    </div>
                    <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${dept.autonomyScore}%` }}
                      />
                    </div>
                  </div>

                  {/* HITL Rule Banner */}
                  <div className="p-1.5 rounded-lg bg-white border border-slate-200/90 text-[9px] text-slate-700 leading-tight">
                    <strong className="text-slate-900 uppercase text-[8px] block font-mono text-slate-500">
                      HITL Boundary Rule:
                    </strong>
                    <span>{dept.hitlRule}</span>
                  </div>
                </div>

                {/* Footer Telemetry */}
                <div className="pt-2 border-t border-slate-200/80 flex items-center justify-between text-[8.5px] font-mono text-slate-500">
                  <span>Ping: {dept.lastHeartbeat}</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setCurrentPage(dept.routePage as any);
                    }}
                    className="text-blue-600 hover:text-blue-800 font-bold flex items-center gap-0.5 cursor-pointer hover:underline"
                  >
                    <span>Cockpit</span>
                    <ChevronRight className="w-2.5 h-2.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Department Dossier Banner */}
        {selectedDept && (
          <div className="mt-2 p-3 rounded-xl bg-slate-900 text-white border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-in fade-in duration-150">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span className="text-xs font-black uppercase text-white tracking-wider">
                  Inspecting: {selectedDept.name} Department Guardrail
                </span>
                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.2 rounded border border-emerald-800">
                  {selectedDept.autonomyScore}% Autonomous
                </span>
              </div>
              <p className="text-[11px] text-slate-300 font-medium">
                {selectedDept.activeWorkload}
              </p>
              <p className="text-[10px] text-slate-400 font-mono">
                Boundary: {selectedDept.hitlRule}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setCurrentPage(selectedDept.routePage as any)}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-sm shrink-0"
            >
              <span>Open {selectedDept.name} Cockpit</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
