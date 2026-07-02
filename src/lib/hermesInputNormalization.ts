const SAFE_TOKEN_FIXES: Record<string, string> = {
  tyou: 'you', thing: 'think', fatest: 'fastest', recomend: 'recommend', recomendation: 'recommendation',
};

export function normalizeHermesRoutingInput(input: string): string {
  return input.replace(/\b(tyou|thing|fatest|recomend|recomendation)\b/gi, token => SAFE_TOKEN_FIXES[token.toLowerCase()] || token);
}
