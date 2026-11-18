import React, { useState, useMemo } from 'react';
import {
  Trophy,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ArrowRight,
  Search,
  DollarSign,
  Eye,
  FileText,
  Calendar,
  Layers,
  ShieldAlert,
  Table,
  LayoutGrid,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  Globe2,
  Sparkles,
  Info,
  Scale
} from 'lucide-react';
import { TournamentRound, TournamentEntry, TournamentDecision, StrategyItem } from '../../types';

interface TradingTournamentViewProps {
  round: TournamentRound;
  entries: TournamentEntry[];
  strategies: StrategyItem[];
  onSelectStrategy: (strategy: StrategyItem) => void;
  onOpenBacktestReport: (reportId: string, strategy?: StrategyItem) => void;
  onPromoteToRiskReview?: (strategyId: string) => void;
  compactMode?: boolean;
}

export const TradingTournamentView: React.FC<TradingTournamentViewProps> = ({
  round,
  entries,
  strategies,
  onSelectStrategy,
  onOpenBacktestReport,
  onPromoteToRiskReview,
  compactMode = true,
}) => {
  const [selectedDivision, setSelectedDivision] = useState<string>('ALL');
  const [filterDecision, setFilterDecision] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [expandedEntryId, setExpandedEntryId] = useState<string | null>('entry-fx-01');

  // Filter entries
  const filteredEntries = useMemo(() => {
    return entries.filter(e => {
      const entryDivision = e.division || (e.market === 'Forex' ? 'Forex' : e.market === 'Crypto' ? 'Crypto' : 'Equities & Multi-Asset');
      const matchesDivision = selectedDivision === 'ALL' || entryDivision === selectedDivision;
      const matchesDecision = filterDecision === 'ALL' || e.decision === filterDecision;
      const matchesSearch =
        e.strategyName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.market.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (e.currencyPair && e.currencyPair.toLowerCase().includes(searchQuery.toLowerCase())) ||
        e.type.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesDivision && matchesDecision && matchesSearch;
    });
  }, [entries, selectedDivision, filterDecision, searchQuery]);

  // Group entries by division for clean grouped views
  const groupedEntries = useMemo(() => {
    const groups: { [key: string]: TournamentEntry[] } = {
      'Forex': [],
      'Equities & Multi-Asset': [],
      'Crypto': []
    };

    filteredEntries.forEach(entry => {
      const div = entry.division || (entry.market === 'Forex' ? 'Forex' : entry.market === 'Crypto' ? 'Crypto' : 'Equities & Multi-Asset');
      if (!groups[div]) {
        groups[div] = [];
      }
      groups[div].push(entry);
    });

    return groups;
  }, [filteredEntries]);

  // Division Benchmark Meta information
  const divisionMeta: Record<string, {
    title: string;
    benchmarkName: string;
    benchmarkReturn: string;
    sharedDataFeed: string;
    riskCeiling: string;
    spreadFriction: string;
    description: string;
    badgeColor: string;
  }> = {
    'Forex': {
      title: 'Forex Division (G10 Currencies)',
      benchmarkName: 'USD DXY Currency Benchmark (+3.4%)',
      benchmarkReturn: '+3.4%',
      sharedDataFeed: 'EBS / Currenex Institutional FX L2 Feed',
      riskCeiling: '3.5% Max Drawdown Ceiling',
      spreadFriction: '0.8 – 1.2 pips modeled spread · $4.50/lot commission',
      description: 'Standardized Forex showcase. Evaluated exclusively against G10 currency benchmarks under institutional ECN spread friction, pip risk controls, and session liquidity windows.',
      badgeColor: 'bg-emerald-50 text-emerald-800 border-emerald-300'
    },
    'Equities & Multi-Asset': {
      title: 'Equities & Multi-Asset Division',
      benchmarkName: 'S&P 500 Index Benchmark (+24.2%)',
      benchmarkReturn: '+24.2%',
      sharedDataFeed: 'Polygon.io + FactSet Institutional Tick Feeds',
      riskCeiling: '4.0% Max Drawdown Ceiling',
      spreadFriction: '1.5 – 2.0 bps modeled slippage · $0.005/share',
      description: 'Equities, Pairs, and Macro models evaluated against broad equity and fixed-income benchmarks under identical liquidity constraints.',
      badgeColor: 'bg-blue-50 text-blue-800 border-blue-300'
    },
    'Crypto': {
      title: 'Crypto Division (Digital Assets)',
      benchmarkName: 'BTC / ETH Equal-Weight Benchmark (+22.1%)',
      benchmarkReturn: '+22.1%',
      sharedDataFeed: 'Binance / Coinbase Pro L3 Stream',
      riskCeiling: '4.0% Max Drawdown Ceiling',
      spreadFriction: '4.0 bps taker fee · 3.0 bps modeled slippage',
      description: 'Microstructure and orderflow models evaluated against crypto market cap weighted baskets.',
      badgeColor: 'bg-amber-50 text-amber-800 border-amber-300'
    }
  };

  const getDecisionBadge = (decision: TournamentDecision) => {
    switch (decision) {
      case 'ADVANCE':
        return {
          label: 'ADVANCE',
          fullLabel: 'ADVANCE TO RISK REVIEW',
          bg: 'bg-emerald-50 text-emerald-800 border-emerald-300',
          dot: 'bg-emerald-500',
          icon: CheckCircle2,
          hint: 'Met Sharpe & consistency targets; eligible for Dual Risk Review'
        };
      case 'CONTINUE_TESTING':
        return {
          label: 'CONTINUE TESTING',
          fullLabel: 'CONTINUE TESTING',
          bg: 'bg-blue-50 text-blue-800 border-blue-300',
          dot: 'bg-blue-500',
          icon: Clock,
          hint: 'Awaiting Trade Count Quota (> 300) or Regime Stress Tests'
        };
      case 'ELIMINATE':
        return {
          label: 'ELIMINATE',
          fullLabel: 'ELIMINATED',
          bg: 'bg-rose-50 text-rose-800 border-rose-300',
          dot: 'bg-rose-500',
          icon: XCircle,
          hint: 'Eliminated: Risk Ceiling Breach or Negative Expectancy'
        };
      default:
        return {
          label: decision,
          fullLabel: decision,
          bg: 'bg-slate-50 text-slate-700 border-slate-300',
          dot: 'bg-slate-400',
          icon: Info,
          hint: ''
        };
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedEntryId(prev => (prev === id ? null : id));
  };

  return (
    <div className="h-full flex flex-col min-h-0 space-y-2 overflow-hidden">
      {/* Top Banner: Tournament Metadata & Controlled Simulation Sandbox Notice */}
      <div className="bg-white rounded-xl p-3 border border-slate-200/90 shadow-2xs space-y-2 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 flex items-center justify-center shrink-0 shadow-xs">
              <Trophy className="w-4 h-4 text-amber-600" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-xs font-black text-slate-900 tracking-tight">{round.name}</h2>
                <span className="text-[10px] font-extrabold px-2 py-0.2 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                  Active Tournament
                </span>
                <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.2 rounded-md border border-slate-200">
                  {entries.length} Contenders ({entries.filter(e => e.market === 'Forex').length} Forex)
                </span>
                <span className="text-[10px] font-black text-purple-700 bg-purple-50 px-2 py-0.2 rounded-md border border-purple-200">
                  [SIMULATED WALK-FORWARD]
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                Fair, standardized quantitative showcase. Models compete strictly within asset divisions under shared historical data, friction assumptions, and risk ceilings.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[10px] font-semibold text-slate-700 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200 shrink-0">
            <span className="text-emerald-700 font-bold">{round.advancedCount} Advancing</span>
            <span className="text-slate-300">•</span>
            <span className="text-blue-700 font-bold">{round.testingCount} In Testing</span>
            <span className="text-slate-300">•</span>
            <span className="text-rose-700 font-bold">{round.eliminatedCount} Eliminated</span>
          </div>
        </div>

        {/* 4 Standardized Shared Conditions (Same Simulated Conditions Requirement) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-1.5 pt-1.5 border-t border-slate-100 text-[10px]">
          <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
            <div className="text-slate-400 font-bold uppercase text-[9px] flex items-center gap-1">
              <Calendar className="w-3 h-3 text-slate-500" />
              <span>1. Standard Test Window</span>
            </div>
            <div className="font-extrabold text-slate-900 mt-0.5">{round.testWindow}</div>
            <div className="text-[9px] text-slate-500">Fixed 30-month walk-forward</div>
          </div>

          <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
            <div className="text-slate-400 font-bold uppercase text-[9px] flex items-center gap-1">
              <DollarSign className="w-3 h-3 text-slate-500" />
              <span>2. Shared Starting Capital</span>
            </div>
            <div className="font-extrabold text-slate-900 mt-0.5">${round.startingCapital.toLocaleString()} Simulated</div>
            <div className="text-[9px] text-slate-500">Uniform cash base for all models</div>
          </div>

          <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
            <div className="text-slate-400 font-bold uppercase text-[9px] flex items-center gap-1">
              <Layers className="w-3 h-3 text-slate-500" />
              <span>3. Benchmark Market Data</span>
            </div>
            <div className="font-extrabold text-slate-900 mt-0.5 truncate">{round.marketDataSet}</div>
            <div className="text-[9px] text-slate-500">Cleaned L2 tick history & EBS FX feeds</div>
          </div>

          <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
            <div className="text-slate-400 font-bold uppercase text-[9px] flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 text-slate-500" />
              <span>4. Shared Risk Ceilings</span>
            </div>
            <div className="font-extrabold text-rose-700 mt-0.5">
              FX Max DD: 3.5% · Equity DD: 4.0%
            </div>
            <div className="text-[9px] text-slate-500">Max risk: 1.0% per trade across all groups</div>
          </div>
        </div>

        {/* Division Selector & Filter Bar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2 pt-1 border-t border-slate-100 text-[11px]">
          {/* Division Selector Tabs */}
          <div className="flex items-center gap-1 flex-wrap">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1 hidden sm:inline">Division:</span>
            <button
              type="button"
              onClick={() => setSelectedDivision('ALL')}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                selectedDivision === 'ALL'
                  ? 'bg-slate-900 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All Divisions ({entries.length})
            </button>
            <button
              type="button"
              onClick={() => setSelectedDivision('Forex')}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1 ${
                selectedDivision === 'Forex'
                  ? 'bg-emerald-600 text-white shadow-2xs'
                  : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200'
              }`}
            >
              <Globe2 className="w-3 h-3" />
              <span>Forex Division ({entries.filter(e => e.market === 'Forex').length})</span>
            </button>
            <button
              type="button"
              onClick={() => setSelectedDivision('Equities & Multi-Asset')}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                selectedDivision === 'Equities & Multi-Asset'
                  ? 'bg-blue-600 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Equities & Multi-Asset ({entries.filter(e => e.division === 'Equities & Multi-Asset').length})
            </button>
            <button
              type="button"
              onClick={() => setSelectedDivision('Crypto')}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                selectedDivision === 'Crypto'
                  ? 'bg-amber-600 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Crypto ({entries.filter(e => e.division === 'Crypto').length})
            </button>
          </div>

          {/* Right Tools: Decision Filter, Search, View Mode Toggle */}
          <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
            {/* Decision Filter Dropdown */}
            <select
              value={filterDecision}
              onChange={e => setFilterDecision(e.target.value)}
              className="px-2 py-1 rounded-lg border border-slate-200 text-xs font-semibold bg-white text-slate-700"
            >
              <option value="ALL">All Outcomes</option>
              <option value="ADVANCE">Advance Only ({round.advancedCount})</option>
              <option value="CONTINUE_TESTING">Continue Testing ({round.testingCount})</option>
              <option value="ELIMINATE">Eliminated ({round.eliminatedCount})</option>
            </select>

            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search model, pair, author..."
                className="pl-7 pr-2.5 py-1 rounded-lg border border-slate-200 text-xs focus:outline-hidden w-full sm:w-48"
              />
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200 shrink-0">
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`p-1 rounded-md text-xs font-bold transition-all cursor-pointer flex items-center gap-1 ${
                  viewMode === 'table' ? 'bg-white text-blue-600 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
                }`}
                title="Tabular Leaderboard View"
              >
                <Table className="w-3.5 h-3.5" />
                <span className="hidden md:inline text-[11px]">Table</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                className={`p-1 rounded-md text-xs font-bold transition-all cursor-pointer flex items-center gap-1 ${
                  viewMode === 'cards' ? 'bg-white text-blue-600 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
                }`}
                title="Detailed Cards View"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span className="hidden md:inline text-[11px]">Cards</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar space-y-3 pr-0.5">
        {/* If viewing all or specific division, render group sections with fair benchmarks */}
        {Object.entries(groupedEntries).map(([groupName, groupList]) => {
          if (groupList.length === 0) return null;
          const meta = divisionMeta[groupName] || {
            title: `${groupName} Division`,
            benchmarkName: 'Standard Benchmark',
            benchmarkReturn: 'N/A',
            sharedDataFeed: 'Standard Feeds',
            riskCeiling: '4.0% Max DD',
            spreadFriction: 'Modeled slippage',
            description: '',
            badgeColor: 'bg-slate-50 text-slate-700 border-slate-300'
          };

          return (
            <div key={groupName} className="space-y-1.5">
              {/* Division Header & Fair Benchmark Banner */}
              <div className="bg-white rounded-xl p-2.5 border border-slate-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-black border ${meta.badgeColor}`}>
                      {meta.title}
                    </span>
                    <span className="text-[11px] font-bold text-slate-700">
                      Benchmark: <strong className="text-purple-700">{meta.benchmarkName}</strong>
                    </span>
                    <span className="text-[10px] text-slate-400">
                      • {groupList.length} Models Competing
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {meta.description}
                  </p>
                </div>

                <div className="flex items-center gap-2 text-[10px] text-slate-600 shrink-0 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
                  <span><strong>Friction:</strong> {meta.spreadFriction}</span>
                  <span className="text-slate-300">•</span>
                  <span className="text-rose-700 font-bold">{meta.riskCeiling}</span>
                </div>
              </div>

              {/* TABULAR LEADERBOARD VIEW */}
              {viewMode === 'table' ? (
                <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
                  <div className="overflow-x-auto custom-scrollbar">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-50/90 border-b border-slate-200 text-[10px] font-black text-slate-500 uppercase tracking-wider">
                          <th className="py-2.5 px-3 w-12 text-center">Rank</th>
                          <th className="py-2.5 px-3 min-w-[200px]">Strategy & Author</th>
                          <th className="py-2.5 px-3 text-right">Return (% & $)</th>
                          <th className="py-2.5 px-3 text-right">Max Drawdown</th>
                          <th className="py-2.5 px-3 text-center">Consistency</th>
                          <th className="py-2.5 px-3 text-center">Trade Count</th>
                          <th className="py-2.5 px-3 text-right">Est. Costs</th>
                          <th className="py-2.5 px-3 text-center">Sharpe / Win</th>
                          <th className="py-2.5 px-3 text-center min-w-[150px]">Tournament Decision</th>
                          <th className="py-2.5 px-3 text-right w-24">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {groupList.map(entry => {
                          const badge = getDecisionBadge(entry.decision);
                          const Icon = badge.icon;
                          const matchingStrat = strategies.find(s => s.id === entry.strategyId);
                          const isExpanded = expandedEntryId === entry.id;
                          const isForex = entry.market === 'Forex';
                          const ddCeiling = isForex ? 3.5 : round.sharedRiskLimits.maxDrawdownPct;
                          const isDdBreached = entry.maxDrawdownPct > ddCeiling;

                          return (
                            <React.Fragment key={entry.id}>
                              <tr
                                onClick={() => toggleExpand(entry.id)}
                                className={`hover:bg-blue-50/40 transition-colors cursor-pointer ${
                                  isExpanded ? 'bg-blue-50/30' : ''
                                }`}
                              >
                                {/* Rank */}
                                <td className="py-2.5 px-3 text-center">
                                  <div className="flex flex-col items-center">
                                    <span className={`w-6 h-6 rounded-md font-black text-xs flex items-center justify-center border ${
                                      entry.divisionRank === 1 ? 'bg-amber-100 text-amber-900 border-amber-300' :
                                      entry.divisionRank === 2 ? 'bg-slate-100 text-slate-700 border-slate-300' :
                                      entry.divisionRank === 3 ? 'bg-amber-50 text-amber-800 border-amber-200' :
                                      'bg-slate-50 text-slate-500 border-slate-200'
                                    }`}>
                                      #{entry.divisionRank || entry.rank}
                                    </span>
                                    <span className="text-[8px] text-slate-400 mt-0.5">#{entry.rank} Ovr</span>
                                  </div>
                                </td>

                                {/* Strategy & Author */}
                                <td className="py-2.5 px-3">
                                  <div className="space-y-0.5">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="font-black text-slate-900 hover:text-blue-600 transition-colors">
                                        {entry.strategyName}
                                      </span>
                                      <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                                        {entry.market}
                                      </span>
                                      {entry.currencyPair && (
                                        <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                                          {entry.currencyPair}
                                        </span>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                                      <img src={entry.authorAvatar} alt={entry.author} className="w-3.5 h-3.5 rounded-full object-cover" />
                                      <span>{entry.author}</span>
                                      <span>•</span>
                                      <span className="font-mono text-slate-600 text-[9px]">{entry.strategyId}</span>
                                      {entry.tradingSession && (
                                        <>
                                          <span>•</span>
                                          <span className="text-slate-600">{entry.tradingSession}</span>
                                        </>
                                      )}
                                    </div>
                                  </div>
                                </td>

                                {/* Return */}
                                <td className="py-2.5 px-3 text-right">
                                  <div className={`font-black text-xs ${entry.returnPct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                    {entry.returnPct > 0 ? `+${entry.returnPct}%` : `${entry.returnPct}%`}
                                  </div>
                                  <div className="text-[10px] text-slate-500 font-medium">
                                    {entry.returnDollar >= 0 ? `+$${entry.returnDollar.toLocaleString()}` : `-$${Math.abs(entry.returnDollar).toLocaleString()}`}
                                  </div>
                                </td>

                                {/* Max Drawdown */}
                                <td className="py-2.5 px-3 text-right">
                                  <div className={`font-black text-xs ${isDdBreached ? 'text-rose-600 font-extrabold' : 'text-slate-900'}`}>
                                    {entry.maxDrawdownPct.toFixed(2)}%
                                  </div>
                                  <div className="text-[9px]">
                                    {isDdBreached ? (
                                      <span className="text-rose-600 font-bold">Breach ({ddCeiling}%)</span>
                                    ) : (
                                      <span className="text-slate-400">Safe (&lt; {ddCeiling}%)</span>
                                    )}
                                  </div>
                                </td>

                                {/* Consistency Score */}
                                <td className="py-2.5 px-3 text-center">
                                  <div className="font-black text-blue-700 text-xs">
                                    {entry.consistencyScorePct}%
                                  </div>
                                  <div className="text-[9px] text-slate-400">Pos. Weeks</div>
                                </td>

                                {/* Trade Count */}
                                <td className="py-2.5 px-3 text-center">
                                  <div className={`font-black text-xs ${entry.tradeCount < 300 ? 'text-amber-700' : 'text-slate-900'}`}>
                                    {entry.tradeCount}
                                  </div>
                                  <div className="text-[9px]">
                                    {entry.tradeCount >= 300 ? (
                                      <span className="text-emerald-600 font-semibold">Valid (&gt;300)</span>
                                    ) : (
                                      <span className="text-amber-600 font-semibold">Quota Deficit</span>
                                    )}
                                  </div>
                                </td>

                                {/* Estimated Costs */}
                                <td className="py-2.5 px-3 text-right">
                                  <div className="font-bold text-slate-800 text-xs">
                                    ${entry.estimatedCosts.toLocaleString()}
                                  </div>
                                  <div className="text-[9px] text-slate-400">
                                    {isForex ? 'Spread + Lots' : 'Fees + Drag'}
                                  </div>
                                </td>

                                {/* Sharpe / Win Rate */}
                                <td className="py-2.5 px-3 text-center">
                                  <div className="font-black text-purple-700 text-xs">
                                    {entry.sharpe.toFixed(2)}
                                  </div>
                                  <div className="text-[9px] text-slate-500">
                                    Win: {entry.winRate}%
                                  </div>
                                </td>

                                {/* Decision Badge & Next Gate */}
                                <td className="py-2.5 px-3 text-center">
                                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-black border ${badge.bg}`}>
                                    <Icon className="w-2.5 h-2.5" />
                                    <span>{badge.label}</span>
                                  </span>
                                  <div className="text-[8px] text-slate-500 truncate max-w-[140px] mx-auto mt-0.5" title={entry.nextGate}>
                                    {entry.nextGate}
                                  </div>
                                </td>

                                {/* Action Buttons */}
                                <td className="py-2.5 px-3 text-right">
                                  <div className="flex items-center justify-end gap-1" onClick={e => e.stopPropagation()}>
                                    <button
                                      type="button"
                                      onClick={() => onOpenBacktestReport(entry.backtestReportId, matchingStrat)}
                                      className="p-1 rounded-md bg-white hover:bg-slate-100 text-blue-700 border border-slate-200 transition-colors"
                                      title="View Walk-Forward Backtest Report"
                                    >
                                      <FileText className="w-3.5 h-3.5" />
                                    </button>
                                    {matchingStrat && (
                                      <button
                                        type="button"
                                        onClick={() => onSelectStrategy(matchingStrat)}
                                        className="p-1 rounded-md bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 transition-colors"
                                        title="Inspect Model Details"
                                      >
                                        <Eye className="w-3.5 h-3.5" />
                                      </button>
                                    )}
                                    <button
                                      type="button"
                                      onClick={() => toggleExpand(entry.id)}
                                      className="p-1 rounded-md bg-white hover:bg-slate-100 text-slate-400 border border-slate-200 transition-colors"
                                      title="Toggle Audit Details"
                                    >
                                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                    </button>
                                  </div>
                                </td>
                              </tr>

                              {/* EXPANDABLE ROW AUDIT & FOREX DETAILS */}
                              {isExpanded && (
                                <tr className="bg-slate-50/70 border-b border-slate-200">
                                  <td colSpan={10} className="py-2.5 px-4 text-xs">
                                    <div className="space-y-2">
                                      {/* Reason & Evidence Box */}
                                      <div className="p-2.5 rounded-lg bg-white border border-slate-200 space-y-1.5">
                                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                                          <div className="font-extrabold text-slate-900 flex items-center gap-1.5 text-xs">
                                            <span className="text-slate-400 uppercase tracking-wider text-[9px]">Decision Reason:</span>
                                            <span className={entry.decision === 'ELIMINATE' ? 'text-rose-700' : 'text-slate-800'}>
                                              {entry.decisionReason}
                                            </span>
                                          </div>
                                          <span className="text-[10px] text-purple-700 font-bold bg-purple-50 px-2 py-0.2 rounded border border-purple-200">
                                            [SIMULATED PAPER RESULT]
                                          </span>
                                        </div>

                                        <div className="text-[11px] text-slate-600 bg-slate-50/70 p-2 rounded-md border border-slate-100">
                                          <strong className="text-slate-700">Evidence Audit: </strong>
                                          {entry.evidenceNotes}
                                        </div>

                                        {/* Forex-Specific Metric Breakdown Bar */}
                                        {isForex && (
                                          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-1.5 pt-1 text-[10px]">
                                            <div className="p-1.5 rounded bg-emerald-50/60 border border-emerald-200">
                                              <span className="text-emerald-900 font-bold block text-[9px] uppercase">Currency Pair:</span>
                                              <span className="font-extrabold text-slate-900">{entry.currencyPair || 'EUR/USD'}</span>
                                            </div>
                                            <div className="p-1.5 rounded bg-emerald-50/60 border border-emerald-200">
                                              <span className="text-emerald-900 font-bold block text-[9px] uppercase">Active Session:</span>
                                              <span className="font-extrabold text-slate-900">{entry.tradingSession || 'London/NY Overlap'}</span>
                                            </div>
                                            <div className="p-1.5 rounded bg-emerald-50/60 border border-emerald-200">
                                              <span className="text-emerald-900 font-bold block text-[9px] uppercase">Pip Metrics:</span>
                                              <span className="font-extrabold text-emerald-700">
                                                {entry.pipMetrics ? `+${entry.pipMetrics.pipGain} pips · max DD ${entry.pipMetrics.maxPipDrawdown} pips` : '+485 pips'}
                                              </span>
                                            </div>
                                            <div className="p-1.5 rounded bg-emerald-50/60 border border-emerald-200">
                                              <span className="text-emerald-900 font-bold block text-[9px] uppercase">Modeled Spread:</span>
                                              <span className="font-extrabold text-slate-900">
                                                {entry.pipMetrics?.avgSpreadPips ? `${entry.pipMetrics.avgSpreadPips} pips` : '0.8 pips (EBS L2)'}
                                              </span>
                                            </div>
                                            <div className="p-1.5 rounded bg-emerald-50/60 border border-emerald-200">
                                              <span className="text-emerald-900 font-bold block text-[9px] uppercase">Execution Costs:</span>
                                              <span className="font-extrabold text-slate-900">${entry.estimatedCosts} ($4.50/lot)</span>
                                            </div>
                                            <div className="p-1.5 rounded bg-emerald-50/60 border border-emerald-200">
                                              <span className="text-emerald-900 font-bold block text-[9px] uppercase">Risk Limit:</span>
                                              <span className="font-extrabold text-slate-900">1.0% Equity ($1k/trade)</span>
                                            </div>
                                          </div>
                                        )}

                                        {/* Gate Handoff Line */}
                                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 border-t border-slate-100 text-[10px]">
                                          <div className="flex items-center gap-1.5 text-slate-700">
                                            <span className="font-bold text-slate-400 uppercase text-[9px]">Next Stage Gate:</span>
                                            <strong className="text-purple-700">{entry.nextGate}</strong>
                                            <span className="text-slate-400 hidden sm:inline">(Live execution disabled; paper gateway only)</span>
                                          </div>

                                          <div className="flex items-center gap-2">
                                            {entry.decision === 'ADVANCE' && onPromoteToRiskReview && (
                                              <button
                                                type="button"
                                                onClick={() => onPromoteToRiskReview(entry.strategyId)}
                                                className="px-2.5 py-1 rounded-md bg-purple-600 hover:bg-purple-700 text-white text-[10px] font-black flex items-center gap-1 transition-all cursor-pointer shadow-2xs"
                                              >
                                                <span>Promote to Risk Review Gate</span>
                                                <ArrowRight className="w-3 h-3" />
                                              </button>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                /* DETAILED CARDS VIEW */
                <div className="space-y-2">
                  {groupList.map(entry => {
                    const badge = getDecisionBadge(entry.decision);
                    const Icon = badge.icon;
                    const matchingStrat = strategies.find(s => s.id === entry.strategyId);
                    const isForex = entry.market === 'Forex';
                    const ddCeiling = isForex ? 3.5 : round.sharedRiskLimits.maxDrawdownPct;

                    return (
                      <div
                        key={entry.id}
                        className="bg-white rounded-xl p-3 border border-slate-200 shadow-2xs hover:border-blue-400 transition-all space-y-2.5"
                      >
                        {/* Row Top Lockup: Rank, Name, Author, Decision Badge */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2.5">
                            <div className={`w-8 h-8 rounded-lg font-black text-xs flex flex-col items-center justify-center shrink-0 border ${
                              entry.divisionRank === 1 ? 'bg-amber-100 text-amber-800 border-amber-300' :
                              entry.divisionRank === 2 ? 'bg-slate-100 text-slate-700 border-slate-300' :
                              entry.divisionRank === 3 ? 'bg-amber-50 text-amber-900 border-amber-200' :
                              'bg-slate-50 text-slate-400 border-slate-200'
                            }`}>
                              <span>#{entry.divisionRank || entry.rank}</span>
                              <span className="text-[7px] text-slate-400 font-bold uppercase">Div</span>
                            </div>

                            <div>
                              <div className="flex items-center gap-2 flex-wrap">
                                <h3
                                  className="text-xs font-black text-slate-900 hover:text-blue-600 transition-colors cursor-pointer"
                                  onClick={() => matchingStrat && onSelectStrategy(matchingStrat)}
                                >
                                  {entry.strategyName}
                                </h3>
                                <span className="text-[10px] font-bold text-slate-600 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">
                                  {entry.market} • {entry.type}
                                </span>
                                {entry.currencyPair && (
                                  <span className="text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 px-1.5 py-0.2 rounded border border-emerald-200">
                                    {entry.currencyPair}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mt-0.5">
                                <img src={entry.authorAvatar} alt={entry.author} className="w-3.5 h-3.5 rounded-full object-cover" />
                                <span>{entry.author}</span>
                                <span>•</span>
                                <span>ID: <code className="font-mono text-slate-600">{entry.strategyId}</code></span>
                                {entry.tradingSession && (
                                  <>
                                    <span>•</span>
                                    <span className="text-slate-600">{entry.tradingSession}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
                            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black border ${badge.bg}`}>
                              <Icon className="w-3 h-3" />
                              <span>{badge.label}</span>
                            </span>
                          </div>
                        </div>

                        {/* 5 Core Leaderboard Quant Metrics */}
                        <div className="grid grid-cols-2 sm:grid-cols-6 gap-1.5 text-center text-xs">
                          <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                            <div className="text-[9px] text-slate-400 font-bold uppercase">Return (% & $)</div>
                            <div className={`font-black mt-0.5 ${entry.returnPct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                              {entry.returnPct > 0 ? `+${entry.returnPct}%` : `${entry.returnPct}%`}
                            </div>
                            <div className="text-[9px] text-slate-500 font-medium">
                              {entry.returnDollar >= 0 ? `+$${entry.returnDollar.toLocaleString()}` : `-$${Math.abs(entry.returnDollar).toLocaleString()}`}
                            </div>
                          </div>

                          <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                            <div className="text-[9px] text-slate-400 font-bold uppercase">Max Drawdown</div>
                            <div className={`font-black mt-0.5 ${entry.maxDrawdownPct > ddCeiling ? 'text-rose-600 font-extrabold' : 'text-slate-900'}`}>
                              {entry.maxDrawdownPct.toFixed(2)}%
                            </div>
                            <div className="text-[9px] text-slate-400">
                              {entry.maxDrawdownPct <= ddCeiling ? `Safe (Ceiling ${ddCeiling}%)` : 'Ceiling Breach!'}
                            </div>
                          </div>

                          <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                            <div className="text-[9px] text-slate-400 font-bold uppercase">Consistency</div>
                            <div className="font-black text-blue-700 mt-0.5">{entry.consistencyScorePct}%</div>
                            <div className="text-[9px] text-slate-500">Positive Weeks</div>
                          </div>

                          <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                            <div className="text-[9px] text-slate-400 font-bold uppercase">Trade Count</div>
                            <div className={`font-black mt-0.5 ${entry.tradeCount < 300 ? 'text-amber-700' : 'text-slate-900'}`}>
                              {entry.tradeCount}
                            </div>
                            <div className="text-[9px] text-slate-500">{entry.tradeCount >= 300 ? 'Valid Sample' : 'Needs > 300'}</div>
                          </div>

                          <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                            <div className="text-[9px] text-slate-400 font-bold uppercase">Estimated Costs</div>
                            <div className="font-black text-slate-700 mt-0.5">${entry.estimatedCosts.toLocaleString()}</div>
                            <div className="text-[9px] text-slate-500">{isForex ? 'Spread + Lots' : 'Fees + Drag'}</div>
                          </div>

                          <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                            <div className="text-[9px] text-slate-400 font-bold uppercase">Sharpe Ratio</div>
                            <div className="font-black text-purple-700 mt-0.5">{entry.sharpe.toFixed(2)}</div>
                            <div className="text-[9px] text-slate-500">Win: {entry.winRate}%</div>
                          </div>
                        </div>

                        {/* Tournament Decision Reason & Evidence Box */}
                        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 text-xs space-y-1">
                          <div className="flex items-start justify-between gap-2">
                            <div className="space-y-0.5">
                              <div className="font-extrabold text-slate-900 flex items-center gap-1.5 text-[11px]">
                                <span className="text-slate-400 uppercase tracking-wider text-[9px]">Decision Reason:</span>
                                <span>{entry.decisionReason}</span>
                              </div>
                              <div className="text-[10px] text-slate-600">
                                <strong className="text-slate-700">Evidence Audit: </strong>
                                {entry.evidenceNotes}
                              </div>
                            </div>
                          </div>

                          {/* Gate Handoff Line */}
                          <div className="pt-1.5 border-t border-slate-200/70 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-[10px]">
                            <div className="flex items-center gap-1.5 text-slate-700">
                              <span className="font-bold text-slate-500 uppercase text-[9px]">Next Gate:</span>
                              <strong className="text-purple-700">{entry.nextGate}</strong>
                              <span className="text-slate-400">(Live trading strictly prohibited; paper gateway only)</span>
                            </div>

                            <div className="flex items-center gap-1.5 shrink-0">
                              <button
                                type="button"
                                onClick={() => onOpenBacktestReport(entry.backtestReportId, matchingStrat)}
                                className="px-2.5 py-0.5 rounded-md bg-white hover:bg-slate-100 text-blue-700 text-[10px] font-bold border border-slate-200 flex items-center gap-1 transition-all cursor-pointer shadow-2xs"
                              >
                                <FileText className="w-3 h-3" />
                                <span>Supporting Report</span>
                              </button>

                              {matchingStrat && (
                                <button
                                  type="button"
                                  onClick={() => onSelectStrategy(matchingStrat)}
                                  className="px-2.5 py-0.5 rounded-md bg-white hover:bg-slate-100 text-slate-700 text-[10px] font-bold border border-slate-200 flex items-center gap-1 transition-all cursor-pointer shadow-2xs"
                                >
                                  <Eye className="w-3 h-3" />
                                  <span>Inspect Model</span>
                                </button>
                              )}

                              {entry.decision === 'ADVANCE' && onPromoteToRiskReview && (
                                <button
                                  type="button"
                                  onClick={() => onPromoteToRiskReview(entry.strategyId)}
                                  className="px-2.5 py-0.5 rounded-md bg-purple-600 hover:bg-purple-700 text-white text-[10px] font-black flex items-center gap-1 transition-all cursor-pointer shadow-2xs"
                                  title="Promote to Risk Review Gate (Pre-requisite for Paper Trading)"
                                >
                                  <span>Send to Risk Review</span>
                                  <ArrowRight className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
