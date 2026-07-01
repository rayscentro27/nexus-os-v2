export interface HermesAdvisorResponse {
  shortAnswer: string;
  plainEnglishMeaning: string;
  proof: string[];
  whatIsMissing: string[];
  safeNextAction: string;
  approvalRequiredActions: string[];
  sourceLabel: string;
}

export function renderAdvisorResponse(response: HermesAdvisorResponse): string {
  const proof = response.proof.length ? `\n\nProof I checked: ${response.proof.join('; ')}.` : '';
  const missing = response.whatIsMissing.length ? `\n\nWhat is missing: ${response.whatIsMissing.join('; ')}.` : '';
  const approvals = response.approvalRequiredActions.length
    ? `\n\nNeeds Ray approval before execution: ${response.approvalRequiredActions.join('; ')}.`
    : '';
  return `${response.shortAnswer}\n\n${response.plainEnglishMeaning}${proof}${missing}\n\nSafe next action: ${response.safeNextAction}${approvals}\n\nSource: ${response.sourceLabel}`;
}

export function processGroupsFromCommands(commands: string[]): string[] {
  const groups = new Set<string>();
  for (const command of commands) {
    const text = command.toLowerCase();
    if (text.includes('hermes')) groups.add('Hermes/agent');
    if (text.includes('python')) groups.add('Python services');
    if (text.includes('node') || text.includes('npm') || text.includes('vite')) groups.add('Node services');
    if (text.includes('cloudflared') || text.includes('tunnel')) groups.add('tunnel/gateway');
    if (text.includes('research') || text.includes('orchestrator') || text.includes('youtube')) groups.add('research/orchestrator');
    if (text.includes('trading') || text.includes('oanda') || text.includes('signal')) groups.add('trading/demo');
  }
  return [...groups];
}

export function summarizeLiveStaticUnproven(input: {
  runningProcesses: number;
  schedulerCount: number;
  loadedSchedulers: number;
  liveSections: string[];
  staticSections: string[];
  unproven: string[];
  checkedAt: string;
}): HermesAdvisorResponse {
  return {
    shortAnswer: `Nexus has live proof in ${input.runningProcesses} local process(es) and ${input.liveSections.length} Supabase-backed section(s), but some pieces are still static or unproven.`,
    plainEnglishMeaning:
      `“Live” means I have direct proof such as an active process or live Supabase rows. “Static/report-only” means the UI or report exists but is not proving fresh backend activity. “Unproven” means something may be installed or have old data, but I do not have enough process/log/write proof to call it running.`,
    proof: [
      `${input.runningProcesses} process(es) with direct ps proof`,
      `${input.schedulerCount} scheduler plist(s) inspected; ${input.loadedSchedulers} loaded`,
      `${input.liveSections.join(', ') || 'no live sections listed'} marked live in the Hermes operations snapshot`,
    ],
    whatIsMissing: [
      ...input.unproven,
      ...input.staticSections.slice(0, 6).map((section) => `${section} is still static/report-only`),
    ],
    safeNextAction: 'Refresh the read-only operations collector, then inspect recent logs or live Supabase write receipts for the unproven items.',
    approvalRequiredActions: ['starting/stopping schedulers', 'deploying', 'publishing', 'sending', 'charging', 'trading'],
    sourceLabel: `Mac Mini operations audit + Hermes operations snapshot checked ${input.checkedAt}`,
  };
}

export function summarizeCliAvailability(names: string[], checkedAt: string): HermesAdvisorResponse {
  return {
    shortAnswer: `You have these CLI tools available on the Mac Mini: ${names.join(', ') || 'none proven'}.`,
    plainEnglishMeaning:
      'Availability means the command exists on the machine. It does not prove authentication, permission, configured tokens, or remaining rate limits.',
    proof: [`CLI inventory found ${names.length} available command(s)`],
    whatIsMissing: ['current authentication status unless a tool-specific check proves it', 'current token/rate-limit proof unless logs or config show it'],
    safeNextAction: 'Use read-only commands for inspection; require approval before deploys, writes, scheduler changes, sends, charges, or trades.',
    approvalRequiredActions: ['deploy', 'seed/write data', 'start/stop/restart jobs', 'external API actions'],
    sourceLabel: `CLI inventory checked ${checkedAt}`,
  };
}
