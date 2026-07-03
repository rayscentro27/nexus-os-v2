import type { AlphaProvider } from "./alphaTypes";

export const ALPHA_ENV_DEFAULTS = Object.freeze({
  HERMES_ALPHA_ENABLED: false,
  HERMES_ALPHA_PROVIDER: "mock" as AlphaProvider,
  HERMES_ALPHA_ALLOW_WEB: false,
  HERMES_ALPHA_ALLOW_OANDA: false,
  HERMES_ALPHA_ALLOW_SUPABASE: false,
  HERMES_ALPHA_ALLOW_NEXUS_CONTEXT: false,
  HERMES_ALPHA_ALLOW_LIVE_TRADING: false,
  HERMES_ALPHA_ALLOW_EXTERNAL_MODEL: false,
  HERMES_ALPHA_MAX_DAILY_COST_USD: 0,
});

export interface AlphaRuntimeConfig {
  HERMES_ALPHA_ENABLED: boolean;
  HERMES_ALPHA_PROVIDER: AlphaProvider;
  HERMES_ALPHA_ALLOW_WEB: boolean;
  HERMES_ALPHA_ALLOW_OANDA: boolean;
  HERMES_ALPHA_ALLOW_SUPABASE: boolean;
  HERMES_ALPHA_ALLOW_NEXUS_CONTEXT: boolean;
  HERMES_ALPHA_ALLOW_LIVE_TRADING: boolean;
  HERMES_ALPHA_ALLOW_EXTERNAL_MODEL: boolean;
  HERMES_ALPHA_MAX_DAILY_COST_USD: number;
  HERMES_ALPHA_OLLAMA_BASE_URL: string;
  HERMES_ALPHA_OLLAMA_API_KEY: string;
  HERMES_ALPHA_MODEL: string;
}

export function getAlphaRuntimeConfig(overrides: Partial<AlphaRuntimeConfig> = {}): AlphaRuntimeConfig {
  return {
    ...ALPHA_ENV_DEFAULTS,
    HERMES_ALPHA_OLLAMA_BASE_URL: "",
    HERMES_ALPHA_OLLAMA_API_KEY: "",
    HERMES_ALPHA_MODEL: "",
    ...overrides,
  };
}

export function assertPhaseOneSafety(config: AlphaRuntimeConfig): void {
  const unsafe = config.HERMES_ALPHA_ENABLED
    || config.HERMES_ALPHA_PROVIDER !== "mock"
    || config.HERMES_ALPHA_ALLOW_WEB
    || config.HERMES_ALPHA_ALLOW_OANDA
    || config.HERMES_ALPHA_ALLOW_SUPABASE
    || config.HERMES_ALPHA_ALLOW_NEXUS_CONTEXT
    || config.HERMES_ALPHA_ALLOW_LIVE_TRADING
    || config.HERMES_ALPHA_ALLOW_EXTERNAL_MODEL
    || config.HERMES_ALPHA_MAX_DAILY_COST_USD !== 0;
  if (unsafe) throw new Error("Hermes Alpha Phase 1 is disabled, offline, mock-only, zero-cost, and connection-free.");
}

export const ALPHA_BLOCKED_ACTIONS = Object.freeze([
  "external_send",
  "social_publish",
  "customer_charge",
  "production_write",
  "broker_connection",
  "trade_execution",
  "client_context_access",
]);
