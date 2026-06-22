import { useState } from 'react';
import { isSupabaseConfigured } from '../lib/supabaseClient';
import {
  Overview, Communication, Monetization, Automation, Social, Trading, Approvals,
} from '../components/tabs';

const TABS = [
  { key: 'overview', label: 'Overview', el: <Overview /> },
  { key: 'communication', label: 'Communication', el: <Communication /> },
  { key: 'monetization', label: 'Monetization', el: <Monetization /> },
  { key: 'automation', label: 'Automation', el: <Automation /> },
  { key: 'social', label: 'Social', el: <Social /> },
  { key: 'trading', label: 'Trading', el: <Trading /> },
  { key: 'approvals', label: 'Approvals / Proof Log', el: <Approvals /> },
];

export function App() {
  const [active, setActive] = useState('overview');
  const current = TABS.find((t) => t.key === active) ?? TABS[0];
  return (
    <div className="app">
      <div className="brand">
        <h1>Nexus <span className="v">OS v2</span></h1>
        <span className="sub">Communication · Monetization · Automation — one ledger, one truth</span>
      </div>
      <div className="muted" style={{ fontSize: 12 }}>
        {isSupabaseConfigured ? 'Supabase ledger connected.' : 'Supabase not configured — showing setup state (no fake data).'}
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${active === t.key ? 'active' : ''}`}
            onClick={() => setActive(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {current.el}
    </div>
  );
}
