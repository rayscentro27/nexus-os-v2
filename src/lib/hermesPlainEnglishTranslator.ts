/**
 * Hermes Plain-English Translator — translates technical status/report terms
 * into common language a CEO can understand.
 *
 * No I/O. No model calls. All deterministic.
 */

/** Safely convert any value to a string. */
function safeStr(val: unknown, fallback = ''): string {
  if (val == null) return fallback;
  if (typeof val === 'string') return val;
  return String(val);
}

// ── Term Translations ──

const STATUS_TRANSLATIONS: Record<string, string> = {
  live: 'This section is truly connected to live Supabase data.',
  live_supabase: 'This section is truly connected to live Supabase data.',
  static: 'This section is still mostly a mockup or bundled data. It may look active, but it is not fully connected to live backend data yet.',
  local_static: 'This section is still mostly a mockup or bundled data. It may look active, but it is not fully connected to live backend data yet.',
  static_fallback: 'This section is still mostly a mockup or bundled data. It may look active, but it is not fully connected to live backend data yet.',
  report_snapshot: 'This section is reading the latest generated report. That is useful, but it is not the same as a live database-backed workflow.',
  mismatch: 'Something does not match between what the UI shows and what the backend actually has.',
  blocked: 'This section is blocked and cannot work until specific issues are resolved.',
  unknown: 'The status of this section is unclear.',
};

const PROOF_TRANSLATIONS: Record<string, string> = {
  active_process: 'There is a real process currently running or recently seen by the process inventory.',
  loaded_only: 'The scheduler is loaded, but that does not prove it actually ran or produced results.',
  recent_output: 'The system recently produced a report/log/output, so we know something ran recently.',
  installed_only: 'The tool or scheduler is installed, but we do not have proof it is running or producing results.',
  available_script_only: 'A script exists, but it has not been run recently.',
  not_proven_live: 'This may be installed or partially set up, but we do not have enough proof to call it live.',
  not_proven: 'There is not enough evidence yet.',
  no_proof: 'There is not enough evidence yet.',
  unproven: 'There is not enough evidence yet.',
  verified: 'This has been verified with real data or real process proof.',
};

const SOURCE_TRANSLATIONS: Record<string, string> = {
  supabase: 'Data comes directly from a live Supabase database.',
  local_static: 'Data comes from local bundled files, not a live database.',
  mixed: 'Data comes from a mix of live and local sources.',
  none: 'No data source identified.',
};

const RISK_TRANSLATIONS: Record<string, string> = {
  low: 'Low risk — this is safe to inspect or discuss.',
  medium: 'Medium risk — this could have side effects if misused.',
  high: 'High risk — this must be carefully controlled.',
  critical: 'Critical — this needs explicit approval before any action.',
};

const CATEGORY_TRANSLATIONS: Record<string, string> = {
  unclear: 'general conversation / uncategorized',
  nexus_topic: 'Nexus planning or build work',
  supabase_query: 'Supabase/live data check',
  trading: 'Trading Lab / paper-demo review',
  greeting: 'conversation',
  model_status: 'Hermes model/status check',
  cost_status: 'Model cost/token review',
  section_status: 'Nexus section status review',
  process_status: 'Process/activity verification',
  report_status: 'Report review',
  settings_status: 'Settings/config review',
  approval_status: 'Ray Review / approval workflow',
  page_view: 'page navigation',
  hermes_message: 'Hermes conversation',
  opencode_result: 'code/build result',
  build_result: 'build result',
  route_error: 'error encountered',
  runtime_error: 'error encountered',
  button_action: 'UI action',
  approval_action: 'Ray Review action',
  task_created: 'task planning',
  report_generated: 'report generation',
  blocker_detected: 'blocker identified',
  ray_feedback: 'Ray feedback',
  decision: 'decision made',
  next_step: 'next step identified',
  memory_saved: 'memory saved',
  source_hint_saved: 'source hint saved',
};

/**
 * Translate a technical status term to plain English.
 */
export function translateStatusTerm(term: string): string {
  const key = safeStr(term).toLowerCase().replace(/[\s-]+/g, '_');
  return STATUS_TRANSLATIONS[key] || `"${term}" — status is unclear.`;
}

