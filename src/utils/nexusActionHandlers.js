export const nexusActions = {
  operating_cycles: { label: 'Operating cycles', type: 'navigate', target: 'automation', fallbackMessage: 'Scheduler details are available in Automation Scheduler.' },
  ray_review: { label: 'Ray Review', type: 'navigate', target: 'rayreview', fallbackMessage: 'The review queue is available.' },
  research_money: { label: 'Research to money', type: 'navigate', target: 'research', fallbackMessage: 'Research pipeline is available.' },
  revenue: { label: 'Revenue dashboard', type: 'navigate', target: 'monetization', fallbackMessage: 'Revenue dashboard is available.' },
  ask_hermes: { label: 'Ask Hermes', type: 'open_drawer', target: 'hermes', fallbackMessage: 'Hermes inline chat is available.' },
  reports: { label: 'Open reports', type: 'navigate', target: 'reports', fallbackMessage: 'Report Center is available.' },
  scheduler: { label: 'Open scheduler', type: 'navigate', target: 'automation', fallbackMessage: 'Scheduler panel is available.' },
  money_customer: { label: 'Prove $97 journey', type: 'navigate', target: 'rayreview', fallbackMessage: 'Synthetic insert remains approval-gated.' },
  money_resend: { label: 'Clear communication gate', type: 'navigate', target: 'reports', fallbackMessage: 'Resend remains blocked pending configuration.' },
  money_research: { label: 'Choose revenue candidates', type: 'navigate', target: 'opportunity', fallbackMessage: 'Opportunity candidates are available.' },
  running_daily: { label: 'Daily cycle details', type: 'navigate', target: 'automation', fallbackMessage: 'Daily cycle is safe and loaded.' },
  running_research: { label: 'Research details', type: 'navigate', target: 'research', fallbackMessage: 'Research engine is active.' },
  running_trading: { label: 'Trading demo details', type: 'navigate', target: 'trading', fallbackMessage: 'Only practice and paper activity is available.' },
  blocked_details: { label: 'Safety gate details', type: 'show_details', target: 'safety', fallbackMessage: 'This action is blocked or requires Ray approval.' },
  copy_next_command: { label: 'Copy next command', type: 'copy_command', target: 'python3 scripts/activation/run_daily_operating_cycle.py --json', fallbackMessage: 'Copy unavailable; select the command text manually.' },
};

export async function runNexusAction(actionId, handlers = {}) {
  const action = nexusActions[actionId];
  if (!action) return handlers.showMessage?.('This action is not available yet.');
  if (action.type === 'navigate') return handlers.navigate?.(action.target) ?? handlers.showMessage?.(action.fallbackMessage);
  if (action.type === 'open_drawer') return handlers.openHermes?.() ?? handlers.showMessage?.(action.fallbackMessage);
  if (action.type === 'show_details') return handlers.showMessage?.(action.fallbackMessage);
  if (action.type === 'copy_command') {
    try { await navigator.clipboard.writeText(action.target); return handlers.showMessage?.('Next command copied.'); }
    catch { return handlers.showMessage?.(action.fallbackMessage); }
  }
}
