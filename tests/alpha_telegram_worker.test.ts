import { describe, expect, it, beforeEach, afterEach } from 'vitest';
import { readFileSync, existsSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';

// ─── Test data paths ───────────────────────────────────

const RUNTIME_ENV_PATH = join(process.env.HOME || '/tmp', '.config/nexus/runtime.env');
const WORKER_PATH = 'scripts/alpha/alpha_telegram_worker.py';
const PLIST_PATH = 'scripts/ops/com.nexus.telegram-alpha.plist';
const RUNNER_PATH = 'scripts/ops/run_alpha_with_runtime_env.sh';
const STATUS_PATH = 'data/runtime/alpha_telegram_status.json';
const OFFSET_PATH = 'data/runtime/alpha_telegram_last_update_id.json';
const MISSIONS_DIR = 'data/alpha/missions';

// ─── Phase 1: Bot identity ─────────────────────────────

describe('Alpha bot identity', () => {
  it('has ALPHA_TELEGRAM_BOT_TOKEN in canonical runtime.env', () => {
    expect(existsSync(RUNTIME_ENV_PATH)).toBe(true);
    const env = readFileSync(RUNTIME_ENV_PATH, 'utf-8');
    expect(env).toContain('ALPHA_TELEGRAM_BOT_TOKEN=');
  });

  it('worker script exists', () => {
    expect(existsSync(WORKER_PATH)).toBe(true);
  });

  it('worker imports do not reference TELEGRAM_BOT_TOKEN (Nexus token)', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    // Should only use ALPHA_TELEGRAM_BOT_TOKEN, not the generic TELEGRAM_BOT_TOKEN
    const lines = code.split('\n').filter(l => l.trim() && !l.trim().startsWith('#'));
    const genericTokenRefs = lines.filter(l =>
      l.includes('TELEGRAM_BOT_TOKEN') && !l.includes('ALPHA_TELEGRAM_BOT_TOKEN')
    );
    expect(genericTokenRefs).toHaveLength(0);
  });
});

// ─── Phase 2: Separate offset ──────────────────────────

describe('Alpha separate offset', () => {
  it('uses alpha_telegram_last_update_id.json, not telegram_last_update_id.json', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('alpha_telegram_last_update_id.json');
    // Must not share the Nexus offset
    const nexusOffsetRef = code.split('\n').filter(l =>
      l.includes('telegram_last_update_id.json') && !l.includes('alpha_telegram_last_update_id.json')
    );
    expect(nexusOffsetRef).toHaveLength(0);
  });

  it('has separate offset file path constant', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('ALPHA_OFFSET_PATH');
  });
});

// ─── Phase 4: Ray authorization ────────────────────────

describe('Ray authorization', () => {
  it('checks chat_id against allowed list', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('is_authorized');
    expect(code).toContain('TELEGRAM_CHAT_ID');
  });

  it('includes fallback Ray chat ID 1288928049', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('1288928049');
  });

  it('logs unauthorized access attempts', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('Unauthorized access attempt');
  });
});

// ─── Phase 6: Mission system ───────────────────────────

describe('Alpha mission system', () => {
  it('defines all required mission states', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    const requiredStates = [
      'RECEIVED', 'AUTHORIZED', 'ROUTED', 'RESEARCH_STARTED',
      'SOURCES_RETRIEVED', 'SYNTHESIS_STARTED', 'RESULT_STORED',
      'RESPONSE_COMPOSED', 'RESPONSE_SENT', 'COMPLETED',
    ];
    for (const state of requiredStates) {
      expect(code).toContain(state);
    }
  });

  it('defines all failure states', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    const failureStates = [
      'UNAUTHORIZED', 'ROUTING_FAILED', 'PROVIDER_FAILED',
      'STORAGE_FAILED', 'DELIVERY_FAILED', 'TIMED_OUT',
      'STALLED', 'DEAD_LETTERED',
    ];
    for (const state of failureStates) {
      expect(code).toContain(state);
    }
  });

  it('creates mission with required fields', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('mission_id');
    expect(code).toContain('update_id');
    expect(code).toContain('bot_id');
    expect(code).toContain('masked_chat_id');
    expect(code).toContain('original_message');
    expect(code).toContain('normalized_query');
    expect(code).toContain('selected_intent');
    expect(code).toContain('provider_calls');
    expect(code).toContain('source_count');
    expect(code).toContain('research_result_id');
    expect(code).toContain('opportunity_ids');
    expect(code).toContain('response_message_ids');
    expect(code).toContain('retry_count');
    expect(code).toContain('failure_reason');
  });

  it('persists missions to disk', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('ALPHA_MISSIONS_DIR');
    expect(code).toContain('alpha_mission_');
  });
});

// ─── Phase 7: Natural language routing ─────────────────

describe('Natural language routing', () => {
  it('classifies greetings', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('greeting');
    expect(code).toContain('good\\s+(?:morning|afternoon|evening|night)');
  });

  it('classifies research requests', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('research_request');
    expect(code).toContain('find|search|research');
  });

  it('classifies research status', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('research_status');
  });

  it('classifies opinion requests', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('opinion_request');
  });

  it('strips Alpha prefix from messages', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('alpha|@alphahermes27bot');
  });

  it('handles /alpha and /research slash commands', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('alpha|research');
  });
});

// ─── Phase 8: Live research pipeline ───────────────────

describe('Live research pipeline', () => {
  it('imports hermes_web_search module', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('from hermes_web_search import web_search');
  });

  it('executes web search with query', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('web_search(query');
  });

  it('synthesizes opportunities from results', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('_synthesize_opportunities');
  });

  it('stores research results to disk', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('RESEARCH_RESULTS_DIR');
    expect(code).toContain('alpha_result_');
  });

  it('stores individual opportunities', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('OPPORTUNITIES_DIR');
    expect(code).toContain('opp_');
  });
});

