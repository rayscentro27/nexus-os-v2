import React, { useState } from 'react';

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

export default function ReportViewer({ report }) {
  const [copyStatus, setCopyStatus] = useState('');
  if (!report) return <div className="nxos-empty">Select a report. Missing reports are shown as unavailable instead of a blank pane.</div>;
  async function copyPath() { try { await navigator.clipboard.writeText(report.path); setCopyStatus('Path copied'); } catch { setCopyStatus(`Copy: ${report.path}`); } }
  return <article className="nxos-report-viewer">
    <header><div><h2>{report.title}</h2><p>{report.path} · {report.modified || 'timestamp unavailable'}</p></div><button type="button" onClick={copyPath}>Copy path</button></header>
    {copyStatus && <div className="nxos-copy-status">{copyStatus}</div>}
    <div className="nxos-markdown">{report.available ? renderMarkdown(report.content) : <div className="nxos-empty">Report not generated yet. Run: {report.command}</div>}</div>
  </article>;
}
