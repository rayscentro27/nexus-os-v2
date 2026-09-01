import React, { useMemo, useState } from 'react'
import { Pause, Play, RotateCcw, SkipForward, ShieldCheck } from 'lucide-react'
import { tradingLabData } from '../data/tradingLabData'
import '../admin/tradingLab.css'

const tabs = ['Overview', 'Strategies', 'Experiments', 'Tournament', 'Paper', 'Replay', 'Learning']

export default function TradingLabPanel() {
  const [tab, setTab] = useState('Overview')
  const [bar, setBar] = useState(0)
  const [playing, setPlaying] = useState(false)
  const selected = tradingLabData.experiments[0]
  const equity = useMemo(() => selected.equity, [selected])
  const step = () => setBar((value) => Math.min(value + 1, Math.max(equity.length - 1, 0)))
  return <div className="nx2-page trading-lab" data-testid="trading-lab">
    <div className="nx2-hero"><div><div className="nx2-eyebrow">TRADING LAB / ADMIN REVIEW</div><h2>Bounded quantitative research</h2><p>Compare evidence, replay experiments, and keep paper research separate from live authority.</p></div><div className="trading-lab-safety"><ShieldCheck size={18} /><strong>PAPER ONLY</strong><small>All live authorities: NONE</small></div></div>
    <nav className="trading-lab-tabs" aria-label="Trading Lab sections">{tabs.map((item) => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}</nav>
    <div className="trading-lab-grid">
      <section className="nx2-card trading-lab-main"><div className="nx2-card-head"><div><div className="nx2-eyebrow">{tab.toUpperCase()}</div><h3>{tab === 'Replay' ? 'Experiment replay' : tab === 'Tournament' ? 'Candidate tournament' : 'WP8.5 research evidence'}</h3></div><span className="nx2-status nx2-status-blue">Read / research</span></div>
        {tab === 'Replay' ? <><div className="replay-meta"><strong>{selected.strategy}</strong><span>{selected.id}</span><span>BACKTEST · {tradingLabData.source} · {tradingLabData.range}</span></div><div className="replay-chart" data-testid="replay-chart"><svg viewBox="0 0 720 220" role="img" aria-label="Bounded backtest equity replay"><path d="M20 180 L180 155 L340 160 L500 120 L700 125" fill="none" stroke="currentColor" strokeWidth="3" /><line x1="20" y1="190" x2="700" y2="190" stroke="currentColor" opacity=".2" /><circle cx={20 + bar * 680} cy="180" r="6" fill="currentColor" /></svg><small>Bar {bar + 1} of {Math.max(equity.length, 1)} · future bars withheld · no fills in this OOS sample</small></div><div className="replay-controls"><button onClick={() => setBar(0)} aria-label="Reset replay"><RotateCcw size={15} /></button><button onClick={() => setPlaying((value) => !value)} aria-label={playing ? 'Pause replay' : 'Play replay'}>{playing ? <Pause size={15} /> : <Play size={15} />}</button><button onClick={step} aria-label="Step forward"><SkipForward size={15} /></button><span>Replay authority: NONE</span></div></> : <div className="trading-lab-table">{tradingLabData.experiments.map((item, index) => <article key={item.id} className="trading-lab-row"><div className="rank">{index + 1}</div><div><strong>{item.family.replaceAll('_', ' ')}</strong><small>{item.strategy} · {item.params}</small></div><div><b>{item.score}</b><small>score</small></div><div><b>{item.oos.trades}</b><small>OOS trades</small></div><span className="nx2-status nx2-status-amber">{item.decision}</span><button onClick={() => setTab('Replay')}>Open replay</button></article>)}</div>}
      </section>
      <aside className="nx2-card trading-lab-side"><div className="nx2-card-head"><div><div className="nx2-eyebrow">PROVENANCE</div><h3>Experiment review</h3></div></div><div className="nx2-stat-line"><span>Market</span><b>FOREX / EUR_USD</b></div><div className="nx2-stat-line"><span>Timeframe</span><b>H1</b></div><div className="nx2-stat-line"><span>Data</span><b>{tradingLabData.bars} bars</b></div><div className="nx2-stat-line"><span>Paper candidates</span><b>{tradingLabData.experiments.length}</b></div><div className="nx2-stat-line"><span>Live authority</span><b>NONE</b></div><p className="nx2-muted">OOS samples are intentionally small and do not establish profitability. Failed and insufficient experiments remain durable and replayable.</p></aside>
    </div>
  </div>
}
