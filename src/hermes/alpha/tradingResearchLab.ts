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

export function createBacktestPlan(objective: string) {
  return {
    status: "draft_only" as const,
    objective,
    steps: ["Freeze strategy rules", "Select approved historical data", "Model spread/slippage/costs", "Split in-sample and out-of-sample windows", "Compare with baseline", "Run sensitivity and regime checks", "Produce reproducible receipt"],
    executionEnabled: false,
  };
}

export function createTradingRiskReview(objective: string) {
  return {
    status: "research_only" as const,
    objective,
    risks: ["overfitting", "look-ahead bias", "data snooping", "spread/slippage", "drawdown", "consecutive losses", "regime dependence", "operational failure"],
    recommendation: "Do not connect a broker or place a trade; validate the specification and downside limits offline.",
    liveTradingBlocked: true,
  };
}
