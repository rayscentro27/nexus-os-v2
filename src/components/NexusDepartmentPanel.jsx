import React from 'react';

export function StatusCard({ label, value, tone = 'neutral', detail }) {
  return <article className={`nxos-status-card tone-${tone}`}><small>{label}</small><strong>{value}</strong>{detail && <p>{detail}</p>}</article>;
}

export default function NexusDepartmentPanel({ title, description, children }) {
  return (
    <section className="nxos-department" aria-labelledby="department-title">
      <header><div><p className="nxos-eyebrow">Nexus department</p><h1 id="department-title">{title}</h1><p>{description}</p></div><span className="nxos-live"><i /> Interface ready</span></header>
      {children}
    </section>
  );
}
