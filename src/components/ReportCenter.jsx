import React, { useMemo, useState } from 'react';
import ReportViewer from './ReportViewer';
import { reportRegistry } from '../data/reportRegistry';

export default function ReportCenter({ onAskHermes }) {
  const [category, setCategory] = useState('All');
  const filtered = useMemo(() => reportRegistry.filter((item) => category === 'All' || item.category === category), [category]);
  const [selectedId, setSelectedId] = useState(reportRegistry[0]?.id);
  const selected = reportRegistry.find((item) => item.id === selectedId) || filtered[0];
  const categories = ['All', ...new Set(reportRegistry.map((item) => item.category))];
  return <div className="nxos-report-layout"><aside><h3>Report library</h3><select value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((item) => <option key={item}>{item}</option>)}</select>{filtered.map((report) => <button type="button" className={selected?.id === report.id ? 'active' : ''} key={report.id} onClick={() => setSelectedId(report.id)}><strong>{report.title}</strong><small>{report.category} · {report.available ? 'Ready' : 'Missing'}</small></button>)}</aside><ReportViewer report={selected} onAskHermes={onAskHermes} /></div>;
}
