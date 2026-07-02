import type { HermesResponseMode, LastAnswerState } from './hermesDecisionState';

const rawPath = /\b(?:reports|src|docs|scripts)\/[\w./-]+/g;
const uuid = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/gi;

function cleanForCeo(text: string, strict = false): string {
  const withoutTechnical = text.replace(rawPath, '').replace(uuid, '[record]').replace(/\bRLS[- /\w]*/gi, 'access controls');
  if (strict) return withoutTechnical.split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean).slice(0, 1).join(' ').slice(0, 800);
  if (/conversation-only draft|not saved|not submitted|not executed/i.test(withoutTechnical)) return withoutTechnical.slice(0, 1400);
  if (/\*\*Direct answer:|\*\*Business opportunity:|\*\*Status summary:/i.test(withoutTechnical)) return withoutTechnical.slice(0, 1800);
  const paragraphs = withoutTechnical.split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);
  return paragraphs.slice(0, 2).join('\n\n').slice(0, 900);
}

function renderSystemHealthCeo(text: string): string {
  const counts = text.match(/(\d+) locally reported healthy; (\d+) blocked or approval-gated/i);
  const healthy = counts?.[1] || 'Most';
  const blocked = counts?.[2] || 'some';
  return `The system is mostly healthy. ${healthy} areas look good, and ${blocked} still need review or approval. This is based on local reports, not a fresh production check. The next move is to verify Supabase and deployment live.`;
}

export function renderLastAnswerProvenance(target: LastAnswerState | null): string {
  if (!target) return 'I do not have a successful prior answer trace in this session.';
  if (target.domain === 'clients' && target.sources.includes('client_profiles')) {
    const status = target.sourceStatus || 'failed';
    if (status === 'empty_success') {
      return 'That came from an attempted live Supabase read of client_profiles. Status: empty_success. The read succeeded and returned 0 client rows. I did not use approvals or task_requests to count clients.';
    }
    if (status === 'success') {
      return `That came from a successful live Supabase read of client_profiles. Status: success. It returned ${target.sourceRowCount ?? 'verified'} client rows. I did not use approvals or task_requests to count clients.`;
    }
    return `That came from an attempted live Supabase read of client_profiles. Status: failed. Blocker: ${target.blockers.join('; ') || 'the read did not succeed'}. No verified client count is available. I did not use approvals or task_requests to count clients.`;
  }
  return `That answer used route **${target.route}** for **${target.intent}**. Sources: ${target.sources.join(', ') || 'none recorded'}. Supabase: ${target.usedSupabase ? 'used' : 'not used'}. Assumptions: ${target.assumptions.join('; ') || 'none recorded'}. Confidence: ${target.confidence}.`;
}

export function renderResponseMode(input: { text: string; mode: HermesResponseMode; lastAnswer?: LastAnswerState | null }): string {
  const target = input.lastAnswer || null;
  if (input.mode === 'casual') return input.text;
  if (input.mode === 'ceo') {
    if (target?.domain === 'system_health') return renderSystemHealthCeo(target.text);
    return cleanForCeo(target?.text || input.text, Boolean(target));
  }
  if (input.mode === 'trace') {
    return renderLastAnswerProvenance(target);
  }
  if (!target) return input.text;
  return `${target.text}\n\n**Audit details**\n- Route: ${target.route}\n- Intent/domain: ${target.intent} / ${target.domain}\n- Sources: ${target.sources.join(', ') || 'none recorded'}\n- Supabase: ${target.usedSupabase ? 'used' : 'not used'}\n- Timestamp: ${target.timestamp}\n- Confidence: ${target.confidence}\n- Blockers: ${target.blockers.join('; ') || 'none recorded'}\n- Assumptions: ${target.assumptions.join('; ') || 'none recorded'}`;
}
