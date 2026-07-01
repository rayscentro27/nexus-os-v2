/**
 * Hermes Routing Trace — logs every routing decision for debugging.
 *
 * Answers: "Why did you answer that way?", "Where did that route?",
 * "What source did you use?", "Did you use Supabase?", "Did you use the model?"
 *
 * Stored in localStorage (browser-safe). Never logs secrets or full PII.
 */

export interface RoutingTraceEntry {
  id: string;
  timestamp: string;
  message: string;
  surface: 'full_workroom' | 'inline_drawer' | 'specialist' | 'unknown';
  page: string | null;
  activationLevel: number;
  activationLevelName: string;
  intent: string;
  sourceDecision: string;
  route: string;
  modelRoute: string;
  usedSupabase: boolean;
  supabaseTables: string[];
  usedModel: boolean;
  usedMemory: boolean;
  selectedEntity: string | null;
  safetyGate: boolean;
  answerBuilder: string;
  fallbackReason: string | null;
  correctnessHint: string;
  detectedDomain: string;
  previousTopic: string | null;
  detectedTopic: string;
  topicChanged: boolean;
  memoryCandidateFound: boolean;
  memoryUsed: boolean;
  memoryRejected: boolean;
  memoryRejectionReason: string | null;
  domainOverrideApplied: boolean;
  casualOverrideApplied: boolean;
  invariantViolations: string[];
  confidence: 'high' | 'medium' | 'low';
}

const STORAGE_KEY = 'nexus-hermes-routing-trace-v1';
const MAX_ENTRIES = 100;

function safe(): Storage | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null;
  } catch {
    return null;
  }
}

/** Record a routing trace entry. */
type NewMemoryTraceFields = 'detectedDomain' | 'previousTopic' | 'detectedTopic' | 'topicChanged' | 'memoryCandidateFound' | 'memoryUsed' | 'memoryRejected' | 'memoryRejectionReason' | 'domainOverrideApplied' | 'casualOverrideApplied' | 'invariantViolations';
type RoutingTraceInput = Omit<RoutingTraceEntry, 'id' | 'timestamp' | NewMemoryTraceFields> & Partial<Pick<RoutingTraceEntry, NewMemoryTraceFields>>;

