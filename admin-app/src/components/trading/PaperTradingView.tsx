import React, { useState } from 'react';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  ArrowUpRight, 
  ArrowDownRight, 
  ShieldCheck, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Search, 
  Filter, 
  X,
  ExternalLink,
  Sliders,
  BarChart2
} from 'lucide-react';
import { PaperPosition, PaperOrder } from '../../types';

interface PaperTradingViewProps {
  positions: PaperPosition[];
  orders: PaperOrder[];
  onClosePosition: (positionId: string) => void;
  onOpenChart?: (symbol: string) => void;
  compactMode?: boolean;
}

export const PaperTradingView: React.FC<PaperTradingViewProps> = ({
  positions,
  orders,
  onClosePosition,
  onOpenChart,
  compactMode = true,
}) => {
  const [activeTab, setActiveTab] = useState<'positions' | 'orders'>('positions');
  const [orderFilter, setOrderFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [closingPosId, setClosingPosId] = useState<string | null>(null);

  // Account balances (Simulated)
  const simulatedBuyingPower = 425800.00;
  const simulatedCash = 284500.00;
  const simulatedEquity = 512480.00;
  const dayPnl = 4280.50;
  const dayPnlPct = 0.84;
  const totalPnl = 34120.00;
  const totalPnlPct = 7.13;

  const filteredOrders = orders.filter(o => {
    const matchesFilter = orderFilter === 'ALL' || o.status === orderFilter;
    const matchesSearch = 
      o.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.strategyName.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="h-full flex flex-col min-h-0 space-y-1.5 overflow-hidden">
      {/* Sleek Integrated Paper Account Telemetry Bar */}
      <div className="bg-white rounded-xl px-3 py-1.5 border border-slate-200/90 shadow-2xs flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-blue-100 text-blue-700 border border-blue-200">
            SIMULATED
          </span>
          <span className="text-xs font-black text-slate-900">Nexus Paper Sim</span>
          <span className="text-[10px] text-slate-400 hidden sm:inline">•</span>
          <span className="text-[10px] font-semibold text-slate-500 hidden sm:inline">Alpaca Gateway (34ms)</span>
          <span className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded font-bold border border-emerald-200 hidden md:inline">
            Zero Real Risk
          </span>
        </div>

        {/* 5 Account Balances in CSS Grid Auto-Fit Container */}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(125px,1fr))] gap-1.5 text-xs flex-1 max-w-3xl">
          <div className="px-2 py-0.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Equity:</span>
            <span className="font-black text-slate-900">${simulatedEquity.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
          </div>

          <div className="px-2 py-0.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between gap-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Buying Pwr:</span>
            <span className="font-extrabold text-slate-800">${simulatedBuyingPower.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
          </div>

          <div className="px-2 py-0.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between gap-1 hidden lg:flex">
            <span className="text-slate-400 text-[10px] font-bold uppercase">Cash:</span>
            <span className="font-extrabold text-slate-800">${simulatedCash.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
          </div>

          <div className="px-2 py-0.5 rounded-lg bg-emerald-50/70 border border-emerald-200 flex items-center justify-between gap-1">
            <span className="text-emerald-700 text-[10px] font-bold uppercase">Day P/L:</span>
            <span className="font-black text-emerald-600">+${dayPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
          </div>

          <div className="px-2 py-0.5 rounded-lg bg-emerald-50/70 border border-emerald-200 flex items-center justify-between gap-1 hidden sm:flex">
            <span className="text-emerald-700 text-[10px] font-bold uppercase">Total P/L:</span>
            <span className="font-black text-emerald-600">+${totalPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
          </div>
        </div>
      </div>

      {/* Main Tabs Container: Open Positions vs Order History */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex-1 min-h-0 flex flex-col">
        {/* Navigation Tabs */}
        <div className="px-3.5 py-2 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/60 shrink-0">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('positions')}
              className={`px-3 py-1 rounded-lg text-xs font-extrabold transition-all cursor-pointer ${
                activeTab === 'positions'
                  ? 'bg-blue-600 text-white shadow-2xs'
                  : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
              }`}
            >
              Open Positions ({positions.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('orders')}
              className={`px-3 py-1 rounded-lg text-xs font-extrabold transition-all cursor-pointer ${
                activeTab === 'orders'
                  ? 'bg-blue-600 text-white shadow-2xs'
                  : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
              }`}
            >
              Order History ({orders.length})
            </button>
          </div>

          {activeTab === 'orders' && (
            <div className="flex items-center gap-2 text-xs">
              <div className="relative">
                <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Search orders..."
                  className="pl-7 pr-2.5 py-1 rounded-lg border border-slate-200 text-xs focus:outline-hidden"
                />
              </div>

              <select
                value={orderFilter}
                onChange={e => setOrderFilter(e.target.value)}
                className="px-2 py-1 rounded-lg border border-slate-200 text-xs font-semibold bg-white"
              >
                <option value="ALL">All Statuses</option>
                <option value="FILLED">Filled</option>
                <option value="PENDING">Pending</option>
                <option value="CANCELLED">Cancelled</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>
          )}
        </div>

        {/* TAB CONTENT: OPEN POSITIONS */}
        {activeTab === 'positions' ? (
          <div className="overflow-x-auto overflow-y-auto custom-scrollbar flex-1 min-h-0">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 z-10">
                <tr className="border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-3">Instrument</th>
                  <th className="py-2.5 px-2">Side & Qty</th>
                  <th className="py-2.5 px-2">Entry Price</th>
                  <th className="py-2.5 px-2">Current Price</th>
                  <th className="py-2.5 px-2">Unrealized P/L</th>
                  <th className="py-2.5 px-2">Stop / Target</th>
                  <th className="py-2.5 px-2">Strategy</th>
                  <th className="py-2.5 px-2">Risk Amount</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {positions.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-xs text-slate-400">
                      No open paper positions currently active.
                    </td>
                  </tr>
                ) : (
                  positions.map(pos => {
                    const isLong = pos.side === 'LONG';
                    const isProfitable = pos.unrealizedPnl >= 0;

                    return (
                      <tr key={pos.id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-2.5 px-3">
                          <div className="font-extrabold text-slate-900 flex items-center gap-1.5">
                            <span>{pos.symbol}</span>
                            <span className="px-1 py-0.2 rounded text-[8px] font-black bg-blue-100 text-blue-700">PAPER</span>
                          </div>
                          <div className="text-[10px] text-slate-500 truncate max-w-[140px]">{pos.name}</div>
                        </td>

                        <td className="py-2.5 px-2">
                          <span className={`px-1.5 py-0.2 rounded text-[10px] font-black ${
                            isLong ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}>
                            {pos.side}
                          </span>
                          <span className="font-bold text-slate-800 ml-1.5">{pos.quantity}</span>
                        </td>

                        <td className="py-2.5 px-2 font-semibold text-slate-700">
                          ${pos.entryPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </td>

                        <td className="py-2.5 px-2 font-bold text-slate-900">
                          ${pos.currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </td>

                        <td className="py-2.5 px-2">
                          <div className={`font-black flex items-center gap-1 ${
                            isProfitable ? 'text-emerald-600' : 'text-rose-600'
                          }`}>
                            {isProfitable ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                            <span>{isProfitable ? '+' : ''}${pos.unrealizedPnl.toFixed(2)}</span>
                          </div>
                          <div className={`text-[10px] font-semibold ${isProfitable ? 'text-emerald-700' : 'text-rose-700'}`}>
                            {isProfitable ? '+' : ''}{pos.unrealizedPnlPct.toFixed(2)}%
                          </div>
                        </td>

                        <td className="py-2.5 px-2 text-[10px]">
                          <div className="flex items-center justify-between gap-1">
                            <span className="text-rose-600 font-semibold">SL: ${pos.stopPrice.toFixed(2)}</span>
                            <span className="text-emerald-600 font-semibold">TP: ${pos.targetPrice.toFixed(2)}</span>
                          </div>
                          {/* Mini Visual Bracket Progress Bar */}
                          <div className="w-24 h-1.5 bg-slate-200 rounded-full overflow-hidden flex mt-1 relative" title={`Entry: $${pos.entryPrice} · Current: $${pos.currentPrice}`}>
                            <div className="bg-rose-400 h-full" style={{ width: '35%' }} />
                            <div className="bg-emerald-400 h-full" style={{ width: '65%' }} />
                            <div 
                              className="absolute top-0 bottom-0 w-1.5 bg-blue-600 rounded-full shadow-xs" 
                              style={{ 
                                left: `${Math.max(5, Math.min(95, isLong ? 40 + pos.unrealizedPnlPct * 8 : 40 - pos.unrealizedPnlPct * 8))}%` 
                              }} 
                            />
                          </div>
                        </td>

                        <td className="py-2.5 px-2">
                          <div className="font-semibold text-slate-800 truncate max-w-[160px]">{pos.strategyName}</div>
                          <div className="text-[10px] text-slate-400">{pos.openedAt}</div>
                        </td>

                        <td className="py-2.5 px-2 font-semibold text-slate-700">
                          ${pos.riskAmount.toFixed(2)}
                        </td>

                        <td className="py-2.5 px-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {onOpenChart && (
                              <button
                                type="button"
                                onClick={() => onOpenChart(pos.symbol)}
                                className="px-2 py-0.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 text-[10px] font-bold border border-blue-200 transition-colors flex items-center gap-1 cursor-pointer"
                                title="Open Live Chart with Stop Loss and Take Profit brackets"
                              >
                                <BarChart2 className="w-3 h-3 text-blue-600" />
                                <span>Chart &amp; SL/TP</span>
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => onClosePosition(pos.id)}
                              className="px-2 py-0.5 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 text-[10px] font-bold border border-rose-200 transition-colors cursor-pointer"
                            >
                              Close (Sim)
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        ) : (
          /* TAB CONTENT: ORDER HISTORY */
          <div className="overflow-x-auto overflow-y-auto custom-scrollbar flex-1 min-h-0">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 z-10">
                <tr className="border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-3">Order ID & Symbol</th>
                  <th className="py-2.5 px-2">Side & Type</th>
                  <th className="py-2.5 px-2">Quantity</th>
                  <th className="py-2.5 px-2">Fill Price</th>
                  <th className="py-2.5 px-2">Status</th>
                  <th className="py-2.5 px-2">Submitted / Filled</th>
                  <th className="py-2.5 px-2">Strategy</th>
                  <th className="py-2.5 px-3">Operational Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-xs text-slate-400">
                      No paper orders matching your filter.
                    </td>
                  </tr>
                ) : (
                  filteredOrders.map(order => (
                    <tr key={order.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-2.5 px-3">
                        <div className="font-extrabold text-slate-900 flex items-center gap-1.5">
                          <span>{order.symbol}</span>
                          <span className="px-1 py-0.2 rounded text-[8px] font-black bg-blue-100 text-blue-700">PAPER</span>
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">{order.id}</div>
                      </td>

                      <td className="py-2.5 px-2">
                        <span className={`px-1.5 py-0.2 rounded text-[10px] font-black ${
                          order.side === 'BUY' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                        }`}>
                          {order.side}
                        </span>
                        <span className="text-slate-500 text-[10px] font-bold ml-1.5">{order.type}</span>
                      </td>

                      <td className="py-2.5 px-2 font-bold text-slate-800">{order.quantity}</td>

                      <td className="py-2.5 px-2 font-semibold text-slate-900">
                        {order.fillPrice ? `$${order.fillPrice.toFixed(2)}` : '—'}
                      </td>

                      <td className="py-2.5 px-2">
                        <span className={`px-2 py-0.2 rounded-full text-[10px] font-extrabold ${
                          order.status === 'FILLED' ? 'bg-emerald-100 text-emerald-800' :
                          order.status === 'PENDING' ? 'bg-blue-100 text-blue-800' :
                          order.status === 'CANCELLED' ? 'bg-slate-100 text-slate-600' :
                          'bg-rose-100 text-rose-800'
                        }`}>
                          {order.status}
                        </span>
                      </td>

                      <td className="py-2.5 px-2 text-[10px] text-slate-600">
                        <div>Sub: {order.submittedAt}</div>
                        {order.filledAt && <div className="text-slate-400">Fill: {order.filledAt}</div>}
                      </td>

                      <td className="py-2.5 px-2 font-medium text-slate-800 truncate max-w-[150px]">
                        {order.strategyName}
                      </td>

                      <td className="py-2.5 px-3 text-[10px] text-slate-600 leading-snug">
                        {order.reason}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
