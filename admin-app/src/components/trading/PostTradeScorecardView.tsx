import React, { useState } from 'react';
import {
  Award,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  DollarSign,
  ShieldCheck,
  Sparkles,
  BarChart2,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  Play,
  Download
} from 'lucide-react';
import {
  POST_TRADE_SCORECARDS,
  PostTradeScorecard
} from '../../data/tradeAnalyticsData';

interface PostTradeScorecardViewProps {
  compactMode?: boolean;
  onOpenChart?: (symbol: string) => void;
}

export const PostTradeScorecardView: React.FC<PostTradeScorecardViewProps> = ({
  compactMode = true,
  onOpenChart
}) => {
  const [selectedTrade, setSelectedTrade] = useState<PostTradeScorecard>(
    POST_TRADE_SCORECARDS[0]
  );

  const totalClosedPnl = POST_TRADE_SCORECARDS.reduce(
    (acc, t) => acc + t.realizedPnl,
    0
  );

  const totalPnlLeftOnTable = POST_TRADE_SCORECARDS.reduce(
    (acc, t) => acc + t.pnlLeftOnTableDollars,
    0
  );

  const gradeDistribution = {
    'A+': POST_TRADE_SCORECARDS.filter(t => t.disciplineGrade === 'A+').length,
    A: POST_TRADE_SCORECARDS.filter(t => t.disciplineGrade === 'A').length,
    'B+': POST_TRADE_SCORECARDS.filter(t => t.disciplineGrade === 'B+').length,
    Other: POST_TRADE_SCORECARDS.filter(
      t => !['A+', 'A', 'B+'].includes(t.disciplineGrade)
    ).length
  };

  const handleExportScorecardCsv = () => {
    const headers = ['Trade ID', 'Symbol', 'Strategy', 'Side', 'Realized PnL ($)', 'Discipline Grade', 'MAE Pips', 'MFE Pips', 'Left on Table ($)', 'Post-Mortem Notes'];
    const rows = POST_TRADE_SCORECARDS.map(t => [
      t.tradeId,
      t.symbol,
      `"${t.strategyName}"`,
      t.side,
      t.realizedPnl.toFixed(2),
      t.disciplineGrade,
      t.maePips,
      t.mfePips,
      t.pnlLeftOnTableDollars.toFixed(2),
      `"${t.postMortemNotes.replace(/"/g, '""')}"`
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `PostTrade_Discipline_Scorecard_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden select-none">
      {/* 1. TOP TELEMETRY STRIP */}
      <div className="bg-white rounded-xl px-3 py-2 border border-slate-200/90 shadow-2xs flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-lg bg-amber-50 border border-amber-200">
            <Award className="w-4 h-4 text-amber-600" />
          </div>
          <div>
            <span className="text-xs font-black text-slate-900 flex items-center gap-1.5">
              <span>POST-TRADE EXECUTION SCORECARD &amp; DISCIPLINE AUDITOR</span>
              <span className="px-1.5 py-0.2 rounded text-[8px] font-black bg-emerald-100 text-emerald-900 border border-emerald-300">
                98.4% RULE ADHERENCE
              </span>
            </span>
            <p className="text-[10px] text-slate-500 font-medium">
              Objective post-mortem evaluation: Rules compliance, emotional deviation checks, Adverse (MAE) vs Favorable (MFE) excursion.
            </p>
          </div>
        </div>

        {/* Aggregate KPI Chips & Export Action */}
        <div className="flex items-center gap-1.5 text-xs font-mono flex-wrap">
          <div className="px-2 py-0.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900">
            <span className="text-emerald-700 text-[9px] uppercase font-bold mr-1">Closed P&amp;L:</span>
            <strong className="text-emerald-800 font-black">+${totalClosedPnl.toFixed(2)}</strong>
          </div>

          <div className="px-2 py-0.5 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-slate-400 text-[9px] uppercase font-bold mr-1">Left on Table:</span>
            <strong className="text-slate-700 font-black">${totalPnlLeftOnTable.toFixed(2)}</strong>
          </div>

          <div className="px-2 py-0.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-900">
            <span className="text-blue-700 text-[9px] uppercase font-bold mr-1">Grade 'A' Cohort:</span>
            <strong className="text-blue-800 font-black">
              {gradeDistribution['A+'] + gradeDistribution['A']} / {POST_TRADE_SCORECARDS.length}
            </strong>
          </div>

          <button
            type="button"
            onClick={handleExportScorecardCsv}
            className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1 cursor-pointer transition-colors shadow-2xs font-sans"
            title="Download complete Trade Audit & Discipline CSV report"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV Audit</span>
          </button>
        </div>
      </div>

      {/* 2. MAIN SPLIT: CLOSED TRADES SCORECARD TABLE (LEFT) + TRADE DOSSIER & MAE/MFE (RIGHT) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2 overflow-hidden">
        {/* CLOSED TRADES TABLE (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200/90 shadow-2xs flex flex-col min-h-0 overflow-hidden">
          <div className="px-3 py-1.5 border-b border-slate-100 flex items-center justify-between text-xs bg-slate-50/50 shrink-0">
            <span className="font-extrabold text-slate-800 text-xs">
              Closed Trade Ledger ({POST_TRADE_SCORECARDS.length})
            </span>
            <span className="text-[10px] text-slate-400">
              Click any trade to review post-mortem breakdown
            </span>
          </div>

          <div className="flex-1 min-h-0 overflow-auto custom-scrollbar">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 text-[9px] font-bold text-slate-400 uppercase border-b border-slate-100">
                <tr>
                  <th className="py-2 px-2.5">Trade / Strategy</th>
                  <th className="py-2 px-2">Fill Interval</th>
                  <th className="py-2 px-2">Realized P&amp;L</th>
                  <th className="py-2 px-2 text-center">MAE (Drawdown)</th>
                  <th className="py-2 px-2 text-center">MFE (Peak)</th>
                  <th className="py-2 px-2.5 text-right">Discipline Grade</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-[10px]">
                {POST_TRADE_SCORECARDS.map(trade => {
                  const isSelected = selectedTrade.tradeId === trade.tradeId;
                  const isWin = trade.realizedPnl >= 0;

                  return (
                    <tr
                      key={trade.tradeId}
                      onClick={() => setSelectedTrade(trade)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-blue-50/80 font-semibold'
                          : 'hover:bg-slate-50'
                      }`}
                    >
                      <td className="py-2 px-2.5">
                        <div className="font-extrabold text-slate-900 flex items-center gap-1.5">
                          <span>{trade.symbol}</span>
                          <span
                            className={`px-1 py-0.2 rounded text-[7.5px] font-black ${
                              trade.side === 'LONG'
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-rose-100 text-rose-800'
                            }`}
                          >
                            {trade.side}
                          </span>
                        </div>
                        <span className="text-[9px] text-slate-500 truncate max-w-[140px] block">
                          {trade.strategyName}
                        </span>
                      </td>

                      <td className="py-2 px-2 text-slate-600 font-mono">
                        <div>{trade.entryTime}</div>
                        <div className="text-slate-400 text-[8.5px]">{trade.exitTime}</div>
                      </td>

                      <td className="py-2 px-2 font-mono">
                        <span
                          className={`font-black ${
                            isWin ? 'text-emerald-600' : 'text-rose-600'
                          }`}
                        >
                          {isWin ? '+' : ''}${trade.realizedPnl.toFixed(2)}
                        </span>
                        <span className="text-[8.5px] text-slate-400 block">
                          ({trade.realizedPips > 0 ? `+${trade.realizedPips}` : trade.realizedPips} pts)
                        </span>
                      </td>

                      <td className="py-2 px-2 text-center font-mono text-rose-600 font-bold">
                        -{trade.maePips} pts
                      </td>

                      <td className="py-2 px-2 text-center font-mono text-emerald-700 font-bold">
                        +{trade.mfePips} pts
                      </td>

                      <td className="py-2 px-2.5 text-right">
                        <span
                          className={`px-2 py-0.5 rounded text-[9px] font-black uppercase border ${
                            trade.disciplineGrade.startsWith('A')
                              ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                              : trade.disciplineGrade.startsWith('B')
                              ? 'bg-blue-100 text-blue-900 border-blue-300'
                              : 'bg-rose-100 text-rose-900 border-rose-300'
                          }`}
                        >
                          Grade {trade.disciplineGrade}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* DETAILED SCORECARD DOSSIER & MAE/MFE INSPECTOR (5 Cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3 flex flex-col min-h-0 space-y-3 overflow-y-auto custom-scrollbar">
          {/* Grade Stamp Header */}
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-amber-50 to-orange-50/40 border border-amber-200 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded bg-amber-200 text-amber-950">
                AUDIT SCORECARD
              </span>
              <div className="flex items-center gap-1 font-mono text-xs font-black text-amber-950">
                <span>Discipline Rating:</span>
                <span className="px-2 py-0.5 rounded bg-amber-600 text-white text-xs font-black">
                  {selectedTrade.disciplineGrade}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <div>
                <strong className="text-slate-900 text-xs font-black">
                  {selectedTrade.symbol} · {selectedTrade.strategyName}
                </strong>
                <span className="text-[10px] text-slate-500 block">
                  Fill: {selectedTrade.entryPrice} → Exit: {selectedTrade.exitPrice}
                </span>
              </div>
              <div className="text-right font-mono">
                <span className="text-xs font-black text-emerald-600 block">
                  +${selectedTrade.realizedPnl.toFixed(2)}
                </span>
                <span className="text-[8.5px] text-slate-400">
                  Left on Table: ${selectedTrade.pnlLeftOnTableDollars}
                </span>
              </div>
            </div>
          </div>

          {/* Adverse Excursion (MAE) vs Favorable Excursion (MFE) Visualizer */}
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between border-b border-slate-200 pb-1">
              <span className="text-[10px] font-black uppercase text-slate-700 flex items-center gap-1">
                <BarChart2 className="w-3.5 h-3.5 text-blue-600" />
                <span>Excursion Analysis (MAE vs. MFE)</span>
              </span>
              <span className="text-[9px] text-slate-400">Execution Efficiency</span>
            </div>

            <div className="grid grid-cols-2 gap-1.5 text-xs font-mono">
              <div className="p-2 rounded bg-rose-50 border border-rose-200 text-rose-950">
                <span className="text-[8px] uppercase block text-rose-700 font-bold">
                  Max Adverse Excursion (MAE):
                </span>
                <strong className="text-xs font-black text-rose-700">
                  -{selectedTrade.maePips} pts (-${selectedTrade.maeDollars})
                </strong>
                <span className="text-[8px] text-rose-600 block mt-0.5">
                  How close price came to Stop Loss
                </span>
              </div>

              <div className="p-2 rounded bg-emerald-50 border border-emerald-200 text-emerald-950">
                <span className="text-[8px] uppercase block text-emerald-700 font-bold">
                  Max Favorable Excursion (MFE):
                </span>
                <strong className="text-xs font-black text-emerald-700">
                  +{selectedTrade.mfePips} pts (+${selectedTrade.mfeDollars})
                </strong>
                <span className="text-[8px] text-emerald-600 block mt-0.5">
                  Peak unrealized run-up before exit
                </span>
              </div>
            </div>

            {/* Visual ratio bar */}
            <div className="space-y-0.5">
              <div className="flex justify-between text-[8px] text-slate-400 uppercase font-bold">
                <span>Adverse Drawdown ({selectedTrade.maePips} pts)</span>
                <span>Favorable Payout ({selectedTrade.mfePips} pts)</span>
              </div>
              <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden flex">
                <div
                  className="bg-rose-500 h-full"
                  style={{
                    width: `${Math.min(
                      50,
                      (selectedTrade.maePips / (selectedTrade.maePips + selectedTrade.mfePips || 1)) * 100
                    )}%`
                  }}
                />
                <div
                  className="bg-emerald-500 h-full flex-1"
                />
              </div>
            </div>
          </div>

          {/* Rule-by-Rule Adherence Checklist */}
          <div className="p-2.5 rounded-xl bg-white border border-slate-200 space-y-1.5 shadow-2xs">
            <span className="text-[10px] font-black uppercase text-slate-700 flex items-center gap-1 border-b border-slate-100 pb-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Systematic Rule Compliance Checklist</span>
            </span>

            <div className="space-y-1 text-[9.5px]">
              {selectedTrade.rulesAdhered.map((rule, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 p-1 rounded bg-slate-50 border border-slate-100 text-slate-800"
                >
                  <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                  <span>{rule.rule}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Nova AI Auditor Notes */}
          <div className="p-2.5 rounded-xl bg-indigo-50/70 border border-indigo-200 space-y-1">
            <div className="flex items-center gap-1 text-[9.5px] font-black text-indigo-900 uppercase">
              <Sparkles className="w-3 h-3 text-indigo-600" />
              <span>Nova AI Post-Mortem Assessment</span>
            </div>
            <p className="text-[10px] text-slate-800 font-semibold leading-relaxed">
              {selectedTrade.postMortemNotes}
            </p>
          </div>

          {/* Direct Launch to Visual Replay */}
          {onOpenChart && (
            <button
              type="button"
              onClick={() => onOpenChart(selectedTrade.symbol)}
              className="w-full py-2 px-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl text-xs font-black shadow-md flex items-center justify-center gap-2 cursor-pointer transition-all active:scale-[0.99]"
            >
              <Play className="w-3.5 h-3.5 fill-white" />
              <span>Launch Visual Replay for {selectedTrade.symbol} ({selectedTrade.entryTime})</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