export function logRoutingTrace(entry: RoutingTraceInput): RoutingTraceEntry {
  const full: RoutingTraceEntry = {
    detectedDomain: 'unknown', previousTopic: null, detectedTopic: 'unknown', topicChanged: false,
    memoryCandidateFound: false, memoryUsed: entry.usedMemory, memoryRejected: false,
    memoryRejectionReason: null, domainOverrideApplied: false, casualOverrideApplied: false,
    invariantViolations: [],
    ...entry,
    message: redactAndTruncate(entry.message),
    id: `trace-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
  };
  const ls = safe();
  if (!ls) return full;
  try {
    const raw = ls.getItem(STORAGE_KEY);
    const entries: RoutingTraceEntry[] = raw ? JSON.parse(raw) : [];
    entries.push(full);
    ls.setItem(STORAGE_KEY, JSON.stringify(entries.slice(-MAX_ENTRIES)));
  } catch {
    // quota exceeded — ignore
  }
  return full;
}

function redactAndTruncate(message: string): string {
  return message
    .replace(/(?:sk-|ghp_|gho_|eyJ)[A-Za-z0-9._-]{12,}/g, '[redacted]')
    .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, '[email]')
    .slice(0, 500);
}

/** Get all routing trace entries. */
export function getRoutingTraces(): RoutingTraceEntry[] {
  const ls = safe();
  if (!ls) return [];
  try {
    const raw = ls.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** Get the most recent routing trace. */
export function getLastRoutingTrace(): RoutingTraceEntry | null {
  const traces = getRoutingTraces();
  return [...traces].reverse().find(trace => trace.answerBuilder !== 'routing_trace') || (traces.length > 0 ? traces[traces.length - 1] : null);
}

/** Clear all routing traces. */
export function clearRoutingTraces(): void {
  const ls = safe();
  if (ls) try { ls.removeItem(STORAGE_KEY); } catch { /* ignore */ }
}

/**
 * Answer "Why did you answer that way?" from the routing trace.
 */
export function answerWhyFromTrace(): string {
  const trace = getLastRoutingTrace();
  if (!trace) {
    return 'I do not have a routing trace for my last answer. This may be because the trace facility was added after that message was sent.';
  }
  return buildTraceAnswer(trace);
}

/**
 * Answer "Where did that route?" from the routing trace.
 */
export function answerWhereDidThatRoute(): string {
  const trace = getLastRoutingTrace();
  if (!trace) {
    return 'I do not have a routing trace for my last answer.';
  }
  return `My last answer routed through:\n\n- **Activation Level:** ${trace.activationLevel} (${trace.activationLevelName})\n- **Intent:** ${trace.intent}\n- **Route:** ${trace.route}\n- **Model Route:** ${trace.modelRoute}\n- **Source Decision:** ${trace.sourceDecision}\n- **Answer Builder:** ${trace.answerBuilder}\n${trace.fallbackReason ? `- **Fallback Reason:** ${trace.fallbackReason}` : ''}`;
}

/**
 * Answer "What source did you use?" from the routing trace.
 */
export function answerWhatSource(): string {
  const trace = getLastRoutingTrace();
  if (!trace) {
    return 'I do not have a routing trace for my last answer.';
  }
  return `For my last answer, I used:\n\n- **Source:** ${trace.sourceDecision}\n- **Supabase:** ${trace.usedSupabase ? 'Yes' : 'No'}\n- **Model:** ${trace.usedModel ? 'Yes' : 'No'}\n- **Conversation Memory:** ${trace.usedMemory ? 'Yes' : 'No'}\n- **Safety Gate:** ${trace.safetyGate ? 'Yes (blocked)' : 'No'}`;
}

/**
 * Answer "Did you use Supabase?" from the routing trace.
 */
export function answerDidYouUseSupabase(): string {
  const trace = getLastRoutingTrace();
  if (!trace) {
    return 'I do not have a routing trace for my last answer.';
  }
  return trace.usedSupabase
    ? `Yes, I used live Supabase data for my last answer. Source: ${trace.sourceDecision}. The query was authenticated and RLS-gated.`
    : `No, I did not use Supabase for my last answer. Source: ${trace.sourceDecision}. ${trace.route === 'no_model' ? 'The question was answerable from local context.' : 'The question did not require live data.'}`;
}

/**
 * Answer "Did you use the model?" from the routing trace.
 */
export function answerDidYouUseModel(): string {
  const trace = getLastRoutingTrace();
  if (!trace) {
    return 'I do not have a routing trace for my last answer.';
  }
  return trace.usedModel
    ? `Yes, I used the model for my last answer. Route: ${trace.modelRoute}. Source: ${trace.sourceDecision}.`
    : `No, I did not use the model for my last answer. Route: ${trace.modelRoute}. The question was answerable from ${trace.sourceDecision}.`;
}

export function answerMemoryFromTrace(message: string): string {
  const trace = getLastRoutingTrace();
  if (!trace) return 'I do not have a routing trace for my last answer.';
  if (/why did you not use|why didn'?t you use|previous recommendation/i.test(message)) {
    return trace.memoryRejected
      ? `I did not use the previous recommendation because ${trace.memoryRejectionReason} I detected the ${trace.detectedDomain} domain${trace.topicChanged ? ' and treated it as a new topic' : ''}.`
      : `I did not reject eligible memory for that answer. Memory used: ${trace.memoryUsed ? 'yes' : 'no'}.`;
  }
  if (/why did you use memory/i.test(message)) {
    return trace.memoryUsed
      ? `I used memory because the topic boundary approved it. Detected topic: ${trace.detectedTopic}. Resolved entity: ${trace.selectedEntity || 'conversation context'}.`
      : `I did not use memory. ${trace.memoryRejectionReason || 'No eligible memory reference was found.'}`;
  }
  if (/new topic/i.test(message)) return trace.topicChanged ? `Yes. I treated it as a new ${trace.detectedTopic} topic.` : `No. I treated it as a continuation of ${trace.detectedTopic}.`;
  if (/what domain/i.test(message)) return `I detected the **${trace.detectedDomain}** domain. Domain override applied: ${trace.domainOverrideApplied ? 'yes' : 'no'}.`;
  return trace.memoryUsed
    ? `Yes, I used eligible conversation memory${trace.selectedEntity ? ` for ${trace.selectedEntity}` : ''}.`
    : `No, I did not use prior memory. ${trace.memoryRejectionReason || 'No memory candidate was needed.'}`;
}

/** Build a full trace answer for "Why did you answer that way?" */
function buildTraceAnswer(trace: RoutingTraceEntry): string {
  let answer = `Here is exactly how I processed your last message:\n\n`;
  answer += `**Message:** "${trace.message.slice(0, 100)}${trace.message.length > 100 ? '...' : ''}"\n\n`;
  answer += `**Activation Level:** ${trace.activationLevel} — ${trace.activationLevelName}\n`;
  answer += `**Intent:** ${trace.intent}\n`;
  answer += `**Route:** ${trace.route}\n`;
  answer += `**Model Route:** ${trace.modelRoute}\n`;
  answer += `**Source:** ${trace.sourceDecision}\n`;
  answer += `**Used Supabase:** ${trace.usedSupabase ? 'Yes' : 'No'}\n`;
  answer += `**Used Model:** ${trace.usedModel ? 'Yes' : 'No'}\n`;
  answer += `**Used Memory:** ${trace.usedMemory ? 'Yes' : 'No'}\n`;
  answer += `**Detected Domain:** ${trace.detectedDomain}\n`;
  answer += `**Topic Changed:** ${trace.topicChanged ? 'Yes' : 'No'}\n`;
  if (trace.memoryRejected) answer += `**Memory Rejected:** ${trace.memoryRejectionReason}\n`;
  answer += `**Safety Gate:** ${trace.safetyGate ? 'Active (blocked execution)' : 'Not triggered'}\n`;
  if (trace.selectedEntity) {
    answer += `**Resolved Entity:** ${trace.selectedEntity}\n`;
  }
  answer += `**Answer Builder:** ${trace.answerBuilder}\n`;
  answer += `**Confidence:** ${trace.confidence}\n`;
  if (trace.fallbackReason) {
    answer += `**Fallback Reason:** ${trace.fallbackReason}\n`;
  }
  answer += `\nThis trace is stored locally in your browser and does not contain secrets or sensitive data.`;
  return answer;
}

/**
 * Check if a message is asking about the routing trace.
 */
export function isRoutingTraceQuestion(message: string): boolean {
  const lower = message.toLowerCase();
  return /\b(why\s+did\s+you\s+answer|where\s+did\s+(that|it)\s+route|what\s+route\s+did\s+that\s+take|what\s+source\s+did\s+you\s+use|did\s+you\s+use\s+supabase|did\s+you\s+use\s+(?:the\s+)?model|did\s+you\s+use\s+memory|why\s+did\s+you\s+(?:not\s+)?use\s+memory|why\s+did\s+you\s+not\s+use\s+the\s+previous\s+recommendation|did\s+you\s+treat\s+that\s+as\s+a\s+new\s+topic|what\s+domain\s+did\s+you\s+detect|what\s+activation\s+level|show\s+my\s+routing\s+trace|why\s+did\s+you\s+route)\b/i.test(lower);
}

/**
 * Get the answer for a routing trace question.
 */
export function answerRoutingTraceQuestion(message: string): string | null {
  if (!isRoutingTraceQuestion(message)) return null;
  const lower = message.toLowerCase();

  if (/\bwhy\s+did\s+you\s+answer\b/i.test(lower)) {
    return answerWhyFromTrace();
  }
  if (/\b(where\s+did|what\s+route)\b/i.test(lower)) {
    return answerWhereDidThatRoute();
  }
  if (/\bwhat\s+source\b/i.test(lower)) {
    return answerWhatSource();
  }
  if (/\bdid\s+you\s+use\s+supabase\b/i.test(lower)) {
    return answerDidYouUseSupabase();
  }
  if (/\bdid\s+you\s+use\s+(?:the\s+)?model\b/i.test(lower)) {
    return answerDidYouUseModel();
  }
  if (/\b(memory|previous recommendation|new topic|what domain)\b/i.test(lower)) return answerMemoryFromTrace(message);
  if (/\bshow\s+my\s+routing\s+trace\b/i.test(lower)) return getRoutingTraces().slice(-10).map(buildTraceAnswer).join('\n\n---\n\n');

  return answerWhyFromTrace();
}
