export const nexusNavigationConfig = [
  { id: 'command', label: 'Command Center', description: 'Today, approvals, blockers, and money actions', status: 'Live', role: 'admin', enabled: true },
  { id: 'activation', label: 'Activation Status', description: 'Visual proof of which sections are live, static, or blocked', status: 'Proof', role: 'admin', enabled: true },
  { id: 'health', label: 'System Health', description: 'Engines, connectors, and safety gates', status: 'Healthy', role: 'admin', enabled: true },
  { id: 'review', label: 'Ray Review', description: 'Approve, reject, or hold queued decisions', status: '64 cards', role: 'admin', enabled: true },
  { id: 'hermes', label: 'Hermes Workroom', description: 'Chat, delegate, and create safe work plans', status: 'Ready', role: 'admin', enabled: true },
  { id: 'reports', label: 'Reports', description: 'Read the latest operating evidence', status: 'Available', role: 'admin', enabled: true },
  { id: 'clients', label: 'Clients', description: 'Test customer and onboarding readiness', status: 'Gated', role: 'admin', enabled: true },
  { id: 'credit', label: 'Credit & Funding', description: 'Credit, funding, grants, and readiness', status: 'Active', role: 'admin', enabled: true },
  { id: 'opportunities', label: 'Business Opportunities', description: 'Scored business and partner ideas', status: '26 ready', role: 'admin', enabled: true },
  { id: 'research', label: 'Research Engine', description: 'Sources, scores, memory, and opportunities', status: '50 candidates', role: 'admin', enabled: true },
  { id: 'monetization', label: 'Monetization', description: 'Offers, funnel, and revenue status', status: '9 offers', role: 'admin', enabled: true },
  { id: 'marketing', label: 'Marketing Drafts', description: 'Draft-only content and outreach', status: 'Draft only', role: 'admin', enabled: true },
  { id: 'trading', label: 'Trading Demo', description: 'Oanda practice and paper results', status: 'Demo only', role: 'admin', enabled: true },
  { id: 'automation', label: 'Automation Scheduler', description: 'Safe schedules and recent runs', status: '2 loaded', role: 'admin', enabled: true },
  { id: 'tools', label: 'CLI / Tool Registry', description: 'Tool access and command safety', status: 'Validated', role: 'admin', enabled: true },
  { id: 'settings', label: 'Settings', description: 'Safety policies and feature gates', status: 'Safe', role: 'admin', enabled: true },
];

export const navigationById = Object.fromEntries(nexusNavigationConfig.map((item) => [item.id, item]));
