import React, { useState } from 'react';
import { 
  Sparkles, 
  AlertCircle, 
  ExternalLink, 
  Filter, 
  Calendar, 
  Activity, 
  Search, 
  Tag, 
  CheckCircle2, 
  TrendingUp,
  Globe2,
  Clock,
  AlertTriangle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { MarketIntelligenceItem, EconomicEventItem } from '../../types';
import { INITIAL_ECONOMIC_EVENTS } from '../../data/tradingEngineData';

interface MarketIntelligenceViewProps {
  intelligence: MarketIntelligenceItem[];
  economicEvents?: EconomicEventItem[];
  compactMode?: boolean;
}

export const MarketIntelligenceView: React.FC<MarketIntelligenceViewProps> = ({ 
  intelligence,
  economicEvents = INITIAL_ECONOMIC_EVENTS,
  compactMode = true 
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [materialityFilter, setMaterialityFilter] = useState<string>('ALL');
  const [eventPairFilter, setEventPairFilter] = useState<string>('ALL');
  const [isEcoCalendarExpanded, setIsEcoCalendarExpanded] = useState<boolean>(true);

  const filteredItems = intelligence.filter(item => {
    const matchesCat = selectedCategory === 'ALL' || item.category === selectedCategory;
    const matchesMat = materialityFilter === 'ALL' || item.materiality === materialityFilter;
    return matchesCat && matchesMat;
  });

  const filteredEvents = economicEvents.filter(ev => {
    if (eventPairFilter === 'ALL') return true;
    return ev.affectedPairs.some(p => p.toLowerCase().includes(eventPairFilter.toLowerCase()));
  });

  const CATEGORIES = ['ALL', 'Macro', 'Volatility', 'Regime Shift', 'Event-Driven', 'Earnings', 'Sentiment'];

  return (
    <div className="h-full flex flex-col min-h-0 space-y-2 overflow-hidden">
      {/* Top Banner */}
      <div className="bg-white rounded-xl p-2.5 border border-slate-200/90 shadow-2xs space-y-2 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-600" />
            <span className="text-xs font-black text-slate-900">Quantitative Market Intelligence & Alpha Feeds</span>
            <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-purple-100 text-purple-800">
              Nexus Research + Alpha
            </span>
            <span className="text-[11px] text-slate-400 hidden md:inline">
              • Macro catalysts, volatility regimes, economic calendar, and quantitative interpretations
            </span>
          </div>

          {/* Filter Materiality */}
          <div className="flex items-center gap-2">
            <select
              value={materialityFilter}
              onChange={e => setMaterialityFilter(e.target.value)}
              className="px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-semibold bg-white text-slate-700"
            >
              <option value="ALL">All Materiality</option>
              <option value="High">High Materiality Only</option>
              <option value="Medium">Medium Materiality</option>
              <option value="Low">Low Materiality</option>
            </select>
          </div>
        </div>

        {/* Categories Bar */}
        <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar pb-0.5 text-xs pt-1 border-t border-slate-100">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              type="button"
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer whitespace-nowrap text-xs ${
                selectedCategory === cat
                  ? 'bg-purple-600 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* COMPACT ECONOMIC EVENTS & AFFECTED PAIRS WIDGET */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden shrink-0">
        <div className="px-3 py-2 bg-slate-50/80 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
              <Calendar className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-black text-slate-900 tracking-tight">High-Impact Macroeconomic Calendar</span>
                <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 border border-amber-300">
                  Prototype Examples · Not Live Market Data
                </span>
              </div>
              <span className="text-[10px] text-slate-500">
                Central bank announcements & economic releases with affected currency pairs and modeled pip impact.
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Filter by Pair */}
            <div className="flex items-center gap-1 text-[11px]">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Pair:</span>
              <select
                value={eventPairFilter}
                onChange={e => setEventPairFilter(e.target.value)}
                className="px-2 py-0.5 rounded-md border border-slate-200 text-[11px] font-bold bg-white text-slate-700"
              >
                <option value="ALL">All Pairs</option>
                <option value="EUR/USD">EUR/USD</option>
                <option value="USD/JPY">USD/JPY</option>
                <option value="GBP/USD">GBP/USD</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => setIsEcoCalendarExpanded(!isEcoCalendarExpanded)}
              className="p-1 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-200/60 transition-colors"
              title={isEcoCalendarExpanded ? 'Collapse Calendar' : 'Expand Calendar'}
            >
              {isEcoCalendarExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Compact Table View */}
        {isEcoCalendarExpanded && (
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-[10px] font-black text-slate-400 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-1.5 px-3">Time & Currency</th>
                  <th className="py-1.5 px-3">Economic Event</th>
                  <th className="py-1.5 px-3 text-center">Impact</th>
                  <th className="py-1.5 px-3">Affected Pairs</th>
                  <th className="py-1.5 px-3 text-center">Consensus / Prev</th>
                  <th className="py-1.5 px-3 text-right">Pip Volatility Risk</th>
                  <th className="py-1.5 px-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-[11px]">
                {filteredEvents.map(ev => (
                  <tr key={ev.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2 px-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span className="text-base">{ev.flag}</span>
                        <div className="flex flex-col">
                          <span className="font-extrabold text-slate-900">{ev.country}</span>
                          <span className="text-[10px] text-slate-500">{ev.timeEst}</span>
                        </div>
                      </div>
                    </td>

                    <td className="py-2 px-3 font-bold text-slate-900 max-w-[260px]">
                      {ev.eventName}
                    </td>

                    <td className="py-2 px-3 text-center whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase ${
                        ev.impact === 'Critical' ? 'bg-rose-100 text-rose-800 border border-rose-200' :
                        ev.impact === 'High' ? 'bg-amber-100 text-amber-800 border border-amber-200' :
                        'bg-blue-100 text-blue-800 border border-blue-200'
                      }`}>
                        {ev.impact}
                      </span>
                    </td>

                    <td className="py-2 px-3">
                      <div className="flex items-center gap-1 flex-wrap">
                        {ev.affectedPairs.map(pair => (
                          <span
                            key={pair}
                            className={`px-1.5 py-0.2 rounded font-mono font-bold text-[10px] border ${
                              pair === 'EUR/USD' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                              pair === 'USD/JPY' ? 'bg-blue-50 text-blue-800 border-blue-200' :
                              'bg-slate-100 text-slate-700 border-slate-200'
                            }`}
                          >
                            {pair}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="py-2 px-3 text-center whitespace-nowrap">
                      <span className="font-bold text-slate-800">{ev.consensus}</span>
                      <span className="text-[10px] text-slate-400"> (Prev: {ev.previous})</span>
                      {ev.actual && (
                        <div className="text-[10px] text-emerald-700 font-extrabold">Act: {ev.actual}</div>
                      )}
                    </td>

                    <td className="py-2 px-3 text-right whitespace-nowrap font-bold text-purple-700">
                      {ev.volatilityEstimate}
                    </td>

                    <td className="py-2 px-3 text-center whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded-md text-[9px] font-extrabold ${
                        ev.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800 animate-pulse' :
                        ev.status === 'UPCOMING' ? 'bg-slate-100 text-slate-700' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {ev.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Intelligence Items in CSS Grid Auto-Fit Container */}
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-2 pr-0.5">
        {filteredItems.map(item => (
          <div
            key={item.id}
            className="bg-white rounded-xl p-3 border border-slate-200/90 shadow-2xs space-y-2 hover:border-purple-300 transition-all flex flex-col justify-between"
          >
            <div className="space-y-1.5">
              {/* Header: Title, Source, Materiality */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-1.5">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-1.5 py-0.2 rounded-md text-[9px] font-extrabold bg-purple-50 text-purple-700 border border-purple-200">
                      {item.category}
                    </span>
                    <span className="text-[10px] font-semibold text-slate-500">
                      Source: <strong className="text-slate-700">{item.source}</strong> • {item.timestamp}
                    </span>
                  </div>
                  <h3 className="text-xs font-black text-slate-900 leading-snug">{item.title}</h3>
                </div>

                <div className="flex items-center gap-1.5 self-start">
                  <span className={`px-2 py-0.2 rounded-full text-[9px] font-extrabold uppercase ${
                    item.materiality === 'High' ? 'bg-rose-100 text-rose-800' :
                    item.materiality === 'Medium' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {item.materiality} Materiality
                  </span>
                  <span className="text-[10px] font-bold text-purple-700 bg-purple-50 px-1.5 py-0.2 rounded-md border border-purple-200">
                    {item.confidence}% Conf.
                  </span>
                </div>
              </div>

              {/* Affected Symbols & Related Strategy */}
              <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                <span className="text-slate-400 font-medium">Affected:</span>
                <div className="flex flex-wrap gap-1">
                  {item.affectedSymbols.map(sym => (
                    <span
                      key={sym}
                      className={`px-1.5 py-0.2 rounded font-mono font-bold text-[10px] ${
                        sym.includes('/') ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      {sym}
                    </span>
                  ))}
                </div>

                <span className="text-slate-300 mx-0.5">•</span>
                <span className="text-slate-400 font-medium">Strategy:</span>
                <span className="font-bold text-slate-800">{item.relatedStrategy}</span>
              </div>
            </div>

            {/* Alpha Interpretation & Actionable Recommendation */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1.5 border-t border-slate-100 text-xs mt-2">
              <div className="p-2 rounded-lg bg-purple-50/50 border border-purple-100 space-y-0.5">
                <div className="text-[9px] font-bold text-purple-900 uppercase flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-purple-600" />
                  <span>Alpha Quantitative Interpretation</span>
                </div>
                <p className="text-slate-800 text-[11px] font-medium leading-relaxed">{item.alphaInterpretation}</p>
              </div>

              <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 space-y-0.5">
                <div className="text-[9px] font-bold text-slate-700 uppercase flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-blue-600" />
                  <span>Actionable Recommendation</span>
                </div>
                <p className="text-slate-800 text-[11px] font-medium leading-relaxed">{item.recommendation}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
