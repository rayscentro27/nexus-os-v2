import { assertPhaseOneSafety, getAlphaRuntimeConfig, type AlphaRuntimeConfig } from "./alphaSafety";

export interface AlphaProviderResult {
  provider: "mock";
  text: string;
  externalCallPerformed: false;
  estimatedCostUsd: 0;
}

export function runAlphaProvider(prompt: string, overrides: Partial<AlphaRuntimeConfig> = {}): AlphaProviderResult {
  const config = getAlphaRuntimeConfig(overrides);
  assertPhaseOneSafety(config);
  return {
    provider: "mock",
    text: `Offline Alpha analysis prepared for: ${prompt.trim()}`,
    externalCallPerformed: false,
    estimatedCostUsd: 0,
  };
}
