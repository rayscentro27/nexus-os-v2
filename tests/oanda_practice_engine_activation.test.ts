import { describe, expect, it } from 'vitest';
import fs from 'node:fs';

describe('native Nexus Oanda practice engine activation', () => {
  const engine = fs.readFileSync('scripts/trading/nexus_oanda_practice_engine.py', 'utf8');
  const wrapper = fs.readFileSync('scripts/ops/run_nexus_oanda_practice_engine.sh', 'utf8');
  const plist = fs.readFileSync('launchd/com.nexus.oanda-practice-trading.plist.template', 'utf8');
  const vibe = fs.readFileSync('scripts/trading/vibe_trading_adapter.py', 'utf8');
  const commandCenter = fs.readFileSync('src/components/CommandCenter.jsx', 'utf8');

  it('implements the native practice bridge components and state machine', () => {
    for (const name of [
      'class OandaPracticeClient',
      'class MarketDataAdapter',
      'class StrategyAdapter',
      'class RiskEngine',
      'class OrderExecutor',
      'class PositionReconciler',
      'class TradingAuditRecorder',
      'class TradingKillSwitch',
      'class TradingStatusAdapter',
    ]) {
      expect(engine).toContain(name);
    }
    for (const state of ['WAITING_FOR_VALID_SIGNAL', 'SIGNAL_REJECTED', 'ORDER_FILLED', 'KILL_SWITCHED']) {
      expect(engine).toContain(state);
    }
  });

  it('enforces practice-only credentials and hard risk controls', () => {
    expect(engine).toContain('oanda_environment_not_practice');
    expect(engine).toContain('oanda_live_endpoint_detected_blocked');
    expect(engine).toContain('TEMPORARY_PRACTICE_CERTIFICATION_LIMITS');
    expect(engine).toContain('max_order_units');
    expect(engine).toContain('max_open_positions');
    expect(engine).toContain('stale_signal_seconds');
    expect(engine).toContain('duplicate_signal');
    expect(engine).toContain('spread_guard_rejected');
    expect(engine).toContain('real_money_trading');
  });

  it('replaces the old Vibe CLI blocker with a canonical launchd service', () => {
    expect(vibe).toContain('Paper/demo/backtest status only');
    expect(wrapper).toContain('run_with_nexus_runtime_env.sh');
    expect(wrapper).toContain('nexus_oanda_practice_engine.py');
    expect(plist).toContain('com.nexus.oanda-practice-trading');
    expect(plist).not.toMatch(/OANDA_API_TOKEN|OANDA_ACCOUNT_ID|SECRET|TOKEN/);
  });

  it('exposes runtime-backed trading state in the Command Center', () => {
    expect(commandCenter).toContain('/runtime/oanda-practice-status.json');
    expect(commandCenter).toContain('executive-oanda-practice-trading');
    expect(commandCenter).toContain('Oanda practice');
    expect(commandCenter).toContain('run real-money trading');
  });
});
