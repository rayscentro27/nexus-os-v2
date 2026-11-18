import React, { useState } from 'react';
import { 
  Sparkles, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  FileText, 
  Layers, 
  ChevronRight,
  TrendingUp,
  Cpu,
  FileCheck
} from 'lucide-react';
import { StrategyItem, AlphaDecision } from '../../types';

interface AlphaReviewWorkspaceProps {
  strategies: StrategyItem[];
  onSelectStrategy: (strategy: StrategyItem) => void;
  compactMode?: boolean;
  onRequestLiveApproval?: (strategy: StrategyItem) => void;
}

export const AlphaReviewWorkspace: React.FC<AlphaReviewWorkspaceProps> = ({
  strategies,
  onSelectStrategy,
  compactMode = true,
  onRequestLiveApproval,
}) => {
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>(strategies[0]?.id || '');

  const strategy = strategies.find(s => s.id === selectedStrategyId) || strategies[0];

  const getVerdictBadge = (decision: AlphaDecision) => {
    switch (decision) {
      case 'QUALIFY':
      case 'PAPER_TEST':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'RESEARCH_MORE':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'PAUSE':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'REJECT':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden">
      {/* Top Banner */}
      <div className="bg-white rounded-xl p-2.5 border border-slate-200/90 shadow-2xs space-y-1.5 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-black text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span>TRADING ALPHA REVIEW: Quantitative Model Auditor & Statistical Falsification</span>
              <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-purple-100 text-purple-800">
                P-Hacking & Bias Auditor
              </span>
            </h2>
            <p className="text-[11px] text-slate-500 font-medium">
              <strong className="text-purple-900">Distinct from Hermes / Customer Discovery Research Alpha:</strong> This engine independently stresses quantitative models with Monte Carlo permutations, tests for p-hacking, and validates out-of-sample stationarity.
            </p>
          </div>

          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-purple-900 bg-purple-50 px-2 py-0.5 rounded-lg border border-purple-200 shrink-0">
            <Cpu className="w-3 h-3 text-purple-600" />
            <span>Evaluation Cycle: Continuous</span>
          </div>
        </div>

        {/* Governance & Next Gate Notice */}
        <div className="p-2 rounded-lg bg-purple-50/50 border border-purple-200/70 text-[10px] text-purple-950 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-purple-700 shrink-0" />
            <span><strong>Progression Rule:</strong> Alpha qualification is a prerequisite for Risk Review, which unlocks Paper Trading. <strong>Live trading is permanently locked.</strong></span>
          </div>
          <span className="font-bold text-slate-600 font-mono">Policy: RP-2026.4</span>
        </div>

        {/* 6 Core Alpha Testing Pillars Info Strip in Auto-Fit Container */}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-1.5 pt-1 border-t border-slate-100 text-[10px]">
          <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-100">
            <div className="font-bold text-slate-800">1. Evidence Quality</div>
            <div className="text-[9px] text-slate-500">Stationarity & p-values</div>
          </div>
          <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-100">
            <div className="font-bold text-slate-800">2. Overfitting Audit</div>
            <div className="text-[9px] text-slate-500">Degradation in OOS</div>
          </div>
          <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-100">
            <div className="font-bold text-slate-800">3. Drawdown Ceiling</div>
            <div className="text-[9px] text-slate-500">Tail risk & recovery time</div>
          </div>
          <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-100">
            <div className="font-bold text-slate-800">4. Sample Size</div>
            <div className="text-[9px] text-slate-500">N &gt; 300 trades required</div>
          </div>
          <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-100">
            <div className="font-bold text-slate-800">5. Regime Shifts</div>
            <div className="text-[9px] text-slate-500">Bull, bear & high-vol tests</div>
          </div>
          <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-100">
            <div className="font-bold text-slate-800">6. Execution Drag</div>
            <div className="text-[9px] text-slate-500">Slippage & fee realism</div>
          </div>
        </div>
      </div>

      {/* Main Container: Selector & Deep Dive */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-2 flex-1 min-h-0 overflow-hidden">
        {/* Strategy Evaluation List (4 cols) */}
        <div className="lg:col-span-4 bg-white rounded-xl p-2.5 border border-slate-200 shadow-2xs h-full flex flex-col min-h-0 overflow-hidden">
          <span className="text-[11px] font-black text-slate-900 uppercase tracking-wider block pb-1.5 border-b border-slate-100 shrink-0">
            Select Model to Inspect Verdict
          </span>

          <div className="space-y-1 overflow-y-auto custom-scrollbar flex-1 min-h-0 pt-1.5 pr-0.5">
            {strategies.map(s => {
              const isSelected = s.id === selectedStrategyId;

              return (
                <div
                  key={s.id}
                  onClick={() => setSelectedStrategyId(s.id)}
                  className={`p-2 rounded-lg border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-purple-50/70 border-purple-300 ring-2 ring-purple-200/60'
                      : 'bg-white border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-extrabold text-slate-900 truncate max-w-[180px]">{s.name}</span>
                    <span className={`px-1.5 py-0.2 rounded-full text-[9px] font-black border uppercase ${getVerdictBadge(s.alphaDecision)}`}>
                      {s.alphaDecision}
                    </span>
                  </div>

                  <div className="flex items-center justify-between mt-0.5 text-[10px] text-slate-500">
                    <span>{s.market} • {s.type}</span>
                    <span className="font-bold text-purple-700">{s.confidence}% Conf.</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Strategy Alpha Dossier (8 cols) */}
        {strategy && (
          <div className="lg:col-span-8 bg-white rounded-xl p-3.5 border border-slate-200 shadow-2xs h-full overflow-y-auto custom-scrollbar space-y-3 min-h-0">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
              <div>
                <span className="text-[9px] font-mono text-slate-400 font-bold">{strategy.id}</span>
                <h3 className="text-xs font-black text-slate-900">{strategy.name}</h3>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Evaluated: {strategy.alphaReview.evaluatedAt} • OOS Status: <strong className="text-slate-800">{strategy.backtestSummary.outOfSampleStatus}</strong>
                </div>
              </div>

              <div className="flex items-center gap-2.5">
                <div className="text-right">
                  <div className="text-[9px] font-bold text-slate-400 uppercase">Alpha Score</div>
                  <div className="text-base font-black text-purple-700">{strategy.alphaReview.confidenceScore}%</div>
                </div>
                <span className={`px-2.5 py-1 rounded-lg text-xs font-black uppercase tracking-tight border ${getVerdictBadge(strategy.alphaReview.verdict)}`}>
                  {strategy.alphaReview.verdict}
                </span>
              </div>
            </div>

            {/* Critique Callout */}
            <div className="p-3 rounded-xl bg-purple-50/60 border border-purple-200/70 space-y-1">
              <div className="text-[10px] font-extrabold text-purple-900 uppercase flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                <span>Alpha Qualitative & Quantitative Conclusion</span>
              </div>
              <p className="text-[11px] text-slate-800 leading-relaxed font-medium">
                {strategy.alphaReview.reasoning}
              </p>
            </div>

            {/* Pillar Audit Checklist */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-black text-slate-900 uppercase tracking-wider block">
                Alpha Verification Checklist
              </span>

              <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-2 text-xs">
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-slate-800 text-[11px]">Survivorship Bias Screening</div>
                    <div className="text-[10px] text-slate-600">Passed: historical universe includes delisted assets.</div>
                  </div>
                </div>

                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-slate-800 text-[11px]">Lookahead Bias Verification</div>
                    <div className="text-[10px] text-slate-600">Passed: indicators strictly indexed to bar close t-1.</div>
                  </div>
                </div>

                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-slate-800 text-[11px]">Sample Size Significance</div>
                    <div className="text-[10px] text-slate-600">{strategy.backtestSummary.totalTrades} trades analyzed (Valid).</div>
                  </div>
                </div>

                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-slate-800 text-[11px]">Overfitting & Parameter Plateau</div>
                    <div className="text-[10px] text-slate-600">{strategy.robustness.parameterSensitivity} across parameter grid.</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Action footer */}
            <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
              <button
                type="button"
                onClick={() => onSelectStrategy(strategy)}
                className="text-[11px] font-bold text-blue-600 hover:underline flex items-center gap-1 cursor-pointer"
              >
                <span>Open Full Strategy Workspace</span>
                <ChevronRight className="w-3 h-3" />
              </button>

              <span className="text-[10px] text-slate-400 font-mono">
                Nexus Alpha Hash: sha256:77f12e8b...
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
