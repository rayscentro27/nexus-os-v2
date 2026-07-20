export type HermesModelFirstMode = 'OFF' | 'SHADOW' | 'RAY_ONLY_PILOT' | 'ACTIVE';
export type LettaRuntimeMode = 'HOSTED' | 'SELF_HOSTED';
export type OpenRouterHealthState =
  | 'READY'
  | 'MISSING_KEY'
  | 'MISSING_MODEL'
  | 'UNSUPPORTED_MODEL'
  | 'PROVIDER_UNAVAILABLE'
  | 'RATE_LIMITED'
  | 'BUDGET_EXCEEDED'
  | 'DEGRADED';
export type LettaRuntimeState = 'READY' | 'MISSING_API_KEY' | 'MISSING_BASE_URL' | 'MISSING_MODE' | 'MISSING_AGENT_ID' | 'BLOCKED';

export interface LettaRuntimeConfig {
  mode: LettaRuntimeMode | null;
  apiKeyPresent: boolean;
  baseUrlPresent: boolean;
  hermesAgentIdPresent: boolean;
  model: string;
  embeddingModel?: string;
}

export interface OpenRouterRuntimeConfig {
  apiKeyPresent: boolean;
  primaryModel: string;
  backupModel: string;
  maxOutputTokens: number;
  dailyLimitUsd: number;
  monthlyLimitUsd: number;
}

export interface HermesModelFirstRuntimeStatus {
  modelFirstMode: HermesModelFirstMode;
  openRouter: OpenRouterRuntimeConfig & { state: OpenRouterHealthState };
  letta: LettaRuntimeConfig & { state: LettaRuntimeState; packageName: string; packageVersion: string };
  activationBlocked: boolean;
  blockers: string[];
}

type RuntimeEnv = Record<string, string | undefined>;

const DEFAULT_PRIMARY_MODEL = 'openai/gpt-5.6-luna';
const DEFAULT_BACKUP_MODEL = 'google/gemini-2.5-flash';
const DEFAULT_MAX_OUTPUT_TOKENS = 600;
const DEFAULT_DAILY_LIMIT_USD = 0.5;
const DEFAULT_MONTHLY_LIMIT_USD = 10;

function present(value: string | undefined): boolean {
  return Boolean(value && value.trim());
}

function readNumber(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function readMode(value: string | undefined): HermesModelFirstMode {
  if (value === 'SHADOW' || value === 'RAY_ONLY_PILOT' || value === 'ACTIVE') return value;
  return 'OFF';
}

function readLettaMode(value: string | undefined): LettaRuntimeMode | null {
  if (value === 'HOSTED' || value === 'SELF_HOSTED') return value;
  return null;
}

function defaultEnv(): RuntimeEnv {
  const maybeProcess = globalThis as typeof globalThis & { process?: { env?: RuntimeEnv } };
  return maybeProcess.process?.env || {};
}

export function getOpenRouterRuntimeConfig(env: RuntimeEnv = defaultEnv()): OpenRouterRuntimeConfig {
  return {
    apiKeyPresent: present(env.OPENROUTER_API_KEY),
    primaryModel: env.HERMES_OPENROUTER_MODEL || DEFAULT_PRIMARY_MODEL,
    backupModel: env.HERMES_OPENROUTER_BACKUP_MODEL || DEFAULT_BACKUP_MODEL,
    maxOutputTokens: readNumber(env.HERMES_OPENROUTER_MAX_OUTPUT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS),
    dailyLimitUsd: readNumber(env.HERMES_OPENROUTER_DAILY_LIMIT_USD, DEFAULT_DAILY_LIMIT_USD),
    monthlyLimitUsd: readNumber(env.HERMES_OPENROUTER_MONTHLY_LIMIT_USD, DEFAULT_MONTHLY_LIMIT_USD),
  };
}

export function getLettaRuntimeConfig(env: RuntimeEnv = defaultEnv()): LettaRuntimeConfig {
  return {
    mode: readLettaMode(env.LETTA_RUNTIME_MODE),
    apiKeyPresent: present(env.LETTA_API_KEY),
    baseUrlPresent: present(env.LETTA_BASE_URL),
    hermesAgentIdPresent: present(env.LETTA_HERMES_AGENT_ID),
    model: env.HERMES_OPENROUTER_MODEL || DEFAULT_PRIMARY_MODEL,
    embeddingModel: env.LETTA_EMBEDDING_MODEL,
  };
}

export function classifyOpenRouter(config: OpenRouterRuntimeConfig, estimatedCostUsd = 0): OpenRouterHealthState {
  if (!config.apiKeyPresent) return 'MISSING_KEY';
  if (!config.primaryModel) return 'MISSING_MODEL';
  if (estimatedCostUsd > config.dailyLimitUsd || estimatedCostUsd > config.monthlyLimitUsd) return 'BUDGET_EXCEEDED';
  return 'DEGRADED';
}

export function classifyLetta(config: LettaRuntimeConfig): LettaRuntimeState {
  if (!config.mode) return 'MISSING_MODE';
  if (config.mode === 'HOSTED' && !config.apiKeyPresent) return 'MISSING_API_KEY';
  if (config.mode === 'SELF_HOSTED' && !config.baseUrlPresent) return 'MISSING_BASE_URL';
  if (!config.hermesAgentIdPresent) return 'MISSING_AGENT_ID';
  return 'READY';
}

export function getHermesModelFirstRuntimeStatus(env: RuntimeEnv = defaultEnv()): HermesModelFirstRuntimeStatus {
  const openRouter = getOpenRouterRuntimeConfig(env);
  const letta = getLettaRuntimeConfig(env);
  const openRouterState = classifyOpenRouter(openRouter);
  const lettaState = classifyLetta(letta);
  const blockers = [
    ...(openRouterState === 'MISSING_KEY' ? ['BLOCKED_PENDING_OPENROUTER_KEY'] : []),
    ...(lettaState !== 'READY' ? ['BLOCKED_PENDING_LETTA_RUNTIME'] : []),
  ];

  return {
    modelFirstMode: readMode(env.HERMES_MODEL_FIRST_MODE),
    openRouter: { ...openRouter, state: openRouterState },
    letta: {
      ...letta,
      state: lettaState,
      packageName: '@letta-ai/letta-client',
      packageVersion: '1.12.1',
    },
    activationBlocked: blockers.length > 0,
    blockers,
  };
}
