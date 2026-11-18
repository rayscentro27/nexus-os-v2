// Plain English translation dictionary and helper functions
// Translates internal engineering / machine states into everyday operator language

export const PLAIN_LANGUAGE_MAP: Record<string, { title: string; explanation: string }> = {
  // Opportunity & Research states
  MORE_ECONOMIC_RESEARCH_REQUIRED: {
    title: 'Finance needs more information before it can evaluate this opportunity.',
    explanation: 'Additional unit economics, competitor pricing, or market evidence is required before approval.'
  },
  PARTIAL_EVIDENCE: {
    title: 'Some answers are available, but more evidence is needed.',
    explanation: 'Initial source data was parsed, but secondary verification benchmarks are still pending.'
  },
  EVALUATION_IN_PROGRESS: {
    title: 'Nexus is currently evaluating this.',
    explanation: 'Autonomous models are reviewing feasibility, cost impact, and market demand.'
  },
  CANDIDATE_REJECTED: {
    title: 'This option did not pass testing — Nexus is evaluating another.',
    explanation: 'The strategy or proposal failed validation thresholds. The broader program remains fully active.'
  },
  CANDIDATE_ADVANCED: {
    title: 'Passed evaluation and advanced to the next stage.',
    explanation: 'Meets quality, risk, and economic criteria and moved downstream.'
  },

  // Ingestion & Pipeline states
  RETRY_EXHAUSTED: {
    title: 'Nexus tried several times and could not complete this automatically.',
    explanation: 'All automatic retry attempts were attempted. Requires review or alternative source.'
  },
  PROVIDER_BACKOFF: {
    title: 'Provider temporarily busy — Nexus is waiting to retry.',
    explanation: 'The external service reached rate limits. Nexus is pacing requests automatically.'
  },
  EXPONENTIAL_BACKOFF: {
    title: 'Temporary provider cooldown active — retrying shortly.',
    explanation: 'Requests are spaced out automatically to avoid service disruptions.'
  },
  FAILED_RETRYABLE: {
    title: 'Temporary connection delay — retry in progress.',
    explanation: 'Network or API glitch occurred. Nexus is scheduled to re-attempt automatically.'
  },
  FAILED_FINAL: {
    title: 'Could not complete — flagged for review.',
    explanation: 'The requested resource was unavailable or incompatible with the ingestion parser.'
  },
  QUEUED: {
    title: 'Waiting in line to be processed.',
    explanation: 'Positioned in the queue and will begin as soon as active workers complete.'
  },
  PROCESSING: {
    title: 'Nexus is actively working on this right now.',
    explanation: 'Transcribing, analyzing, or structuring source material.'
  },
  INGESTED: {
    title: 'Successfully completed and stored.',
    explanation: 'Full content has been structured, verified, and saved to the knowledge database.'
  },

  // Security & Systems states
  RLS_ISOLATION_PASS: {
    title: 'Client data separation passed security testing.',
    explanation: 'Row-Level Security rules verified that no cross-tenant data leaks are possible.'
  },
  SYSTEMS_READY: {
    title: 'Ready for production review.',
    explanation: 'All unit tests, security scans, and rollback manifests have been verified.'
  },
  HANDOFF_ACK: {
    title: 'The next department received this work.',
    explanation: 'Downstream agent acknowledged receipt of the canonical package.'
  },
  WAITING_RAY_APPROVAL: {
    title: 'Waiting for your approval.',
    explanation: 'Human-in-the-loop decision gate: this step requires executive authorization to proceed.'
  },
  WAITING_RAY: {
    title: 'Waiting for your review.',
    explanation: 'This action is paused until you confirm or authorize it.'
  },
  APPROVED: {
    title: 'Approved and authorized.',
    explanation: 'Executive sign-off received. Progression unblocked.'
  },

  // Trading & Financial states
  PAPER_TESTING_ACTIVE: {
    title: 'Simulated paper testing active (Zero real money at risk).',
    explanation: 'All orders execute in a sandbox environment to test algorithmic performance safely.'
  },
  NOT_CONNECTED: {
    title: 'Live connection not linked.',
    explanation: 'Real bank or API credentials are not connected. Zero live funds are involved.'
  },
  NOT_PROVEN: {
    title: 'Not yet verified with live data.',
    explanation: 'Metric is derived from simulation or models and has not yet been proven in production.'
  }
};

/**
 * Returns a human-friendly plain English translation of any internal machine status
 */
export function toPlainLanguage(status: string): string {
  if (!status) return 'Status unknown';
  const clean = status.trim().toUpperCase().replace(/[\s-]/g, '_');
  if (PLAIN_LANGUAGE_MAP[clean]) {
    return PLAIN_LANGUAGE_MAP[clean].title;
  }
  // Convert SNAKE_CASE to Title Case
  return status
    .toLowerCase()
    .split(/[_\s-]+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Returns plain English explanation details
 */
export function getStatusExplanation(status: string): string | undefined {
  if (!status) return undefined;
  const clean = status.trim().toUpperCase().replace(/[\s-]/g, '_');
  return PLAIN_LANGUAGE_MAP[clean]?.explanation;
}
