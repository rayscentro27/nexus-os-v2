import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  SkipBack,
  Sliders,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Zap,
  Clock,
  Sparkles,
  ArrowRight,
  Maximize2,
  DollarSign,
  Layers,
  ChevronRight,
  ChevronLeft,
  Activity,
  BarChart2,
  RefreshCw,
  X,
  Grid,
  Columns,
  LayoutGrid,
  Target,
  Plus,
  Volume2,
  VolumeX,
  Calculator,
  Download,
  Minus,
  MousePointer,
  Trash2,
  Keyboard,
  Info
} from 'lucide-react';
import { REPLAY_SESSIONS, InstrumentReplaySession, CandleData, ReplayTradeEvent } from '../../data/tradeReplayData';
import { soundEngine } from '../../utils/audioAlerts';
import { PortfolioShockSimulatorModal } from './PortfolioShockSimulatorModal';

export interface ChartPendingOrder {
  id: string;
  type: 'LIMIT_BUY' | 'LIMIT_SELL' | 'ALERT';
  price: number;
  symbol: string;
  placedAt: string;
}

export interface ChartDrawing {
  id: string;
  type: 'H_LINE' | 'TRENDLINE' | 'FIBONACCI';
  price1: number;
  candleIdx1?: number;
  price2?: number;
  candleIdx2?: number;
  color: string;
  label: string;
}

interface MiniCandleChartProps {
  session: InstrumentReplaySession;
  timeframe: string;
  replayIndex?: number;
  terminalMode: 'LIVE' | 'REPLAY';
  hoveredTime?: string | null;
  onHoverTime?: (time: string | null) => void;
  onFocus?: () => void;
  isFocused?: boolean;
}

