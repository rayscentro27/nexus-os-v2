import { ALPHA_SOURCE_ORDER } from "./alphaTypes";
import { ALPHA_ENV_DEFAULTS, getAlphaRuntimeConfig } from "./alphaSafety";

export interface NoSupabaseGuardResult {
  passed: true;
  noSupabaseUsed: true;
  sourceOrder: readonly string[];
  connectionEnabled: false;
  productionAccess: false;
}

export function runNoSupabaseGuard(): NoSupabaseGuardResult {
  const config = getAlphaRuntimeConfig();
  if (config.HERMES_ALPHA_ALLOW_SUPABASE !== false || ALPHA_ENV_DEFAULTS.HERMES_ALPHA_ALLOW_SUPABASE !== false) {
    throw new Error("Phase 1 connection guard failed.");
  }
  return {
    passed: true,
    noSupabaseUsed: true,
    sourceOrder: ALPHA_SOURCE_ORDER,
    connectionEnabled: false,
    productionAccess: false,
  };
}
