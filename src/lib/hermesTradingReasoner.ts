import { getHermesPageRuntimeContext } from './hermesContextBridge';
import tradingProof from '../../reports/trading_lab_proof_latest.json';

export type TradingQuestionType = 'list' | 'recommend' | 'last_test' | 'status' | 'execution' | 'general';

export function classifyTradingQuestion(message: string): TradingQuestionType {
  const lower = message.toLowerCase();
  if (/\b(place|execute|open|make)\b.*\btrade\b|\bbuy\b|\bsell\b/.test(lower)) return 'execution';
  if (/\b(what|which|list|show).*\b(strategies|setups|systems)\b|\bstrategies.*(?:available|have|in the trading lab)\b/.test(lower)) return 'list';
  if (/\b(recommend|best|choose|pick|which one)\b/.test(lower)) return 'recommend';
  if (/\b(last|latest|recent).*\b(test|backtest|trade|result)\b/.test(lower)) return 'last_test';
  if (/\b(running|status|active|live)\b/.test(lower)) return 'status';
  return 'general';
}

function strategies() {
  return getHermesPageRuntimeContext('trading').visibleItems.filter(item => item.type === 'strategy');
}

export function answerTradingQuestion(message: string): { text: string; handler: string; source: string; confidence: 'high' | 'medium' } {
  const type = classifyTradingQuestion(message);
  const known = strategies();
  if (type === 'execution') return { text: 'I cannot place or execute a trade. Trading remains paper/demo only, and live or funded broker execution is blocked.', handler: 'trading_safety_block', source: 'safety_policy', confidence: 'high' };
  if (type === 'list') {
    const list = known.map((item, index) => `${index + 1}. **${item.title}** — ${item.status}; source: ${item.dataSource}.`).join('\n');
    return { text: `The Trading Lab currently exposes these local paper/demo strategy records:\n\n${list}\n\nThe latest proof report has no recent backtest timestamp or strategy report. These names are visible local context, not proof that a strategy is profitable or currently running.`, handler: 'trading_strategy_list', source: 'trading_page_context_and_proof_report', confidence: 'high' };
  }
  if (type === 'recommend') {
    return { text: `I cannot honestly recommend a specific trading strategy yet because I do not have enough verified backtest/report evidence in the current context. The local Trading Lab lists ${known.map(item => item.title).join(', ')}, but the latest proof report records no recent backtest timestamp and no latest strategy report.\n\nTo recommend one, I need comparable sample size, drawdown, profit factor, out-of-sample results, and stability for each strategy.\n\n**Next safe action:** review the latest paper/demo trading reports or run a paper-only backtest. No live/funded trading.`, handler: 'trading_evidence_recommendation', source: 'trading_page_context_and_proof_report', confidence: 'high' };
  }
  if (type === 'last_test') return { text: `The latest Trading Lab proof does not identify a recent backtest or latest strategy report. It records latestBacktestAt as ${tradingProof.latestBacktestAt ?? 'not available'} and lists “No proof of recent backtest execution” as a blocker. I cannot claim a newer trading test from this context.`, handler: 'trading_last_test', source: 'trading_lab_proof_report', confidence: 'high' };
  if (type === 'status') return { text: `Trading Lab is paper-only. The proof snapshot records live trading disabled, no funded broker connection, and no recent verified backtest or strategy report. It also records a trading engine process, but that is not evidence of a profitable or currently executing strategy.`, handler: 'trading_status', source: 'trading_lab_proof_report', confidence: 'high' };
  return { text: `Trading Lab is limited to local paper/demo research. Known strategy records: ${known.map(item => item.title).join(', ')}. I need verified comparable backtest evidence before selecting one.`, handler: 'trading_general', source: 'trading_page_context_and_proof_report', confidence: 'medium' };
}
