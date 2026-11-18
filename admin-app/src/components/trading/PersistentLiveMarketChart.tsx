import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  ReferenceDot,
  ReferenceArea
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  ShieldAlert,
  Sliders,
  Maximize2,
  Minimize2,
  ChevronDown,
  ChevronUp,
  Play,
  Pause,
  Zap,
  CheckCircle2,
  RotateCcw,
  Target,
  DollarSign,
  Radio,
  Eye,
  SlidersHorizontal,
  X,
  Crosshair,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Info,
  Clock,
  Layers
} from 'lucide-react';
import { PaperPosition } from '../../types';

export interface PersistentLiveMarketChartProps {
  activePositions?: PaperPosition[];
  selectedSymbol?: string;
  onSelectSymbol?: (symbol: string) => void;
  onClosePosition?: (positionId: string) => void;
  onOpenFullCharts?: () => void;
  defaultExpanded?: boolean;
}

interface PriceTick {
  time: string;
  price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  vwap: number;
  isEntryBar?: boolean;
}

interface SymbolSpec {
  symbol: string;
  name: string;
  assetClass: 'Forex' | 'Equities' | 'Crypto';
  decimals: number;
  multiplier: number;
  basePrice: number;
  volatility: number;
  spreadPips: number;
  defaultSLOffset: number;
  defaultTPOffset: number;
}

const SYMBOL_SPECS: Record<string, SymbolSpec> = {
  'EUR/USD': {
    symbol: 'EUR/USD',
    name: 'Euro / US Dollar',
    assetClass: 'Forex',
    decimals: 4,
    multiplier: 10000,
    basePrice: 1.0864,
    volatility: 0.00015,
    spreadPips: 0.8,
    defaultSLOffset: 0.0025,
    defaultTPOffset: 0.0055
  },
  'NVDA': {
    symbol: 'NVDA',
    name: 'NVIDIA Corporation',
    assetClass: 'Equities',
    decimals: 2,
    multiplier: 100,
    basePrice: 126.85,
    volatility: 0.18,
    spreadPips: 0.04,
    defaultSLOffset: 3.20,
    defaultTPOffset: 7.50
  },
  'BTC/USDT': {
    symbol: 'BTC/USDT',
    name: 'Bitcoin Perpetual',
    assetClass: 'Crypto',
    decimals: 2,
    multiplier: 1,
    basePrice: 64450.00,
    volatility: 45.0,
    spreadPips: 2.5,
    defaultSLOffset: 950.00,
    defaultTPOffset: 2200.00
  },
  'QQQ': {
    symbol: 'QQQ',
    name: 'Invesco QQQ ETF',
    assetClass: 'Equities',
    decimals: 2,
    multiplier: 100,
    basePrice: 484.20,
    volatility: 0.45,
    spreadPips: 0.06,
    defaultSLOffset: 4.50,
    defaultTPOffset: 10.00
  },
  'ETH/USDT': {
    symbol: 'ETH/USDT',
    name: 'Ethereum Perpetual',
    assetClass: 'Crypto',
    decimals: 2,
    multiplier: 1,
    basePrice: 2707.25,
    volatility: 4.8,
    spreadPips: 0.45,
    defaultSLOffset: 45.00,
    defaultTPOffset: 110.00
  }
};

// Generate realistic starting timeline ticks
const generateInitialTicks = (spec: SymbolSpec, count: number = 36): PriceTick[] => {
  const ticks: PriceTick[] = [];
  let current = spec.basePrice;
  const now = new Date();
  let vwapSum = 0;
  let volSum = 0;

  for (let i = count - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 3000);
    const timeStr = t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const delta = (Math.random() - 0.48) * spec.volatility;
    current = +(current + delta).toFixed(spec.decimals);
    const high = +(current + Math.random() * spec.volatility * 0.8).toFixed(spec.decimals);
    const low = +(current - Math.random() * spec.volatility * 0.8).toFixed(spec.decimals);
    const vol = Math.floor(Math.random() * 250 + 50);

    vwapSum += current * vol;
    volSum += vol;
    const vwap = +(vwapSum / volSum).toFixed(spec.decimals);

    ticks.push({
      time: timeStr,
      price: current,
      open: +(current - delta * 0.5).toFixed(spec.decimals),
      high,
      low,
      close: current,
      volume: vol,
      vwap,
      isEntryBar: i === Math.floor(count * 0.6) // Entry bar marked ~60% along timeline
    });
  }
  return ticks;
};

interface HoveredMarkerDossier {
  type: 'ENTRY' | 'STOP_LOSS' | 'TAKE_PROFIT' | 'RUNNER_TP' | 'CURRENT_PRICE';
  x: number;
  y: number;
  title: string;
  price: number;
  badge: string;
  badgeBg: string;
  badgeText: string;
  deltaPips: number;
  deltaDollars: number;
  rrImpact?: string;
  orderId: string;
  latency: string;
  notes: string;
}