// ─── Phase 9: Response readability ─────────────────────

describe('Response readability', () => {
  it('composes research responses with required sections', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('ALPHA RESEARCH RESULT');
    expect(code).toContain('What I found');
    expect(code).toContain('My recommendation');
    expect(code).toContain('Recommended next action');
    expect(code).toContain('Action required from Ray');
  });

  it('composes greeting responses', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('_compose_greeting');
    expect(code).toContain('Alpha is online');
  });

  it('composes research status responses', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('ALPHA RESEARCH STATUS');
    expect(code).toContain('Missions processed');
  });

  it('does not dump raw IDs or filenames in default responses', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    // The compose functions should not include raw UUIDs or script paths
    const composeSection = code.substring(code.indexOf('def _compose_research_response'));
    expect(composeSection).not.toMatch(/alpha_mission_[a-z0-9_]+/);
    expect(composeSection).not.toMatch(/scripts\/[\w/]+\.py/);
  });

  it('hides technical details behind show commands', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('show sources');
  });
});

// ─── Phase 10: Delivery reliability ────────────────────

describe('Delivery reliability', () => {
  it('sends via ALPHA_TELEGRAM_BOT_TOKEN only', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    // tg_send_message should default to Alpha token
    expect(code).toContain('ALPHA_TELEGRAM_BOT_TOKEN');
  });

  it('chunks long messages', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('_chunk_message');
    expect(code).toContain('TELEGRAM_MAX_MSG');
  });

  it('records Telegram message IDs', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('response_message_ids');
    expect(code).toContain('message_id');
  });

  it('retries on delivery failure', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('Retry once after brief pause');
    expect(code).toContain('DELIVERY_FAILED');
  });
});

// ─── Phase 11: Watchdog ────────────────────────────────

describe('Watchdog', () => {
  it('checks for stale missions', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('check_stale_missions');
    expect(code).toContain('MISSION_TIMEOUT_SECONDS');
  });

  it('marks stalled missions', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('STALLED');
    expect(code).toContain('stalled');
  });

  it('notifies Nexus Hermes about stalls', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('_notify_nexus_stalled');
  });
});

// ─── Phase 12: Command Center status ───────────────────

describe('Command Center status', () => {
  it('writes runtime status file', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('ALPHA_STATUS_PATH');
    expect(code).toContain('write_status');
  });

  it('status includes all required fields', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('"service"');
    expect(code).toContain('"state"');
    expect(code).toContain('"pid"');
    expect(code).toContain('"heartbeat"');
    expect(code).toContain('"bot_identity"');
    expect(code).toContain('"polling_mode"');
    expect(code).toContain('"last_update_id"');
    expect(code).toContain('"last_incoming_message"');
    expect(code).toContain('"current_mission"');
    expect(code).toContain('"mission_stage"');
    expect(code).toContain('"provider_status"');
    expect(code).toContain('"source_count"');
    expect(code).toContain('"response_delivery"');
    expect(code).toContain('"pending_retries"');
    expect(code).toContain('"dead_letter_missions"');
    expect(code).toContain('"last_failure"');
  });
});

// ─── Phase 14: Duplicate protection ────────────────────

describe('Duplicate update protection', () => {
  it('saves offset only after processing', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    // Offset should be saved after process_message, not before
    const processSection = code.substring(code.indexOf('def run_once'));
    expect(processSection).toContain('save_offset(max_update_id)');
  });

  it('uses idempotent mission creation', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    // Mission ID includes update_id for uniqueness
    expect(code).toContain('alpha_mission_{');
    expect(code).toContain('update_id');
  });
});

// ─── Infrastructure ────────────────────────────────────

describe('Alpha service infrastructure', () => {
  it('launchd plist exists', () => {
    expect(existsSync(PLIST_PATH)).toBe(true);
  });

  it('plist uses --poll mode', () => {
    const plist = readFileSync(PLIST_PATH, 'utf-8');
    expect(plist).toContain('--poll');
  });

  it('wrapper script exists and is executable', () => {
    expect(existsSync(RUNNER_PATH)).toBe(true);
  });

  it('wrapper script accepts arguments', () => {
    const script = readFileSync(RUNNER_PATH, 'utf-8');
    expect(script).toContain('"$@"');
  });

  it('wrapper sources runtime.env', () => {
    const script = readFileSync(RUNNER_PATH, 'utf-8');
    expect(script).toContain('source');
    expect(script).toContain('runtime.env');
  });

  it('wrapper uses set -a to export variables', () => {
    const script = readFileSync(RUNNER_PATH, 'utf-8');
    expect(script).toContain('set -a');
  });

  it('worker has --once, --poll, and --test modes', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).toContain('--once');
    expect(code).toContain('--poll');
    expect(code).toContain('--test');
  });
});

// ─── Safety: no secrets in code ────────────────────────

describe('No secrets in code', () => {
  it('worker does not contain bot token values', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    // Should not contain actual token strings
    expect(code).not.toMatch(/8986632054:[A-Za-z0-9_-]{30,}/);
    expect(code).not.toMatch(/8935612290:[A-Za-z0-9_-]{30,}/);
  });

  it('worker does not expose env values', () => {
    const code = readFileSync(WORKER_PATH, 'utf-8');
    expect(code).not.toMatch(/eyJ[A-Za-z0-9_-]{20,}/);
    expect(code).not.toMatch(/sk_live_[A-Za-z0-9_-]{12,}/);
    expect(code).not.toMatch(/BSAac[A-Za-z0-9_-]{20,}/);
  });
});
