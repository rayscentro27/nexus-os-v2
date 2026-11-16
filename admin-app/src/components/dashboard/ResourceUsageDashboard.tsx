import React, { useEffect, useMemo, useState } from 'react';
import {
  Cpu,
  HardDrive,
  Sparkles,
  Pause,
  Play,
  RefreshCw,
  Box,
  BarChart3,
  ShieldCheck,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { useNexus } from '../../context/NexusContext';
import { TruthBadge } from '../common/TruthBadge';
import {
  NexusCluster3DCanvas,
  InfraNode3DTelemetry,
} from './NexusCluster3DCanvas';

interface ResourceNodeMetrics extends InfraNode3DTelemetry {
  gpuLabel: string;
  memoryLabel: string;
  aiComputeLabel: string;
  providerBadge: string;
  policyNote: string;
  truthClass: 'VERIFIED' | 'ESTIMATED' | 'PAPER';
  historyGpu: number[];
  historyMem: number[];
  historyAi: number[];
}

interface TrendPoint {
  time: string;
  gpuPct: number;
  memoryPct: number;
  aiComputePct: number;
}

type TimeWindow = 'live' | '15m' | '1h';
type DashboardViewMode = 'telemetry' | '3d';

const INITIAL_RESOURCE_NODES: ResourceNodeMetrics[] = [
  {
    id: 'node-mac-mini',
    name: 'Mac mini (Apple Silicon Metal)',
    shortLabel: 'Mac mini',
    role: 'Ollama Quant Inference · Research FIFO · Trading R1',
    gpuPct: 48,
    memoryPct: 58,
    aiComputePct: 86,
    gpuLabel: '11.5 / 24 GB Metal',
    memoryLabel: '13.9 / 24 GB Unified',
    aiComputeLabel: '18.4 tok/s local',
    providerBadge: 'LOCAL METAL GPU',
    policyNote: 'Handles local LLM builds, Research ingestion, and R1 paper reconciler.',
    status: 'HEALTHY',
    accentHex: 0x2563eb,
    truthClass: 'ESTIMATED',
    historyGpu: [42, 44, 47, 51, 49, 45, 46, 48, 50, 47, 46, 48],
    historyMem: [55, 56, 56, 57, 58, 57, 58, 58, 59, 58, 57, 58],
    historyAi: [89, 88, 86, 84, 85, 87, 87, 86, 85, 86, 87, 86],
  },
  {
    id: 'node-contabo',
    name: 'Contabo VPS Cluster',
    shortLabel: 'Contabo',
    role: 'n8n Automation · Postiz Scheduler · Commerce Preview',
    gpuPct: 12,
    memoryPct: 52,
    aiComputePct: 92,
    gpuLabel: 'Shared Compute (CPU)',
    memoryLabel: '16.6 / 32 GB RAM',
    aiComputeLabel: '92% Worker Headroom',
    providerBadge: 'CONTAINER WORKERS',
    policyNote: 'Executes heavy persistent containers and webhook relays.',
    status: 'HEALTHY',
    accentHex: 0x059669,
    truthClass: 'ESTIMATED',
    historyGpu: [10, 11, 13, 12, 14, 12, 11, 12, 13, 12, 11, 12],
    historyMem: [50, 51, 51, 52, 53, 52, 52, 51, 52, 52, 53, 52],
    historyAi: [94, 93, 92, 92, 91, 92, 93, 92, 91, 92, 92, 92],
  },
  {
    id: 'node-oracle',
    name: 'Oracle Cloud (Control Host)',
    shortLabel: 'Oracle Control',
    role: 'Nova / Hermes Routing & Essential Coordination Only',
    gpuPct: 0,
    memoryPct: 41,
    aiComputePct: 97,
    gpuLabel: '0% (Policy Locked)',
    memoryLabel: '6.5 / 16 GB RAM',
    aiComputeLabel: '97% Routing Ready',
    providerBadge: 'COORDINATION ONLY',
    policyNote: 'Strict guardrail: zero heavy GPU or batch LLM builds allowed on Oracle.',
    status: 'POLICY_LOCK',
    accentHex: 0x0f172a,
    truthClass: 'VERIFIED',
    historyGpu: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    historyMem: [40, 41, 41, 40, 41, 42, 41, 41, 40, 41, 41, 41],
    historyAi: [97, 97, 98, 97, 97, 96, 97, 97, 98, 97, 97, 97],
  },
  {
    id: 'node-openrouter',
    name: 'OpenRouter & Cloud Inference',
    shortLabel: 'OpenRouter AI',
    role: 'Nova Operator · Creative Prompt Synth · Discovery',
    gpuPct: 34,
    memoryPct: 29,
    aiComputePct: 74,
    gpuLabel: 'Cloud Token Burst',
    memoryLabel: 'Context KV Cache',
    aiComputeLabel: '$18.50 est. runway',
    providerBadge: 'API COMPUTE QUOTA',
    policyNote: 'Runway constrained until Ray approves apr_openrouter_topup ($50.00).',
    status: 'CAUTION',
    accentHex: 0x7c3aed,
    truthClass: 'ESTIMATED',
    historyGpu: [28, 31, 35, 38, 33, 30, 32, 34, 36, 33, 35, 34],
    historyMem: [26, 27, 29, 30, 29, 28, 28, 29, 30, 29, 28, 29],
    historyAi: [78, 77, 76, 76, 75, 75, 75, 74, 74, 74, 74, 74],
  },
  {
    id: 'node-modal',
    name: 'Modal Cloud GPU (Standby)',
    shortLabel: 'Modal GPU',
    role: 'On-Demand L4 / A10G Serverless Burst Containers',
    gpuPct: 4,
    memoryPct: 6,
    aiComputePct: 100,
    gpuLabel: '0 / 1 Active Container',
    memoryLabel: 'Warm Image Cache',
    aiComputeLabel: '100% Burst Ready',
    providerBadge: 'STANDBY BURST',
    policyNote: 'Cold standby ($0.00 active burn) reserved for high-throughput batch runs.',
    status: 'STANDBY',
    accentHex: 0x0284c7,
    truthClass: 'PAPER',
    historyGpu: [2, 2, 4, 3, 2, 4, 5, 4, 3, 4, 4, 4],
    historyMem: [5, 5, 6, 6, 5, 6, 6, 6, 5, 6, 6, 6],
    historyAi: [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
  },
];

function MiniTrendSparkline({
  values,
  stroke,
}: {
  values: number[];
  stroke: string;
}) {
  const width = 72;
  const height = 22;
  const points = values
    .map((val, idx) => {
      const x = (idx / Math.max(1, values.length - 1)) * width;
      const y = height - (Math.max(2, Math.min(98, val)) / 100) * (height - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible shrink-0"
      aria-hidden="true"
    >
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

function getProgressBarColor(pct: number, kind: 'gpu' | 'mem' | 'ai'): string {
  if (kind === 'ai') {
    if (pct < 60) return 'bg-rose-600';
    if (pct < 80) return 'bg-amber-500';
    return 'bg-violet-600';
  }
  if (pct >= 85) return 'bg-rose-600';
  if (pct >= 70) return 'bg-amber-500';
  return kind === 'gpu' ? 'bg-blue-600' : 'bg-emerald-600';
}

export const ResourceUsageDashboard: React.FC<{ compact?: boolean }> = ({
  compact = false,
}) => {
  const { approvals, credentials, navigateToObject } = useNexus();

  const [nodes, setNodes] = useState<ResourceNodeMetrics[]>(INITIAL_RESOURCE_NODES);
  const [selectedNodeId, setSelectedNodeId] = useState<string>('ALL');
  const [isStreaming, setIsStreaming] = useState<boolean>(true);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('live');
  const [viewMode, setViewMode] = useState<DashboardViewMode>('telemetry');
  const [is3DFullscreen, setIs3DFullscreen] = useState<boolean>(false);
  const [sampleCounter, setSampleCounter] = useState<number>(0);

  // Sync OpenRouter AI-Compute availability dynamically with authoritative approval & credential state
  const openRouterTopupApproval = approvals.find(a => a.id === 'apr_openrouter_topup');
  const openRouterCred = credentials.find(c => c.id === 'cred-openrouter');
  const isTopupApproved = openRouterTopupApproval?.status === 'APPROVED';

  const effectiveNodes = useMemo(() => {
    return nodes.map(node => {
      if (node.id === 'node-openrouter') {
        const aiAvail = isTopupApproved ? 96 : node.aiComputePct;
        const aiLabel = isTopupApproved
          ? 'Top-up Approved · Full Headroom'
          : openRouterCred?.state === 'CONNECTED'
          ? '$18.50 est. runway (Top-up Pending)'
          : 'Not Connected';
        return {
          ...node,
          aiComputePct: aiAvail,
          aiComputeLabel: aiLabel,
          status: isTopupApproved ? ('HEALTHY' as const) : ('CAUTION' as const),
          policyNote: isTopupApproved
            ? 'OpenRouter top-up cleared by Ray; full inference quota available.'
            : 'Runway constrained ($18.50 est.) until Ray approves apr_openrouter_topup ($50.00).',
        };
      }
      return node;
    });
  }, [nodes, isTopupApproved, openRouterCred]);

  const sampleOnce = () => {
    setSampleCounter(c => c + 1);
    setNodes(prev =>
      prev.map(node => {
        if (node.id === 'node-oracle') {
          // Strict Oracle workload guardrail: 0% heavy GPU, light routing memory drift only
          const nextMem = Math.max(38, Math.min(44, node.memoryPct + (Math.random() > 0.5 ? 1 : -1)));
          const nextAi = Math.max(95, Math.min(99, node.aiComputePct + (Math.random() > 0.5 ? 1 : -1)));
          return {
            ...node,
            gpuPct: 0,
            memoryPct: nextMem,
            aiComputePct: nextAi,
            historyGpu: [...node.historyGpu.slice(1), 0],
            historyMem: [...node.historyMem.slice(1), nextMem],
            historyAi: [...node.historyAi.slice(1), nextAi],
          };
        }

        const drift = (val: number, min: number, max: number, span: number) =>
          Math.max(
            min,
            Math.min(max, Math.round(val + (Math.random() - 0.48) * span))
          );

        const nextGpu =
          node.id === 'node-modal'
            ? drift(node.gpuPct, 2, 8, 2)
            : drift(node.gpuPct, 10, 72, 6);
        const nextMem =
          node.id === 'node-modal'
            ? drift(node.memoryPct, 4, 8, 2)
            : drift(node.memoryPct, 24, 78, 4);
        const nextAi =
          node.id === 'node-modal'
            ? 100
            : drift(node.aiComputePct, 68, 98, 3);

        return {
          ...node,
          gpuPct: nextGpu,
          memoryPct: nextMem,
          aiComputePct: nextAi,
          historyGpu: [...node.historyGpu.slice(1), nextGpu],
          historyMem: [...node.historyMem.slice(1), nextMem],
          historyAi: [...node.historyAi.slice(1), nextAi],
        };
      })
    );
  };

  useEffect(() => {
    if (!isStreaming) return;
    const id = window.setInterval(() => {
      sampleOnce();
    }, 3200);
    return () => clearInterval(id);
  }, [isStreaming]);

  const activeScopeNodes = useMemo(() => {
    if (selectedNodeId === 'ALL') return effectiveNodes;
    return effectiveNodes.filter(n => n.id === selectedNodeId);
  }, [effectiveNodes, selectedNodeId]);

  const aggregates = useMemo(() => {
    // Active GPU load averages across GPU-capable nodes (excluding policy-locked 0% Oracle)
    const gpuPool =
      selectedNodeId === 'ALL'
        ? effectiveNodes.filter(n => n.id !== 'node-oracle')
        : activeScopeNodes;

    const avgGpu = Math.round(
      gpuPool.reduce((sum, n) => sum + n.gpuPct, 0) / Math.max(1, gpuPool.length)
    );
    const avgMem = Math.round(
      activeScopeNodes.reduce((sum, n) => sum + n.memoryPct, 0) /
        Math.max(1, activeScopeNodes.length)
    );
    const avgAi = Math.round(
      activeScopeNodes.reduce((sum, n) => sum + n.aiComputePct, 0) /
        Math.max(1, activeScopeNodes.length)
    );

    return { avgGpu, avgMem, avgAi };
  }, [effectiveNodes, activeScopeNodes, selectedNodeId]);

  const trendSeries: TrendPoint[] = useMemo(() => {
    const len = 12;
    const suffix = timeWindow === 'live' ? 's' : timeWindow === '15m' ? 'm' : 'm';
    const step = timeWindow === 'live' ? 5 : timeWindow === '15m' ? 1 : 5;

    return Array.from({ length: len }, (_, i) => {
      const stepsAgo = len - 1 - i;
      const label =
        stepsAgo === 0
          ? 'Now'
          : `-${stepsAgo * step}${suffix}`;

      const gpuPool =
        selectedNodeId === 'ALL'
          ? effectiveNodes.filter(n => n.id !== 'node-oracle')
          : activeScopeNodes;

      const gVal = Math.round(
        gpuPool.reduce((acc, n) => acc + (n.historyGpu[i] ?? n.gpuPct), 0) /
          Math.max(1, gpuPool.length)
      );
      const mVal = Math.round(
        activeScopeNodes.reduce((acc, n) => acc + (n.historyMem[i] ?? n.memoryPct), 0) /
          Math.max(1, activeScopeNodes.length)
      );
      const aVal = Math.round(
        activeScopeNodes.reduce(
          (acc, n) =>
            acc +
            (n.id === 'node-openrouter' && isTopupApproved
              ? 96
              : n.historyAi[i] ?? n.aiComputePct),
          0
        ) / Math.max(1, activeScopeNodes.length)
      );

      return {
        time: label,
        gpuPct: gVal,
        memoryPct: mVal,
        aiComputePct: aVal,
      };
    });
  }, [effectiveNodes, activeScopeNodes, selectedNodeId, timeWindow, isTopupApproved]);

  // COMPACT MODE FOR OVERVIEW PAGE
  if (compact) {
    return (
      <section className="bg-white rounded-2xl border border-slate-200/90 p-5 space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold text-slate-900">Resource Usage</h2>
          </div>
          <div className="flex items-center gap-1.5">
            <TruthBadge truth="ESTIMATED" label={isStreaming ? 'LIVE STREAM' : 'PAUSED'} />
            <button
              type="button"
              onClick={() => setIsStreaming(v => !v)}
              className="p-1 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-50 cursor-pointer"
              title={isStreaming ? 'Pause telemetry stream' : 'Resume telemetry stream'}
              aria-label={isStreaming ? 'Pause telemetry stream' : 'Resume telemetry stream'}
            >
              {isStreaming ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {/* 3 Animated Progress Bars */}
        <div className="space-y-3 text-xs">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="font-medium text-slate-700">GPU / Metal Compute</span>
              <span className="font-mono font-bold text-slate-900 tabular-nums">
                {aggregates.avgGpu}%
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                  aggregates.avgGpu,
                  'gpu'
                )}`}
                style={{ width: `${aggregates.avgGpu}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="font-medium text-slate-700">Cluster Memory (RAM)</span>
              <span className="font-mono font-bold text-slate-900 tabular-nums">
                {aggregates.avgMem}%
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                  aggregates.avgMem,
                  'mem'
                )}`}
                style={{ width: `${aggregates.avgMem}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="font-medium text-slate-700">AI-Compute Availability</span>
              <span className="font-mono font-bold text-violet-700 tabular-nums">
                {aggregates.avgAi}%
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                  aggregates.avgAi,
                  'ai'
                )}`}
                style={{ width: `${aggregates.avgAi}%` }}
              />
            </div>
          </div>
        </div>

        {/* Compact Multi-Line Trend Strip */}
        <div className="pt-2 border-t border-slate-100">
          <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1.5">
            <span>Rolling Telemetry Trend</span>
            <span className="font-mono">Blue GPU · Green Mem · Violet AI</span>
          </div>
          <div className="h-24 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendSeries} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderColor: '#e2e8f0',
                    borderRadius: '0.5rem',
                    fontSize: '11px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="aiComputePct"
                  name="AI Compute %"
                  stroke="#7c3aed"
                  fill="#ede9fe"
                  fillOpacity={0.35}
                  strokeWidth={1.75}
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="memoryPct"
                  name="Memory %"
                  stroke="#059669"
                  fill="#d1fae5"
                  fillOpacity={0.35}
                  strokeWidth={1.75}
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="gpuPct"
                  name="GPU / Metal %"
                  stroke="#2563eb"
                  fill="#dbeafe"
                  fillOpacity={0.4}
                  strokeWidth={1.75}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <button
          type="button"
          onClick={() => navigateToObject('systems')}
          className="w-full py-1.5 text-xs font-semibold text-blue-600 hover:bg-blue-50 rounded-lg transition-colors flex items-center justify-center gap-1 cursor-pointer"
        >
          <span>Open Full Resource &amp; 3D Cluster View</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </section>
    );
  }

  // FULL RESOURCE USAGE DASHBOARD FOR SYSTEMS PAGE
  return (
    <section className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-4">
      {/* Header Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Cpu className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-900">
              Resource Usage Dashboard · GPU, Memory &amp; AI-Compute
            </h2>
            <TruthBadge
              truth="ESTIMATED"
              label={isStreaming ? 'LIVE TELEMETRY STREAM' : 'STREAM PAUSED'}
            />
            <span className="text-[11px] font-mono text-slate-400">
              Sample #{sampleCounter + 1}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time utilization across Mac mini Metal, Contabo VPS, Oracle Control (policy-locked), OpenRouter quota, and Modal GPU standby.
          </p>
        </div>

        {/* Interactive Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* View Mode Switch: Telemetry vs 3D Twin */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setViewMode('telemetry')}
              className={`px-2.5 py-1 rounded-md font-medium flex items-center gap-1.5 cursor-pointer transition-colors ${
                viewMode === 'telemetry'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Bars &amp; Trends</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('3d')}
              className={`px-2.5 py-1 rounded-md font-medium flex items-center gap-1.5 cursor-pointer transition-colors ${
                viewMode === '3d'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Box className="w-3.5 h-3.5 text-blue-600" />
              <span>3D Cluster Twin</span>
            </button>
          </div>

          {/* Time Window Selector */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-[11px] font-medium">
            {([
              { id: 'live', label: 'Live' },
              { id: '15m', label: '15m' },
              { id: '1h', label: '1h' },
            ] as const).map(w => (
              <button
                key={w.id}
                type="button"
                onClick={() => setTimeWindow(w.id)}
                className={`px-2 py-1 rounded-md cursor-pointer ${
                  timeWindow === w.id
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {w.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setIsStreaming(v => !v)}
            className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium text-slate-700 inline-flex items-center gap-1 cursor-pointer"
          >
            {isStreaming ? (
              <>
                <Pause className="w-3.5 h-3.5 text-amber-600" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 text-emerald-600" />
                <span>Resume</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={sampleOnce}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium inline-flex items-center gap-1 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Sample</span>
          </button>
        </div>
      </div>

      {/* Node Filter Strip */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <button
          type="button"
          onClick={() => setSelectedNodeId('ALL')}
          className={`px-2.5 py-1 rounded-lg font-medium border cursor-pointer transition-colors ${
            selectedNodeId === 'ALL'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
          }`}
        >
          All Infrastructure ({effectiveNodes.length})
        </button>
        {effectiveNodes.map(node => (
          <button
            key={node.id}
            type="button"
            onClick={() => setSelectedNodeId(node.id)}
            className={`px-2.5 py-1 rounded-lg font-medium border cursor-pointer transition-colors ${
              selectedNodeId === node.id
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}
          >
            {node.shortLabel}
          </button>
        ))}
      </div>

      {/* Top 3 Animated Resource Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* 1. GPU / Metal Compute */}
        <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center">
                <Cpu className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-900">GPU / Metal Compute</div>
                <div className="text-[11px] text-slate-500">Mac mini + Modal Standby</div>
              </div>
            </div>
            <span className="text-lg font-bold font-mono text-slate-900 tabular-nums">
              {aggregates.avgGpu}%
            </span>
          </div>

          <div className="h-2.5 w-full rounded-full bg-slate-200/80 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                aggregates.avgGpu,
                'gpu'
              )}`}
              style={{ width: `${aggregates.avgGpu}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>Oracle GPU strictly locked 0%</span>
            <span className="font-mono font-semibold text-blue-700">Normal load</span>
          </div>
        </div>

        {/* 2. Memory Allocation */}
        <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center">
                <HardDrive className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-900">Memory Allocation</div>
                <div className="text-[11px] text-slate-500">Unified VRAM + Host RAM</div>
              </div>
            </div>
            <span className="text-lg font-bold font-mono text-slate-900 tabular-nums">
              {aggregates.avgMem}%
            </span>
          </div>

          <div className="h-2.5 w-full rounded-full bg-slate-200/80 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                aggregates.avgMem,
                'mem'
              )}`}
              style={{ width: `${aggregates.avgMem}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>Mac mini 24GB · Contabo 32GB · Oracle 16GB</span>
            <span className="font-mono font-semibold text-emerald-700">Healthy</span>
          </div>
        </div>

        {/* 3. AI-Compute Availability */}
        <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-violet-50 border border-violet-200 text-violet-700 flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-900">AI-Compute Availability</div>
                <div className="text-[11px] text-slate-500">Local Ollama + OpenRouter + Modal</div>
              </div>
            </div>
            <span className="text-lg font-bold font-mono text-violet-700 tabular-nums">
              {aggregates.avgAi}%
            </span>
          </div>

          <div className="h-2.5 w-full rounded-full bg-slate-200/80 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                aggregates.avgAi,
                'ai'
              )}`}
              style={{ width: `${aggregates.avgAi}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px]">
            {!isTopupApproved ? (
              <button
                type="button"
                onClick={() => navigateToObject('approvals', 'apr_openrouter_topup', 'approval')}
                className="text-amber-800 hover:underline font-medium flex items-center gap-1 cursor-pointer"
              >
                <AlertTriangle className="w-3 h-3 text-amber-600" />
                <span>OpenRouter $50 top-up pending →</span>
              </button>
            ) : (
              <span className="text-emerald-700 font-medium flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" />
                <span>Full inference runway verified</span>
              </span>
            )}
            <span className="font-mono font-semibold text-violet-700">Available</span>
          </div>
        </div>
      </div>

      {/* Main Visualization: Either 2D Animated Trend Lines + Per-Node Breakdown OR Interactive 3D Twin */}
      {viewMode === '3d' ? (
        <div className="space-y-2">
          <NexusCluster3DCanvas
            nodes={effectiveNodes}
            selectedNodeId={selectedNodeId === 'ALL' ? 'node-mac-mini' : selectedNodeId}
            onSelectNode={id => setSelectedNodeId(id)}
            fullscreen={is3DFullscreen}
            onToggleFullscreen={() => setIs3DFullscreen(v => !v)}
          />
          <div className="text-[11px] text-slate-500 flex flex-wrap items-center justify-between gap-2 px-1">
            <span>
              Interactive WebGL cluster topology synced live with GPU, Memory, and AI-Compute bars. Drag to orbit, scroll to zoom, click any chassis to filter metrics.
            </span>
            <span className="font-mono text-slate-600">
              Oracle Control remains isolated for Nova/Hermes coordination only.
            </span>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Trend Lines Chart (5 Cols) */}
          <div className="lg:col-span-5 p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/40 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-semibold text-slate-900">
                  Real-Time Utilization &amp; Availability Trends
                </h3>
                <p className="text-[11px] text-slate-500">
                  {selectedNodeId === 'ALL'
                    ? 'Infrastructure-wide rolling average (%)'
                    : `${activeScopeNodes[0]?.name} rolling telemetry (%)`}
                </p>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-medium">
                <span className="text-blue-700">● GPU</span>
                <span className="text-emerald-700">● Mem</span>
                <span className="text-violet-700">● AI Avail</span>
              </div>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendSeries} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderColor: '#cbd5e1',
                      borderRadius: '0.75rem',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="aiComputePct"
                    name="AI-Compute Avail %"
                    stroke="#7c3aed"
                    fill="#ede9fe"
                    fillOpacity={0.35}
                    strokeWidth={2}
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="memoryPct"
                    name="Memory %"
                    stroke="#059669"
                    fill="#d1fae5"
                    fillOpacity={0.35}
                    strokeWidth={2}
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="gpuPct"
                    name="GPU / Metal %"
                    stroke="#2563eb"
                    fill="#dbeafe"
                    fillOpacity={0.4}
                    strokeWidth={2}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Per-Node Animated Progress Bars & Trend Sparklines (7 Cols) */}
          <div className="lg:col-span-7 divide-y divide-slate-100 rounded-xl border border-slate-200/80 overflow-hidden">
            {activeScopeNodes.map(node => (
              <div
                key={node.id}
                onClick={() =>
                  setSelectedNodeId(prev => (prev === node.id ? 'ALL' : node.id))
                }
                className="p-3.5 bg-white hover:bg-slate-50/70 transition-colors cursor-pointer space-y-2.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-slate-900">{node.name}</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                        {node.providerBadge}
                      </span>
                      <TruthBadge truth={node.truthClass} />
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">{node.role}</div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-[10px] text-slate-400">AI-Compute Trend</div>
                      <MiniTrendSparkline values={node.historyAi} stroke="#7c3aed" />
                    </div>
                  </div>
                </div>

                {/* Node 3 Progress Bars */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-[11px]">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-600 font-medium">GPU / Compute</span>
                      <span className="font-mono font-semibold text-slate-900 tabular-nums">
                        {node.gpuPct}% · {node.gpuLabel}
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                          node.gpuPct,
                          'gpu'
                        )}`}
                        style={{ width: `${Math.max(node.gpuPct, node.id === 'node-oracle' ? 0 : 2)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-600 font-medium">Memory</span>
                      <span className="font-mono font-semibold text-slate-900 tabular-nums">
                        {node.memoryPct}% · {node.memoryLabel}
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                          node.memoryPct,
                          'mem'
                        )}`}
                        style={{ width: `${node.memoryPct}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-600 font-medium">AI Availability</span>
                      <span className="font-mono font-semibold text-violet-700 tabular-nums">
                        {node.aiComputePct}% · {node.aiComputeLabel}
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressBarColor(
                          node.aiComputePct,
                          'ai'
                        )}`}
                        style={{ width: `${node.aiComputePct}%` }}
                      />
                    </div>
                  </div>
                </div>

                <div className="text-[11px] text-slate-500">{node.policyNote}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};