/**
 * Explain a proof level in plain English.
 */
export function explainProofLevel(proofLevel: string): string {
  const key = safeStr(proofLevel).toLowerCase().replace(/[\s-]+/g, '_');
  return PROOF_TRANSLATIONS[key] || `Proof level "${proofLevel}" — interpretation unknown.`;
}

/**
 * Explain a source mode in plain English.
 */
export function explainSourceMode(sourceMode: string): string {
  const key = safeStr(sourceMode).toLowerCase().replace(/[\s-]+/g, '_');
  return SOURCE_TRANSLATIONS[key] || `Source "${sourceMode}" — interpretation unknown.`;
}

/**
 * Explain a risk level in plain English.
 */
export function explainRiskLevel(riskLevel: string): string {
  const key = safeStr(riskLevel).toLowerCase();
  return RISK_TRANSLATIONS[key] || `Risk level "${riskLevel}" — interpretation unknown.`;
}

/**
 * Translate an activity category to plain English.
 */
export function translateCategory(category: string): string {
  const key = safeStr(category).toLowerCase().replace(/[\s-]+/g, '_');
  return CATEGORY_TRANSLATIONS[key] || category;
}

/**
 * Is this a low-value category that should be filtered from summaries?
 */
export function isLowValueCategory(category: string): boolean {
  const key = safeStr(category).toLowerCase();
  return ['greeting', 'page_view', 'unclear'].includes(key);
}

/**
 * Build a structured plain-English operational answer.
 */
export function buildPlainEnglishOperationalAnswer(input: {
  plainAnswer: string;
  whatThisMeans: string;
  proof: string;
  blocker?: string;
  nextSafeAction: string;
}): string {
  const lines = [
    `Plain answer:`,
    input.plainAnswer,
    ``,
    `What this means:`,
    input.whatThisMeans,
    ``,
    `Proof:`,
    input.proof,
  ];
  if (input.blocker) {
    lines.push(``, `Blocker:`, input.blocker);
  }
  lines.push(``, `Next safe action:`, input.nextSafeAction);
  return lines.join('\n');
}

/**
 * Build a CEO summary answer.
 */
export function buildCeoSummary(input: {
  summary: string;
  businessImpact: string;
  whatIsWorking: string[];
  whatIsNotWorking: string[];
  nextMove: string;
}): string {
  const lines = [
    `CEO Summary:`,
    input.summary,
    ``,
    `Business impact:`,
    input.businessImpact,
    ``,
    `What is working:`,
    ...input.whatIsWorking.map((w) => `  - ${w}`),
    ``,
    `What is not working yet:`,
    ...input.whatIsNotWorking.map((w) => `  - ${w}`),
    ``,
    `Next move:`,
    `  - ${input.nextMove}`,
  ];
  return lines.join('\n');
}

/**
 * Detect CEO summary / plain English request.
 */
export function isCeoSummaryRequest(query: string): boolean {
  const lower = safeStr(query).toLowerCase();
  return /\b(ceo\s+version|plain\s+english|what\s+should\s+i\s+care\s+about|what\s+matters|what\s+is\s+the\s+takeaway|simplify\s+this|translate\s+this\s+report|give\s+me\s+the\s+ceo|plain[- ]?language)\b/i.test(lower);
}

/**
 * Detect daily activity / "what did you do today" questions.
 */
export function isDailyActivityQuestion(query: string): boolean {
  const lower = safeStr(query).toLowerCase();
  return /\b(what\s+did\s+(you|we|nexus)\s+(do|work\s+on|accomplish)|what\s+changed|what\s+got\s+done|what\s+happened\s+(since|today|yesterday)|what\s+should\s+i\s+know\s+from|summarize\s+(today|yesterday|this\s+day|the\s+day)|ceo\s+summary\s+for|what\s+did\s+you\s+do\s+today|what\s+did\s+we\s+do\s+today|daily\s+summary|today\s+in\s+plain|give\s+me\s+the\s+ceo\s+summary)\b/i.test(lower);
}
