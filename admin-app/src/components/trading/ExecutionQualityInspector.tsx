import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  Filter,
  Layers,
  Search,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Zap
} from 'lucide-react';
import {
  EXECUTION_QUALITY_RECORDS,
  ExecutionQualityRecord
} from '../../data/tradeAnalyticsData';

interface ExecutionQualityInspectorProps {
  compactMode?: boolean;
}

export const ExecutionQualityInspector: React.FC<ExecutionQualityInspectorProps> = ({
  compactMode = true
}) => {
  const [filterRegime, setFilterRegime] = useState<string>('ALL');
  const [selectedRecord, setSelectedRecord] = useState<ExecutionQualityRecord | null>(
    EXECUTION_QUALITY_RECORDS[2] || EXECUTION_QUALITY_RECORDS[0]
  );

  const filteredRecords = EXECUTION_QUALITY_RECORDS.filter(r => {
    return filterRegime === 'ALL' || r.sessionRegime === filterRegime;
  });

  const avgLatency = Math.round(
    EXECUTION_QUALITY_RECORDS.reduce((acc, r) => acc + r.latencyMs, 0) /
      EXECUTION_QUALITY_RECORDS.length
  );

  const totalSlippageCost = EXECUTION_QUALITY_RECORDS.reduce(
    (acc, r) => acc + r.slippageCostDollars,
    0
  );

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden select-none">
      {/* 1. TOP TELEMETRY STRIP */}
      <div className="bg-white rounded-xl px-3 py-2 border border-slate-200/90 shadow-2xs flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-lg bg-blue-50 border border-blue-200">
            <Zap className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <span className="text-xs font-black text-slate-900 flex items-center gap-1.5">
              <span>EXECUTION QUALITY &amp; SLIPPAGE AUDITOR</span>
              <span className="px-1.5 py-0.2 rounded text-[8px] font-black bg-amber-100 text-amber-900 border border-amber-300">
                1 FEED LATENCY ALERT
              </span>
            </span>
            <p className="text-[10px] text-slate-500 font-medium">
              Tick-by-tick fill auditing: Expected arrival price vs matched execution price across liquidity providers.
            </p>
          </div>
        </div>

        {/* Aggregate KPI Chips */}
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <div className="px-2 py-0.5 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-slate-400 text-[9px] uppercase font-bold mr-1">Avg Latency:</span>
            <strong className="text-slate-900 font-black">{avgLatency}ms</strong>
          </div>

          <div className="px-2 py-0.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900">
            <span className="text-amber-700 text-[9px] uppercase font-bold mr-1">Binance L3:</span>
            <strong className="text-amber-800 font-black">142ms (Degraded)</strong>
          </div>

          <div className="px-2 py-0.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900">
            <span className="text-emerald-700 text-[9px] uppercase font-bold mr-1">Net Slippage:</span>
            <strong className="text-emerald-800 font-black">+$0.62 (Controlled)</strong>
          </div>
        </div>
      </div>

      {/* 2. MAIN SPLIT: EXECUTION LOG TABLE (LEFT) + DISLOCATION & LATENCY AUDIT (RIGHT) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2 overflow-hidden">
        {/* EXECUTION ORDERS AUDIT TABLE (8 Cols) */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-slate-200/90 shadow-2xs flex flex-col min-h-0 overflow-hidden">
          {/* Filter Bar */}
          <div className="px-3 py-1.5 border-b border-slate-100 flex items-center justify-between text-xs bg-slate-50/50 shrink-0">
            <span className="font-extrabold text-slate-800 text-xs">
              Fill Execution Ledger ({filteredRecords.length})
            </span>

            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400">Regime:</span>
              <select
                value={filterRegime}
                onChange={e => setFilterRegime(e.target.value)}
                className="px-2 py-0.5 rounded bg-white border border-slate-200 text-[10.5px] font-bold text-slate-700"
              >
                <option value="ALL">All Market Regimes</option>
                <option value="London Open">London Open</option>
                <option value="NY Overlap">NY Overlap</option>
                <option value="Asian Session">Asian Session</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="flex-1 min-h-0 overflow-auto custom-scrollbar">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 text-[9px] font-bold text-slate-400 uppercase border-b border-slate-100">
                <tr>
                  <th className="py-2 px-2.5">Order / Symbol</th>
                  <th className="py-2 px-2">Gateway Route</th>
                  <th className="py-2 px-2 text-center">Fill Latency</th>
                  <th className="py-2 px-2">Expected Price</th>
                  <th className="py-2 px-2">Actual Fill</th>
                  <th className="py-2 px-2">Slippage</th>
                  <th className="py-2 px-2">Spread</th>
                  <th className="py-2 px-2.5 text-right">Audit Grade</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-[10px]">
                {filteredRecords.map(rec => {
                  const isSelected = selectedRecord?.id === rec.id;
                  const isAdverse = rec.slippagePips > 0;
                  const isFavorable = rec.slippagePips < 0;

                  return (
                    <tr
                      key={rec.id}
                      onClick={() => setSelectedRecord(rec)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-blue-50/80 font-semibold'
                          : 'hover:bg-slate-50'
                      }`}
                    >
                      <td className="py-2 px-2.5">
                        <div className="font-extrabold text-slate-900 flex items-center gap-1">
                          <span>{rec.symbol}</span>
                          <span
                            className={`px-1 py-0.2 rounded text-[7.5px] font-black ${
                              rec.side === 'BUY'
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-rose-100 text-rose-800'
                            }`}
                          >
                            {rec.side}
                          </span>
                        </div>
                        <span className="text-[8.5px] font-mono text-slate-400">
                          {rec.orderId}
                        </span>
                      </td>

                      <td className="py-2 px-2 font-mono text-slate-700">
                        {rec.route}
                      </td>

                      <td className="py-2 px-2 text-center font-mono">
                        <span
                          className={`px-1.5 py-0.2 rounded font-black text-[9px] ${
                            rec.latencyMs > 100
                              ? 'bg-rose-100 text-rose-800 border border-rose-300'
                              : rec.latencyMs > 50
                              ? 'bg-amber-100 text-amber-800 border border-amber-300'
                              : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                          }`}
                        >
                          {rec.latencyMs}ms
                        </span>
                      </td>

                      <td className="py-2 px-2 font-mono text-slate-600">
                        {rec.expectedPrice.toFixed(rec.symbol.includes('BTC') ? 1 : 4)}
                      </td>

                      <td className="py-2 px-2 font-mono font-bold text-slate-900">
                        {rec.actualPrice.toFixed(rec.symbol.includes('BTC') ? 1 : 4)}
                      </td>

                      <td className="py-2 px-2 font-mono">
                        <span
                          className={`font-black ${
                            isAdverse
                              ? 'text-rose-600'
                              : isFavorable
                              ? 'text-emerald-600'
                              : 'text-slate-400'
                          }`}
                        >
                          {rec.slippagePips > 0 ? `+${rec.slippagePips}` : rec.slippagePips} pips
                        </span>
                      </td>

                      <td className="py-2 px-2 font-mono text-slate-600">
                        {rec.spreadAtFillPips} pips
                      </td>

                      <td className="py-2 px-2.5 text-right">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[8px] font-black uppercase border ${
                            rec.executionGrade === 'EXCELLENT'
                              ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                              : rec.executionGrade === 'DEGRADED_LATENCY'
                              ? 'bg-amber-100 text-amber-950 border-amber-300'
                              : 'bg-blue-100 text-blue-900 border-blue-300'
                          }`}
                        >
                          {rec.executionGrade.replace('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* LATENCY AUDIT & SPREAD DISLOCATION (4 Cols) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 flex flex-col min-h-0 space-y-3 overflow-y-auto custom-scrollbar">
          {/* Selected Record Spotlight */}
          {selectedRecord && (
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-900">
                  FILL MICROSTRUCTURE DOSSIER
                </span>
                <span className="font-mono text-[9px] font-bold text-slate-500">
                  {selectedRecord.id}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <strong>{selectedRecord.symbol} · {selectedRecord.side}</strong>
                <span className="font-mono font-black text-slate-900">
                  Fill: {selectedRecord.actualPrice}
                </span>
              </div>

              {selectedRecord.flaggedAnomaly ? (
                <div className="p-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-[9.5px] space-y-0.5">
                  <div className="font-bold flex items-center gap-1 text-amber-950">
                    <AlertTriangle className="w-3 h-3 text-amber-600" />
                    <span>Microstructure Anomaly Flagged</span>
                  </div>
                  <p>{selectedRecord.flaggedAnomaly}</p>
                </div>
              ) : (
                <div className="p-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-[9.5px]">
                  <span>Optimal matching. Zero adverse price degradation between tick ingestion and order router fill.</span>
                </div>
              )}
            </div>
          )}

          {/* Gateway Routing Latency SLA Matrix */}
          <div className="p-2.5 rounded-xl bg-white border border-slate-200 space-y-2 shadow-2xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-1">
              <span className="text-[10px] font-black uppercase text-slate-700 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-blue-600" />
                <span>Gateway Latency SLA Benchmarks</span>
              </span>
              <span className="text-[9px] text-slate-400">Target &lt;50ms</span>
            </div>

            <div className="space-y-1.5 text-xs font-mono">
              {[
                { name: 'EBS ECN Direct', latency: 22, status: 'EXCELLENT', color: 'text-emerald-700' },
                { name: 'OANDA Practice Gateway', latency: 28, status: 'NORMAL', color: 'text-emerald-700' },
                { name: 'Alpaca Sim Sandbox', latency: 34, status: 'NORMAL', color: 'text-emerald-700' },
                { name: 'Webull Sandbox Relay', latency: 48, status: 'BORDERLINE', color: 'text-amber-700' },
                { name: 'Binance Microstructure L3', latency: 142, status: 'ALERT (>50ms)', color: 'text-rose-700 font-bold' }
              ].map(gw => (
                <div key={gw.name} className="flex items-center justify-between p-1.5 rounded bg-slate-50 border border-slate-100 text-[10px]">
                  <span className="text-slate-800">{gw.name}</span>
                  <div className="flex items-center gap-2">
                    <span className={`font-black ${gw.color}`}>{gw.latency}ms</span>
                    <span className="text-[8px] uppercase px-1 rounded bg-slate-200/80 text-slate-700 font-bold">
                      {gw.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Session Spread Dislocation Profile */}
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 text-xs">
            <span className="text-[10px] font-black uppercase text-slate-700 flex items-center gap-1">
              <Activity className="w-3.5 h-3.5 text-indigo-600" />
              <span>Regime Spread Dislocation Profile</span>
            </span>

            <div className="space-y-1 text-[9.5px]">
              <div className="flex justify-between items-center text-slate-700">
                <span>NY/London Overlap:</span>
                <strong className="text-emerald-700">0.3 - 0.5 bps (Tightest)</strong>
              </div>
              <div className="flex justify-between items-center text-slate-700">
                <span>London Open:</span>
                <strong className="text-slate-800">0.6 - 0.9 bps (Normal)</strong>
              </div>
              <div className="flex justify-between items-center text-slate-700">
                <span>Asian Pre-Market:</span>
                <strong className="text-slate-800">0.8 - 1.2 bps (Wide)</strong>
              </div>
              <div className="flex justify-between items-center text-slate-700">
                <span>Daily 17:00 Roll/Swap:</span>
                <strong className="text-amber-800">2.4 - 4.5 bps (Execution Paused)</strong>
              </div>
            </div>

            <div className="pt-1.5 border-t border-slate-200 text-[8.5px] text-slate-500">
              Nexus quant safety filter automatically widens entry buffers or pauses execution during roll/swap intervals.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
