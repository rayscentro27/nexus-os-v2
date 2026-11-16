import React, { useState, useEffect } from 'react';
import {
  Activity,
  Zap,
  Radio,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Search,
  ExternalLink,
  ChevronRight,
  Cpu,
  Server,
  Layers,
  ArrowUpRight,
  TrendingUp,
  Sliders,
  Filter,
  RefreshCw,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Bot
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';
import { DepartmentId } from '../../data/executiveCommandData';

export interface AgentHealthMetric {
  id: string;
  name: string;
  shortCode: string;
  department: string;
  departmentId: DepartmentId;
  role: string;
  runtime: string;
  status: 'OPERATIONAL' | 'DEGRADED' | 'SYNCING' | 'MAINTENANCE';
  pingMs: number;
  pingHistory: number[]; // Last 8 latency points in ms
  uptimePercent: number; // 24h uptime % (e.g., 99.98)
  uptime7d: number;
  uptime30d: number;
  healthScore: number; // 0 - 100
  lastHeartbeatSec: number; // seconds ago
  tasksProcessed: number;
  errorRate: number; // e.g. 0.01%
  cpuLoad: number; // percentage
  memoryUsageMb: number;
  queueDepth: number;
  activeTask: string;
  hitlGuardrail: string;
}

export const INITIAL_AGENT_METRICS: AgentHealthMetric[] = [
  {
    id: 'agent-whisper-res',
    name: 'Whisper & Research Heartbeat',
    shortCode: 'WR-01',
    department: 'Research',
    departmentId: 'research',
    role: 'Universal FIFO ingestion, YouTube caption extraction & faster-whisper ASR fallback',
    runtime: 'Hermes Cloud / Oracle VM (CPU fallback) & Mac mini',
    status: 'OPERATIONAL',
    pingMs: 9,
    pingHistory: [11, 10, 9, 12, 10, 8, 9, 9],
    uptimePercent: 99.98,
    uptime7d: 99.95,
    uptime30d: 99.91,
    healthScore: 99,
    lastHeartbeatSec: 3,
    tasksProcessed: 18420,
    errorRate: 0.02,
    cpuLoad: 14.5,
    memoryUsageMb: 480,
    queueDepth: 0,
    activeTask: 'Polling 14 feeds · NotebookLM manifest sync',
    hitlGuardrail: 'Persists raw packages to Supabase first; Alpha challenge is downstream'
  },
  {
    id: 'agent-atlas-opps',
    name: 'Atlas Opportunity Recommender',
    shortCode: 'AT-02',
    department: 'Opportunities / Atlas',
    departmentId: 'research',
    role: 'Opportunity scoring, zero-cost blueprints, and lowest-barrier model synthesis',
    runtime: 'Supabase Edge Functions / Gemini Flash API',
    status: 'OPERATIONAL',
    pingMs: 14,
    pingHistory: [15, 14, 16, 14, 13, 15, 14, 14],
    uptimePercent: 99.96,
    uptime7d: 99.92,
    uptime30d: 99.89,
    healthScore: 98,
    lastHeartbeatSec: 5,
    tasksProcessed: 6420,
    errorRate: 0.01,
    cpuLoad: 8.2,
    memoryUsageMb: 310,
    queueDepth: 0,
    activeTask: 'Synthesizing Vertical AI SDR regional business model blueprint',
    hitlGuardrail: 'Recommender only; does not approve capital or deploy production services'
  },
  {
    id: 'agent-clyde-funding',
    name: 'Clyde Capital & Funding Recommender',
    shortCode: 'CL-03',
    department: 'Finance / Funding',
    departmentId: 'finance',
    role: 'Non-binary business credit matching, NAICS bankability audit, lender criteria indexing',
    runtime: 'Mac mini Local Daemon / Gemini Pro Grounded API',
    status: 'OPERATIONAL',
    pingMs: 12,
    pingHistory: [14, 13, 12, 11, 12, 13, 12, 12],
    uptimePercent: 99.99,
    uptime7d: 99.97,
    uptime30d: 99.95,
    healthScore: 100,
    lastHeartbeatSec: 2,
    tasksProcessed: 3890,
    errorRate: 0.00,
    cpuLoad: 6.8,
    memoryUsageMb: 260,
    queueDepth: 0,
    activeTask: 'Tier-1 Tradeline audit for GoClear Logistics Corp & Chase Ink match',
    hitlGuardrail: 'AI recommends funding tiers; credit submissions strictly require Ray or Client signature'
  },
  {
    id: 'agent-mercury-quant',
    name: 'Mercury Quant & Tournament Engine',
    shortCode: 'MQ-04',
    department: 'Trading Engine',
    departmentId: 'trading',
    role: 'Quantitative research, Forex backtesting, multi-broker slippage stress tests',
    runtime: 'Mac mini Local Sandbox Daemon (Paper Trading)',
    status: 'OPERATIONAL',
    pingMs: 8,
    pingHistory: [9, 8, 8, 9, 7, 8, 8, 8],
    uptimePercent: 99.95,
    uptime7d: 99.90,
    uptime30d: 99.85,
    healthScore: 97,
    lastHeartbeatSec: 4,
    tasksProcessed: 52180,
    errorRate: 0.04,
    cpuLoad: 28.4,
    memoryUsageMb: 890,
    queueDepth: 2,
    activeTask: 'London Breakout EUR/USD spread modeling · Tournament cycle #412',
    hitlGuardrail: 'LIVE TRADING STRICTLY OFF ($0 live capital); paper & tournament execution only'
  },
  {
    id: 'agent-systems-guardian',
    name: 'Systems Recovery Guardian',
    shortCode: 'SG-05',
    department: 'Systems',
    departmentId: 'systems',
    role: 'Authoritative infrastructure lease management, health probes, bounded self-recovery',
    runtime: 'Dual-Node Consensus (Mac mini & Oracle VM)',
    status: 'OPERATIONAL',
    pingMs: 6,
    pingHistory: [7, 6, 6, 7, 5, 6, 6, 6],
    uptimePercent: 100.0,
    uptime7d: 99.99,
    uptime30d: 99.98,
    healthScore: 100,
    lastHeartbeatSec: 1,
    tasksProcessed: 94820,
    errorRate: 0.00,
    cpuLoad: 5.1,
    memoryUsageMb: 210,
    queueDepth: 0,
    activeTask: '4 Nodes reconciled · Stale lease collector idle (0 leases expired)',
    hitlGuardrail: 'Bounded recovery; destructive commands and arbitrary shell disabled'
  },
  {
    id: 'agent-gatekeeper-upgrade',
    name: 'Gatekeeper Certification Daemon',
    shortCode: 'GK-06',
    department: 'Upgrade Control',
    departmentId: 'upgrade-control',
    role: 'Automated 5-point verification, regression sandbox runs, rollback certification',
    runtime: 'Hermes Cloud Test Harness',
    status: 'OPERATIONAL',
    pingMs: 16,
    pingHistory: [18, 17, 16, 15, 16, 17, 16, 16],
    uptimePercent: 99.94,
    uptime7d: 99.89,
    uptime30d: 99.82,
    healthScore: 96,
    lastHeartbeatSec: 6,
    tasksProcessed: 1420,
    errorRate: 0.00,
    cpuLoad: 11.2,
    memoryUsageMb: 340,
    queueDepth: 0,
    activeTask: 'Pre-flight certification: GoClear v1.0 Production Readiness bundle',
    hitlGuardrail: 'Labs experiments cannot deploy directly; Systems only receives certified packages'
  },
  {
    id: 'agent-needles-labs',
    name: 'Needles & Jeeves Experimenter',
    shortCode: 'NJ-07',
    department: 'Development / Labs',
    departmentId: 'development-labs',
    role: 'Isolated sandbox R&D, Kaggle dataset ingest, local model latency benchmarks',
    runtime: 'Oracle VM / Hermes Cloud Sandbox',
    status: 'OPERATIONAL',
    pingMs: 21,
    pingHistory: [24, 22, 21, 23, 20, 22, 21, 21],
    uptimePercent: 99.88,
    uptime7d: 99.82,
    uptime30d: 99.75,
    healthScore: 94,
    lastHeartbeatSec: 9,
    tasksProcessed: 2840,
    errorRate: 0.08,
    cpuLoad: 34.0,
    memoryUsageMb: 1120,
    queueDepth: 1,
    activeTask: 'Open weights latency stress test · CPU vs GPU quantization evaluation',
    hitlGuardrail: 'Strictly isolated; production deployment forbidden from this environment'
  },
  {
    id: 'agent-mira-marketing',
    name: 'Mira Demand & Market Intelligence',
    shortCode: 'MR-08',
    department: 'Marketing',
    departmentId: 'marketing',
    role: 'Search intent analysis, institutional GoClear copy drafting, outreach generation',
    runtime: 'Supabase Serverless Background Worker',
    status: 'OPERATIONAL',
    pingMs: 18,
    pingHistory: [19, 18, 20, 18, 17, 18, 18, 18],
    uptimePercent: 99.92,
    uptime7d: 99.88,
    uptime30d: 99.80,
    healthScore: 95,
    lastHeartbeatSec: 7,
    tasksProcessed: 4320,
    errorRate: 0.01,
    cpuLoad: 7.9,
    memoryUsageMb: 240,
    queueDepth: 0,
    activeTask: 'GoClear B2B outreach messaging synthesis · SEO pipeline listener',
    hitlGuardrail: 'Drafts autonomous; external outbound publishing requires marketing/Ray sign-off'
  },
  {
    id: 'agent-nexus-creative',
    name: 'Nexus Creative Studio Engine',
    shortCode: 'NC-09',
    department: 'Creative',
    departmentId: 'creative',
    role: 'Asset generation, interactive design prototypes, visual presentation rendering',
    runtime: 'Hermes Cloud Creative Worker',
    status: 'OPERATIONAL',
    pingMs: 24,
    pingHistory: [26, 25, 24, 25, 23, 24, 24, 24],
    uptimePercent: 99.91,
    uptime7d: 99.85,
    uptime30d: 99.79,
    healthScore: 95,
    lastHeartbeatSec: 11,
    tasksProcessed: 1890,
    errorRate: 0.02,
    cpuLoad: 16.8,
    memoryUsageMb: 620,
    queueDepth: 0,
    activeTask: 'GoClear pitch deck slide deck vector rendering · Brand kit exports',
    hitlGuardrail: 'Asset review gate before release to external clients'
  },
  {
    id: 'agent-nova-exec',
    name: 'Nova Executive Orchestrator',
    shortCode: 'NV-10',
    department: 'Executive Intelligence',
    departmentId: 'nova',
    role: 'Company-wide state synthesis, dependency orchestration, executive voice & chat briefings',
    runtime: 'Client Edge & Grounded Gemini Flash / Pro Multimodal API',
    status: 'OPERATIONAL',
    pingMs: 11,
    pingHistory: [13, 12, 11, 10, 11, 12, 11, 11],
    uptimePercent: 99.99,
    uptime7d: 99.96,
    uptime30d: 99.94,
    healthScore: 100,
    lastHeartbeatSec: 1,
    tasksProcessed: 8740,
    errorRate: 0.00,
    cpuLoad: 6.2,
    memoryUsageMb: 190,
    queueDepth: 0,
    activeTask: 'Command Center real-time synchronization · Ray attention monitoring',
    hitlGuardrail: 'Provides decision intelligence; respects Ray as sole strategic governance authority'
  }
];

export const AgentFleetHealthMonitor: React.FC<{
  compact?: boolean;
  onSelectAgent?: (agent: AgentHealthMetric) => void;
}> = ({ compact = false, onSelectAgent }) => {
  const { setCurrentPage } = useNexus();
  const [agents, setAgents] = useState<AgentHealthMetric[]>(INITIAL_AGENT_METRICS);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPERATIONAL' | 'ATTENTION'>('ALL');
  const [sortBy, setSortBy] = useState<'PING' | 'UPTIME' | 'HEALTH' | 'NAME'>('PING');
  const [selectedAgent, setSelectedAgent] = useState<AgentHealthMetric | null>(agents[0]);
  const [isPinging, setIsPinging] = useState(false);
  const [lastProbeTimestamp, setLastProbeTimestamp] = useState<string>('Just now');

  // Simulate real-time heartbeat variance for live realism
  useEffect(() => {
    const interval = setInterval(() => {
      setAgents(prev =>
        prev.map(agent => {
          // Subtle natural fluctuation around base ping
          const variance = Math.floor(Math.random() * 5) - 2; // -2 to +2
          const newPing = Math.max(4, agent.pingMs + variance);
          const newHistory = [...agent.pingHistory.slice(1), newPing];
          return {
            ...agent,
            pingMs: newPing,
            pingHistory: newHistory,
            lastHeartbeatSec: Math.floor(Math.random() * 4) + 1
          };
        })
      );
    }, 4500);

    return () => clearInterval(interval);
  }, []);

  // Trigger manual instantaneous ping sweep
  const handleProbeFleet = () => {
    setIsPinging(true);
    setTimeout(() => {
      setAgents(prev =>
        prev.map(agent => {
          const freshPing = Math.max(4, agent.pingMs + (Math.floor(Math.random() * 3) - 1));
          return {
            ...agent,
            pingMs: freshPing,
            pingHistory: [...agent.pingHistory.slice(1), freshPing],
            lastHeartbeatSec: 1
          };
        })
      );
      setLastProbeTimestamp('1s ago');
      setIsPinging(false);
    }, 600);
  };

  // Filtered and sorted agents
  const filteredAgents = agents
    .filter(agent => {
      if (statusFilter === 'OPERATIONAL' && agent.status !== 'OPERATIONAL') return false;
      if (statusFilter === 'ATTENTION' && agent.status === 'OPERATIONAL') return false;
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        return (
          agent.name.toLowerCase().includes(query) ||
          agent.department.toLowerCase().includes(query) ||
          agent.shortCode.toLowerCase().includes(query) ||
          agent.role.toLowerCase().includes(query)
        );
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'PING') return a.pingMs - b.pingMs;
      if (sortBy === 'UPTIME') return b.uptimePercent - a.uptimePercent;
      if (sortBy === 'HEALTH') return b.healthScore - a.healthScore;
      return a.name.localeCompare(b.name);
    });

  // Fleet-wide aggregates
  const avgPing = Math.round(agents.reduce((acc, a) => acc + a.pingMs, 0) / agents.length);
  const avgUptime = (
    agents.reduce((acc, a) => acc + a.uptimePercent, 0) / agents.length
  ).toFixed(2);
  const operationalCount = agents.filter(a => a.status === 'OPERATIONAL').length;

  const getPingColor = (ping: number) => {
    if (ping <= 12) return 'text-emerald-600 bg-emerald-50 border-emerald-200';
    if (ping <= 20) return 'text-cyan-700 bg-cyan-50 border-cyan-200';
    if (ping <= 35) return 'text-blue-700 bg-blue-50 border-blue-200';
    return 'text-amber-700 bg-amber-50 border-amber-200';
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden flex flex-col h-full select-none">
      {/* ------------------------------------------------------------- */}
      {/* 1. COMPONENT HEADER / TELEMETRY SUMMARY STRIP */}
      {/* ------------------------------------------------------------- */}
      <div className="px-3 py-2.5 bg-slate-950 text-white flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          <div className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-black tracking-wider uppercase text-white">
                Department AI Agent Fleet Health
              </span>
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/80">
                {operationalCount}/{agents.length} OPERATIONAL
              </span>
            </div>
            <p className="text-[9.5px] text-slate-400 font-medium">
              Real-time ping latency, rolling SLA uptime percentages &amp; daemon heartbeat telemetry
            </p>
          </div>
        </div>

        {/* Aggregate KPI Badges & Probe Fleet Action */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 text-[10px] font-mono">
            <span className="text-slate-400">Fleet Avg Ping:</span>
            <strong className="text-emerald-400 font-bold tabular-nums">{avgPing}ms</strong>
          </div>

          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 text-[10px] font-mono">
            <span className="text-slate-400">24h Uptime:</span>
            <strong className="text-cyan-300 font-bold tabular-nums">{avgUptime}%</strong>
          </div>

          <button
            type="button"
            onClick={handleProbeFleet}
            disabled={isPinging}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 active:scale-95 disabled:opacity-50 text-white font-bold text-[10px] cursor-pointer transition-all shadow-xs"
            title="Send immediate sub-second heartbeat probe to all 10 agents"
          >
            <RefreshCw className={`w-3 h-3 ${isPinging ? 'animate-spin' : ''}`} />
            <span>{isPinging ? 'Probing...' : 'Probe Fleet'}</span>
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 2. CONTROLS, SEARCH & FILTER TOOLBAR */}
      {/* ------------------------------------------------------------- */}
      <div className="p-2.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2 shrink-0 text-xs">
        {/* Search Input */}
        <div className="relative min-w-[200px] flex-1 max-w-xs">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by agent, department, shortcode..."
            className="w-full pl-8 pr-2.5 py-1 bg-white rounded-lg border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-bold text-slate-500 font-mono">Status:</span>
          {(['ALL', 'OPERATIONAL', 'ATTENTION'] as const).map(flt => (
            <button
              key={flt}
              type="button"
              onClick={() => setStatusFilter(flt)}
              className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition-colors ${
                statusFilter === flt
                  ? 'bg-slate-900 text-white shadow-2xs'
                  : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
              }`}
            >
              {flt === 'ALL' ? 'All (10)' : flt === 'OPERATIONAL' ? 'Operational' : 'Needs Check'}
            </button>
          ))}

          <span className="text-slate-300">|</span>

          {/* Sort Control */}
          <span className="text-[10px] font-bold text-slate-500 font-mono">Sort:</span>
          {(
            [
              { id: 'PING', label: 'Lowest Ping' },
              { id: 'UPTIME', label: 'Uptime %' },
              { id: 'HEALTH', label: 'Health Score' },
              { id: 'NAME', label: 'Name' }
            ] as const
          ).map(s => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSortBy(s.id)}
              className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition-colors ${
                sortBy === s.id
                  ? 'bg-blue-600 text-white shadow-2xs'
                  : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 3. AGENT TELEMETRY GRID & DETAIL SPLIT VIEW */}
      {/* ------------------------------------------------------------- */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5 p-2.5 overflow-hidden">
        {/* Agent Cards Grid (8 cols on lg) */}
        <div className="lg:col-span-8 flex flex-col gap-2 min-h-0 overflow-hidden">
          <div className="flex items-center justify-between text-[11px] text-slate-500 px-1 font-mono">
            <span>
              Showing {filteredAgents.length} of {agents.length} Agent Daemons
            </span>
            <span>Probe Cycle: {lastProbeTimestamp}</span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto pr-1 space-y-2 custom-scrollbar">
            {filteredAgents.map(agent => {
              const isSelected = selectedAgent?.id === agent.id;
              const pingStyle = getPingColor(agent.pingMs);

              return (
                <div
                  key={agent.id}
                  onClick={() => {
                    setSelectedAgent(agent);
                    if (onSelectAgent) onSelectAgent(agent);
                  }}
                  className={`p-2.5 rounded-xl border transition-all cursor-pointer bg-white flex flex-col gap-2 ${
                    isSelected
                      ? 'border-blue-500 ring-2 ring-blue-400/30 shadow-xs'
                      : 'border-slate-200/90 hover:border-slate-300 hover:bg-slate-50/50'
                  }`}
                >
                  {/* Top Bar of Agent Card */}
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-6 h-6 rounded-lg bg-slate-900 text-cyan-300 flex items-center justify-center font-mono font-black text-[9px] border border-slate-700 shrink-0">
                        {agent.shortCode}
                      </div>

                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-black text-xs text-slate-900 truncate">
                            {agent.name}
                          </span>
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                            {agent.department}
                          </span>
                        </div>
                        <div className="text-[9px] text-slate-500 font-mono truncate">
                          Runtime: {agent.runtime}
                        </div>
                      </div>
                    </div>

                    {/* Status Pill & Real-time Ping */}
                    <div className="flex items-center gap-2 shrink-0">
                      <div className={`px-2 py-0.5 rounded-lg border font-mono font-bold text-[10px] flex items-center gap-1.5 ${pingStyle}`}>
                        <Radio className="w-2.5 h-2.5 animate-pulse" />
                        <span className="tabular-nums">{agent.pingMs}ms</span>
                        <span className="text-[8px] opacity-75 uppercase">ping</span>
                      </div>

                      <div className="px-2 py-0.5 rounded-lg border font-mono font-bold text-[10px] bg-slate-900 text-emerald-400 border-slate-800">
                        <span className="tabular-nums">{agent.uptimePercent}%</span>
                        <span className="text-[8px] text-slate-400 ml-1">24h</span>
                      </div>
                    </div>
                  </div>

                  {/* Mid Section: Telemetry Meters & Ping Sparkline */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-slate-100 text-[9.5px] font-mono">
                    {/* Ping Sparkline Visualizer */}
                    <div className="bg-slate-50 p-1.5 rounded-lg border border-slate-200/80 flex flex-col justify-between">
                      <div className="flex items-center justify-between text-[8px] text-slate-400 uppercase">
                        <span>Ping Jitter</span>
                        <span className="tabular-nums font-bold text-slate-700">{agent.pingMs}ms</span>
                      </div>
                      {/* Mini Bar Sparkline */}
                      <div className="flex items-end gap-1 h-4 pt-1">
                        {agent.pingHistory.map((p, idx) => {
                          const heightPct = Math.min(100, Math.max(20, (p / 30) * 100));
                          return (
                            <div
                              key={idx}
                              style={{ height: `${heightPct}%` }}
                              className={`flex-1 rounded-xs transition-all ${
                                idx === agent.pingHistory.length - 1
                                  ? 'bg-blue-600'
                                  : 'bg-slate-300'
                              }`}
                              title={`${p}ms`}
                            />
                          );
                        })}
                      </div>
                    </div>

                    {/* SLA Uptime 7d / 30d */}
                    <div className="bg-slate-50 p-1.5 rounded-lg border border-slate-200/80 space-y-0.5">
                      <div className="flex items-center justify-between text-[8px] text-slate-400 uppercase">
                        <span>SLA Stability</span>
                        <span className="text-emerald-700 font-bold">{agent.healthScore}/100</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-700">
                        <span>7d: <strong className="tabular-nums">{agent.uptime7d}%</strong></span>
                        <span>30d: <strong className="tabular-nums">{agent.uptime30d}%</strong></span>
                      </div>
                    </div>

                    {/* Heartbeat & Error Rate */}
                    <div className="bg-slate-50 p-1.5 rounded-lg border border-slate-200/80 space-y-0.5">
                      <div className="flex items-center justify-between text-[8px] text-slate-400 uppercase">
                        <span>Heartbeat</span>
                        <span className="text-emerald-600 font-bold">{agent.lastHeartbeatSec}s ago</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-700">
                        <span>Err: <strong className="tabular-nums">{agent.errorRate}%</strong></span>
                        <span>Tasks: <strong className="tabular-nums">{agent.tasksProcessed.toLocaleString()}</strong></span>
                      </div>
                    </div>

                    {/* Compute & Memory Load */}
                    <div className="bg-slate-50 p-1.5 rounded-lg border border-slate-200/80 space-y-0.5">
                      <div className="flex items-center justify-between text-[8px] text-slate-400 uppercase">
                        <span>Resource Load</span>
                        <span className="text-slate-500 font-bold">{agent.cpuLoad}% CPU</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-700">
                        <span>Mem: <strong className="tabular-nums">{agent.memoryUsageMb}MB</strong></span>
                        <span>Queue: <strong className="tabular-nums">{agent.queueDepth}</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* Active Workload One-Liner */}
                  <div className="text-[10px] text-slate-600 bg-slate-50/70 px-2 py-1 rounded-md border border-slate-200/60 truncate flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                    <span className="font-bold text-slate-700 font-mono text-[9px] uppercase">Active:</span>
                    <span className="truncate">{agent.activeTask}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Agent Health Dossier Drawer (4 cols on lg) */}
        <div className="lg:col-span-4 flex flex-col justify-between bg-slate-50/90 p-3 rounded-xl border border-slate-200 overflow-y-auto custom-scrollbar">
          {selectedAgent ? (
            <div className="space-y-3">
              {/* Dossier Header */}
              <div className="pb-2 border-b border-slate-200">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono uppercase text-slate-400 font-bold">
                    Agent Health Dossier
                  </span>
                  <span className="px-1.5 py-0.2 rounded font-mono font-bold text-[8.5px] bg-slate-200 text-slate-800">
                    {selectedAgent.shortCode}
                  </span>
                </div>
                <h3 className="font-black text-sm text-slate-900 mt-0.5 leading-tight">
                  {selectedAgent.name}
                </h3>
                <span className="text-[10px] font-bold text-blue-700">
                  {selectedAgent.department} Department
                </span>
              </div>

              {/* Ping & Uptime Big Cards */}
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="p-2 bg-white rounded-lg border border-slate-200 shadow-2xs">
                  <span className="text-[8px] font-mono uppercase text-slate-400 block font-bold">
                    Real-Time Ping
                  </span>
                  <div className="text-xl font-black text-slate-900 font-mono tabular-nums mt-0.5">
                    {selectedAgent.pingMs}
                    <span className="text-xs text-slate-400 font-normal ml-0.5">ms</span>
                  </div>
                  <span className="text-[8.5px] text-emerald-600 font-bold block mt-0.5">
                    Sub-20ms SLA Pass
                  </span>
                </div>

                <div className="p-2 bg-white rounded-lg border border-slate-200 shadow-2xs">
                  <span className="text-[8px] font-mono uppercase text-slate-400 block font-bold">
                    24-Hour Uptime
                  </span>
                  <div className="text-xl font-black text-emerald-600 font-mono tabular-nums mt-0.5">
                    {selectedAgent.uptimePercent}
                    <span className="text-xs text-slate-400 font-normal ml-0.5">%</span>
                  </div>
                  <span className="text-[8.5px] text-slate-500 font-mono block mt-0.5">
                    30d: {selectedAgent.uptime30d}%
                  </span>
                </div>
              </div>

              {/* Core Responsibility */}
              <div className="p-2 bg-white rounded-lg border border-slate-200 space-y-1">
                <span className="text-[8.5px] font-bold uppercase text-slate-400 font-mono block">
                  Autonomous Responsibility
                </span>
                <p className="text-[11px] text-slate-800 leading-relaxed font-medium">
                  {selectedAgent.role}
                </p>
              </div>

              {/* Execution Runtime & Host Environment */}
              <div className="p-2 bg-white rounded-lg border border-slate-200 space-y-1">
                <span className="text-[8.5px] font-bold uppercase text-slate-400 font-mono block flex items-center gap-1">
                  <Server className="w-3 h-3 text-slate-500" /> Host &amp; Runtime Environment
                </span>
                <p className="text-xs font-mono font-bold text-slate-900">
                  {selectedAgent.runtime}
                </p>
                <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 pt-1 border-t border-slate-100">
                  <span>RAM: {selectedAgent.memoryUsageMb} MB</span>
                  <span>CPU: {selectedAgent.cpuLoad}%</span>
                  <span>Queue: {selectedAgent.queueDepth}</span>
                </div>
              </div>

              {/* HITL Boundary Guardrail (Anti-hallucination / Anti-unauthorized execution) */}
              <div className="p-2.5 rounded-lg bg-rose-50/80 border border-rose-200 space-y-1 text-rose-950">
                <span className="text-[9px] font-bold uppercase text-rose-800 font-mono flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3 text-rose-600" /> Human-In-The-Loop Boundary
                </span>
                <p className="text-[11px] leading-relaxed">
                  {selectedAgent.hitlGuardrail}
                </p>
              </div>

              {/* Live Task Status */}
              <div className="p-2 bg-white rounded-lg border border-slate-200 space-y-1">
                <span className="text-[8.5px] font-bold uppercase text-slate-400 font-mono block">
                  Current Ingest / Processing Cycle
                </span>
                <p className="text-[11px] font-medium text-slate-900">
                  {selectedAgent.activeTask}
                </p>
                <div className="text-[9px] font-mono text-slate-500 flex items-center justify-between pt-0.5">
                  <span>Total Cycles: {selectedAgent.tasksProcessed.toLocaleString()}</span>
                  <span className="text-emerald-700 font-bold">Error: {selectedAgent.errorRate}%</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-slate-400">
              Select an agent from the fleet to inspect detailed health telemetry.
            </div>
          )}

          {/* Quick Department Cockpit Nav Button */}
          {selectedAgent && (
            <div className="pt-2 mt-2 border-t border-slate-200">
              <button
                type="button"
                onClick={() => {
                  const targetPage =
                    selectedAgent.departmentId === 'trading'
                      ? 'trading-engine'
                      : selectedAgent.departmentId === 'client-portal'
                      ? 'clients'
                      : selectedAgent.departmentId;
                  setCurrentPage(targetPage as any);
                }}
                className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-xs"
              >
                <span>Open {selectedAgent.department} Cockpit</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
