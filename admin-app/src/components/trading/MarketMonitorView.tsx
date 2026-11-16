import React, { useState } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Search, 
  Filter, 
  Activity, 
  Zap, 
  Clock, 
  Database,
  ArrowUpRight,
  ArrowDownRight,
  BarChart2
} from 'lucide-react';
import { MarketWatchItem } from '../../types';

interface MarketMonitorViewProps {
  watchlist: MarketWatchItem[];
  onOpenChart?: (symbol: string) => void;
  compactMode?: boolean;
}

export const MarketMonitorView: React.FC<MarketMonitorViewProps> = ({ 
  watchlist,
  onOpenChart,
  compactMode = true
}) => {
  const [selectedMarketTab, setSelectedMarketTab] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [volatilityFilter, setVolatilityFilter] = useState<string>('ALL');
  const [trendFilter, setTrendFilter] = useState<string>('ALL');

  const filteredItems = watchlist.filter(item => {
    const matchesMarket = selectedMarketTab === 'ALL' || item.market === selectedMarketTab;
    const matchesVol = volatilityFilter === 'ALL' || item.volatility === volatilityFilter;
    const matchesTrend = trendFilter === 'ALL' || item.trend === trendFilter;
    const matchesSearch = 
      item.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesMarket && matchesVol && matchesTrend && matchesSearch;
  });

  const MARKETS = ['ALL', 'Equities', 'ETFs', 'Crypto', 'Forex', 'Commodities'];

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden">
      {/* Top Banner & Filters */}
      <div className="bg-white rounded-xl p-2.5 border border-slate-200/90 shadow-2xs space-y-1.5 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-black text-slate-900">Multi-Asset Market Monitor & Watchlists</span>
            <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-blue-100 text-blue-800">
              {filteredItems.length} Monitored
            </span>
            <span className="text-[11px] text-slate-400 hidden md:inline">
              • Real-time tick ingestion, rolling volatility scoring, and quantitative signal saturation
            </span>
          </div>

          <div className="flex items-center gap-2 text-[10px] font-semibold text-slate-600 bg-slate-50 px-2 py-0.5 rounded-lg border border-slate-200 shrink-0">
            <Database className="w-3 h-3 text-blue-600" />
            <span>Feed: 22ms (Polygon + Binance + CME)</span>
          </div>
        </div>

        {/* Auto-Fit Market Breadth Telemetry Strip */}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(130px,1fr))] gap-1.5 pt-1 border-t border-slate-100 text-[11px]">
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Advancing:</span>
            <span className="font-black text-emerald-600">18 (+2.4%)</span>
          </div>
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Declining:</span>
            <span className="font-black text-rose-600">6 (-0.8%)</span>
          </div>
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Avg Spread:</span>
            <span className="font-extrabold text-slate-800">0.012%</span>
          </div>
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Vol Index:</span>
            <span className="font-extrabold text-blue-700">18.4 (Normal)</span>
          </div>
          <div className="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Tick Rate:</span>
            <span className="font-black text-slate-900">1.48M/m</span>
          </div>
        </div>

        {/* Market Class Tabs & Filters Row */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-1.5 pt-1.5 border-t border-slate-100 text-xs">
          {/* Market Class Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar pb-0.5 text-xs">
            {MARKETS.map(m => (
              <button
                key={m}
                type="button"
                onClick={() => setSelectedMarketTab(m)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                  selectedMarketTab === m
                    ? 'bg-blue-600 text-white shadow-2xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          {/* Filter Controls Row */}
          <div className="flex items-center gap-1.5 text-xs">
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search ticker..."
                className="pl-7 pr-2.5 py-1 rounded-lg border border-slate-200 text-xs focus:outline-hidden"
              />
            </div>

            <select
              value={volatilityFilter}
              onChange={e => setVolatilityFilter(e.target.value)}
              className="px-2 py-1 rounded-lg border border-slate-200 text-xs font-semibold bg-white"
            >
              <option value="ALL">All Volatility</option>
              <option value="Low">Low (&lt; 15%)</option>
              <option value="Medium">Medium (15-30%)</option>
              <option value="High">High (&gt; 30%)</option>
            </select>

            <select
              value={trendFilter}
              onChange={e => setTrendFilter(e.target.value)}
              className="px-2 py-1 rounded-lg border border-slate-200 text-xs font-semibold bg-white"
            >
              <option value="ALL">All Trends</option>
              <option value="Bullish">Bullish</option>
              <option value="Bearish">Bearish</option>
              <option value="Neutral">Neutral</option>
            </select>
          </div>
        </div>
      </div>

      {/* Watchlist Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex-1 min-h-0 flex flex-col">
        <div className="overflow-x-auto overflow-y-auto custom-scrollbar flex-1 min-h-0">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="sticky top-0 bg-slate-50 z-10">
              <tr className="border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                <th className="py-2 px-3">Instrument</th>
                <th className="py-2 px-2">Market</th>
                <th className="py-2 px-2">Price</th>
                <th className="py-2 px-2">24h Change</th>
                <th className="py-2 px-2">24h Volume</th>
                <th className="py-2 px-2">Volatility</th>
                <th className="py-2 px-2">Trend</th>
                <th className="py-2 px-2 text-center">Active Signals</th>
                <th className="py-2 px-2">Data Age</th>
                <th className="py-2 px-2 text-right">Trend Sparkline</th>
                <th className="py-2 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredItems.map(item => {
                const isPositive = item.change24h >= 0;

                return (
                  <tr key={item.symbol} className="hover:bg-slate-50/60 transition-colors">
                    {/* Instrument */}
                    <td className="py-2 px-3">
                      <div className="font-extrabold text-slate-900">{item.symbol}</div>
                      <div className="text-[10px] text-slate-500 truncate max-w-[140px]">{item.name}</div>
                    </td>

                    {/* Market */}
                    <td className="py-2 px-2">
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-100 text-slate-700">
                        {item.market}
                      </span>
                    </td>

                    {/* Price */}
                    <td className="py-2 px-2 font-extrabold text-slate-900">
                      ${item.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                    </td>

                    {/* Change */}
                    <td className="py-2 px-2">
                      <span className={`inline-flex items-center gap-0.5 font-bold ${
                        isPositive ? 'text-emerald-600' : 'text-rose-600'
                      }`}>
                        {isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                        <span>{isPositive ? '+' : ''}{item.change24h}%</span>
                      </span>
                    </td>

                    {/* Volume */}
                    <td className="py-2 px-2 font-medium text-slate-700">{item.volume}</td>

                    {/* Volatility */}
                    <td className="py-2 px-2">
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                        item.volatility === 'High' ? 'bg-amber-100 text-amber-800' :
                        item.volatility === 'Medium' ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {item.volatility}
                      </span>
                    </td>

                    {/* Trend */}
                    <td className="py-2 px-2 font-bold text-slate-800">{item.trend}</td>

                    {/* Active Signals */}
                    <td className="py-2 px-2 text-center">
                      <span className="px-1.5 py-0.2 rounded-full text-[9px] font-black bg-blue-50 text-blue-800 border border-blue-200">
                        {item.signalCount} Sig
                      </span>
                    </td>

                    {/* Data Age */}
                    <td className="py-2 px-2 text-[10px] text-slate-500 font-mono">
                      {item.dataAge}
                    </td>

                    {/* SVG Sparkline */}
                    <td className="py-2 px-2 text-right">
                      <div className="w-16 h-5 ml-auto inline-block">
                        <svg viewBox="0 0 80 24" className="w-full h-full overflow-visible">
                          <path
                            d={`M 0 ${20 - (item.sparkline[0] % 15)} ${item.sparkline.map((v, i) => `L ${i * 13} ${20 - (v % 18)}`).join(' ')}`}
                            fill="none"
                            stroke={isPositive ? '#10B981' : '#F43F5E'}
                            strokeWidth="1.8"
                            strokeLinecap="round"
                          />
                        </svg>
                      </div>
                    </td>

                    {/* Actions */}
                    <td className="py-2 px-3 text-right">
                      {onOpenChart ? (
                        <button
                          type="button"
                          onClick={() => onOpenChart(item.symbol)}
                          className="px-2 py-0.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 text-[10px] font-bold border border-blue-200 transition-colors inline-flex items-center gap-1 cursor-pointer"
                          title={`Open Live Chart & Replay for ${item.symbol}`}
                        >
                          <BarChart2 className="w-3 h-3 text-blue-600" />
                          <span>Chart</span>
                        </button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
