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

export function renderResponseMode(input: { text: string; mode: HermesResponseMode; lastAnswer?: LastAnswerState | null }): string {
  const target = input.lastAnswer || null;
  if (input.mode === 'casual') return input.text;
  if (input.mode === 'ceo') return cleanForCeo(target?.text || input.text, Boolean(target));
  if (input.mode === 'trace') {
    if (!target) return 'I do not have a successful prior answer trace in this session.';
    return `That answer used route **${target.route}** for **${target.intent}**. Sources: ${target.sources.join(', ') || 'none recorded'}. Supabase: ${target.usedSupabase ? 'used' : 'not used'}. Assumptions: ${target.assumptions.join('; ') || 'none recorded'}. Confidence: ${target.confidence}.`;
  }
  if (!target) return input.text;
  return `${target.text}\n\n**Audit details**\n- Route: ${target.route}\n- Intent/domain: ${target.intent} / ${target.domain}\n- Sources: ${target.sources.join(', ') || 'none recorded'}\n- Supabase: ${target.usedSupabase ? 'used' : 'not used'}\n- Timestamp: ${target.timestamp}\n- Confidence: ${target.confidence}\n- Blockers: ${target.blockers.join('; ') || 'none recorded'}\n- Assumptions: ${target.assumptions.join('; ') || 'none recorded'}`;
}
