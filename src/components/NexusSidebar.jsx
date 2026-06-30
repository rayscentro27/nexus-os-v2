import React from 'react';
import { nexusNavigationConfig } from '../data/nexusNavigationConfig';

export default function NexusSidebar({ activeId, onNavigate, open, onClose }) {
  return (
    <aside className={`nxos-sidebar ${open ? 'is-open' : ''}`} aria-label="Nexus departments">
      <div className="nxos-brand"><span>N</span><div><strong>Nexus OS</strong><small>Operating Console</small></div></div>
      <nav>
        {nexusNavigationConfig.map((item) => (
          <button
            key={item.id}
            type="button"
            className={activeId === item.id ? 'active' : ''}
            aria-current={activeId === item.id ? 'page' : undefined}
            disabled={!item.enabled}
            onClick={() => { onNavigate(item.id); onClose?.(); }}
          >
            <span className="nxos-nav-copy"><strong>{item.label}</strong><small>{item.description}</small></span>
            <span className="nxos-badge">{item.status}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
