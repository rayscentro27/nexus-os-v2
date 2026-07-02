export type ResponseMode = 'screen' | 'voice_ready';

export interface VoiceReadyResponse {
  plainAnswer: string;
  sourceUsed?: string;
  keyEvidence?: string[];
  blockerMissing?: string;
  nextSafeAction?: string;
  details?: string;
}

function extractPlainAnswer(text: string): string {
  const lines = text.split('\n').filter(l => l.trim().length > 0);
  const firstParagraph: string[] = [];
  for (const line of lines) {
    if (line.startsWith('**') && line.includes(':**')) break;
    if (line.startsWith('- ') || line.startsWith('* ')) break;
    firstParagraph.push(line);
  }
  if (firstParagraph.length === 0) return lines[0] || text.slice(0, 200);
  return firstParagraph.join(' ');
}

function extractSourceUsed(text: string): string | undefined {
  const match = text.match(/\*\*Source(?:\s+checked)?:\*\*\s*(.+?)(?:\n|$)/i);
  return match?.[1]?.trim();
}

function extractKeyEvidence(text: string): string[] {
  const evidenceMatch = text.match(/\*\*Evidence:\*\*\s*\n([\s\S]*?)(?=\*\*|$)/i);
  if (!evidenceMatch) return [];
  return evidenceMatch[1].split('\n').filter(l => l.startsWith('- ')).map(l => l.replace(/^- /, '').trim()).slice(0, 3);
}

function extractBlocker(text: string): string | undefined {
  const match = text.match(/\*\*Blocker(?:s)?:\*\*\s*(.+?)(?:\n|$)/i);
  return match?.[1]?.trim();
}

function extractNextAction(text: string): string | undefined {
  const match = text.match(/\*\*Next safe action:\*\*\s*(.+?)(?:\n|$)/i);
  return match?.[1]?.trim();
}

export function renderVoiceReady(text: string, mode: ResponseMode = 'voice_ready'): VoiceReadyResponse {
  if (mode === 'screen') {
    return {
      plainAnswer: text,
      sourceUsed: extractSourceUsed(text),
      keyEvidence: extractKeyEvidence(text),
      blockerMissing: extractBlocker(text),
      nextSafeAction: extractNextAction(text),
      details: text,
    };
  }

  const plainAnswer = extractPlainAnswer(text);
  const sourceUsed = extractSourceUsed(text);
  const keyEvidence = extractKeyEvidence(text);
  const blockerMissing = extractBlocker(text);
  const nextSafeAction = extractNextAction(text);

  return {
    plainAnswer,
    sourceUsed,
    keyEvidence,
    blockerMissing,
    nextSafeAction,
    details: text,
  };
}

export function formatForVoice(response: VoiceReadyResponse): string {
  let output = response.plainAnswer;

  if (response.sourceUsed) {
    output += ` ${response.sourceUsed}`;
  }

  if (response.blockerMissing && response.blockerMissing !== 'none reported by the source adapter' && !response.blockerMissing.startsWith('none')) {
    output += ` One thing to note: ${response.blockerMissing.charAt(0).toLowerCase() + response.blockerMissing.slice(1)}`;
  }

  if (response.nextSafeAction) {
    output += ` Next step: ${response.nextSafeAction.charAt(0).toLowerCase() + response.nextSafeAction.slice(1)}`;
  }

  return output;
}

export function formatForScreen(response: VoiceReadyResponse): string {
  let output = response.plainAnswer + '\n\n';

  if (response.sourceUsed) {
    output += `**Source:** ${response.sourceUsed}\n`;
  }

  if (response.keyEvidence && response.keyEvidence.length > 0) {
    output += `**Key evidence:**\n`;
    for (const evidence of response.keyEvidence) {
      output += `- ${evidence}\n`;
    }
  }

  if (response.blockerMissing) {
    output += `**Blocker:** ${response.blockerMissing}\n`;
  }

  if (response.nextSafeAction) {
    output += `**Next safe action:** ${response.nextSafeAction}\n`;
  }

  return output;
}
