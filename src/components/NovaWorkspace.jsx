import React from 'react'
import { Bot, ExternalLink, ShieldCheck } from 'lucide-react'

export default function NovaWorkspace() {
  return <section className="nova-workspace" data-testid="nova-workspace">
    <header className="nova-workspace-header">
      <div><div className="nxos-eyebrow">Strategic adviser</div><h2>Nova</h2><p>Challenge plans, compare scenarios, and surface what may be missing.</p></div>
      <span className="nxos-live"><i /> Telegram runtime certified</span>
    </header>
    <div className="nova-status-grid">
      <article><Bot size={20} /><strong>Hermes Nova</strong><span>Separate graph and memory from Hermes.</span><b>Healthy</b></article>
      <article><ShieldCheck size={20} /><strong>Boundary</strong><span>Strategic advice only. No execution authority.</span><b>Preserved</b></article>
      <article><ExternalLink size={20} /><strong>Browser transport</strong><span>Admin adapter is not connected yet; no fake chat path is exposed.</span><b>NOT_CONNECTED</b></article>
    </div>
    <div className="nova-next-step">
      <strong>Use the certified Nova interface</strong>
      <p>Nova is available through the existing authorized Telegram runtime while a governed browser adapter is evaluated. This workspace does not duplicate the Nova graph or claim a browser conversation that is not connected.</p>
      <a href="https://t.me/HermesNova27bot" target="_blank" rel="noreferrer">Open Hermes Nova on Telegram <ExternalLink size={14} /></a>
    </div>
  </section>
}
