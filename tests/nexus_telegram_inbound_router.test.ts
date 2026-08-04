import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const bridgePath = 'scripts/telegram/nexus_telegram_bridge.py'
const bridge = () => readFileSync(bridgePath, 'utf8')

const runBridge = (message: string) =>
  execFileSync('python3', [bridgePath, '--test-command', message], {
    cwd: process.cwd(),
    encoding: 'utf8',
    env: { ...process.env, SUPABASE_URL: '', SUPABASE_SERVICE_ROLE_KEY: '' },
    timeout: 20_000,
  })

const forbiddenFallbacks = [
  'Clarify the question',
  'Source: internal Nexus context',
  "Say 'research deeper'",
  'search the web for',
]

describe('Nexus Telegram inbound router', () => {
  it('routes deterministic Nexus intents before the generic Hermes draft fallback', () => {
    const source = bridge()
    const commandBody = source.slice(source.indexOf('def process_command(text, mission=None):'))
    expect(commandBody.indexOf('handle_nexus_pre_route(full_text, mission=mission)')).toBeGreaterThan(0)
    expect(commandBody.indexOf('handle_nexus_pre_route(full_text, mission=mission)')).toBeLessThan(
      commandBody.indexOf('process_with_new_router(full_text)'),
    )
    expect(source).toContain('def process_command(text, mission=None):')
  })

  it.each([
    ['good morning', /Good (morning|afternoon|evening), Ray\. Nexus Hermes is online/i],
    ['can you provide a report on system status', /Nexus Hermes Live System Report/i],
    ['Nexus, give me the current Alpha research status and the most recent opportunities stored.', /Alpha Research Status/i],
    ['Nexus, show me every research job that ran since August 3, 2026.', /Research Jobs Since 2026-08-03/i],
    ['Nexus, give me the current Oanda practice trading report.', /Oanda Practice Trading Report/i],
    ['Nexus, what failed in the last 24 hours?', /Failures In The Last 24 Hours/i],
  ])('handles %s without the clarify fallback', (message, expected) => {
    const output = runBridge(message)
    expect(output).toMatch(expected)
    for (const forbidden of forbiddenFallbacks) expect(output).not.toContain(forbidden)
  })

  it('persists durable mission states for authorized inbound messages', () => {
    const source = bridge()
    for (const state of [
      'RECEIVED',
      'AUTHORIZED',
      'ROUTED',
      'TOOL_STARTED',
      'TOOL_COMPLETED',
      'RESPONSE_COMPOSED',
      'RESPONSE_SENT',
      'COMPLETED',
      'UNAUTHORIZED',
      'STALLED',
      'DELIVERY_FAILED',
    ]) {
      expect(source).toContain(state)
    }
    expect(source).toContain('chat_id_masked')
    expect(source).toContain('watchdog_stalled_missions')
  })

  it('adds a redacted Command Center mission panel', () => {
    const commandCenter = readFileSync('src/components/CommandCenter.jsx', 'utf8')
    expect(commandCenter).toContain('/runtime/nexus-telegram-missions.json')
    expect(commandCenter).toContain('executive-nexus-communications-missions')
    expect(commandCenter).toContain('Nexus Communications Missions')
  })
})
