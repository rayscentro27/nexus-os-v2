import React, { useState } from 'react';
import { 
  ShieldAlert, 
  AlertTriangle, 
  TrendingDown, 
  TrendingUp, 
  RotateCcw, 
  Zap, 
  CheckCircle2, 
  X, 
  Activity,
  DollarSign,
  ArrowRight
} from 'lucide-react';

interface ShockScenario {
  id: string;
  name: string;
  description: string;
  marketMove: string;
  impactPct: number;
  dollarImpact: number;
  varBreached: boolean;
  recommendedAction: string;
  category: 'EQUITIES' | 'MACRO' | 'CRYPTO' | 'COMMODITIES';
}

const SCENARIOS: ShockScenario[] = [
  {
    id: 'flash-crash',
    name: 'Flash Liquidity Squeeze (-7.0%)',
    description: 'Sudden high-frequency cascade across major ECNs with wide spreads and sharp orderbook withdrawal.',
    marketMove: 'SPX -7.0%, EUR/USD -1.2%, Volatility (VIX) +85%',
    impactPct: -3.85,
    dollarImpact: -19720.00,
    varBreached: true,
    recommendedAction: 'Trigger automatic volatility stop trail; widen slippage tolerance to 3.5 pips.',
    category: 'EQUITIES'
  },
  {
    id: 'fed-surprise',
    name: 'Fed Surprise Rate Hike (+50 bps)',
    description: 'Emergency FOMC policy announcement causing immediate US Dollar spike and bond yield surge.',
    marketMove: 'DXY +2.8%, EUR/USD -240 pips, 2Y Yield +42 bps',
    impactPct: -2.14,
    dollarImpact: -10960.00,
    varBreached: false,
    recommendedAction: 'Hedge USD long exposure; reduce Forex paper lot size by 40%.',
    category: 'MACRO'
  },
  {
    id: 'crypto-cascade',
    name: 'Crypto Liquidity De-peg (-15.0%)',
    description: 'Deleveraging liquidation wave on centralized exchanges affecting BTC/USDT and alt-betas.',
    marketMove: 'BTC/USDT -15.4%, ETH -18.2%, Funding Rate -0.15%',
    impactPct: -4.62,
    dollarImpact: -23680.00,
    varBreached: true,
    recommendedAction: 'Emergency kill switch for crypto ingestion feeds; flatten speculative crypto longs.',
    category: 'CRYPTO'
  },
  {
    id: 'tech-earnings',
    name: 'Mega-Cap Tech Earnings Meltdown (-8.5%)',
    description: 'Disappointing guidance across semiconductor bellwethers triggering semiconductor selloff.',
    marketMove: 'NVDA -11.2%, QQQ -4.8%, AI Momentum Basket -9.5%',
    impactPct: -3.20,
    dollarImpact: -16400.00,
    varBreached: true,
    recommendedAction: 'Rebalance portfolio weight towards defensive dividend and market-neutral pair strategies.',
    category: 'EQUITIES'
  },
  {
    id: 'oil-supply-shock',
    name: 'Stagflation Geopolitical Oil Shock (+12.0%)',
    description: 'Supply constraint announcement causing crude spikes and inflation expectations jump.',
    marketMove: 'WTI Crude +12.4%, Gold +3.2%, Consumer Staples -2.1%',
    impactPct: -1.45,
    dollarImpact: -7430.00,
    varBreached: false,
    recommendedAction: 'Deploy mean-reversion hedging algorithms; tighten profit targets on cyclic momentum.',
    category: 'COMMODITIES'
  }
];

interface PortfolioShockSimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentEquity?: number;
  openPositionsCount?: number;
  onApplyDefensiveStops?: () => void;
}

