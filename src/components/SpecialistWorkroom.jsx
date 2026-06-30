import React from 'react';
import HermesChatPanel from './HermesChatPanel';
import SpecialistChatPanel from './SpecialistChatPanel';

export const specialistRegistry = [
  { id: 'hermes', name: 'Hermes CEO Advisor', role: 'Executive triage and delegation', safe: 'Summaries, plans, task requests', blocked: 'Risky execution' },
  { id: 'credit', name: 'Credit Specialist', role: 'Credit readiness and dispute draft review', safe: 'Profile review, document checklists, draft answers', blocked: 'Dispute sending or bureau contact' },
  { id: 'funding', name: 'Funding Specialist', role: 'Funding, grants, and bankability', safe: 'Readiness and lender prep', blocked: 'Submitting applications' },
  { id: 'research', name: 'Research Specialist', role: 'Source review and opportunity extraction', safe: 'Approved source scoring', blocked: 'Restricted-source ingestion' },
  { id: 'money', name: 'Monetization Specialist', role: 'Offers and revenue pathways', safe: 'Offer/funnel drafts', blocked: 'Charges or live payment changes' },
  { id: 'marketing', name: 'Marketing Specialist', role: 'Content and outreach drafts', safe: 'Draft creation', blocked: 'Publishing or sending' },
  { id: 'trading', name: 'Trading Specialist', role: 'Oanda demo and paper strategy review', safe: 'Read-only demo checks and paper results', blocked: 'Live/funded trading' },
  { id: 'automation', name: 'Automation Engineer', role: 'Internal schedule and job design', safe: 'Bounded internal jobs', blocked: 'External or destructive automation' },
  { id: 'success', name: 'Client Success Specialist', role: 'Onboarding and client journey drafts', safe: 'Synthetic journey review', blocked: 'Client contact without approval' },
];

export default function SpecialistWorkroom() {
  const [active, setActive] = React.useState(specialistRegistry[0].name);
  const [plans, setPlans] = React.useState([]);
  const selected = specialistRegistry.find((item) => item.name === active);
  return <div className="nxos-workroom"><SpecialistChatPanel specialists={specialistRegistry} active={active} onSelect={setActive} /><div className="nxos-workroom-main"><div className="nxos-specialist-policy"><strong>{selected.name}</strong><span>Safe: {selected.safe}</span><span>Blocked: {selected.blocked}</span></div><HermesChatPanel activeSpecialist={active} onPlanCreated={(plan) => setPlans((current) => [plan, ...current])} />{plans.length > 0 && <section className="nxos-plan-list"><h3>Delegation plans queued</h3>{plans.map((plan) => <article key={plan.id}><strong>{plan.specialist}</strong><p>{plan.prompt}</p><span>{plan.status}</span></article>)}</section>}</div></div>;
}