export const PersistentLiveMarketChart: React.FC<PersistentLiveMarketChartProps> = ({
  activePositions = [],
  selectedSymbol: propSymbol,
  onSelectSymbol,
  onClosePosition,
  onOpenFullCharts,
  defaultExpanded = true
}) => {
  // Active instrument selection
  const [internalSymbol, setInternalSymbol] = useState<string>('EUR/USD');
  const activeSymbol = propSymbol || internalSymbol;
  const spec = SYMBOL_SPECS[activeSymbol] || SYMBOL_SPECS['EUR/USD'];

  // Match corresponding paper position if one exists in state
  const activePosition = useMemo(() => {
    return activePositions.find(p => p.symbol === activeSymbol) || null;
  }, [activePositions, activeSymbol]);

  // UI States
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);
  const [isLiveStreaming, setIsLiveStreaming] = useState<boolean>(true);
  const [timeframe, setTimeframe] = useState<'1s' | '5s' | '1m' | '5m'>('1s');
  const [chartMode, setChartMode] = useState<'area' | 'line'>('area');
  const [showVolume, setShowVolume] = useState<boolean>(true);
  const [actionToast, setActionToast] = useState<string | null>(null);

  // Hovered Trade Marker Dossier for Framer-Motion Floating Tooltip
  const [hoveredMarker, setHoveredMarker] = useState<HoveredMarkerDossier | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Price Tick Series State
  const [ticks, setTicks] = useState<PriceTick[]>(() => generateInitialTicks(spec));
  const [tickFlash, setTickFlash] = useState<'up' | 'down' | null>(null);
  const [tickCount, setTickCount] = useState<number>(0);

  // Position & Bracket Levels
  const defaultEntry = activePosition?.entryPrice ?? spec.basePrice;
  const defaultSide = activePosition?.side ?? 'LONG';
  
  const [entryPrice, setEntryPrice] = useState<number>(defaultEntry);
  const [stopLoss, setStopLoss] = useState<number>(
    activePosition?.stopPrice ?? +(defaultEntry - (defaultSide === 'LONG' ? spec.defaultSLOffset : -spec.defaultSLOffset)).toFixed(spec.decimals)
  );
  const [takeProfit, setTakeProfit] = useState<number>(
    activePosition?.targetPrice ?? +(defaultEntry + (defaultSide === 'LONG' ? spec.defaultTPOffset : -spec.defaultTPOffset)).toFixed(spec.decimals)
  );
  const [tradeSide, setTradeSide] = useState<'LONG' | 'SHORT'>(defaultSide);
  const [tradeQuantity, setTradeQuantity] = useState<number>(activePosition?.quantity ?? (spec.assetClass === 'Forex' ? 100000 : 100));

  // Runner Target (TP2)
  const runnerTakeProfit = useMemo(() => {
    const isLong = tradeSide === 'LONG';
    const delta = Math.abs(takeProfit - entryPrice) * 1.55;
    return isLong 
      ? +(entryPrice + delta).toFixed(spec.decimals) 
      : +(entryPrice - delta).toFixed(spec.decimals);
  }, [entryPrice, takeProfit, tradeSide, spec.decimals]);

  // Sync state when activePosition or symbol changes
  useEffect(() => {
    const freshSpec = SYMBOL_SPECS[activeSymbol] || SYMBOL_SPECS['EUR/USD'];
    setTicks(generateInitialTicks(freshSpec));

    if (activePosition) {
      setEntryPrice(activePosition.entryPrice);
      setStopLoss(activePosition.stopPrice);
      setTakeProfit(activePosition.targetPrice);
      setTradeSide(activePosition.side);
      setTradeQuantity(activePosition.quantity);
    } else {
      const base = freshSpec.basePrice;
      setEntryPrice(base);
      setStopLoss(+(base - freshSpec.defaultSLOffset).toFixed(freshSpec.decimals));
      setTakeProfit(+(base + freshSpec.defaultTPOffset).toFixed(freshSpec.decimals));
      setTradeSide('LONG');
    }
  }, [activeSymbol, activePosition]);

  // Current Live Market Price (last tick)
  const currentPrice = ticks[ticks.length - 1]?.price || spec.basePrice;

  // Real-Time Calculations
  const pipsMultiplier = spec.multiplier;
  const isLong = tradeSide === 'LONG';
  
  const pnlPips = +( (isLong ? (currentPrice - entryPrice) : (entryPrice - currentPrice)) * pipsMultiplier ).toFixed(1);
  const pnlDollars = +( (isLong ? (currentPrice - entryPrice) : (entryPrice - currentPrice)) * (tradeQuantity / (spec.assetClass === 'Forex' ? 10000 : 1)) ).toFixed(2);
  const isProfit = Number(pnlDollars) >= 0;

  const riskDistancePips = Math.abs(entryPrice - stopLoss) * pipsMultiplier;
  const riskDollars = Math.round(Math.abs(entryPrice - stopLoss) * (tradeQuantity / (spec.assetClass === 'Forex' ? 10000 : 1)));

  const rewardDistancePips = Math.abs(takeProfit - entryPrice) * pipsMultiplier;
  const rewardDollars = Math.round(Math.abs(takeProfit - entryPrice) * (tradeQuantity / (spec.assetClass === 'Forex' ? 10000 : 1)));

  const runnerRewardPips = Math.abs(runnerTakeProfit - entryPrice) * pipsMultiplier;
  const runnerRewardDollars = Math.round(Math.abs(runnerTakeProfit - entryPrice) * (tradeQuantity / (spec.assetClass === 'Forex' ? 10000 : 1)));

  const riskRewardRatio = riskDistancePips > 0 ? (rewardDistancePips / riskDistancePips).toFixed(2) : '2.00';
  const runnerRRRatio = riskDistancePips > 0 ? (runnerRewardPips / riskDistancePips).toFixed(2) : '3.10';

  // Real-time live tick stream simulator (every 1600ms) with Framer Motion reveal trigger
  useEffect(() => {
    if (!isLiveStreaming) return;

    const interval = setInterval(() => {
      setTicks(prevTicks => {
        const lastTick = prevTicks[prevTicks.length - 1];
        if (!lastTick) return prevTicks;

        const delta = (Math.random() - 0.49) * spec.volatility;
        const newPrice = +(lastTick.price + delta).toFixed(spec.decimals);
        const newHigh = Math.max(lastTick.high, newPrice);
        const newLow = Math.min(lastTick.low, newPrice);
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const newVol = Math.floor(Math.random() * 280 + 40);

        // Flash indicator with smooth bounce
        setTickFlash(newPrice >= lastTick.price ? 'up' : 'down');
        setTickCount(c => c + 1);
        setTimeout(() => setTickFlash(null), 650);

        const updated = [
          ...prevTicks.slice(-42), // keep rolling 42 points for high performance
          {
            time: timeStr,
            price: newPrice,
            open: lastTick.price,
            high: newHigh,
            low: newLow,
            close: newPrice,
            volume: newVol,
            vwap: +( (lastTick.vwap * prevTicks.length + newPrice) / (prevTicks.length + 1) ).toFixed(spec.decimals),
            isEntryBar: false
          }
        ];
        return updated;
      });
    }, 1600);

    return () => clearInterval(interval);
  }, [isLiveStreaming, spec]);

  // Interactive Adjustments
  const handleAdjustSL = (pipsDelta: number) => {
    const delta = pipsDelta / spec.multiplier;
    const newSL = +(stopLoss + (isLong ? delta : -delta)).toFixed(spec.decimals);
    setStopLoss(newSL);
    triggerToast(`Stop-Loss adjusted to ${newSL.toFixed(spec.decimals)} (${pipsDelta > 0 ? '+' : ''}${pipsDelta} pips)`);
  };

  const handleAdjustTP = (pipsDelta: number) => {
    const delta = pipsDelta / spec.multiplier;
    const newTP = +(takeProfit + (isLong ? delta : -delta)).toFixed(spec.decimals);
    setTakeProfit(newTP);
    triggerToast(`Take-Profit adjusted to ${newTP.toFixed(spec.decimals)} (${pipsDelta > 0 ? '+' : ''}${pipsDelta} pips)`);
  };

  const handleSetBreakeven = () => {
    setStopLoss(entryPrice);
    triggerToast(`🛡️ Stop-Loss moved to Breakeven @ ${entryPrice.toFixed(spec.decimals)} (Zero Risk Lock)`);
  };

  const handleApplyRatioPreset = (ratio: number) => {
    const riskDiff = Math.abs(entryPrice - stopLoss);
    const targetDiff = riskDiff * ratio;
    const newTP = isLong 
      ? +(entryPrice + targetDiff).toFixed(spec.decimals)
      : +(entryPrice - targetDiff).toFixed(spec.decimals);
    setTakeProfit(newTP);
    triggerToast(`🎯 Take-Profit calibrated for 1:${ratio} Risk-to-Reward ratio`);
  };

  const handleFlattenPosition = () => {
    if (activePosition && onClosePosition) {
      onClosePosition(activePosition.id);
    }
    triggerToast(`⚡ Market Order: Position FLATTENED on ${activeSymbol} @ ${currentPrice.toFixed(spec.decimals)}`);
  };

  const triggerToast = (msg: string) => {
    setActionToast(msg);
    setTimeout(() => setActionToast(null), 3200);
  };

  // Find price bounds for Y-Axis
  const { yDomainMin, yDomainMax } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    ticks.forEach(t => {
      if (t.low < min) min = t.low;
      if (t.high > max) max = t.high;
    });

    // Expand to comfortably include Entry, Stop Loss, Take Profit, and Runner lines
    min = Math.min(min, stopLoss, entryPrice, currentPrice);
    max = Math.max(max, takeProfit, runnerTakeProfit, entryPrice, currentPrice);

    const span = max - min || 1;
    const pad = span * 0.14;

    return {
      yDomainMin: +(min - pad).toFixed(spec.decimals),
      yDomainMax: +(max + pad).toFixed(spec.decimals)
    };
  }, [ticks, stopLoss, takeProfit, runnerTakeProfit, entryPrice, currentPrice, spec.decimals]);

  // Find timestamp of the entry bar
  const entryBarTime = useMemo(() => {
    const entryBar = ticks.find(t => t.isEntryBar);
    return entryBar ? entryBar.time : ticks[Math.floor(ticks.length * 0.45)]?.time;
  }, [ticks]);

  // Visual Risk-to-Reward horizontal gauge calculations
  const totalGaugeSpan = Math.abs(takeProfit - stopLoss) || 1;
  const currentProgressFromSL = Math.max(0, Math.min(100, ((currentPrice - stopLoss) / (takeProfit - stopLoss)) * 100));
  const entryPositionPct = Math.max(0, Math.min(100, ((entryPrice - stopLoss) / (takeProfit - stopLoss)) * 100));

  return (
    <div 
      ref={containerRef}
      className="bg-slate-900 border-b border-slate-800 text-white select-none transition-all duration-300 shadow-lg relative z-20"
    >
      {/* Toast Notification with Framer-Motion */}
      <AnimatePresence>
        {actionToast && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute top-2 right-4 z-50 pointer-events-none"
          >
            <div className="bg-slate-950/95 text-cyan-300 px-3.5 py-1.5 rounded-lg border border-cyan-500/50 shadow-2xl flex items-center gap-2 text-xs font-mono font-bold backdrop-blur-md">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>{actionToast}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* TOP COMPACT PERSISTENT TICKER STRIP */}
      <div className="px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-sm">
        {/* Left: Instrument Selector & Live Status Indicator */}
        <div className="flex items-center gap-2">
          {/* Live Pulse Dot with Framer-Motion Animation */}
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/30 text-[10px] font-mono text-emerald-400">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="font-extrabold uppercase tracking-wider">LIVE FEED</span>
          </div>

          {/* Symbol Quick Chips with Active Positions Indicator */}
          <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
            {Object.keys(SYMBOL_SPECS).map(sym => {
              const hasPos = activePositions.some(p => p.symbol === sym);
              return (
                <button
                  key={sym}
                  type="button"
                  onClick={() => {
                    setInternalSymbol(sym);
                    onSelectSymbol?.(sym);
                  }}
                  className={`px-2 py-0.5 rounded text-[11px] font-mono font-extrabold transition-all cursor-pointer flex items-center gap-1 ${
                    activeSymbol === sym
                      ? 'bg-blue-600 text-white shadow-2xs'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <span>{sym}</span>
                  {hasPos && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Active Paper Position" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Current Live Price Badge with Framer-Motion Spring Bounce */}
          <motion.div
            key={tickCount}
            initial={{ scale: 1 }}
            animate={{ 
              scale: tickFlash ? [1, 1.05, 1] : 1,
              backgroundColor: tickFlash === 'up' ? 'rgba(6, 78, 59, 0.7)' : tickFlash === 'down' ? 'rgba(136, 19, 55, 0.7)' : 'rgba(15, 23, 42, 0.9)'
            }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className={`px-2.5 py-0.5 rounded-md font-mono text-xs font-black transition-all flex items-center gap-1.5 border ${
              tickFlash === 'up'
                ? 'border-emerald-500 text-emerald-300'
                : tickFlash === 'down'
                ? 'border-rose-500 text-rose-300'
                : 'border-slate-700 text-cyan-300'
            }`}
          >
            <span>{currentPrice.toFixed(spec.decimals)}</span>
            {tickFlash === 'up' && <TrendingUp className="w-3 h-3 text-emerald-400" />}
            {tickFlash === 'down' && <TrendingDown className="w-3 h-3 text-rose-400" />}
          </motion.div>

          {/* Spread & Gateway Tag */}
          <span className="hidden md:inline text-[10px] text-slate-400 font-mono">
            Spread: <strong className="text-slate-300">{spec.spreadPips} pips</strong> · EBS/ECN
          </span>
        </div>

        {/* Center: Real-Time Position Telemetry (Entry, SL, TP, PnL) with Hover Tooltip Triggers */}
        <div className="flex items-center gap-2 text-xs font-mono">
          {/* Active Trade Pill */}
          <div 
            className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 cursor-help hover:border-blue-400 transition-colors"
            title="Click to center entry marker"
          >
            <span className={`px-1 py-0.2 rounded text-[8px] font-black ${isLong ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>
              {tradeSide}
            </span>
            <span className="text-[10px] text-slate-400">Entry:</span>
            <strong className="text-white font-bold">{entryPrice.toFixed(spec.decimals)}</strong>
          </div>

          {/* Stop Loss Level Pill */}
          <div 
            onClick={() => handleAdjustSL(+2)}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-rose-950/60 border border-rose-600/40 text-rose-300 text-[10px] cursor-pointer hover:bg-rose-900/80 transition-colors"
            title="Click to tighten Stop-Loss (+2 pips)"
          >
            <ShieldAlert className="w-3 h-3 text-rose-400" />
            <span className="font-extrabold text-[9px] uppercase">SL:</span>
            <span className="font-bold">{stopLoss.toFixed(spec.decimals)}</span>
            <span className="text-rose-400/80 text-[8.5px]">(-${riskDollars})</span>
          </div>

          {/* Take Profit Level Pill */}
          <div 
            onClick={() => handleAdjustTP(+2)}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-600/40 text-emerald-300 text-[10px] cursor-pointer hover:bg-emerald-900/80 transition-colors"
            title="Click to extend Take-Profit (+2 pips)"
          >
            <Target className="w-3 h-3 text-emerald-400" />
            <span className="font-extrabold text-[9px] uppercase">TP:</span>
            <span className="font-bold">{takeProfit.toFixed(spec.decimals)}</span>
            <span className="text-emerald-400/80 text-[8.5px]">(+${rewardDollars})</span>
          </div>

          {/* Real-Time Position PnL with Spring Reveal */}
          <motion.div
            key={pnlDollars}
            initial={{ scale: 0.98 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            className={`px-2.5 py-0.5 rounded font-black text-xs border ${
              isProfit
                ? 'bg-emerald-900/40 text-emerald-300 border-emerald-500/50 shadow-[0_0_12px_rgba(16,185,129,0.15)]'
                : 'bg-rose-900/40 text-rose-300 border-rose-500/50 shadow-[0_0_12px_rgba(244,63,94,0.15)]'
            }`}
          >
            <span>P&amp;L: {isProfit ? '+' : ''}${pnlDollars}</span>
            <span className="text-[9px] font-normal ml-1">({pnlPips > 0 ? `+${pnlPips}` : pnlPips} p)</span>
          </motion.div>
        </div>

        {/* Right: Expand / Collapse, Full Workspace Button & Quick Controls */}
        <div className="flex items-center gap-1.5">
          {/* Quick R:R Display */}
          <div className="hidden lg:flex items-center gap-1 px-2 py-0.5 bg-slate-900 rounded border border-slate-800 text-[10px] font-mono text-cyan-400">
            <span className="text-slate-500">R:R:</span>
            <strong className="font-bold">1 : {riskRewardRatio}</strong>
          </div>

          {/* Pause / Resume Live Streaming */}
          <button
            type="button"
            onClick={() => setIsLiveStreaming(prev => !prev)}
            className={`p-1 rounded cursor-pointer transition-colors ${isLiveStreaming ? 'text-emerald-400 hover:bg-slate-800' : 'text-amber-400 bg-amber-950/40 border border-amber-500/30'}`}
            title={isLiveStreaming ? 'Pause Real-time Ticks' : 'Resume Real-time Ticks'}
          >
            {isLiveStreaming ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          {/* Jump to Full Terminal */}
          {onOpenFullCharts && (
            <button
              type="button"
              onClick={onOpenFullCharts}
              className="px-2 py-0.5 rounded bg-blue-600/80 hover:bg-blue-600 text-white text-[10px] font-mono font-bold border border-blue-500 cursor-pointer transition-colors flex items-center gap-1"
              title="Open full-screen Chart Terminal"
            >
              <Maximize2 className="w-3 h-3" />
              <span className="hidden sm:inline">Terminal</span>
            </button>
          )}

          {/* Expand / Collapse Chart Canvas */}
          <button
            type="button"
            onClick={() => setIsExpanded(prev => !prev)}
            className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white cursor-pointer transition-colors flex items-center gap-1 text-[10px] font-bold"
            title={isExpanded ? 'Collapse Chart Dock' : 'Expand Live Chart Dock'}
          >
            {isExpanded ? (
              <>
                <Minimize2 className="w-3.5 h-3.5 text-cyan-400" />
                <span className="hidden sm:inline">Collapse</span>
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5 text-cyan-400" />
                <span className="hidden sm:inline">Live Chart</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* EXPANDED INTERACTIVE RECHARTS VIEWPORT WITH FRAMER-MOTION SMOOTH REVEAL */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.28, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="p-2 space-y-2">
              {/* Sub-toolbar: Quick Timeframes, Bracket Steppers, Volume Toggle, and 1-Click Execution */}
              <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-xs">
                {/* Timeframe & Chart Style */}
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-0.5 bg-slate-950 px-1 py-0.5 rounded-lg border border-slate-800 text-[10px] font-mono font-bold">
                    {(['1s', '5s', '1m', '5m'] as const).map(tf => (
                      <button
                        key={tf}
                        type="button"
                        onClick={() => setTimeframe(tf)}
                        className={`px-1.5 py-0.2 rounded cursor-pointer transition-colors ${
                          timeframe === tf ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        {tf}
                      </button>
                    ))}
                  </div>

                  <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400">
                    <button
                      type="button"
                      onClick={() => setChartMode('area')}
                      className={`px-1.5 py-0.2 rounded border cursor-pointer ${chartMode === 'area' ? 'bg-slate-800 text-cyan-300 border-cyan-500/40' : 'border-slate-800 text-slate-400 hover:bg-slate-800'}`}
                    >
                      Area
                    </button>
                    <button
                      type="button"
                      onClick={() => setChartMode('line')}
                      className={`px-1.5 py-0.2 rounded border cursor-pointer ${chartMode === 'line' ? 'bg-slate-800 text-cyan-300 border-cyan-500/40' : 'border-slate-800 text-slate-400 hover:bg-slate-800'}`}
                    >
                      Line
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowVolume(v => !v)}
                      className={`px-1.5 py-0.2 rounded border cursor-pointer ${showVolume ? 'bg-indigo-950 text-indigo-300 border-indigo-500/40' : 'border-slate-800 text-slate-400 hover:bg-slate-800'}`}
                      title="Toggle Volume Delta Histogram"
                    >
                      Vol
                    </button>
                  </div>
                </div>

                {/* Quick Bracket Adjusters (SL & TP Steppers, Breakeven, R:R Presets) */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  {/* SL Steppers */}
                  <div className="flex items-center gap-1 bg-slate-950 px-1.5 py-0.5 rounded border border-rose-500/30 text-[10px] font-mono">
                    <span className="text-rose-400 font-bold uppercase mr-0.5">SL:</span>
                    <button
                      type="button"
                      onClick={() => handleAdjustSL(-5)}
                      className="px-1 bg-slate-800 hover:bg-slate-700 text-rose-300 rounded cursor-pointer"
                      title="Widen Stop Loss (-5 pips)"
                    >
                      -5p
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAdjustSL(+5)}
                      className="px-1 bg-slate-800 hover:bg-slate-700 text-rose-300 rounded cursor-pointer"
                      title="Tighten Stop Loss (+5 pips)"
                    >
                      +5p
                    </button>
                    <button
                      type="button"
                      onClick={handleSetBreakeven}
                      className="px-1.5 py-0.2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded text-[9px] font-black cursor-pointer"
                      title="Move Stop Loss to Breakeven entry"
                    >
                      B/E
                    </button>
                  </div>

                  {/* TP Steppers */}
                  <div className="flex items-center gap-1 bg-slate-950 px-1.5 py-0.5 rounded border border-emerald-500/30 text-[10px] font-mono">
                    <span className="text-emerald-400 font-bold uppercase mr-0.5">TP:</span>
                    <button
                      type="button"
                      onClick={() => handleAdjustTP(-5)}
                      className="px-1 bg-slate-800 hover:bg-slate-700 text-emerald-300 rounded cursor-pointer"
                    >
                      -5p
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAdjustTP(+5)}
                      className="px-1 bg-slate-800 hover:bg-slate-700 text-emerald-300 rounded cursor-pointer"
                    >
                      +5p
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApplyRatioPreset(2.0)}
                      className="px-1 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/40 rounded text-[9px] font-black cursor-pointer"
                      title="Calibrate TP to 1:2 Risk-Reward"
                    >
                      1:2R
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApplyRatioPreset(3.0)}
                      className="px-1 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/40 rounded text-[9px] font-black cursor-pointer"
                      title="Calibrate TP to 1:3 Risk-Reward"
                    >
                      1:3R
                    </button>
                  </div>

                  {/* Flatten Button */}
                  <button
                    type="button"
                    onClick={handleFlattenPosition}
                    className="px-2 py-0.5 rounded bg-rose-600/80 hover:bg-rose-600 text-white font-mono text-[10px] font-black cursor-pointer transition-colors shadow-2xs flex items-center gap-1"
                  >
                    <X className="w-3 h-3" />
                    <span>Flatten</span>
                  </button>
                </div>
              </div>

              {/* MAIN RECHARTS CONTAINER WITH INTERACTIVE FLOATING TOOLTIP */}
              <div className="w-full h-68 bg-slate-950 rounded-xl border border-slate-800/90 relative overflow-hidden p-1 shadow-inner">
                {/* Floating Tooltip Animated via Framer-Motion for Trade Markers */}
                <AnimatePresence>
                  {hoveredMarker && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.92, y: 6 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.94 }}
                      transition={{ duration: 0.16, ease: 'easeOut' }}
                      style={{
                        left: Math.min(Math.max(hoveredMarker.x - 130, 12), 680),
                        top: Math.max(hoveredMarker.y - 145, 12)
                      }}
                      className="absolute z-50 pointer-events-auto bg-slate-950/95 backdrop-blur-md border border-slate-700/80 rounded-xl p-3 shadow-2xl text-xs font-mono w-72 text-white"
                      onMouseEnter={() => {}} // keeps tooltip open if hovered
                      onMouseLeave={() => setHoveredMarker(null)}
                    >
                      {/* Tooltip Header */}
                      <div className="flex items-center justify-between pb-1.5 border-b border-slate-800 mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-black uppercase ${hoveredMarker.badgeBg} ${hoveredMarker.badgeText}`}>
                            {hoveredMarker.badge}
                          </span>
                          <span className="font-bold text-white text-[11px]">{hoveredMarker.title}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setHoveredMarker(null)}
                          className="text-slate-400 hover:text-white p-0.5"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>

                      {/* Tooltip Metrics Grid */}
                      <div className="space-y-1 text-[10px]">
                        <div className="flex justify-between items-center bg-slate-900/80 px-2 py-1 rounded">
                          <span className="text-slate-400">Target Price:</span>
                          <strong className="text-white font-mono text-[11px]">{hoveredMarker.price.toFixed(spec.decimals)}</strong>
                        </div>
                        <div className="flex justify-between items-center px-1">
                          <span className="text-slate-400">Distance to Mkt:</span>
                          <span className={hoveredMarker.deltaPips >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                            {hoveredMarker.deltaPips >= 0 ? '+' : ''}{hoveredMarker.deltaPips.toFixed(1)} pips ({hoveredMarker.deltaDollars >= 0 ? '+' : ''}${hoveredMarker.deltaDollars})
                          </span>
                        </div>
                        {hoveredMarker.rrImpact && (
                          <div className="flex justify-between items-center px-1">
                            <span className="text-slate-400">R:R Ratio Impact:</span>
                            <span className="text-cyan-300 font-bold">{hoveredMarker.rrImpact}</span>
                          </div>
                        )}
                        <div className="flex justify-between items-center px-1 text-slate-400">
                          <span>Execution Venue:</span>
                          <span className="text-slate-300">{hoveredMarker.notes}</span>
                        </div>
                        <div className="flex justify-between items-center px-1 text-slate-500 text-[9px]">
                          <span>Latency / Slip:</span>
                          <span>{hoveredMarker.latency}</span>
                        </div>
                      </div>

                      {/* Tooltip Quick Actions */}
                      <div className="mt-2 pt-1.5 border-t border-slate-800/80 flex items-center justify-between gap-1">
                        {hoveredMarker.type === 'STOP_LOSS' && (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                handleSetBreakeven();
                                setHoveredMarker(null);
                              }}
                              className="px-2 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-[9px] font-bold cursor-pointer"
                            >
                              Lock B/E
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                handleAdjustSL(+5);
                                setHoveredMarker(null);
                              }}
                              className="px-2 py-0.5 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-[9px] font-bold cursor-pointer"
                            >
                              Tighten +5p
                            </button>
                          </>
                        )}

                        {hoveredMarker.type === 'TAKE_PROFIT' && (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                handleApplyRatioPreset(2.0);
                                setHoveredMarker(null);
                              }}
                              className="px-2 py-0.5 rounded bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/40 text-[9px] font-bold cursor-pointer"
                            >
                              Set 1:2 R:R
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                handleApplyRatioPreset(3.0);
                                setHoveredMarker(null);
                              }}
                              className="px-2 py-0.5 rounded bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/40 text-[9px] font-bold cursor-pointer"
                            >
                              Set 1:3 R:R
                            </button>
                          </>
                        )}

                        {hoveredMarker.type === 'ENTRY' && (
                          <button
                            type="button"
                            onClick={() => {
                              handleFlattenPosition();
                              setHoveredMarker(null);
                            }}
                            className="w-full py-0.5 rounded bg-rose-600/80 hover:bg-rose-600 text-white text-[9px] font-bold cursor-pointer"
                          >
                            Close Position @ Market
                          </button>
                        )}

                        {hoveredMarker.type === 'CURRENT_PRICE' && (
                          <div className="w-full text-center text-[9px] text-cyan-400 font-bold">
                            Live Stream Active · EBS L2 Depth Validated
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Legend / Overlay watermark in chart top-left */}
                <div className="absolute top-2 left-3 z-10 pointer-events-none flex items-center gap-3 text-[10px] font-mono text-slate-400">
                  <span className="text-white font-bold flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-cyan-400" />
                    <span>{spec.name}</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-0.5 bg-blue-400" />
                    <span className="text-blue-300">Entry: {entryPrice.toFixed(spec.decimals)}</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-0.5 bg-rose-500 stroke-dasharray" />
                    <span className="text-rose-400 font-bold">SL: {stopLoss.toFixed(spec.decimals)}</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-0.5 bg-emerald-500 stroke-dasharray" />
                    <span className="text-emerald-400 font-bold">TP: {takeProfit.toFixed(spec.decimals)}</span>
                  </span>
                </div>

                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={ticks}
                    margin={{ top: 22, right: 88, left: 10, bottom: 5 }}
                  >
                    <defs>
                      <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.32} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#4f46e5" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>

                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />

                    <XAxis
                      dataKey="time"
                      stroke="#64748b"
                      fontSize={9}
                      fontFamily="monospace"
                      tickLine={false}
                      interval="preserveStartEnd"
                    />

                    <YAxis
                      domain={[yDomainMin, yDomainMax]}
                      orientation="right"
                      stroke="#64748b"
                      fontSize={9}
                      fontFamily="monospace"
                      tickLine={false}
                      tickFormatter={(val: number) => val.toFixed(spec.decimals)}
                      width={70}
                    />

                    {/* Secondary YAxis for Volume */}
                    {showVolume && (
                      <YAxis
                        yAxisId="vol"
                        domain={[0, 1200]}
                        orientation="left"
                        hide={true}
                      />
                    )}

                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload as PriceTick;
                          const distToSL = (data.price - stopLoss) * spec.multiplier;
                          const distToTP = (takeProfit - data.price) * spec.multiplier;
                          return (
                            <div className="bg-slate-900/95 border border-slate-700 text-white p-2.5 rounded-lg shadow-2xl text-[10px] font-mono space-y-1 backdrop-blur-sm">
                              <div className="text-cyan-400 font-bold border-b border-slate-800 pb-0.5 flex justify-between gap-3">
                                <span>Time: {data.time}</span>
                                <span>Vol: {data.volume}</span>
                              </div>
                              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
                                <div>Price: <strong className="text-white">{data.price.toFixed(spec.decimals)}</strong></div>
                                <div>VWAP: <span className="text-slate-300">{data.vwap.toFixed(spec.decimals)}</span></div>
                                <div className="text-rose-400">To Stop: {distToSL.toFixed(1)} pips</div>
                                <div className="text-emerald-400">To Target: {distToTP.toFixed(1)} pips</div>
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />

                    {/* Shaded Profit Zone: Between Entry & Current Price if in profit */}
                    {isProfit && (
                      <ReferenceArea
                        y1={entryPrice}
                        y2={currentPrice}
                        fill="rgba(16, 185, 129, 0.08)"
                        stroke="none"
                      />
                    )}

                    {/* Shaded Risk Zone: Between Entry & Current Price if in drawdown */}
                    {!isProfit && (
                      <ReferenceArea
                        y1={entryPrice}
                        y2={currentPrice}
                        fill="rgba(244, 63, 94, 0.08)"
                        stroke="none"
                      />
                    )}

                    {/* Optional Volume Histogram Bars */}
                    {showVolume && (
                      <Bar
                        yAxisId="vol"
                        dataKey="volume"
                        fill="url(#volumeGradient)"
                        radius={[2, 2, 0, 0]}
                        isAnimationActive={false}
                      />
                    )}

                    {/* Price Series: Area or Line */}
                    {chartMode === 'area' ? (
                      <Area
                        type="monotone"
                        dataKey="price"
                        stroke="#06b6d4"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#priceGradient)"
                        isAnimationActive={false}
                      />
                    ) : (
                      <Line
                        type="monotone"
                        dataKey="price"
                        stroke="#06b6d4"
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={false}
                      />
                    )}

                    {/* VWAP Benchmark Reference Line */}
                    <Line
                      type="monotone"
                      dataKey="vwap"
                      stroke="#a855f7"
                      strokeWidth={1}
                      strokeDasharray="2 2"
                      dot={false}
                      isAnimationActive={false}
                    />

                    {/* ========================================================= */}
                    {/* 1. VISUAL INDICATOR: ACTIVE TRADE ENTRY LEVEL & MARKER   */}
                    {/* ========================================================= */}
                    <ReferenceLine
                      y={entryPrice}
                      stroke="#3b82f6"
                      strokeWidth={2}
                      label={{
                        value: `ENTRY: ${entryPrice.toFixed(spec.decimals)} (${tradeSide})`,
                        position: 'left',
                        fill: '#93c5fd',
                        fontSize: 9,
                        fontFamily: 'monospace',
                        fontWeight: 'bold'
                      }}
                    />

                    {/* Custom SVG Entry Dot with Subtle Hover State & Floating Tooltip */}
                    {entryBarTime && (
                      <ReferenceDot
                        x={entryBarTime}
                        y={entryPrice}
                        shape={(props: any) => {
                          const { cx, cy } = props;
                          if (!cx || !cy) return <g />;
                          return (
                            <g
                              className="cursor-pointer group"
                              onMouseEnter={() => {
                                setHoveredMarker({
                                  type: 'ENTRY',
                                  x: cx,
                                  y: cy,
                                  title: `${activeSymbol} ${tradeSide} Entry`,
                                  price: entryPrice,
                                  badge: 'ACTIVE FILL',
                                  badgeBg: 'bg-blue-900/60',
                                  badgeText: 'text-blue-300',
                                  deltaPips: Number(pnlPips),
                                  deltaDollars: Number(pnlDollars),
                                  rrImpact: `1 : ${riskRewardRatio}`,
                                  orderId: '#ORD-88241',
                                  latency: '3.4ms · 0.1 pip slippage',
                                  notes: 'EBS Prime Gateway'
                                });
                              }}
                              onMouseLeave={() => setHoveredMarker(null)}
                            >
                              <circle cx={cx} cy={cy} r={12} fill="#3b82f6" fillOpacity={0.25} className="animate-ping" />
                              <circle 
                                cx={cx} 
                                cy={cy} 
                                r={6} 
                                fill="#3b82f6" 
                                stroke="#ffffff" 
                                strokeWidth={2} 
                                className="transition-transform duration-200 group-hover:scale-135" 
                              />
                              <text
                                x={cx}
                                y={cy - 10}
                                textAnchor="middle"
                                fill="#93c5fd"
                                fontSize={8}
                                fontWeight="bold"
                                fontFamily="monospace"
                              >
                                ▲ {tradeSide}
                              </text>
                            </g>
                          );
                        }}
                      />
                    )}

                    {/* ========================================================= */}
                    {/* 2. VISUAL INDICATOR: STOP-LOSS (SL) LEVEL & TIMELINE MARKER */}
                    {/* ========================================================= */}
                    <ReferenceLine
                      y={stopLoss}
                      stroke="#f43f5e"
                      strokeWidth={2}
                      strokeDasharray="4 3"
                      label={{
                        value: `SL: ${stopLoss.toFixed(spec.decimals)} (-$${riskDollars})`,
                        position: 'right',
                        fill: '#f43f5e',
                        fontSize: 9,
                        fontFamily: 'monospace',
                        fontWeight: 'bold'
                      }}
                    />

                    {/* Custom Stop-Loss Dot with Subtle Hover State */}
                    {entryBarTime && (
                      <ReferenceDot
                        x={entryBarTime}
                        y={stopLoss}
                        shape={(props: any) => {
                          const { cx, cy } = props;
                          if (!cx || !cy) return <g />;
                          return (
                            <g
                              className="cursor-pointer group"
                              onMouseEnter={() => {
                                setHoveredMarker({
                                  type: 'STOP_LOSS',
                                  x: cx,
                                  y: cy,
                                  title: `${activeSymbol} Stop-Loss Order`,
                                  price: stopLoss,
                                  badge: 'PROTECTION',
                                  badgeBg: 'bg-rose-900/60',
                                  badgeText: 'text-rose-300',
                                  deltaPips: -riskDistancePips,
                                  deltaDollars: -riskDollars,
                                  rrImpact: `Max Risk -$${riskDollars}`,
                                  orderId: '#STP-9021',
                                  latency: 'Guaranteed Stop · 0.0ms slip',
                                  notes: 'Alpaca Smart Router'
                                });
                              }}
                              onMouseLeave={() => setHoveredMarker(null)}
                            >
                              <circle cx={cx} cy={cy} r={9} fill="#f43f5e" fillOpacity={0.2} />
                              <circle 
                                cx={cx} 
                                cy={cy} 
                                r={5} 
                                fill="#f43f5e" 
                                stroke="#ffffff" 
                                strokeWidth={1.5} 
                                className="transition-transform duration-200 group-hover:scale-135" 
                              />
                            </g>
                          );
                        }}
                      />
                    )}

                    {/* ========================================================= */}
                    {/* 3. VISUAL INDICATOR: TAKE-PROFIT 1 TARGET & MARKER        */}
                    {/* ========================================================= */}
                    <ReferenceLine
                      y={takeProfit}
                      stroke="#10b981"
                      strokeWidth={2}
                      strokeDasharray="4 3"
                      label={{
                        value: `TP1: ${takeProfit.toFixed(spec.decimals)} (+${rewardDollars} · ${riskRewardRatio}R)`,
                        position: 'right',
                        fill: '#10b981',
                        fontSize: 9,
                        fontFamily: 'monospace',
                        fontWeight: 'bold'
                      }}
                    />

                    {/* Custom Take Profit 1 Target Dot */}
                    {entryBarTime && (
                      <ReferenceDot
                        x={entryBarTime}
                        y={takeProfit}
                        shape={(props: any) => {
                          const { cx, cy } = props;
                          if (!cx || !cy) return <g />;
                          return (
                            <g
                              className="cursor-pointer group"
                              onMouseEnter={() => {
                                setHoveredMarker({
                                  type: 'TAKE_PROFIT',
                                  x: cx,
                                  y: cy,
                                  title: `${activeSymbol} Take-Profit 1`,
                                  price: takeProfit,
                                  badge: 'TARGET 1',
                                  badgeBg: 'bg-emerald-900/60',
                                  badgeText: 'text-emerald-300',
                                  deltaPips: rewardDistancePips,
                                  deltaDollars: rewardDollars,
                                  rrImpact: `1 : ${riskRewardRatio} R:R`,
                                  orderId: '#TGT-4412',
                                  latency: 'Limit Order · Passive Fill',
                                  notes: 'Scale Out 60% of position'
                                });
                              }}
                              onMouseLeave={() => setHoveredMarker(null)}
                            >
                              <circle cx={cx} cy={cy} r={9} fill="#10b981" fillOpacity={0.2} />
                              <circle 
                                cx={cx} 
                                cy={cy} 
                                r={5} 
                                fill="#10b981" 
                                stroke="#ffffff" 
                                strokeWidth={1.5} 
                                className="transition-transform duration-200 group-hover:scale-135" 
                              />
                            </g>
                          );
                        }}
                      />
                    )}

                    {/* ========================================================= */}
                    {/* 4. VISUAL INDICATOR: RUNNER TAKE-PROFIT 2 TARGET (TP2)     */}
                    {/* ========================================================= */}
                    <ReferenceLine
                      y={runnerTakeProfit}
                      stroke="#8b5cf6"
                      strokeWidth={1.5}
                      strokeDasharray="2 2"
                      label={{
                        value: `TP2 Runner: ${runnerTakeProfit.toFixed(spec.decimals)} (+${runnerRewardDollars} · ${runnerRRRatio}R)`,
                        position: 'right',
                        fill: '#c4b5fd',
                        fontSize: 8.5,
                        fontFamily: 'monospace'
                      }}
                    />

                    {/* Custom Take Profit 2 Runner Dot */}
                    {entryBarTime && (
                      <ReferenceDot
                        x={entryBarTime}
                        y={runnerTakeProfit}
                        shape={(props: any) => {
                          const { cx, cy } = props;
                          if (!cx || !cy) return <g />;
                          return (
                            <g
                              className="cursor-pointer group"
                              onMouseEnter={() => {
                                setHoveredMarker({
                                  type: 'RUNNER_TP',
                                  x: cx,
                                  y: cy,
                                  title: `${activeSymbol} Runner Target 2`,
                                  price: runnerTakeProfit,
                                  badge: 'RUNNER TP2',
                                  badgeBg: 'bg-purple-900/60',
                                  badgeText: 'text-purple-300',
                                  deltaPips: runnerRewardPips,
                                  deltaDollars: runnerRewardDollars,
                                  rrImpact: `1 : ${runnerRRRatio} R:R`,
                                  orderId: '#TGT-4413',
                                  latency: 'Trailing Moonbag Target',
                                  notes: 'Remaining 40% position'
                                });
                              }}
                              onMouseLeave={() => setHoveredMarker(null)}
                            >
                              <circle 
                                cx={cx} 
                                cy={cy} 
                                r={4} 
                                fill="#8b5cf6" 
                                stroke="#ffffff" 
                                strokeWidth={1} 
                                className="transition-transform duration-200 group-hover:scale-140" 
                              />
                            </g>
                          );
                        }}
                      />
                    )}

                    {/* ========================================================= */}
                    {/* 5. REAL-TIME LIVE MARKET PRICE MARKER WITH RADAR RIPPLE   */}
                    {/* ========================================================= */}
                    {ticks.length > 0 && (
                      <ReferenceDot
                        x={ticks[ticks.length - 1].time}
                        y={currentPrice}
                        shape={(props: any) => {
                          const { cx, cy } = props;
                          if (!cx || !cy) return <g />;
                          const dotColor = tickFlash === 'up' ? '#10b981' : tickFlash === 'down' ? '#f43f5e' : '#06b6d4';
                          return (
                            <g
                              className="cursor-pointer group"
                              onMouseEnter={() => {
                                setHoveredMarker({
                                  type: 'CURRENT_PRICE',
                                  x: cx,
                                  y: cy,
                                  title: `${activeSymbol} Live Price`,
                                  price: currentPrice,
                                  badge: 'LIVE TICK',
                                  badgeBg: 'bg-cyan-900/60',
                                  badgeText: 'text-cyan-300',
                                  deltaPips: Number(pnlPips),
                                  deltaDollars: Number(pnlDollars),
                                  orderId: '#TICK-LIVE',
                                  latency: 'EBS L1/L2 Sub-10ms Stream',
                                  notes: `Volume: ${ticks[ticks.length - 1]?.volume || 100}`
                                });
                              }}
                              onMouseLeave={() => setHoveredMarker(null)}
                            >
                              <circle cx={cx} cy={cy} r={14} fill={dotColor} fillOpacity={0.2} className="animate-ping" />
                              <circle 
                                cx={cx} 
                                cy={cy} 
                                r={6} 
                                fill={dotColor} 
                                stroke="#ffffff" 
                                strokeWidth={2} 
                                className="transition-transform duration-200 group-hover:scale-135" 
                              />
                            </g>
                          );
                        }}
                      />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* VISUAL RISK:REWARD GAUGE / BRACKET SCALE THERMOMETER */}
              <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 text-xs font-mono space-y-1">
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span className="flex items-center gap-1 text-rose-400 font-bold">
                    <ShieldAlert className="w-3 h-3" />
                    <span>SL: {stopLoss.toFixed(spec.decimals)} (-${riskDollars})</span>
                  </span>
                  <span className="flex items-center gap-1 text-blue-300 font-bold">
                    <span>Entry: {entryPrice.toFixed(spec.decimals)}</span>
                  </span>
                  <span className="flex items-center gap-1 text-emerald-400 font-bold">
                    <Target className="w-3 h-3" />
                    <span>TP: {takeProfit.toFixed(spec.decimals)} (+${rewardDollars})</span>
                  </span>
                </div>

                {/* Visual Progress Thermometer */}
                <div className="h-2.5 w-full bg-slate-900 rounded-full overflow-hidden relative border border-slate-800">
                  {/* SL Zone (Red) */}
                  <div 
                    className="absolute left-0 top-0 bottom-0 bg-rose-900/50" 
                    style={{ width: `${entryPositionPct}%` }}
                  />
                  {/* TP Zone (Green) */}
                  <div 
                    className="absolute right-0 top-0 bottom-0 bg-emerald-900/40" 
                    style={{ width: `${100 - entryPositionPct}%` }}
                  />
                  {/* Entry Divider Marker */}
                  <div 
                    className="absolute top-0 bottom-0 w-0.5 bg-blue-400 z-10"
                    style={{ left: `${entryPositionPct}%` }}
                    title={`Entry @ ${entryPrice.toFixed(spec.decimals)}`}
                  />
                  {/* Current Market Price Glowing Dot */}
                  <motion.div
                    className="absolute top-0 bottom-0 w-2.5 -ml-1 rounded-full bg-cyan-400 z-20 shadow-[0_0_8px_#22d3ee]"
                    style={{ left: `${currentProgressFromSL}%` }}
                    animate={{ scale: [1, 1.25, 1] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                    title={`Current Price @ ${currentPrice.toFixed(spec.decimals)}`}
                  />
                </div>

                <div className="flex items-center justify-between text-[9px] text-slate-400 pt-0.5">
                  <span>Risk Distance: <strong>{riskDistancePips.toFixed(1)} pips</strong></span>
                  <span className="text-cyan-300 font-extrabold">Active R:R: 1 : {riskRewardRatio}</span>
                  <span>Target Distance: <strong>{rewardDistancePips.toFixed(1)} pips</strong></span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
