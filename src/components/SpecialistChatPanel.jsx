import React from 'react';

export default function SpecialistChatPanel({ specialists, active, onSelect }) {
  return <aside className="nxos-specialist-list"><h3>Workrooms</h3>{specialists.map((specialist) => <button type="button" className={active === specialist.name ? 'active' : ''} key={specialist.id} onClick={() => onSelect(specialist.name)}><strong>{specialist.name}</strong><small>{specialist.role}</small></button>)}</aside>;
}
