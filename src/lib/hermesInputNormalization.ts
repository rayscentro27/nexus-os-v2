const SAFE_TOKEN_FIXES: Record<string, string> = {
  tyou: 'you', thing: 'think', fatest: 'fastest', recomend: 'recommend', recomendation: 'recommendation',
};

export function normalizeHermesRoutingInput(input: string): string {
  return input
    .replace(/\bgo;od\b/gi, 'good')
    .replace(/\b(tyou|thing|fatest|recomend|recomendation)\b/gi, token => SAFE_TOKEN_FIXES[token.toLowerCase()] || token)
    .replace(/\b(favou?rite|recommend(?:ed|ation)?)\s+care\b/gi, (_match, lead: string) => `${lead} vehicle car`);
}
