import React from 'react'
import { ChevronRight } from 'lucide-react'

export function ClientPageHeader({ title, subtitle, badge }) {
  return <div className="client-page-head"><div><h1>{title}</h1><p>{subtitle}</p></div>{badge && <span className="client-page-badge">{badge}</span>}</div>
}

export function ClientStatusBadge({ children, tone = 'blue' }) {
  return <span className={`client-status client-status-${tone}`}>{children}</span>
}

export function ClientProgressRing({ value, label = '/100', tone = 'cyan' }) {
  return <div className={`client-progress-ring ${tone}`} style={{ '--client-progress': value }}><div><strong>{value}</strong><span>{label}</span></div></div>
}

export function ClientMetricCard({ icon: Icon, label, value, note, tone = 'cyan', onClick }) {
  return <section className={`client-card client-metric-card${onClick ? ' clickable' : ''}`} onClick={onClick} role={onClick ? 'button' : undefined} tabIndex={onClick ? 0 : undefined}><div className={`client-metric-icon ${tone}`}><Icon size={24} /></div><span>{label}</span><strong>{value}</strong><small>{note}</small></section>
}

export function ClientScoreCard({ title, value, status, text, label = '/100', onClick }) {
  return <section className={`client-card client-score-card${onClick ? ' clickable' : ''}`} onClick={onClick} role={onClick ? 'button' : undefined} tabIndex={onClick ? 0 : undefined}><h3>{title}</h3><div><ClientProgressRing value={value} label={label} /><div className="client-score-copy"><strong>{status}</strong><p>{text}</p></div></div></section>
}

export function ClientSection({ title, action, children, className = '' }) {
  return <section className={`client-card client-section ${className}`}><header><h2>{title}</h2>{action && <span>{action}</span>}</header>{children}</section>
}

export function ClientActionList({ rows, onNavigate }) {
  return <div className="client-action-list">{rows.map((row, index) => {
    const title = typeof row === 'string' ? row : row.title
    const status = typeof row === 'string' ? 'Next step' : row.status?.replaceAll('_', ' ')
    const route = typeof row === 'object' ? row._route : undefined
    return <article key={title} onClick={route && onNavigate ? () => onNavigate(route) : undefined} role={route && onNavigate ? 'button' : undefined} tabIndex={route && onNavigate ? 0 : undefined}><span>{index + 1}</span><div><strong>{title}</strong><small>{status}</small></div><ChevronRight size={16} /></article>
  })}</div>
}

export function ClientFactorGrid({ rows }) {
  return <div className="client-factor-grid">{rows.map(([name, score, status]) => <article key={name}><span>{name}</span><strong>{score}<small>/100</small></strong><ClientStatusBadge tone={score >= 75 ? 'green' : score >= 60 ? 'blue' : 'orange'}>{status.replaceAll('_', ' ')}</ClientStatusBadge></article>)}</div>
}
