const json = (statusCode, body) => ({
  statusCode,
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify(body),
});

const present = (value) => Boolean(value && String(value).trim());
const readMode = (value) => ['OFF', 'SHADOW', 'RAY_ONLY_PILOT', 'ACTIVE'].includes(value) ? value : 'OFF';
const readLettaMode = (value) => ['HOSTED', 'SELF_HOSTED'].includes(value) ? value : null;

function runtimeStatus() {
  const lettaMode = readLettaMode(process.env.LETTA_RUNTIME_MODE);
  const openRouterKeyPresent = present(process.env.OPENROUTER_API_KEY);
  const lettaReady = lettaMode === 'HOSTED'
    ? present(process.env.LETTA_API_KEY) && present(process.env.LETTA_HERMES_AGENT_ID)
    : lettaMode === 'SELF_HOSTED'
      ? present(process.env.LETTA_BASE_URL) && present(process.env.LETTA_HERMES_AGENT_ID)
      : false;
  const blockers = [
    ...(!openRouterKeyPresent ? ['BLOCKED_PENDING_OPENROUTER_KEY'] : []),
    ...(!lettaReady ? ['BLOCKED_PENDING_LETTA_RUNTIME'] : []),
  ];
  return {
    modelFirstMode: readMode(process.env.HERMES_MODEL_FIRST_MODE),
    openrouterState: openRouterKeyPresent ? 'DEGRADED' : 'MISSING_KEY',
    primaryModel: process.env.HERMES_OPENROUTER_MODEL || 'openai/gpt-5.6-luna',
    backupModel: process.env.HERMES_OPENROUTER_BACKUP_MODEL || 'google/gemini-2.5-flash',
    lettaRuntimeMode: lettaMode || 'NOT_CONFIGURED',
    lettaAgentIdPresent: present(process.env.LETTA_HERMES_AGENT_ID),
    activationBlocked: blockers.length > 0,
    blockers,
  };
}

export async function handler(event) {
  if (event.httpMethod === 'OPTIONS') return json(200, { ok: true });
  if (event.httpMethod === 'GET') return json(200, runtimeStatus());
  if (event.httpMethod !== 'POST') return json(405, { error: 'method_not_allowed' });

  const status = runtimeStatus();
  if (status.activationBlocked || status.modelFirstMode === 'OFF') {
    return json(503, {
      configured: false,
      decisionType: 'DEGRADED',
      response: 'My model-first conversational brain is not configured yet. I can still use the certified legacy Hermes path, but I will not pretend OpenRouter or Letta is active.',
      status,
    });
  }

  return json(501, {
    configured: false,
    decisionType: 'DEGRADED',
    response: 'The model-first Hermes endpoint is gated until OpenRouter health, Letta agent readiness, and Ray-only pilot authorization are verified.',
    status,
  });
}