export const PortfolioShockSimulatorModal: React.FC<PortfolioShockSimulatorModalProps> = ({
  isOpen,
  onClose,
  currentEquity = 512480.00,
  openPositionsCount = 3,
  onApplyDefensiveStops
}) => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('flash-crash');
  const [isSimulated, setIsSimulated] = useState(false);

  if (!isOpen) return null;

  const scenario = SCENARIOS.find(s => s.id === selectedScenarioId) || SCENARIOS[0];
  const simulatedEquity = isSimulated ? currentEquity + scenario.dollarImpact : currentEquity;
  const simulatedDrawdown = isSimulated ? +(1.4 + Math.abs(scenario.impactPct)).toFixed(2) : 1.4;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[92vh] overflow-y-auto custom-scrollbar flex flex-col text-white">
        {/* Header */}
        <div className="px-5 py-3.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-black text-sm text-white tracking-wide">
                  PORTFOLIO STRESS TEST &amp; SHOCK SCENARIOS
                </h3>
                <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
                  REAL-TIME RISK ENGINE
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Simulate instantaneous historical market dislocations on currently open positions &amp; paper equity.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body Content */}
        <div className="p-5 space-y-4 text-xs">
          {/* Scenario Selector Chips */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-black uppercase text-slate-400">
              Select Stress Event Scenario:
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {SCENARIOS.map(s => {
                const isSelected = s.id === selectedScenarioId;
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => {
                      setSelectedScenarioId(s.id);
                      setIsSimulated(true);
                    }}
                    className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? 'bg-rose-950/40 border-rose-500 shadow-md ring-1 ring-rose-500/50'
                        : 'bg-slate-950/50 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between text-[9px] font-bold text-slate-400">
                        <span>{s.category}</span>
                        <span className="font-mono text-rose-400 font-extrabold">{s.impactPct}%</span>
                      </div>
                      <div className="font-bold text-slate-100 text-[11px] mt-0.5 leading-snug">
                        {s.name}
                      </div>
                    </div>
                    <div className="text-[9px] text-slate-400 mt-2 font-mono">
                      Estimated: <span className="text-rose-400 font-bold">${Math.abs(s.dollarImpact).toLocaleString()}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Scenario Impact Dossier */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
              <div>
                <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                  ACTIVE SHOCK SIMULATION
                </span>
                <h4 className="text-sm font-black text-white mt-1">
                  {scenario.name}
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {scenario.description}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsSimulated(prev => !prev)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-black flex items-center gap-1.5 transition-all cursor-pointer ${
                    isSimulated
                      ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-900/40'
                      : 'bg-blue-600 hover:bg-blue-500 text-white'
                  }`}
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>{isSimulated ? 'Shock Active (Live)' : 'Run Shock Simulation'}</span>
                </button>
                {isSimulated && (
                  <button
                    type="button"
                    onClick={() => setIsSimulated(false)}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Revert</span>
                  </button>
                )}
              </div>
            </div>

            {/* Impact Metric Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase font-bold">Simulated Equity:</span>
                <div className="text-base font-black text-white font-mono mt-0.5">
                  ${simulatedEquity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <div className={`text-[10px] font-bold ${isSimulated ? 'text-rose-400' : 'text-slate-500'}`}>
                  {isSimulated ? `${scenario.impactPct}% (${scenario.dollarImpact.toLocaleString()})` : 'Baseline'}
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase font-bold">Drawdown Level:</span>
                <div className={`text-base font-black font-mono mt-0.5 ${simulatedDrawdown >= 4.0 ? 'text-rose-400' : 'text-amber-400'}`}>
                  {simulatedDrawdown.toFixed(2)}%
                </div>
                <div className="text-[10px] text-slate-400">
                  Risk Gate Cap: <strong>4.00%</strong>
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase font-bold">99% VaR Status:</span>
                <div className="text-base font-black font-mono mt-0.5 flex items-center gap-1.5">
                  {scenario.varBreached && isSimulated ? (
                    <span className="text-rose-400 flex items-center gap-1">
                      <AlertTriangle className="w-4 h-4 text-rose-500" />
                      BREACHED
                    </span>
                  ) : (
                    <span className="text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      WITHIN LIMIT
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-400">
                  VaR Limit: $15,000 / day
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase font-bold">Positions At Risk:</span>
                <div className="text-base font-black text-white font-mono mt-0.5">
                  {openPositionsCount} Positions
                </div>
                <div className="text-[10px] text-slate-400">
                  EUR/USD, NVDA, BTC
                </div>
              </div>
            </div>

            {/* Defensive Action Recommendation */}
            <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400 shrink-0" />
                <div>
                  <span className="text-[10px] font-black uppercase text-amber-300">
                    Recommended Defensive Action:
                  </span>
                  <p className="text-[11px] text-slate-200 font-semibold">
                    {scenario.recommendedAction}
                  </p>
                </div>
              </div>

              {onApplyDefensiveStops && (
                <button
                  type="button"
                  onClick={() => {
                    onApplyDefensiveStops();
                    onClose();
                  }}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-slate-950 text-xs font-black transition-colors cursor-pointer flex items-center gap-1 shadow-md"
                >
                  <span>Apply Defensive Stops Now</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400 shrink-0">
          <span>Stochastic Monte Carlo &amp; Historical Volatility Mapping Active</span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold transition-colors cursor-pointer"
          >
            Close Stress Simulator
          </button>
        </div>
      </div>
    </div>
  );
};
