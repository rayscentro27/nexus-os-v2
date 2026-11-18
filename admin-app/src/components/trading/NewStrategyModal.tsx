import React, { useState } from 'react';
import { 
  X, 
  Sparkles, 
  Layers, 
  Sliders, 
  ShieldCheck, 
  Activity, 
  TrendingUp, 
  CheckCircle2, 
  HelpCircle,
  Play
} from 'lucide-react';
import { StrategyItem, StrategyStage, StrategyType, AlphaDecision } from '../../types';

interface NewStrategyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateStrategy: (strategy: StrategyItem) => void;
}

export const NewStrategyModal: React.FC<NewStrategyModalProps> = ({
  isOpen,
  onClose,
  onCreateStrategy,
}) => {
  const [name, setName] = useState('');
  const [market, setMarket] = useState<'Equities' | 'Crypto' | 'Forex' | 'Futures' | 'Options' | 'Multi-Asset'>('Equities');
  const [universe, setUniverse] = useState('S&P 500 High-Liquidity Stocks');
  const [timeframe, setTimeframe] = useState('15m');
  const [type, setType] = useState<StrategyType>('momentum');
  const [indicator, setIndicator] = useState('RSI (14) + EMA 21 Momentum Cross');
  const [filter, setFilter] = useState('200 SMA Bullish Regime Filter + ATR Gate');
  const [takeProfitPct, setTakeProfitPct] = useState(3.5);
  const [stopLossPct, setStopLossPct] = useState(1.2);
  const [trailingStop, setTrailingStop] = useState(true);
  const [stage, setStage] = useState<StrategyStage>('RESEARCHING');
  const [thesis, setThesis] = useState('Captures short-term momentum dislocations after clean regime pullbacks.');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const newId = `strat-${Date.now().toString().slice(-4)}`;
    const randomSharpe = +(1.6 + Math.random() * 0.9).toFixed(2);
    const randomWinRate = Math.floor(54 + Math.random() * 12);
    const randomDD = +(4.0 + Math.random() * 4.5).toFixed(1);

    const newStrategy: StrategyItem = {
      id: newId,
      name,
      market,
      universe,
      timeframe,
      type,
      stage,
      owner: { name: 'Alex Chen (Principal Quant)', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80' },
      createdDate: 'Today',
      lastTested: 'Pending Run',
      dataSource: market === 'Crypto' ? 'Binance Futures WS' : 'Polygon + CME Level 2',
      alphaDecision: 'RESEARCH_MORE',
      confidence: 78,
      evidenceQuality: 'Medium',
      riskLevel: stopLossPct <= 1.5 ? 'Low' : 'Medium',
      currentStatus: 'Active Testing',
      nextAction: 'Execute out-of-sample backtest & stress tests across 5-year tick regime',
      overview: {
        thesis,
        hypothesis: `If market trades above ${filter} and triggers ${indicator}, probability of hitting ${takeProfitPct}% exceeds historical baseline.`,
        marketAssumptions: [
          'High intraday liquidity eliminates slippage exceeding 1.5 bps',
          'Mean reversion cycles hold across 15m bar horizons'
        ],
        entryLogic: `${indicator} confirmed on bar close t-1`,
        exitLogic: `Fixed Take Profit: +${takeProfitPct}%, Stop Loss: -${stopLossPct}%`,
        stopLogic: trailingStop ? `Dynamic trailing stop pegged at 1.5x 14-period ATR` : `Fixed hard stop at -${stopLossPct}%`,
        positionSizingLogic: 'Volatility-adjusted fixed fractional (1.0% maximum portfolio risk per trade)',
        filters: [filter, 'No entries 15 minutes before or after FOMC/CPI releases'],
        timeHorizon: timeframe
      },
      researchEvidence: {
        supportingResearch: ['De Prado Advances in Financial Machine Learning (Ch. 3)'],
        contradictingEvidence: ['Regime decay during sustained 2022 high-inflation rate hikes'],
        sourceLinks: [{ title: 'Hypothesis Jupyter Notebook', url: '#', type: 'Notebook' }],
        dataQuality: 'Clean 15m tick bars with tick-level quote reconstruction',
        dateRange: '2021 - Present'
      },
      backtestSummary: {
        totalTrades: 342,
        winRate: randomWinRate,
        lossRate: 100 - randomWinRate,
        profitFactor: +(1.4 + Math.random() * 0.7).toFixed(2),
        expectancy: +(0.8 + Math.random() * 0.8).toFixed(2),
        averageWin: 850,
        averageLoss: 420,
        maxDrawdown: randomDD,
        volatility: 11.2,
        sharpe: randomSharpe,
        sortino: +(randomSharpe * 1.25).toFixed(2),
        bestPeriod: '+14.2% (Q2 2025)',
        worstPeriod: '-3.1% (Oct 2024)',
        testRange: '2022 - Present',
        outOfSampleStatus: 'Passed'
      },
      robustness: {
        walkForwardTested: true,
        outOfSampleTested: true,
        parameterSensitivity: 'Robust',
        regimeSensitivity: 'Multi-Regime',
        slippageAssumptions: '1.2 bps modeled',
        feeAssumptions: '$0.005 / share IBKR tiered',
        survivorshipBiasCheck: 'Passed',
        lookaheadBiasCheck: 'Passed',
        overfittingRisk: 'Low'
      },
      alphaReview: {
        verdict: 'RESEARCH_MORE',
        confidenceScore: 78,
        reasoning: 'Newly generated model requires baseline multi-regime out-of-sample forward verification.',
        keyRisks: ['Parameter overfitting', 'Slippage sensitivity'],
        recommendedParameters: ['Run 30-day paper test', 'Verify parameter sensitivity range'],
        evaluatedAt: new Date().toISOString()
      },
      versions: [
        {
          version: '1.0.0',
          date: 'Today',
          summary: 'Initial model parameters & rule formulation.',
          codeHash: `git:sha1:${Math.random().toString(36).substring(2, 10)}`,
          parametersChanged: ['Initial release'],
          backtestResult: {
            sharpe: randomSharpe,
            winRate: randomWinRate,
            profitFactor: 1.72,
            maxDrawdown: randomDD
          },
          alphaDecision: 'RESEARCH_MORE',
          reasoning: 'Synthesized model queued for quantitative stress testing.'
        }
      ]
    };

    onCreateStrategy(newStrategy);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/60 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-100 text-blue-700">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-black text-slate-900 tracking-tight flex items-center gap-2">
                <span>Quantitative Model Builder</span>
                <span className="text-[10px] font-extrabold px-2 py-0.2 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  Nexus Alpha DSL
                </span>
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Configure primary signals, risk guardrails, and entry filters before backtest qualification.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-4 text-xs">
          {/* Section 1: Identification & Market */}
          <div className="space-y-2">
            <span className="text-[11px] font-black text-slate-900 uppercase tracking-wider block">
              1. Model Identity & Target Universe
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Strategy Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Statistical Pairs Cointegration Arb"
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold focus:outline-hidden focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Market Class</label>
                <select
                  value={market}
                  onChange={e => setMarket(e.target.value as any)}
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold bg-white"
                >
                  <option value="Equities">Equities (US Equities & ETFs)</option>
                  <option value="Crypto">Crypto (Perpetual Futures & Spot)</option>
                  <option value="Forex">Forex (G10 FX Currency Pairs)</option>
                  <option value="Futures">Futures (Index & Commodity Futures)</option>
                  <option value="Options">Options (Volatility & Vol Surface)</option>
                  <option value="Multi-Asset">Multi-Asset Cross-Market</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Strategy Type</label>
                <select
                  value={type}
                  onChange={e => setType(e.target.value as StrategyType)}
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold bg-white capitalize"
                >
                  <option value="momentum">Momentum</option>
                  <option value="mean reversion">Mean Reversion</option>
                  <option value="volatility">Volatility Arbitrage</option>
                  <option value="pairs/statistical">Pairs / Statistical Arbitrage</option>
                  <option value="trend following">Trend Following</option>
                  <option value="event-driven">Event-Driven</option>
                  <option value="macro">Macro Regime Rotation</option>
                  <option value="breakout">Volatility Breakout</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Bar Timeframe</label>
                <select
                  value={timeframe}
                  onChange={e => setTimeframe(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold bg-white"
                >
                  <option value="1m">1 Minute High-Frequency</option>
                  <option value="5m">5 Minute Intraday</option>
                  <option value="15m">15 Minute (Recommended)</option>
                  <option value="1h">1 Hour Swing</option>
                  <option value="4h">4 Hour Intermediate</option>
                  <option value="Daily">Daily Macro</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Universe Tickers / Assets</label>
                <input
                  type="text"
                  value={universe}
                  onChange={e => setUniverse(e.target.value)}
                  placeholder="e.g. AAPL, MSFT, NVDA, GOOGL, AMZN"
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold focus:outline-hidden focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Alpha Rules & Signals */}
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <span className="text-[11px] font-black text-slate-900 uppercase tracking-wider block">
              2. Alpha Signal & Entry Logic
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Primary Entry Indicator</label>
                <input
                  type="text"
                  value={indicator}
                  onChange={e => setIndicator(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold focus:outline-hidden focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Regime / Trend Filter</label>
                <input
                  type="text"
                  value={filter}
                  onChange={e => setFilter(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold focus:outline-hidden focus:border-blue-500"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Core Hypothesis / Thesis</label>
                <textarea
                  rows={2}
                  value={thesis}
                  onChange={e => setThesis(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold focus:outline-hidden focus:border-blue-500 resize-none"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Risk & Position Sizing Guardrails */}
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <span className="text-[11px] font-black text-slate-900 uppercase tracking-wider block">
              3. Execution Guardrails & Risk Ceilings
            </span>
            <div className="grid grid-cols-3 gap-2">
              <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <label className="block text-[10px] font-bold text-slate-500 uppercase">Take Profit (%)</label>
                <input
                  type="number"
                  step={0.1}
                  value={takeProfitPct}
                  onChange={e => setTakeProfitPct(Number(e.target.value))}
                  className="w-full px-2 py-1 rounded-lg border border-slate-200 text-xs font-black text-emerald-600 bg-white"
                />
              </div>

              <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <label className="block text-[10px] font-bold text-slate-500 uppercase">Stop Loss (%)</label>
                <input
                  type="number"
                  step={0.1}
                  value={stopLossPct}
                  onChange={e => setStopLossPct(Number(e.target.value))}
                  className="w-full px-2 py-1 rounded-lg border border-slate-200 text-xs font-black text-rose-600 bg-white"
                />
              </div>

              <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 space-y-1 flex flex-col justify-between">
                <label className="block text-[10px] font-bold text-slate-500 uppercase">Trailing ATR</label>
                <label className="flex items-center gap-2 cursor-pointer mt-1">
                  <input
                    type="checkbox"
                    checked={trailingStop}
                    onChange={e => setTrailingStop(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-[11px] font-bold text-slate-800">1.5x ATR</span>
                </label>
              </div>
            </div>
          </div>

          {/* Section 4: Initial Stage */}
          <div className="p-3 rounded-xl bg-blue-50/60 border border-blue-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0" />
              <div>
                <span className="font-bold text-blue-950">Initial Stage Allocation:</span>
                <span className="text-blue-800 ml-1.5 font-semibold">
                  {stage} (Enforces Alpha review before capital allocation)
                </span>
              </div>
            </div>
            <select
              value={stage}
              onChange={e => setStage(e.target.value as StrategyStage)}
              className="px-2.5 py-1 rounded-lg border border-blue-300 text-xs font-bold text-blue-900 bg-white"
            >
              <option value="IDEA">IDEA</option>
              <option value="RESEARCHING">RESEARCHING</option>
              <option value="BACKTESTING">BACKTESTING</option>
            </select>
          </div>

          {/* Modal Actions */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-extrabold shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Instantiate & Add to Pipeline</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
