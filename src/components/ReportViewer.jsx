import React, { useState } from 'react';
import { getReportContext } from '../lib/hermesReportContextAdapter';

function renderMarkdown(markdown) {
  return markdown.split('\n').map((line, index) => {
    if (line.startsWith('### ')) return <h3 key={index}>{line.slice(4)}</h3>;
    if (line.startsWith('## ')) return <h2 key={index}>{line.slice(3)}</h2>;
    if (line.startsWith('# ')) return <h1 key={index}>{line.slice(2)}</h1>;
    if (/^[-*] /.test(line)) return <li key={index}>{line.slice(2)}</li>;
    if (/^\d+\. /.test(line)) return <li key={index}>{line.replace(/^\d+\. /, '')}</li>;
    if (line.startsWith('```')) return null;
    return line ? <p key={index}>{line}</p> : <br key={index} />;
  });
}

export default function ReportViewer({ report, onAskHermes }) {
  const [copyStatus, setCopyStatus] = useState('');
  if (!report) return <div className="nxos-empty">Select a report. Missing reports are shown as unavailable instead of a blank pane.</div>;
  async function copyPath() { try { await navigator.clipboard.writeText(report.path); setCopyStatus('Path copied'); } catch { setCopyStatus(`Copy: ${report.path}`); } }
  const context = getReportContext(report.id);
  const revenue = report.id === 'revenue_dashboard' ? context.records[0] : null;
  return <article className="nxos-report-viewer">
    <header><div><h2>{report.title}</h2><p>{report.path} · {context.generatedAt}</p></div><div className="nxos-actions"><button type="button" onClick={copyPath}>Copy path</button>{onAskHermes&&<button type="button" onClick={()=>onAskHermes(`Based on the selected report ${report.title}, what does this report mean and what should I do next?`)}>Ask Hermes about this report</button>}</div></header>
    {copyStatus && <div className="nxos-copy-status">{copyStatus}</div>}
    <section className="nxos-table-card" aria-label="Report action summary"><h3>Action summary</h3><p><strong>Plain English:</strong> {context.summary}</p><p><strong>Why it matters:</strong> This approved snapshot identifies the current state and the next decision without executing it.</p><p><strong>Current status:</strong> {context.ok ? 'Available for safe read-only review' : 'Unavailable'}</p><p><strong>Recommended next action:</strong> Review the evidence and route any external or persistent action through Ray Review.</p><p><strong>Safe actions:</strong> Copy source path; ask Hermes; review bundled evidence.</p><p><strong>Approval-gated:</strong> Writes, sends, charges, publishing, deployments, and trading.</p><p><strong>Freshness:</strong> Static/generated snapshot; not live. Source: {context.source}</p>{revenue&&<div><p><strong>Revenue details:</strong> Confirmed ${revenue.confirmedRevenueUsd}; pending test ${revenue.pendingTestRevenueUsd}; possible offer value ${revenue.possibleOfferValueUsd}; blocked ${revenue.blockedRevenueUsd}.</p><p><strong>Exact next money action:</strong> {revenue.exactNextMoneyAction}</p><p><strong>External action performed:</strong> {String(revenue.externalActionPerformed)}</p><p><strong>Ray approval:</strong> Review the test Checkout and synthetic onboarding approval cards.</p></div>}</section>
    <div className="nxos-markdown">{report.available ? renderMarkdown(report.content) : <div className="nxos-empty">Report not generated yet. Run: {report.command}</div>}</div>
  </article>;
}
