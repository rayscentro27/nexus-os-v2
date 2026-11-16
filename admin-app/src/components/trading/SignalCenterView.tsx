import React, { useState } from 'react';
import { 
  Radio, 
  ArrowUpRight, 
  ArrowDownRight, 
  Minus, 
  Sparkles, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ShieldAlert, 
  Search, 
  Filter, 
  Eye, 
  Play, 
  ExternalLink,
  BarChart2
} from 'lucide-react';
import { TradingSignal, SignalStatus } from '../../types';

interface SignalCenterViewProps {
  signals: TradingSignal[];
  onCreatePaperOrder: (signal: TradingSignal) => void;
  onUpdateSignalStatus: (signalId: string, newStatus: SignalStatus) => void;
  onOpenChart?: (symbol: string) => void;
  compactMode?: boolean;
}

export const SignalCenterView: React.FC<SignalCenterViewProps> = ({
  signals,
  onCreatePaperOrder,
  onUpdateSignalStatus,
  onOpenChart,
  compactMode = true,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [directionFilter, setDirectionFilter] = useState<string>('ALL');
  const [assetClassFilter, setAssetClassFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSignal, setSelectedSignal] = useState<TradingSignal | null>(null);

  const filteredSignals = signals.filter(s => {
    const matchesStatus = statusFilter === 'ALL' || s.status === statusFilter;
    const matchesDirection = directionFilter === 'ALL' || s.direction === directionFilter;
    const matchesAsset = assetClassFilter === 'ALL' || s.assetClass.toLowerCase().includes(assetClassFilter.toLowerCase());
    const matchesSearch = 
      s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.strategyName.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesDirection && matchesAsset && matchesSearch;
  });

  const getStatusBadge = (status: SignalStatus) => {
    switch (status) {
      case 'NEW':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'WATCHING':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'VALIDATED':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'PAPER_ORDER_CREATED':
        return 'bg-cyan-100 text-cyan-800 border-cyan-200';
      case 'REJECTED':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'EXPIRED':
        return 'bg-slate-100 text-slate-600 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden">
      {/* Top Banner */}
      <div className="bg-white rounded-xl p-2.5 border border-slate-200/90 shadow-2xs space-y-1.5 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
            <span className="text-xs font-black text-slate-900 tracking-tight">Signal Generation Center</span>
            <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-blue-100 text-blue-800">
              {filteredSignals.length} Active Signals
            </span>
            <span className="text-[11px] text-slate-400 hidden sm:inline">
              • Signals do NOT automatically execute without governance gates
            </span>
          </div>

          <div className="text-[10px] bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-lg text-slate-600 font-semibold flex items-center gap-1.5 self-start sm:self-auto">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Ingestion: Unthrottled (100%)</span>
          </div>
        </div>

        {/* Filter Controls Auto-Fit Container */}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-1.5 pt-1.5 border-t border-slate-100 text-[11px]">
          <div className="relative">
            <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search symbol, signal ID..."
              className="w-full pl-7 pr-2.5 py-1 rounded-lg border border-slate-200 text-[11px] focus:outline-hidden"
            />
          </div>

          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="w-full px-2 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold bg-white"
          >
            <option value="ALL">All Signal Statuses</option>
            <option value="NEW">NEW</option>
            <option value="WATCHING">WATCHING</option>
            <option value="VALIDATED">VALIDATED</option>
            <option value="PAPER_ORDER_CREATED">PAPER_ORDER_CREATED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="EXPIRED">EXPIRED</option>
          </select>

          <select
            value={directionFilter}
            onChange={e => setDirectionFilter(e.target.value)}
            className="w-full px-2 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold bg-white"
          >
            <option value="ALL">All Directions (Long / Short)</option>
            <option value="LONG">LONG Only</option>
            <option value="SHORT">SHORT Only</option>
            <option value="NEUTRAL">NEUTRAL Only</option>
          </select>

          <select
            value={assetClassFilter}
            onChange={e => setAssetClassFilter(e.target.value)}
            className="w-full px-2 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold bg-white"
          >
            <option value="ALL">All Asset Classes</option>
            <option value="Equities">Equities</option>
            <option value="Forex">Forex (FX Majors)</option>
            <option value="Crypto">Crypto</option>
          </select>
        </div>

        {/* Visual Signal Direction & Quality Telemetry Bar */}
        <div className="pt-1.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-bold uppercase text-[9px]">Directional Bias:</span>
            <div className="w-28 h-2 bg-slate-100 rounded-full overflow-hidden flex border border-slate-200">
              <div className="bg-emerald-500 h-full" style={{ width: '65%' }} title="Long Bias: 65%" />
              <div className="bg-rose-500 h-full" style={{ width: '35%' }} title="Short Bias: 35%" />
            </div>
            <span className="text-emerald-700 font-bold">65% Bullish</span>
            <span className="text-slate-300">/</span>
            <span className="text-rose-700 font-bold">35% Bearish</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-slate-500">
              Avg Quality: <strong className="text-blue-700 font-bold">84.2%</strong>
            </span>
            <span className="text-slate-500">
              Risk Filter Passed: <strong className="text-emerald-700 font-bold">100%</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Signals Grid: CSS Grid Auto-Fit Container */}
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar grid grid-cols-[repeat(auto-fit,minmax(270px,1fr))] gap-2 pr-0.5">
        {filteredSignals.map(sig => {
          const isLong = sig.direction === 'LONG';
          const isShort = sig.direction === 'SHORT';
          const isForex = sig.assetClass === 'Forex';

          return (
            <div
              key={sig.id}
              className="bg-white rounded-xl p-3 border border-slate-200/90 shadow-2xs hover:border-blue-400 transition-all space-y-2 flex flex-col justify-between"
            >
              <div className="space-y-1.5">
                {/* Header: Symbol, Asset Class & Status */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-black text-slate-900">{sig.symbol}</span>
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-black flex items-center gap-0.5 ${
                      isLong ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                      isShort ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {isLong ? <ArrowUpRight className="w-3 h-3" /> : isShort ? <ArrowDownRight className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                      <span>{sig.direction}</span>
                    </span>
                    <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      {sig.assetClass}
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    <span className={`px-2 py-0.2 rounded-full text-[9px] font-extrabold border ${getStatusBadge(sig.status)}`}>
                      {sig.status}
                    </span>
                  </div>
                </div>

                {/* Feed Health & Simulated Sandbox Pill */}
                <div className="flex items-center justify-between text-[9px] bg-slate-50 px-2 py-0.5 rounded border border-slate-100">
                  <span className="text-slate-500 font-medium">
                    Feed: {isForex ? 'EBS Institutional L2 (Operational)' : 'Standard L2 Feed'}
                  </span>
                  <span className="text-purple-700 font-bold">
                    [SIMULATED]
                  </span>
                </div>

                {/* Strategy and Confidence */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-slate-700 truncate max-w-[170px]">{sig.strategyName}</span>
                    <span className="text-[10px] font-bold text-blue-700 flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-blue-500" />
                      <span>{sig.confidence}%</span>
                    </span>
                  </div>
                  {/* Visual Confidence Bar */}
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-300 ${
                        sig.confidence >= 80 ? 'bg-emerald-500' : sig.confidence >= 65 ? 'bg-blue-500' : 'bg-amber-500'
                      }`}
                      style={{ width: `${sig.confidence}%` }}
                    />
                  </div>
                </div>

                {/* Price Matrix */}
                <div className="grid grid-cols-3 gap-1 p-1.5 rounded-lg bg-slate-50 border border-slate-100 text-center text-[10px]">
                  <div>
                    <div className="text-[8px] text-slate-400 font-bold uppercase">Proposed Entry</div>
                    <div className="font-black text-slate-900 mt-0.5">${sig.proposedEntry.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[8px] text-slate-400 font-bold uppercase">Stop Loss</div>
                    <div className="font-bold text-rose-600 mt-0.5">${sig.proposedStop.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[8px] text-slate-400 font-bold uppercase">Target Price</div>
                    <div className="font-bold text-emerald-600 mt-0.5">${sig.proposedTarget.toFixed(2)}</div>
                  </div>
                </div>

                {/* Risk / Reward & Time */}
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-medium">
                  <span>R:R: <strong className="text-slate-800 font-bold">{sig.riskReward}</strong></span>
                  <span>Exp: <strong className="text-slate-700">{sig.expiration}</strong></span>
                </div>

                {/* Evidence & Rationale */}
                <div className="space-y-1 text-[10px]">
                  {sig.rationale && (
                    <div className="bg-slate-50/80 p-1.5 rounded-lg border border-slate-100 text-slate-700 leading-snug">
                      <strong className="text-slate-900 font-bold">Rationale: </strong>
                      {sig.rationale}
                    </div>
                  )}

                  <p className="text-slate-600 bg-slate-50/60 p-1.5 rounded-lg border border-slate-100 leading-snug font-normal">
                    <strong className="text-slate-800 font-bold">Evidence: </strong>
                    {sig.evidence}
                  </p>
                </div>

                {/* Risk Limit Checked Connection */}
                {sig.riskLimitCheck && (
                  <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-200 text-[10px] flex items-center justify-between">
                    <span className="text-slate-500 font-bold text-[9px] uppercase">Risk Limit Check:</span>
                    <div className="flex items-center gap-1.5">
                      <span className="font-semibold text-slate-700">{sig.riskLimitCheck.limitName}</span>
                      <span className={`px-1.5 py-0.2 rounded font-black text-[8px] border ${
                        sig.riskLimitCheck.status === 'PASSED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        sig.riskLimitCheck.status === 'WARNING' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                        'bg-rose-50 text-rose-700 border-rose-200'
                      }`}>
                        {sig.riskLimitCheck.status}
                      </span>
                    </div>
                  </div>
                )}

                {/* Resulting Paper Action Connection */}
                {sig.resultingPaperAction && (
                  <div className="p-1.5 rounded-lg bg-blue-50/70 border border-blue-200 text-[10px] space-y-0.5">
                    <div className="flex items-center justify-between font-bold text-blue-900 text-[9px] uppercase">
                      <span>Resulting Paper Action:</span>
                      <span className="font-mono text-[8px] text-blue-700 bg-blue-100 px-1 rounded">SIMULATED</span>
                    </div>
                    <p className="text-blue-950 font-medium leading-tight">
                      {sig.resultingPaperAction.details}
                    </p>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-1.5">
                <span className="text-[9px] text-slate-400 font-mono">{sig.id}</span>

                <div className="flex items-center gap-1">
                  {onOpenChart && (
                    <button
                      type="button"
                      onClick={() => onOpenChart(sig.symbol)}
                      className="px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold border border-slate-200 transition-colors flex items-center gap-1 cursor-pointer"
                      title="View chart with Entry, Stop Loss, and Take Profit lines"
                    >
                      <BarChart2 className="w-3 h-3 text-cyan-600" />
                      <span>Chart</span>
                    </button>
                  )}

                  {sig.status === 'NEW' && (
                    <button
                      type="button"
                      onClick={() => onUpdateSignalStatus(sig.id, 'VALIDATED')}
                      className="px-2 py-0.5 rounded-md bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-[10px] font-bold border border-emerald-200 transition-colors cursor-pointer"
                    >
                      Validate
                    </button>
                  )}

                  {sig.status !== 'PAPER_ORDER_CREATED' && (
                    <button
                      type="button"
                      onClick={() => onCreatePaperOrder(sig)}
                      className="px-2.5 py-0.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-bold shadow-2xs transition-all flex items-center gap-1 cursor-pointer"
                    >
                      <Play className="w-2.5 h-2.5 fill-white" />
                      <span>Paper Order</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
