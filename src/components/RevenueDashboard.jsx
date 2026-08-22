import React from 'react';

const Metric = ({ label, value, truth }) => <article><small>{label}</small><strong>{value}</strong><span className="nxos-source-label">{truth}</span></article>;

export default function RevenueDashboard() {
  return <div className="nxos-stack">
    <section className="nxos-callout"><strong>Revenue Truth Layer</strong><p>Actual, test, synthetic, pipeline, opportunity estimates, and unknown data are intentionally separated. No financial mutation is available from this view.</p></section>
    <div className="nxos-metric-grid">
      <Metric label="Actual revenue" value="UNKNOWN" truth="NOT_CONNECTED · not $0" />
      <Metric label="Controlled test purchase" value="$97" truth="TEST · excluded from actual" />
      <Metric label="Synthetic Persona D" value="UNKNOWN" truth="SYNTHETIC · certification only" />
      <Metric label="Opportunity pipeline" value="See Phase K" truth="OPPORTUNITY_ESTIMATE · not revenue" />
    </div>
    <section className="nxos-table-card"><h2>Operating truth</h2>
      {[
        ['Leads / booked calls', 'UNKNOWN', 'NOT_CONNECTED'],
        ['$97 purchases / upgrades', 'UNKNOWN', 'NOT_CONNECTED'],
        ['MRR / active subscriptions', 'UNKNOWN', 'NOT_CONNECTED'],
        ['Funding commissions earned', 'UNKNOWN', 'NOT_CONNECTED'],
        ['Affiliate conversions / commissions', 'UNKNOWN', 'NOT_CONNECTED'],
        ['Phase K opportunities needing Ray', 'CONNECTED', 'GOVERNED OPPORTUNITY STATE'],
      ].map(([label, value, truth]) => <div className="nxos-table-row" key={label}><strong>{label}</strong><span>{value}</span><span>{truth}</span></div>)}
    </section>
    <section className="nxos-callout"><h2>Next governed action</h2><p>Review the pending Phase K opportunity decision and choose a bounded authoritative revenue source. A test checkout may certify the test path only; it cannot create production revenue.</p></section>
  </div>;
}
