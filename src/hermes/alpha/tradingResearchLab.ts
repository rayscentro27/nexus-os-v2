import { scoreAlphaObjective } from "./alphaScoring";

export function analyzeTradingStrategy(objective: string) {
  return {
    status: "research_only" as const,
    score: scoreAlphaObjective("trading_research", objective),
    specification: {
      hypothesis: objective.trim(),
      requiredInputs: ["instrument", "timeframe", "entry", "exit", "stop", "position sizing", "data period"],
      requiredMetrics: ["win rate", "profit factor", "max drawdown", "risk/reward", "sample size", "expectancy", "stability"],
    },
    nextExperiment: "Write a deterministic strategy specification and offline backtest plan with costs and out-of-sample validation.",
    demoOnly: true,
    brokerConnected: false,
    tradesPlaced: 0,
    liveTradingBlocked: true,
  };
}