const MiniCandleChart: React.FC<MiniCandleChartProps> = ({
  session,
  timeframe,
  replayIndex,
  terminalMode,
  hoveredTime,
  onHoverTime,
  onFocus,
  isFocused = false
}) => {
  const visibleCandles = useMemo(() => {
    if (terminalMode === 'LIVE' || replayIndex === undefined) {
      return session.candles;
    }
    return session.candles.slice(0, Math.max(8, replayIndex + 1));
  }, [terminalMode, session.candles, replayIndex]);

  const { minPrice, maxPrice, priceRange } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    visibleCandles.forEach(c => {
      if (c.low < min) min = c.low;
      if (c.high > max) max = c.high;
    });
    const range = max - min || 1;
    const padding = range * 0.08;
    return {
      minPrice: min - padding,
      maxPrice: max + padding,
      priceRange: range + padding * 2
    };
  }, [visibleCandles]);

  const w = 420;
  const h = 200;
  const priceAxisW = 55;
  const plotW = w - priceAxisW;
  const plotH = h - 18;

  const getY = (p: number) => plotH - ((p - minPrice) / priceRange) * plotH;
  const spacing = plotW / Math.max(1, visibleCandles.length);
  const bodyW = Math.max(2, Math.min(10, spacing * 0.7));

  const lastCandle = visibleCandles[visibleCandles.length - 1];
  const lastPrice = lastCandle ? lastCandle.close : session.currentPrice;
  const priceChange = lastCandle && visibleCandles[0] ? +(lastCandle.close - visibleCandles[0].open).toFixed(session.decimals) : 0;
  const isUp = priceChange >= 0;

  return (
    <div className={`bg-slate-950 rounded-xl border flex flex-col min-h-0 overflow-hidden relative shadow-2xs ${isFocused ? 'border-cyan-500 ring-1 ring-cyan-500/50' : 'border-slate-800'}`}>
      {/* Pane Header */}
      <div className="px-2.5 py-1 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs text-slate-300 shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="font-black text-white text-xs">{session.symbol}</span>
          <span className="text-[10px] text-slate-400 font-mono">({timeframe})</span>
          <span className={`text-[10px] font-bold font-mono ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
            {lastPrice.toFixed(session.decimals)} ({isUp ? '+' : ''}{priceChange})
          </span>
        </div>
        <div className="flex items-center gap-1">
          {onFocus && (
            <button
              type="button"
              onClick={onFocus}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[9px] font-bold cursor-pointer transition-colors"
              title="Maximize / Focus this asset"
            >
              Focus
            </button>
          )}
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="flex-1 min-h-0 relative p-1">
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-full" preserveAspectRatio="none">
          {/* Price Axis Grid */}
          <line x1={0} y1={plotH * 0.25} x2={plotW} y2={plotH * 0.25} stroke="#1e293b" strokeDasharray="2 2" />
          <line x1={0} y1={plotH * 0.5} x2={plotW} y2={plotH * 0.5} stroke="#1e293b" strokeDasharray="2 2" />
          <line x1={0} y1={plotH * 0.75} x2={plotW} y2={plotH * 0.75} stroke="#1e293b" strokeDasharray="2 2" />

          {/* Candlesticks */}
          {visibleCandles.map((c, i) => {
            const x = i * spacing + spacing / 2;
            const yOpen = getY(c.open);
            const yClose = getY(c.close);
            const yHigh = getY(c.high);
            const yLow = getY(c.low);
            const bull = c.close >= c.open;
            const top = Math.min(yOpen, yClose);
            const height = Math.max(1.5, Math.abs(yClose - yOpen));

            return (
              <g key={`mini-${i}`}>
                <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={bull ? '#10b981' : '#f43f5e'} strokeWidth={1} />
                <rect
                  x={x - bodyW / 2}
                  y={top}
                  width={bodyW}
                  height={height}
                  fill={bull ? '#10b981' : '#f43f5e'}
                />
              </g>
            );
          })}

          {/* Current Price Line */}
          <line x1={0} y1={getY(lastPrice)} x2={plotW} y2={getY(lastPrice)} stroke="#06b6d4" strokeWidth={1} strokeDasharray="2 2" />
          <text x={plotW + 4} y={getY(lastPrice) + 3} fill="#06b6d4" fontSize="8" fontFamily="monospace" fontWeight="bold">
            {lastPrice.toFixed(session.decimals)}
          </text>
        </svg>
      </div>
    </div>
  );
};

export interface LiveChartAndReplayTerminalProps {
  initialSymbol?: string;
  onClose?: () => void;
  compactMode?: boolean;
  onNavigateTab?: (tab: string) => void;
  isDedicatedSection?: boolean;
}

export const LiveChartAndReplayTerminal: React.FC<LiveChartAndReplayTerminalProps> = ({
  initialSymbol = 'EUR/USD',
  onClose,
  compactMode = true,
  onNavigateTab,
  isDedicatedSection = true
}) => {
  // Selected instrument
  const [selectedSymbol, setSelectedSymbol] = useState<'EUR/USD' | 'NVDA' | 'BTC/USDT'>(
    (initialSymbol as any) || 'EUR/USD'
  );

  // Terminal operating mode: LIVE active trading vs Historical Replay DVR
  const [terminalMode, setTerminalMode] = useState<'LIVE' | 'REPLAY'>('LIVE');

  // Chart timeframe
  const [timeframe, setTimeframe] = useState<'1m' | '5m' | '15m' | '1h'>('5m');

  // Multi-chart split view: 1x1, 1x2 correlated, or 2x2 matrix
  const [gridSplit, setGridSplit] = useState<'1x1' | '1x2' | '2x2'>('1x1');

  // Viewport Fit mode (Zero-scroll mode)
  const [fitToScreen, setFitToScreen] = useState<boolean>(true);

  // Audio Alerts state
  const [isSoundMuted, setIsSoundMuted] = useState<boolean>(false);

  // Modals state
  const [isShockModalOpen, setIsShockModalOpen] = useState<boolean>(false);
  const [isHotkeysModalOpen, setIsHotkeysModalOpen] = useState<boolean>(false);

  // Inspector tab
  const [inspectorTab, setInspectorTab] = useState<'BRACKETS' | 'SIZING' | 'REPLAY'>('BRACKETS');

  // Interactive Drawing Tools state
  const [activeTool, setActiveTool] = useState<'POINTER' | 'H_LINE' | 'TRENDLINE' | 'FIBONACCI'>('POINTER');
  const [drawings, setDrawings] = useState<ChartDrawing[]>(() => {
    try {
      const saved = localStorage.getItem(`chart_drawings_${initialSymbol || 'EUR/USD'}`);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [drawingStartPoint, setDrawingStartPoint] = useState<{ price: number; candleIdx: number } | null>(null);

  // Smart Liquidity & Fair Value Gap (FVG) Overlays
  const [showFVG, setShowFVG] = useState<boolean>(true);
  const [showLiquidity, setShowLiquidity] = useState<boolean>(true);

  // Position Sizing Calculator state
  const [riskTolerancePct, setRiskTolerancePct] = useState<number>(1.0); // 1.0%
  const accountEquity = 512480.00;

  // Replay DVR Engine state
  const session = REPLAY_SESSIONS[selectedSymbol] || REPLAY_SESSIONS['EUR/USD'];
  const totalCandles = session.candles.length;
  const [replayIndex, setReplayIndex] = useState<number>(Math.floor(totalCandles * 0.75));
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);

  // Custom interactive stop-loss and take-profit state
  const [customStopLoss, setCustomStopLoss] = useState<number>(session.activePosition.stopLossPrice);
  const [customTakeProfit, setCustomTakeProfit] = useState<number>(session.activePosition.takeProfitPrice);
  const [isDraggingBracket, setIsDraggingBracket] = useState<'SL' | 'TP' | null>(null);

  // Hover and order placement state
  const [hoveredCandle, setHoveredCandle] = useState<CandleData | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);
  const [hoverPrice, setHoverPrice] = useState<number | null>(null);
  const [pendingOrders, setPendingOrders] = useState<ChartPendingOrder[]>([]);
  const [bracketUpdatedToast, setBracketUpdatedToast] = useState<string | null>(null);

  // Correlated asset session for 1x2 split
  const correlatedSymbol = selectedSymbol === 'EUR/USD' ? 'NVDA' : 'BTC/USDT';
  const correlatedSession = REPLAY_SESSIONS[correlatedSymbol] || REPLAY_SESSIONS['EUR/USD'];

  // Sync symbol changes and reload stored drawings
  useEffect(() => {
    const newSession = REPLAY_SESSIONS[selectedSymbol];
    if (newSession) {
      setCustomStopLoss(newSession.activePosition.stopLossPrice);
      setCustomTakeProfit(newSession.activePosition.takeProfitPrice);
      setReplayIndex(Math.floor(newSession.candles.length * 0.75));
    }
    try {
      const saved = localStorage.getItem(`chart_drawings_${selectedSymbol}`);
      setDrawings(saved ? JSON.parse(saved) : []);
    } catch {
      setDrawings([]);
    }
    setDrawingStartPoint(null);
  }, [selectedSymbol]);

  // Persist drawings to localStorage
  const saveDrawings = (newDrawings: ChartDrawing[]) => {
    setDrawings(newDrawings);
    try {
      localStorage.setItem(`chart_drawings_${selectedSymbol}`, JSON.stringify(newDrawings));
    } catch {
      // Ignored
    }
  };

  // Clear all drawings for symbol
  const handleClearDrawings = () => {
    saveDrawings([]);
    showToast(`All drawings cleared for ${selectedSymbol}.`);
    soundEngine.playAlertPing();
  };

  // Replay playback timer tick
  useEffect(() => {
    if (!isPlaying) return;
    const intervalMs = Math.max(100, 1000 / playbackSpeed);
    const timer = setInterval(() => {
      setReplayIndex(prev => {
        if (prev >= totalCandles - 1) {
          setIsPlaying(false);
          soundEngine.playTakeProfit();
          return prev;
        }
        return prev + 1;
      });
    }, intervalMs);
    return () => clearInterval(timer);
  }, [isPlaying, playbackSpeed, totalCandles]);

  // Visible candles based on terminal mode
  const visibleCandles = useMemo(() => {
    if (terminalMode === 'LIVE') {
      return session.candles;
    }
    return session.candles.slice(0, Math.max(10, replayIndex + 1));
  }, [terminalMode, session.candles, replayIndex]);

  // Active trade calculations
  const entryPrice = session.activePosition.entryPrice;
  const currentPrice = terminalMode === 'LIVE' 
    ? session.currentPrice 
    : visibleCandles[visibleCandles.length - 1]?.close || session.currentPrice;

  // Real-time pip/point calculations
  const multiplier = session.pipOrPointMultiplier;
  const decimals = session.decimals;

  const pipsToTarget = Math.round(Math.abs(customTakeProfit - entryPrice) * multiplier * 10) / 10;
  const pipsToStop = Math.max(0.1, Math.round(Math.abs(entryPrice - customStopLoss) * multiplier * 10) / 10);
  const livePips = Math.round((currentPrice - entryPrice) * multiplier * 10) / 10;

  // Dynamic Position Sizing Math
  const dollarRiskBudget = Math.round(accountEquity * (riskTolerancePct / 100));
  const calculatedLotSize = +(dollarRiskBudget / Math.max(1, pipsToStop * 10)).toFixed(2);
  const nominalExposure = Math.round(calculatedLotSize * (selectedSymbol.includes('/') ? 100000 : currentPrice));
  const marginRequired = Math.round(nominalExposure / 30); // 30:1 regulatory leverage

  // Dollar risk and reward based on custom inputs
  const calculatedRiskDollars = Math.round(pipsToStop * 10);
  const calculatedRewardDollars = Math.round(pipsToTarget * 10);
  const calculatedRR = pipsToStop > 0 ? (pipsToTarget / pipsToStop).toFixed(2) : '0.00';

  // Current PnL in dollars
  const calculatedLivePnl = terminalMode === 'LIVE'
    ? session.activePosition.currentPnl
    : Math.round(livePips * 10);

  // Price boundaries for SVG Chart
  const { minPrice, maxPrice, priceRange } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;

    visibleCandles.forEach(c => {
      if (c.low < min) min = c.low;
      if (c.high > max) max = c.high;
    });

    min = Math.min(min, customStopLoss, entryPrice, currentPrice);
    max = Math.max(max, customTakeProfit, entryPrice, currentPrice);

    // Add breathing room padding
    const range = max - min || 1;
    const padding = range * 0.12;

    return {
      minPrice: min - padding,
      maxPrice: max + padding,
      priceRange: max - min + padding * 2
    };
  }, [visibleCandles, customStopLoss, customTakeProfit, entryPrice, currentPrice]);

  // SVG Chart Dimensions
  const chartHeight = 360;
  const chartWidth = 720;
  const priceAxisWidth = 70;
  const timeAxisHeight = 24;
  const plotWidth = chartWidth - priceAxisWidth;
  const plotHeight = chartHeight - timeAxisHeight;

  // Coordinate transforms
  const getY = (price: number) => {
    return plotHeight - ((price - minPrice) / priceRange) * plotHeight;
  };

  const getPriceFromY = (y: number) => {
    const ratio = Math.max(0, Math.min(1, 1 - y / plotHeight));
    return +(minPrice + ratio * priceRange).toFixed(decimals);
  };

  const candleSpacing = plotWidth / Math.max(1, visibleCandles.length);
  const candleBodyWidth = Math.max(3, Math.min(16, candleSpacing * 0.7));

  // Toast notification helper
  const showToast = (msg: string) => {
    setBracketUpdatedToast(msg);
    setTimeout(() => setBracketUpdatedToast(null), 3000);
  };

  // 1-Click Order / Alert Placement
  const handlePlaceOrderAtHover = (type: 'LIMIT' | 'ALERT') => {
    if (!hoverPrice) return;
    if (type === 'LIMIT') {
      handleAddLimitOrder(session.activePosition.side === 'LONG' ? 'LIMIT_BUY' : 'LIMIT_SELL', hoverPrice);
    } else {
      handleAddLimitOrder('ALERT', hoverPrice);
    }
  };

  const handleAddLimitOrder = (type: 'LIMIT_BUY' | 'LIMIT_SELL' | 'ALERT', price: number) => {
    const newOrder: ChartPendingOrder = {
      id: `ord-${Date.now()}`,
      type,
      price,
      symbol: selectedSymbol,
      placedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setPendingOrders(prev => [...prev, newOrder]);
    soundEngine.playOrderFill();
    showToast(`${type.replace('_', ' ')} placed @ ${price.toFixed(decimals)} (Simulated Fill Queue)`);
  };

  const handleCancelOrder = (id: string) => {
    setPendingOrders(prev => prev.filter(o => o.id !== id));
    soundEngine.playAlertPing();
    showToast('Pending order cancelled.');
  };

  const handleApplyPresetRatio = (ratio: number) => {
    const currentRisk = Math.abs(entryPrice - customStopLoss);
    const newReward = currentRisk * ratio;
    const newTP = session.activePosition.side === 'LONG'
      ? +(entryPrice + newReward).toFixed(decimals)
      : +(entryPrice - newReward).toFixed(decimals);
    setCustomTakeProfit(newTP);
    soundEngine.playTakeProfit();
    showToast(`Take Profit calibrated for 1:${ratio} Risk-to-Reward ratio.`);
  };

  const handleMarketExecution = (side: 'BUY' | 'SELL') => {
    soundEngine.playOrderFill();
    showToast(`Executed MARKET ${side} on ${selectedSymbol} @ ${currentPrice.toFixed(decimals)} (Filled @ EBS ECN 22ms)`);
  };

  const handleFlattenPosition = () => {
    soundEngine.playTakeProfit();
    showToast(`Position flattened on ${selectedSymbol}. PnL realized: +$${calculatedLivePnl.toFixed(2)}`);
  };

  const handleApplyCalculatedSizing = () => {
    soundEngine.playOrderFill();
    showToast(`Sizing applied: ${calculatedLotSize} lots ($${dollarRiskBudget.toLocaleString()} Risk Budget / ${riskTolerancePct}%)`);
  };

  // Replay events
  const currentReplayTime = visibleCandles[visibleCandles.length - 1]?.time || '08:00';
  const activeEvents = session.events.filter(e => e.time <= currentReplayTime);
  const latestEvent = activeEvents[activeEvents.length - 1];

  // Quick SL/TP stepper adjustment
  const handleAdjustSL = (pipsDelta: number) => {
    const delta = pipsDelta / multiplier;
    setCustomStopLoss(prev => +(prev + delta).toFixed(decimals));
    soundEngine.playStopLoss();
    showToast(`Stop Loss adjusted by ${pipsDelta > 0 ? '+' : ''}${pipsDelta} pips.`);
  };

  const handleAdjustTP = (pipsDelta: number) => {
    const delta = pipsDelta / multiplier;
    setCustomTakeProfit(prev => +(prev + delta).toFixed(decimals));
    soundEngine.playTakeProfit();
    showToast(`Take Profit adjusted by ${pipsDelta > 0 ? '+' : ''}${pipsDelta} pips.`);
  };

  const handleSetBreakEven = () => {
    setCustomStopLoss(entryPrice);
    soundEngine.playTakeProfit();
    showToast(`Stop Loss moved to Break-Even @ ${entryPrice.toFixed(decimals)} (Zero Risk).`);
  };

  const handleTrailStop = () => {
    const trailPrice = +(currentPrice - (15 / multiplier)).toFixed(decimals);
    setCustomStopLoss(trailPrice);
    soundEngine.playStopLoss();
    showToast(`Trailing Stop set 15 pips behind market @ ${trailPrice.toFixed(decimals)}.`);
  };

  // CSV Audit Export
  const handleExportCsvAudit = () => {
    const headers = ['Time (EST)', 'Event Type', 'Price', 'Side', 'PnL ($)', 'Strategy', 'Notes'];
    const rows = session.events.map(e => [
      e.time,
      e.type,
      e.price.toFixed(decimals),
      e.side,
      e.pnl !== undefined ? e.pnl.toFixed(2) : '0.00',
      session.activePosition.strategyName,
      `"${e.note.replace(/"/g, '""')}"`
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${selectedSymbol.replace('/', '_')}_Execution_Audit_${session.sessionDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    soundEngine.playTakeProfit();
    showToast(`Exported CSV Audit log for ${selectedSymbol}.`);
  };

  // Interactive Chart Canvas Click for Drawing Tools
  const handleCanvasClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (activeTool === 'POINTER') return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const svgY = (y / rect.height) * chartHeight;
    const svgX = (x / rect.width) * chartWidth;
    const clickedPrice = getPriceFromY(svgY);
    const candleIdx = Math.floor(svgX / candleSpacing);

    if (activeTool === 'H_LINE') {
      const newDrawing: ChartDrawing = {
        id: `draw-${Date.now()}`,
        type: 'H_LINE',
        price1: clickedPrice,
        color: '#38bdf8',
        label: `S/R @ ${clickedPrice.toFixed(decimals)}`
      };
      saveDrawings([...drawings, newDrawing]);
      soundEngine.playAlertPing();
      showToast(`Horizontal Support/Resistance level placed @ ${clickedPrice.toFixed(decimals)}.`);
      setActiveTool('POINTER');
    } else if (activeTool === 'TRENDLINE' || activeTool === 'FIBONACCI') {
      if (!drawingStartPoint) {
        setDrawingStartPoint({ price: clickedPrice, candleIdx });
        soundEngine.playAlertPing();
        showToast(`Point 1 set @ ${clickedPrice.toFixed(decimals)}. Click Point 2 to complete ${activeTool}.`);
      } else {
        const newDrawing: ChartDrawing = {
          id: `draw-${Date.now()}`,
          type: activeTool,
          price1: drawingStartPoint.price,
          candleIdx1: drawingStartPoint.candleIdx,
          price2: clickedPrice,
          candleIdx2: candleIdx,
          color: activeTool === 'FIBONACCI' ? '#f59e0b' : '#a855f7',
          label: activeTool === 'FIBONACCI' ? `Fib (${Math.min(drawingStartPoint.price, clickedPrice).toFixed(decimals)} - ${Math.max(drawingStartPoint.price, clickedPrice).toFixed(decimals)})` : `Trendline`
        };
        saveDrawings([...drawings, newDrawing]);
        soundEngine.playOrderFill();
        showToast(`${activeTool === 'FIBONACCI' ? 'Fibonacci Retracement' : 'Trendline'} placed successfully.`);
        setDrawingStartPoint(null);
        setActiveTool('POINTER');
      }
    }
  };

  // Keyboard Shortcuts Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying(p => !p);
        soundEngine.playAlertPing();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setReplayIndex(prev => Math.max(0, prev - 1));
        setIsPlaying(false);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setReplayIndex(prev => Math.min(totalCandles - 1, prev + 1));
        setIsPlaying(false);
      } else if (e.key === 'b' || e.key === 'B') {
        e.preventDefault();
        handleAddLimitOrder('LIMIT_BUY', currentPrice);
      } else if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        handleAddLimitOrder('LIMIT_SELL', currentPrice);
      } else if (e.key === '1') {
        setTimeframe('1m');
      } else if (e.key === '2') {
        setTimeframe('5m');
      } else if (e.key === '3') {
        setTimeframe('15m');
      } else if (e.key === '4') {
        setTimeframe('1h');
      } else if (e.key === 'f' || e.key === 'F') {
        setFitToScreen(p => !p);
      } else if (e.key === 'm' || e.key === 'M') {
        setIsSoundMuted(p => {
          soundEngine.enabled = p;
          return !p;
        });
      } else if (e.key === 'Escape') {
        setActiveTool('POINTER');
        setDrawingStartPoint(null);
        setIsHotkeysModalOpen(false);
        setIsShockModalOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [totalCandles, currentPrice]);

  return (
    <div className={`w-full select-none flex flex-col ${fitToScreen ? 'h-full min-h-0 overflow-hidden space-y-1.5' : 'min-h-full space-y-2 pb-6'}`}>
      {/* Toast Notification */}
      {bracketUpdatedToast && (
        <div className="fixed top-16 right-6 z-50 animate-in slide-in-from-top duration-200">
          <div className="bg-slate-900 text-white px-3.5 py-2 rounded-xl shadow-2xl flex items-center gap-2 text-xs font-bold border border-slate-700">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>{bracketUpdatedToast}</span>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* 1. TOP HEADER & TELEMETRY STRIP                                         */}
      {/* ======================================================================= */}
      <div className="bg-white rounded-xl px-3 py-1.5 border border-slate-200/90 shadow-2xs flex flex-wrap items-center justify-between gap-1.5 shrink-0">
        {/* Left: Instrument Picker, Mode Switcher, Timeframe, Tools */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Instrument Chips */}
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            {(['EUR/USD', 'NVDA', 'BTC/USDT'] as const).map(sym => (
              <button
                key={sym}
                type="button"
                onClick={() => setSelectedSymbol(sym)}
                className={`px-2.5 py-1 rounded-md text-xs font-black transition-all cursor-pointer ${
                  selectedSymbol === sym
                    ? 'bg-white text-blue-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {sym}
              </button>
            ))}
          </div>

          {/* Mode Switcher: LIVE vs REPLAY */}
          <div className="flex items-center gap-0.5 bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-bold">
            <button
              type="button"
              onClick={() => {
                setTerminalMode('LIVE');
                setIsPlaying(false);
              }}
              className={`px-2.5 py-1 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
                terminalMode === 'LIVE'
                  ? 'bg-blue-600 text-white font-black shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Live Active</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setTerminalMode('REPLAY');
                setInspectorTab('REPLAY');
              }}
              className={`px-2.5 py-1 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
                terminalMode === 'REPLAY'
                  ? 'bg-amber-600 text-white font-black shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <RotateCcw className="w-3 h-3 text-white" />
              <span>Day Replay (DVR)</span>
            </button>
          </div>

          {/* Timeframe Chips */}
          <div className="hidden sm:flex items-center gap-0.5 text-[10px] font-bold text-slate-500 bg-slate-50 px-1 py-0.5 rounded-lg border border-slate-200">
            {(['1m', '5m', '15m', '1h'] as const).map(tf => (
              <button
                key={tf}
                type="button"
                onClick={() => setTimeframe(tf)}
                className={`px-1.5 py-0.5 rounded cursor-pointer ${
                  timeframe === tf ? 'bg-slate-800 text-white font-black' : 'hover:bg-slate-200 text-slate-600'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Multi-Chart Split Screen Grid Toggles */}
          <div className="flex items-center gap-0.5 bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-bold">
            <button
              type="button"
              onClick={() => setGridSplit('1x1')}
              className={`px-2 py-0.5 rounded flex items-center gap-1 cursor-pointer transition-all ${
                gridSplit === '1x1'
                  ? 'bg-white text-blue-900 shadow-2xs font-black'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Single Chart Focus (1x1)"
            >
              <Maximize2 className="w-3 h-3" />
              <span className="hidden md:inline">1x1</span>
            </button>
            <button
              type="button"
              onClick={() => setGridSplit('1x2')}
              className={`px-2 py-0.5 rounded flex items-center gap-1 cursor-pointer transition-all ${
                gridSplit === '1x2'
                  ? 'bg-blue-600 text-white shadow-2xs font-black'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title={`Correlated Split: ${session.symbol} + ${correlatedSymbol}`}
            >
              <Columns className="w-3 h-3" />
              <span className="hidden md:inline">1x2</span>
            </button>
            <button
              type="button"
              onClick={() => setGridSplit('2x2')}
              className={`px-2 py-0.5 rounded flex items-center gap-1 cursor-pointer transition-all ${
                gridSplit === '2x2'
                  ? 'bg-purple-600 text-white shadow-2xs font-black'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Quad Matrix (2x2)"
            >
              <LayoutGrid className="w-3 h-3" />
              <span className="hidden md:inline">2x2</span>
            </button>
          </div>
        </div>

        {/* Right: Sound, Hotkeys, Stress Shock, Zero-Scroll Toggle & Live Price */}
        <div className="flex items-center gap-1.5 text-xs flex-wrap">
          {/* Fit To Screen (Zero Scroll Toggle) */}
          <button
            type="button"
            onClick={() => setFitToScreen(p => !p)}
            className={`px-2 py-1 rounded-md text-[10px] font-extrabold flex items-center gap-1 border transition-all cursor-pointer ${
              fitToScreen
                ? 'bg-cyan-50 border-cyan-300 text-cyan-900 shadow-2xs'
                : 'bg-slate-100 hover:bg-slate-200 border-slate-200 text-slate-700'
            }`}
            title="Toggle Viewport Fit: Fits entire chart on screen without scrolling"
          >
            <Maximize2 className="w-3 h-3 text-cyan-600" />
            <span>Zero-Scroll: {fitToScreen ? 'ON' : 'OFF'}</span>
          </button>

          {/* Sound Toggle */}
          <button
            type="button"
            onClick={() => {
              setIsSoundMuted(p => {
                soundEngine.enabled = p;
                if (p) soundEngine.playOrderFill();
                return !p;
              });
            }}
            className={`p-1.5 rounded-md border transition-all cursor-pointer ${
              !isSoundMuted
                ? 'bg-slate-100 hover:bg-slate-200 border-slate-200 text-blue-700'
                : 'bg-slate-100 border-slate-300 text-slate-400'
            }`}
            title={!isSoundMuted ? 'Audio alerts active. Click to mute' : 'Audio alerts muted. Click to enable'}
          >
            {!isSoundMuted ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
          </button>

          {/* Keyboard Hotkeys Guide */}
          <button
            type="button"
            onClick={() => setIsHotkeysModalOpen(true)}
            className="px-2 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold border border-slate-200 transition-colors cursor-pointer flex items-center gap-1"
            title="View Keyboard Hotkeys (Space, B, S, 1-4, F, M)"
          >
            <Keyboard className="w-3 h-3 text-slate-600" />
            <span className="hidden sm:inline">Hotkeys</span>
          </button>

          {/* 1-Click Portfolio Shock Simulator */}
          <button
            type="button"
            onClick={() => setIsShockModalOpen(true)}
            className="px-2 py-1 rounded-md bg-rose-50 hover:bg-rose-100 text-rose-800 text-[10px] font-bold border border-rose-200 transition-colors cursor-pointer flex items-center gap-1"
            title="1-Click Portfolio Stress Shock Simulator (-7% Crash, Fed Hike, Crypto Depeg)"
          >
            <ShieldAlert className="w-3 h-3 text-rose-600" />
            <span className="hidden sm:inline">Stress Shock</span>
          </button>

          {/* Live Price Tag */}
          <div className="px-2.5 py-1 rounded-lg bg-slate-900 text-white flex items-center gap-1.5 font-mono">
            <span className="text-[10px] text-slate-400 font-bold uppercase">LAST:</span>
            <span className="font-black text-sm text-cyan-300">
              {currentPrice.toFixed(decimals)}
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          </div>

          {/* Trade PnL Badge */}
          <div
            className={`px-2 py-1 rounded-lg border font-mono font-bold flex items-center gap-1 ${
              calculatedLivePnl >= 0
                ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                : 'bg-rose-50 text-rose-800 border-rose-300'
            }`}
          >
            <span>P/L:</span>
            <span className="font-black">
              {calculatedLivePnl >= 0 ? `+$${calculatedLivePnl.toFixed(2)}` : `-$${Math.abs(calculatedLivePnl).toFixed(2)}`}
            </span>
          </div>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* ======================================================================= */}
      {/* 2. REPLAY DVR CONTROLS BAR (Only visible in REPLAY mode)                 */}
      {/* ======================================================================= */}
      {terminalMode === 'REPLAY' && (
        <div className="bg-gradient-to-r from-amber-500/10 via-orange-500/5 to-slate-50 border border-amber-300/80 rounded-xl px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 shrink-0 text-xs shadow-2xs">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-white p-0.5 rounded-lg border border-amber-200 shadow-2xs">
              <button
                type="button"
                onClick={() => setReplayIndex(0)}
                className="p-1 rounded text-slate-600 hover:bg-slate-100 cursor-pointer"
                title="Restart Session"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>

              <button
                type="button"
                onClick={() => setReplayIndex(prev => Math.max(0, prev - 1))}
                className="p-1 rounded text-slate-600 hover:bg-slate-100 cursor-pointer"
                title="Step 1 Bar Back (Left Arrow)"
              >
                <SkipBack className="w-3.5 h-3.5" />
              </button>

              <button
                type="button"
                onClick={() => setIsPlaying(prev => !prev)}
                className={`px-3 py-1 rounded-md font-black text-xs flex items-center gap-1 cursor-pointer transition-all active:scale-95 ${
                  isPlaying
                    ? 'bg-rose-600 text-white shadow-xs'
                    : 'bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-xs'
                }`}
              >
                {isPlaying ? (
                  <>
                    <Pause className="w-3.5 h-3.5" />
                    <span>Pause</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Play (Space)</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => setReplayIndex(prev => Math.min(totalCandles - 1, prev + 1))}
                className="p-1 rounded text-slate-600 hover:bg-slate-100 cursor-pointer"
                title="Step 1 Bar Forward (Right Arrow)"
              >
                <SkipForward className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Playback Speed */}
            <div className="flex items-center gap-1 bg-white px-2 py-0.5 rounded-lg border border-amber-200 text-xs font-bold">
              <span className="text-slate-400 text-[10px] uppercase">Speed:</span>
              {[1, 2, 5, 10].map(s => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setPlaybackSpeed(s)}
                  className={`px-1.5 py-0.2 rounded text-[10px] cursor-pointer ${
                    playbackSpeed === s
                      ? 'bg-amber-600 text-white font-black'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {s}x
                </button>
              ))}
            </div>

            {/* Current Playback Timestamp */}
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-white rounded-lg border border-amber-200 font-mono text-xs font-bold text-amber-950">
              <Clock className="w-3.5 h-3.5 text-amber-600" />
              <span>{currentReplayTime} EST</span>
              <span className="text-[10px] text-slate-400">
                (Bar {replayIndex + 1}/{totalCandles})
              </span>
            </div>
          </div>

          {/* Scrubber Range Slider */}
          <div className="flex-1 min-w-[180px] flex items-center gap-2 max-w-md">
            <span className="text-[10px] font-bold text-slate-400">04:00</span>
            <input
              type="range"
              min={0}
              max={totalCandles - 1}
              value={replayIndex}
              onChange={e => {
                setReplayIndex(Number(e.target.value));
                setIsPlaying(false);
              }}
              className="w-full h-1.5 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
            />
            <span className="text-[10px] font-bold text-slate-400">17:00</span>
          </div>

          {/* Quick jump to trade events */}
          <div className="flex items-center gap-1">
            {session.events.map(evt => (
              <button
                key={evt.id}
                type="button"
                onClick={() => {
                  const targetIdx = session.candles.findIndex(c => c.time === evt.time);
                  if (targetIdx !== -1) {
                    setReplayIndex(targetIdx);
                    setIsPlaying(false);
                    soundEngine.playAlertPing();
                  }
                }}
                className={`px-2 py-0.5 rounded text-[9px] font-black uppercase border transition-all cursor-pointer ${
                  evt.type === 'ENTRY'
                    ? 'bg-blue-50 text-blue-800 border-blue-300 hover:bg-blue-100'
                    : evt.type === 'TAKE_PROFIT'
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
                    : 'bg-amber-50 text-amber-900 border-amber-300 hover:bg-amber-100'
                }`}
              >
                {evt.type === 'ENTRY' ? '▶ Entry' : evt.type === 'TAKE_PROFIT' ? '★ TP Hit' : '🛡 Stop Trail'}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* 3. MAIN WORKSPACE: CHART VIEWPORT (LEFT) + INSPECTOR (RIGHT)            */}
      {/* ======================================================================= */}
      <div className={`flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2 ${fitToScreen ? 'overflow-hidden' : ''}`}>
        {/* CHART VIEWPORT (8 Cols) */}
        {gridSplit === '2x2' ? (
          <div className="lg:col-span-8 grid grid-cols-2 grid-rows-2 gap-2 min-h-0 overflow-hidden">
            {(['EUR/USD', 'NVDA', 'BTC/USDT', 'QQQ'] as const).map(sym => {
              const quadSession = REPLAY_SESSIONS[sym] || REPLAY_SESSIONS['EUR/USD'];
              return (
                <MiniCandleChart
                  key={sym}
                  session={quadSession}
                  timeframe={timeframe}
                  replayIndex={replayIndex}
                  terminalMode={terminalMode}
                  onFocus={() => {
                    setSelectedSymbol(sym as any);
                    setGridSplit('1x1');
                  }}
                  isFocused={selectedSymbol === sym}
                />
              );
            })}
          </div>
        ) : (
          <div className={`lg:col-span-8 ${gridSplit === '1x2' ? 'grid grid-cols-1 xl:grid-cols-2 gap-2' : ''} flex flex-col min-h-0 overflow-hidden`}>
            <div className="bg-slate-950 rounded-xl border border-slate-800 shadow-2xs flex flex-col flex-1 min-h-0 relative overflow-hidden">
              {/* Chart Action Toolbar: Interactive Drawings & Smart Overlays */}
              <div className="px-3 py-1 bg-slate-900 border-b border-slate-800 flex flex-wrap items-center justify-between text-xs text-slate-300 shrink-0 gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-black text-white text-xs tracking-wide">
                    {session.symbol} · {timeframe}
                  </span>
                  <span className="px-1.5 py-0.2 rounded text-[8px] font-bold bg-blue-900/60 text-blue-300 border border-blue-700">
                    {session.activePosition.strategyName}
                  </span>

                  {/* Drawing Tools Selector */}
                  <div className="flex items-center gap-0.5 bg-slate-950 p-0.5 rounded border border-slate-800 text-[10px]">
                    <button
                      type="button"
                      onClick={() => setActiveTool('POINTER')}
                      className={`p-1 rounded cursor-pointer ${
                        activeTool === 'POINTER' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                      }`}
                      title="Pointer / Pan Tool"
                    >
                      <MousePointer className="w-3 h-3" />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setActiveTool('H_LINE');
                        soundEngine.playAlertPing();
                        showToast('Click anywhere on chart to place a Horizontal Support/Resistance Level.');
                      }}
                      className={`p-1 rounded cursor-pointer flex items-center gap-1 ${
                        activeTool === 'H_LINE' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                      }`}
                      title="Draw Horizontal S/R Line"
                    >
                      <Minus className="w-3 h-3" />
                      <span className="text-[8.5px]">H-Line</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setActiveTool('TRENDLINE');
                        setDrawingStartPoint(null);
                        soundEngine.playAlertPing();
                        showToast('Click point 1 then point 2 on chart to draw a Trendline.');
                      }}
                      className={`p-1 rounded cursor-pointer flex items-center gap-1 ${
                        activeTool === 'TRENDLINE' ? 'bg-purple-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                      }`}
                      title="Draw Trendline (Click 2 points)"
                    >
                      <TrendingUp className="w-3 h-3" />
                      <span className="text-[8.5px]">Trend</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setActiveTool('FIBONACCI');
                        setDrawingStartPoint(null);
                        soundEngine.playAlertPing();
                        showToast('Click high then low to draw Fibonacci Retracement Levels.');
                      }}
                      className={`p-1 rounded cursor-pointer flex items-center gap-1 ${
                        activeTool === 'FIBONACCI' ? 'bg-amber-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                      }`}
                      title="Draw Fibonacci Retracement"
                    >
                      <Layers className="w-3 h-3" />
                      <span className="text-[8.5px]">Fib</span>
                    </button>

                    {drawings.length > 0 && (
                      <button
                        type="button"
                        onClick={handleClearDrawings}
                        className="p-1 rounded text-rose-400 hover:text-rose-300 hover:bg-rose-950/50 cursor-pointer ml-1"
                        title="Clear All Drawings"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Overlays: FVG & Liquidity Toggles */}
                <div className="flex items-center gap-1.5 text-[10px]">
                  <button
                    type="button"
                    onClick={() => setShowFVG(p => !p)}
                    className={`px-1.5 py-0.5 rounded font-mono font-bold cursor-pointer border transition-colors ${
                      showFVG
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                        : 'bg-slate-800 text-slate-500 border-slate-700'
                    }`}
                    title="Toggle Fair Value Gap (FVG) Imbalance Overlays"
                  >
                    FVG Imbalances: {showFVG ? 'ON' : 'OFF'}
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowLiquidity(p => !p)}
                    className={`px-1.5 py-0.5 rounded font-mono font-bold cursor-pointer border transition-colors ${
                      showLiquidity
                        ? 'bg-blue-950 text-blue-300 border-blue-800'
                        : 'bg-slate-800 text-slate-500 border-slate-700'
                    }`}
                    title="Toggle Buyside / Sellside Liquidity Pool Lines"
                  >
                    Liquidity Pools: {showLiquidity ? 'ON' : 'OFF'}
                  </button>
                </div>
              </div>

              {/* SVG Vector Chart Canvas */}
              <div className="flex-1 min-h-0 relative overflow-hidden bg-slate-950 flex items-center justify-center p-1">
                {/* Floating Tool Active Banner */}
                {activeTool !== 'POINTER' && (
                  <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-cyan-700 text-white px-3 py-0.5 rounded-full text-[10px] font-bold shadow-xl animate-pulse z-30 flex items-center gap-1.5 border border-cyan-400">
                    <MousePointer className="w-3 h-3" />
                    <span>Drawing Mode Active: Click chart to place {activeTool} (Press Esc to cancel)</span>
                  </div>
                )}

                {/* Floating Drag Indicator */}
                {isDraggingBracket && (
                  <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-blue-600 text-white px-3.5 py-0.5 rounded-full text-[10px] font-black shadow-2xl animate-pulse z-30 flex items-center gap-1.5 border border-blue-400">
                    <Sliders className="w-3 h-3" />
                    <span>
                      Calibrating {isDraggingBracket === 'SL' ? 'Stop Loss' : 'Take Profit'} · Release mouse to deploy
                    </span>
                  </div>
                )}

                <svg
                  className={`w-full h-full overflow-visible ${
                    isDraggingBracket ? 'cursor-ns-resize select-none' : activeTool !== 'POINTER' ? 'cursor-crosshair' : ''
                  }`}
                  viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                  preserveAspectRatio="none"
                  onClick={handleCanvasClick}
                  onMouseMove={e => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    const svgY = (y / rect.height) * chartHeight;
                    const svgX = (x / rect.width) * chartWidth;

                    const candleIdx = Math.floor(svgX / candleSpacing);
                    if (candleIdx >= 0 && candleIdx < visibleCandles.length) {
                      setHoveredCandle(visibleCandles[candleIdx]);
                      setMousePos({ x, y });
                    }

                    const calcPrice = getPriceFromY(svgY);
                    setHoverPrice(calcPrice);

                    if (isDraggingBracket === 'SL') {
                      if (calcPrice < entryPrice) {
                        setCustomStopLoss(calcPrice);
                      }
                    } else if (isDraggingBracket === 'TP') {
                      if (calcPrice > entryPrice) {
                        setCustomTakeProfit(calcPrice);
                      }
                    }
                  }}
                  onMouseLeave={() => {
                    setHoveredCandle(null);
                    setHoverPrice(null);
                    setIsDraggingBracket(null);
                  }}
                  onMouseUp={() => {
                    if (isDraggingBracket) {
                      soundEngine.playTakeProfit();
                      showToast(`Bracket ${isDraggingBracket} calibrated successfully.`);
                    }
                    setIsDraggingBracket(null);
                  }}
                >
                  <defs>
                    <linearGradient id="bull-fvg-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#10b981" stopOpacity="0.08" />
                    </linearGradient>
                    <linearGradient id="bear-fvg-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.08" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal Price Grid Lines */}
                  {[0.1, 0.3, 0.5, 0.7, 0.9].map((ratio, idx) => {
                    const y = plotHeight * ratio;
                    const price = minPrice + (1 - ratio) * priceRange;
                    return (
                      <g key={`grid-${idx}`}>
                        <line x1={0} y1={y} x2={plotWidth} y2={y} stroke="#1e293b" strokeDasharray="3 3" strokeWidth={1} />
                        <text x={plotWidth + 8} y={y + 3} fill="#64748b" fontSize={7.5} fontFamily="monospace">
                          {price.toFixed(decimals)}
                        </text>
                      </g>
                    );
                  })}

                  {/* SMART LIQUIDITY POOLS (BSL & SSL) */}
                  {showLiquidity && (
                    <g id="liquidity-pools">
                      {/* Buyside Liquidity (BSL) */}
                      <line
                        x1={0}
                        y1={getY(maxPrice - priceRange * 0.05)}
                        x2={plotWidth}
                        y2={getY(maxPrice - priceRange * 0.05)}
                        stroke="#38bdf8"
                        strokeDasharray="4 2"
                        strokeWidth={1.25}
                      />
                      <rect x={plotWidth - 110} y={getY(maxPrice - priceRange * 0.05) - 10} width={105} height={13} fill="#0369a1" rx={2} />
                      <text x={plotWidth - 58} y={getY(maxPrice - priceRange * 0.05) - 1} fill="#ffffff" fontSize={6.5} fontWeight="bold" textAnchor="middle">
                        ★ BUY-SIDE LIQUIDITY
                      </text>

                      {/* Sellside Liquidity (SSL) */}
                      <line
                        x1={0}
                        y1={getY(minPrice + priceRange * 0.05)}
                        x2={plotWidth}
                        y2={getY(minPrice + priceRange * 0.05)}
                        stroke="#f43f5e"
                        strokeDasharray="4 2"
                        strokeWidth={1.25}
                      />
                      <rect x={plotWidth - 110} y={getY(minPrice + priceRange * 0.05) - 3} width={105} height={13} fill="#881337" rx={2} />
                      <text x={plotWidth - 58} y={getY(minPrice + priceRange * 0.05) + 6} fill="#ffffff" fontSize={6.5} fontWeight="bold" textAnchor="middle">
                        ★ SELL-SIDE LIQUIDITY
                      </text>
                    </g>
                  )}

                  {/* SMART FAIR VALUE GAPS (FVG) */}
                  {showFVG && visibleCandles.length > 8 && (
                    <g id="fvg-overlays">
                      {/* Bullish FVG Imbalance box */}
                      <rect
                        x={Math.max(0, (visibleCandles.length - 12) * candleSpacing)}
                        y={getY(entryPrice + (12 / multiplier))}
                        width={candleSpacing * 6}
                        height={Math.abs(getY(entryPrice + (12 / multiplier)) - getY(entryPrice - (4 / multiplier)))}
                        fill="url(#bull-fvg-grad)"
                        stroke="#10b981"
                        strokeDasharray="2 2"
                        strokeWidth={1}
                      />
                      <text
                        x={Math.max(0, (visibleCandles.length - 12) * candleSpacing) + 6}
                        y={getY(entryPrice + (12 / multiplier)) + 10}
                        fill="#34d399"
                        fontSize={6.5}
                        fontWeight="bold"
                        fontFamily="monospace"
                      >
                        BULLISH FVG (Imbalance)
                      </text>
                    </g>
                  )}

                  {/* USER CHART DRAWINGS */}
                  <g id="user-drawings">
                    {drawings.map(d => {
                      if (d.type === 'H_LINE') {
                        const y = getY(d.price1);
                        return (
                          <g key={d.id}>
                            <line x1={0} y1={y} x2={plotWidth} y2={y} stroke={d.color} strokeWidth={1.5} strokeDasharray="3 3" />
                            <rect x={plotWidth - 90} y={y - 8} width={85} height={15} fill="#0f172a" stroke={d.color} strokeWidth={1} rx={3} />
                            <text x={plotWidth - 48} y={y + 3} fill="#ffffff" fontSize={7} fontWeight="bold" textAnchor="middle">
                              {d.label}
                            </text>
                          </g>
                        );
                      }
                      if (d.type === 'TRENDLINE' && d.candleIdx1 !== undefined && d.candleIdx2 !== undefined && d.price2 !== undefined) {
                        const x1 = d.candleIdx1 * candleSpacing + candleSpacing / 2;
                        const y1 = getY(d.price1);
                        const x2 = d.candleIdx2 * candleSpacing + candleSpacing / 2;
                        const y2 = getY(d.price2);
                        return (
                          <g key={d.id}>
                            <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={d.color} strokeWidth={2} />
                            <circle cx={x1} cy={y1} r={3} fill={d.color} />
                            <circle cx={x2} cy={y2} r={3} fill={d.color} />
                            <text x={x2 + 4} y={y2 + 2} fill={d.color} fontSize={7} fontWeight="bold">
                              Trend
                            </text>
                          </g>
                        );
                      }
                      if (d.type === 'FIBONACCI' && d.price2 !== undefined) {
                        const highP = Math.max(d.price1, d.price2);
                        const lowP = Math.min(d.price1, d.price2);
                        const diff = highP - lowP;
                        const fibLevels = [
                          { pct: '0.0%', p: highP, color: '#94a3b8' },
                          { pct: '23.6%', p: highP - diff * 0.236, color: '#38bdf8' },
                          { pct: '38.2%', p: highP - diff * 0.382, color: '#818cf8' },
                          { pct: '50.0%', p: highP - diff * 0.5, color: '#fbbf24' },
                          { pct: '61.8% (Golden)', p: highP - diff * 0.618, color: '#f59e0b' },
                          { pct: '100.0%', p: lowP, color: '#94a3b8' }
                        ];
                        return (
                          <g key={d.id}>
                            {/* Golden pocket zone */}
                            <rect
                              x={0}
                              y={getY(highP - diff * 0.5)}
                              width={plotWidth}
                              height={Math.abs(getY(highP - diff * 0.5) - getY(highP - diff * 0.618))}
                              fill="rgba(245, 158, 11, 0.12)"
                            />
                            {fibLevels.map((lvl, lIdx) => {
                              const y = getY(lvl.p);
                              return (
                                <g key={`fib-${lIdx}`}>
                                  <line x1={0} y1={y} x2={plotWidth} y2={y} stroke={lvl.color} strokeDasharray="2 2" strokeWidth={1} />
                                  <text x={8} y={y - 2} fill={lvl.color} fontSize={6.5} fontWeight="bold" fontFamily="monospace">
                                    Fib {lvl.pct} ({lvl.p.toFixed(decimals)})
                                  </text>
                                </g>
                              );
                            })}
                          </g>
                        );
                      }
                      return null;
                    })}
                  </g>

                  {/* Volume Bars at Bottom */}
                  {visibleCandles.map((c, i) => {
                    const x = i * candleSpacing + candleSpacing / 2;
                    const maxVol = Math.max(...visibleCandles.map(v => v.volume), 1);
                    const volHeight = (c.volume / maxVol) * 45;
                    const isBull = c.close >= c.open;

                    return (
                      <rect
                        key={`vol-${i}`}
                        x={x - candleBodyWidth / 2}
                        y={plotHeight - volHeight}
                        width={candleBodyWidth}
                        height={volHeight}
                        fill={isBull ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)'}
                      />
                    );
                  })}

                  {/* Candlesticks (Wick + Body) */}
                  {visibleCandles.map((c, i) => {
                    const x = i * candleSpacing + candleSpacing / 2;
                    const yOpen = getY(c.open);
                    const yClose = getY(c.close);
                    const yHigh = getY(c.high);
                    const yLow = getY(c.low);
                    const isBull = c.close >= c.open;
                    const bodyTop = Math.min(yOpen, yClose);
                    const bodyHeight = Math.max(2, Math.abs(yClose - yOpen));

                    return (
                      <g key={`candle-${i}`}>
                        <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={isBull ? '#10b981' : '#f43f5e'} strokeWidth={1.5} />
                        <rect
                          x={x - candleBodyWidth / 2}
                          y={bodyTop}
                          width={candleBodyWidth}
                          height={bodyHeight}
                          fill={isBull ? '#10b981' : '#f43f5e'}
                        />
                      </g>
                    );
                  })}

                  {/* ENTRY LINE */}
                  <g>
                    <line x1={0} y1={getY(entryPrice)} x2={plotWidth} y2={getY(entryPrice)} stroke="#3b82f6" strokeWidth={1.5} />
                    <rect x={plotWidth - 75} y={getY(entryPrice) - 8} width={70} height={16} fill="#1e3a8a" rx={3} />
                    <text x={plotWidth - 40} y={getY(entryPrice) + 3} fill="#ffffff" fontSize={7.5} fontWeight="bold" textAnchor="middle">
                      ENTRY {entryPrice.toFixed(decimals)}
                    </text>
                  </g>

                  {/* TAKE PROFIT LINE (Draggable) */}
                  <g
                    className="cursor-ns-resize"
                    onMouseDown={e => {
                      e.stopPropagation();
                      setIsDraggingBracket('TP');
                    }}
                  >
                    <line x1={0} y1={getY(customTakeProfit)} x2={plotWidth} y2={getY(customTakeProfit)} stroke="#10b981" strokeWidth={1.75} strokeDasharray="4 2" />
                    <rect x={plotWidth - 85} y={getY(customTakeProfit) - 8} width={80} height={16} fill="#065f46" rx={3} />
                    <text x={plotWidth - 45} y={getY(customTakeProfit) + 3} fill="#ffffff" fontSize={7.5} fontWeight="bold" textAnchor="middle">
                      TP: {customTakeProfit.toFixed(decimals)}
                    </text>
                  </g>

                  {/* STOP LOSS LINE (Draggable) */}
                  <g
                    className="cursor-ns-resize"
                    onMouseDown={e => {
                      e.stopPropagation();
                      setIsDraggingBracket('SL');
                    }}
                  >
                    <line x1={0} y1={getY(customStopLoss)} x2={plotWidth} y2={getY(customStopLoss)} stroke="#f43f5e" strokeWidth={1.75} strokeDasharray="4 2" />
                    <rect x={plotWidth - 85} y={getY(customStopLoss) - 8} width={80} height={16} fill="#881337" rx={3} />
                    <text x={plotWidth - 45} y={getY(customStopLoss) + 3} fill="#ffffff" fontSize={7.5} fontWeight="bold" textAnchor="middle">
                      SL: {customStopLoss.toFixed(decimals)}
                    </text>
                  </g>

                  {/* CURRENT PRICE LIVE TICK LINE */}
                  <g>
                    <line x1={0} y1={getY(currentPrice)} x2={plotWidth} y2={getY(currentPrice)} stroke="#06b6d4" strokeWidth={1.25} />
                    <circle cx={plotWidth - 6} cy={getY(currentPrice)} r={3.5} fill="#06b6d4" />
                  </g>

                  {/* Hover Crosshair */}
                  {hoverPrice && mousePos && (
                    <g>
                      <line x1={0} y1={getY(hoverPrice)} x2={plotWidth} y2={getY(hoverPrice)} stroke="#64748b" strokeDasharray="2 2" strokeWidth={0.75} />
                      <line x1={mousePos.x} y1={0} x2={mousePos.x} y2={plotHeight} stroke="#64748b" strokeDasharray="2 2" strokeWidth={0.75} />
                    </g>
                  )}
                </svg>

                {/* Hover Tooltip Overlay */}
                {hoveredCandle && (
                  <div className="absolute top-2 left-2 bg-slate-900/95 border border-slate-700 text-white p-2 rounded-lg text-[10px] font-mono shadow-2xl space-y-0.5 pointer-events-none z-20">
                    <div className="text-cyan-400 font-bold border-b border-slate-800 pb-0.5">
                      Time: {hoveredCandle.time} EST
                    </div>
                    <div className="grid grid-cols-2 gap-x-2 text-[9px]">
                      <div>O: <span className="text-white font-bold">{hoveredCandle.open.toFixed(decimals)}</span></div>
                      <div>H: <span className="text-emerald-400 font-bold">{hoveredCandle.high.toFixed(decimals)}</span></div>
                      <div>L: <span className="text-rose-400 font-bold">{hoveredCandle.low.toFixed(decimals)}</span></div>
                      <div>C: <span className="text-cyan-300 font-bold">{hoveredCandle.close.toFixed(decimals)}</span></div>
                    </div>
                    <div className="text-slate-400 text-[8px] pt-0.5">
                      Vol: {hoveredCandle.volume.toLocaleString()}
                    </div>
                  </div>
                )}
              </div>

              {/* Bottom Chart Footer Legend & Execution Gateway Telemetry */}
              <div className="px-3 py-1.5 bg-slate-900 border-t border-slate-800 flex flex-wrap items-center justify-between gap-1.5 text-[10px] text-slate-300 shrink-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="flex items-center gap-1.5 bg-blue-950/70 border border-blue-800/80 px-2 py-0.5 rounded">
                    <span className="w-2 h-1 bg-blue-400 rounded-full" />
                    <span className="text-white font-mono font-bold">Entry: {entryPrice.toFixed(decimals)}</span>
                  </span>
                  <span className="flex items-center gap-1.5 bg-emerald-950/70 border border-emerald-800/80 px-2 py-0.5 rounded">
                    <span className="w-2 h-1 bg-emerald-400 rounded-full" />
                    <span className="text-emerald-300 font-mono font-bold">TP: {customTakeProfit.toFixed(decimals)}</span>
                    <span className="text-emerald-400 font-bold text-[9px]">(+{pipsToTarget} p)</span>
                  </span>
                  <span className="flex items-center gap-1.5 bg-rose-950/70 border border-rose-800/80 px-2 py-0.5 rounded">
                    <span className="w-2 h-1 bg-rose-400 rounded-full" />
                    <span className="text-rose-300 font-mono font-bold">SL: {customStopLoss.toFixed(decimals)}</span>
                    <span className="text-rose-400 font-bold text-[9px]">(-{pipsToStop} p)</span>
                  </span>
                </div>

                <div className="flex items-center gap-2.5">
                  <span className="text-[9.5px] text-slate-400 font-mono">
                    Spread: <strong className="text-slate-200">{session.activePosition.spreadPips} pips</strong>
                  </span>
                  <span className="text-slate-700">|</span>
                  <span className="text-[9.5px] text-slate-400">Alpaca Sim Gateway</span>
                  <span className="px-1.5 py-0.2 rounded text-[8.5px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-black flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>Zero Real Risk</span>
                  </span>
                </div>
              </div>
            </div>

            {/* In 1x2 mode, also render the second synchronized companion chart */}
            {gridSplit === '1x2' && (
              <MiniCandleChart
                session={correlatedSession}
                timeframe={timeframe}
                replayIndex={replayIndex}
                terminalMode={terminalMode}
                onFocus={() => {
                  setSelectedSymbol(correlatedSymbol as any);
                  setGridSplit('1x1');
                }}
              />
            )}
          </div>
        )}

        {/* ===================================================================== */}
        {/* RIGHT INSPECTOR & TRADE MANAGER (4 Columns)                           */}
        {/* ===================================================================== */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs flex flex-col min-h-0 overflow-hidden">
          {/* Sub-Tab Navigation inside Inspector */}
          <div className="p-1 bg-slate-100 border-b border-slate-200 flex items-center gap-1 text-[11px] font-bold shrink-0">
            <button
              type="button"
              onClick={() => setInspectorTab('BRACKETS')}
              className={`flex-1 py-1 rounded text-center transition-all cursor-pointer ${
                inspectorTab === 'BRACKETS'
                  ? 'bg-white text-blue-900 shadow-2xs font-black'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Active Brackets
            </button>
            <button
              type="button"
              onClick={() => setInspectorTab('SIZING')}
              className={`flex-1 py-1 rounded text-center transition-all cursor-pointer flex items-center justify-center gap-1 ${
                inspectorTab === 'SIZING'
                  ? 'bg-white text-purple-900 shadow-2xs font-black'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Calculator className="w-3 h-3 text-purple-600" />
              <span>Position Sizer</span>
            </button>
            {terminalMode === 'REPLAY' && (
              <button
                type="button"
                onClick={() => setInspectorTab('REPLAY')}
                className={`flex-1 py-1 rounded text-center transition-all cursor-pointer ${
                  inspectorTab === 'REPLAY'
                    ? 'bg-white text-amber-900 shadow-2xs font-black'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Replay Journal
              </button>
            )}
          </div>

          {/* INSPECTOR BODY */}
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-3 space-y-2.5 text-xs">
            {inspectorTab === 'BRACKETS' && (
              <>
                {/* Trade Position Header */}
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-50/70 to-slate-50 border border-blue-200/80 space-y-1.5 shadow-2xs">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-blue-100 text-blue-900 border border-blue-300">
                      ACTIVE POSITION
                    </span>
                    <span className="font-mono text-[9px] font-extrabold text-slate-500">
                      ID: pos-8842
                    </span>
                  </div>

                  <div className="flex items-center justify-between pt-0.5">
                    <div>
                      <h3 className="text-sm font-black text-slate-900 leading-tight">
                        {session.symbol} · {session.activePosition.side}
                      </h3>
                      <p className="text-[10px] text-slate-500 font-medium">
                        {session.activePosition.size}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-black text-emerald-600">
                        +${calculatedLivePnl.toFixed(2)}
                      </div>
                      <div className="text-[9.5px] font-bold text-emerald-700">
                        +{livePips} pips
                      </div>
                    </div>
                  </div>
                </div>

                {/* Risk / Reward Metrics Meter */}
                <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase text-slate-700 flex items-center gap-1">
                      <Activity className="w-3.5 h-3.5 text-blue-600" />
                      <span>Dynamic Risk / Reward Meter</span>
                    </span>
                    <span className="text-xs font-black text-blue-700 font-mono bg-white px-1.5 py-0.2 rounded border border-blue-200">
                      1 : {calculatedRR} R:R
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono">
                    <div className="p-1.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-950">
                      <span className="text-[8px] uppercase block text-rose-700 font-bold">Max Dollar Risk:</span>
                      <strong className="text-xs font-black text-rose-700">-${calculatedRiskDollars}.00</strong>
                      <span className="text-[8.5px] block text-rose-600">({pipsToStop} pips)</span>
                    </div>

                    <div className="p-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-950">
                      <span className="text-[8px] uppercase block text-emerald-700 font-bold">Target Reward:</span>
                      <strong className="text-xs font-black text-emerald-700">+${calculatedRewardDollars}.00</strong>
                      <span className="text-[8.5px] block text-emerald-600">({pipsToTarget} pips)</span>
                    </div>
                  </div>
                </div>

                {/* Interactive Bracket Adjusters */}
                <div className="p-2.5 rounded-xl bg-white border border-slate-200 space-y-2 shadow-2xs">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-1">
                    <span className="text-[10px] font-black uppercase text-slate-800 flex items-center gap-1">
                      <Sliders className="w-3.5 h-3.5 text-purple-600" />
                      <span>Interactive Bracket Steppers</span>
                    </span>
                    <span className="text-[9px] text-slate-400">Drag or Step</span>
                  </div>

                  {/* Stop Loss Steppers */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-bold text-rose-900">Stop Loss:</span>
                      <span className="font-mono font-bold text-slate-900">{customStopLoss.toFixed(decimals)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleAdjustSL(-5)}
                        className="flex-1 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-bold text-[10px] cursor-pointer"
                      >
                        -5 pips
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAdjustSL(-1)}
                        className="flex-1 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-bold text-[10px] cursor-pointer"
                      >
                        -1 pip
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAdjustSL(1)}
                        className="flex-1 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-bold text-[10px] cursor-pointer"
                      >
                        +1 pip
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAdjustSL(5)}
                        className="flex-1 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-bold text-[10px] cursor-pointer"
                      >
                        +5 pips
                      </button>
                    </div>
                  </div>

                  {/* Take Profit Steppers */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-bold text-emerald-900">Take Profit:</span>
                      <span className="font-mono font-bold text-slate-900">{customTakeProfit.toFixed(decimals)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleAdjustTP(-5)}
                        className="flex-1 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 font-bold text-[10px] cursor-pointer"
                      >
                        -5 pips
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAdjustTP(-1)}
                        className="flex-1 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 font-bold text-[10px] cursor-pointer"
                      >
                        -1 pip
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAdjustTP(1)}
                        className="flex-1 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 font-bold text-[10px] cursor-pointer"
                      >
                        +1 pip
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAdjustTP(5)}
                        className="flex-1 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 font-bold text-[10px] cursor-pointer"
                      >
                        +5 pips
                      </button>
                    </div>
                  </div>

                  {/* Smart Actions */}
                  <div className="grid grid-cols-2 gap-1.5 pt-1 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={handleSetBreakEven}
                      className="py-1 px-2 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-800 border border-blue-200 font-bold text-[10px] cursor-pointer transition-colors"
                    >
                      🛡 Move to Break-Even
                    </button>
                    <button
                      type="button"
                      onClick={handleTrailStop}
                      className="py-1 px-2 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 font-bold text-[10px] cursor-pointer transition-colors"
                    >
                      ⚡ Trail 15 Pips
                    </button>
                  </div>
                </div>

                {/* Instant Market Execution Buttons */}
                <div className="grid grid-cols-2 gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleMarketExecution('BUY')}
                    className="py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs cursor-pointer shadow-xs transition-colors flex items-center justify-center gap-1"
                  >
                    <span>BUY MARKET (B)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMarketExecution('SELL')}
                    className="py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-black text-xs cursor-pointer shadow-xs transition-colors flex items-center justify-center gap-1"
                  >
                    <span>SELL MARKET (S)</span>
                  </button>
                </div>
              </>
            )}

            {/* POSITION SIZER TAB */}
            {inspectorTab === 'SIZING' && (
              <div className="space-y-3">
                <div className="p-2.5 rounded-xl bg-purple-50 border border-purple-200 space-y-1">
                  <span className="text-[9px] font-black uppercase text-purple-900 block">
                    DYNAMIC POSITION SIZING CALCULATOR
                  </span>
                  <p className="text-[10px] text-purple-800">
                    Risk-based mathematical position sizing formula: <code>Lot Size = Risk Budget / (SL Pips × Multiplier)</code>
                  </p>
                </div>

                {/* Account Equity & Risk Budget */}
                <div className="p-2.5 rounded-xl bg-white border border-slate-200 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Account Equity:</span>
                    <span className="font-mono font-black text-slate-900">
                      ${accountEquity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-600 font-bold">Risk Per Trade:</span>
                      <span className="font-mono font-black text-purple-700">{riskTolerancePct}% (${dollarRiskBudget.toLocaleString()})</span>
                    </div>
                    <div className="grid grid-cols-4 gap-1">
                      {[0.5, 1.0, 1.5, 2.0].map(pct => (
                        <button
                          key={pct}
                          type="button"
                          onClick={() => setRiskTolerancePct(pct)}
                          className={`py-1 rounded text-[10px] font-bold border transition-colors cursor-pointer ${
                            riskTolerancePct === pct
                              ? 'bg-purple-600 text-white border-purple-700 shadow-2xs'
                              : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                          }`}
                        >
                          {pct}%
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[11px]">
                    <span className="text-slate-500">Stop Loss Distance:</span>
                    <span className="font-mono font-bold text-rose-600">{pipsToStop} pips</span>
                  </div>
                </div>

                {/* Sizing Recommendation Results */}
                <div className="p-3 rounded-xl bg-slate-900 text-white space-y-2 shadow-2xs font-mono">
                  <div className="text-[9.5px] uppercase font-bold text-slate-400">
                    Recommended Order Sizing:
                  </div>
                  <div className="flex items-baseline justify-between border-b border-slate-800 pb-2">
                    <span className="text-xs text-slate-300 font-sans">Calculated Lots:</span>
                    <span className="text-lg font-black text-cyan-400">{calculatedLotSize} Lots</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[10px] pt-1">
                    <div>
                      <span className="text-slate-400 block text-[8.5px]">Max Dollar Risk:</span>
                      <span className="text-rose-400 font-bold">-${dollarRiskBudget.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[8.5px]">Margin Required:</span>
                      <span className="text-slate-200 font-bold">${marginRequired.toLocaleString()}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleApplyCalculatedSizing}
                    className="w-full py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-black text-xs cursor-pointer shadow-md transition-all mt-2"
                  >
                    Apply Sizing to Active Order
                  </button>
                </div>
              </div>
            )}

            {/* REPLAY JOURNAL TAB */}
            {inspectorTab === 'REPLAY' && (
              <div className="space-y-2.5">
                <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-between">
                  <div>
                    <span className="text-[9px] font-black uppercase text-amber-950 block">
                      REPLAY JOURNAL AUDIT
                    </span>
                    <span className="text-[10px] text-amber-800">
                      {session.events.length} Recorded executions
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleExportCsvAudit}
                    className="px-2.5 py-1 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-[10px] flex items-center gap-1 cursor-pointer transition-colors shadow-2xs"
                  >
                    <Download className="w-3 h-3" />
                    <span>Export CSV</span>
                  </button>
                </div>

                {/* Day's Trade Execution Cards */}
                <div className="space-y-1.5">
                  {session.events.map(evt => (
                    <div
                      key={evt.id}
                      onClick={() => {
                        const targetIdx = session.candles.findIndex(c => c.time === evt.time);
                        if (targetIdx !== -1) {
                          setReplayIndex(targetIdx);
                          setIsPlaying(false);
                          soundEngine.playAlertPing();
                        }
                      }}
                      className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-all cursor-pointer space-y-1 shadow-2xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] font-black uppercase px-1.5 py-0.2 rounded bg-slate-100 text-slate-800">
                          {evt.time} EST · {evt.type}
                        </span>
                        {evt.pnl !== undefined && (
                          <span className="font-mono font-black text-[10px] text-emerald-600">
                            +${evt.pnl.toFixed(2)}
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-700 leading-tight">
                        {evt.note}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* PORTFOLIO SHOCK SIMULATOR MODAL */}
      <PortfolioShockSimulatorModal
        isOpen={isShockModalOpen}
        onClose={() => setIsShockModalOpen(false)}
        currentEquity={accountEquity}
        openPositionsCount={3}
        onApplyDefensiveStops={handleTrailStop}
      />

      {/* KEYBOARD SHORTCUTS CHEAT SHEET MODAL */}
      {isHotkeysModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden flex flex-col text-white">
            <div className="px-4 py-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Keyboard className="w-4 h-4 text-cyan-400" />
                <h3 className="font-black text-xs text-white tracking-wide">
                  TERMINAL KEYBOARD SHORTCUTS
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsHotkeysModalOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 space-y-2 text-xs divide-y divide-slate-800">
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-300">Play / Pause DVR Replay</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-cyan-300">Space</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-300">Step 1 Bar Back / Forward</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-cyan-300">← / →</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-300">Quick Market Buy</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-emerald-400">B</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-300">Quick Market Sell</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-rose-400">S</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-300">Timeframe Switch</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-purple-300">1, 2, 3, 4</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-300">Toggle Zero-Scroll Fit</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-blue-300">F</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-300">Toggle Audio Mute</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-yellow-300">M</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-300">Clear Active Tool / Close</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-slate-300">Esc</kbd>
              </div>
            </div>
            <div className="px-4 py-2 bg-slate-950 border-t border-slate-800 text-[10px] text-slate-400 text-center">
              Active across Live Chart &amp; Replay Terminal
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
