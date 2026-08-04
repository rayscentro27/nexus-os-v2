#!/usr/bin/env node
import { createClient } from '@supabase/supabase-js';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const ROOT = path.resolve(process.cwd());
const ORIGINAL_ROOT = process.env.NEXUS_ORIGINAL_REPO || '/Users/raymonddavis/nexus-os-v2';
const DEFAULT_RUNTIME_DIR = '/Users/raymonddavis/nexus-hermes-runtime';
const PROCESS_KEY = 'official_hermes_runtime_adapter';
const REPORT_DIR = path.join(ROOT, 'reports', 'runtime');

export const HERMES_RUNTIME_ADAPTER_VERSION = 'Nexus Hermes Runtime Adapter v0.1';
export const OFFICIAL_HERMES_TARGET = '0.20.0';
export const ALLOWED_TASK_TYPES = new Set([
  'READ_ONLY_REPOSITORY_AUDIT',
  'RUN_TEST_SUITE',
  'BUILD_VERIFICATION',
  'GENERATE_INTERNAL_REPORT',
  'RESEARCH_SUMMARY_WITHOUT_CLIENT_DATA',
]);
export const PROHIBITED_TASK_TYPES = new Set([
  'SEND_CLIENT_MESSAGE',
  'SEND_DISPUTE',
  'APPLY_FOR_FUNDING',
  'CHARGE_CUSTOMER',
  'EXECUTE_TRADE',
  'CHANGE_RLS',
  'DELETE_PRODUCTION_DATA',
  'DEPLOY_PRODUCTION',
  'ARBITRARY_SHELL_COMMAND',
]);

function readEnvFile(file) {
  if (!fs.existsSync(file)) return {};
  const out = {};
  for (const raw of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [key, ...rest] = line.split('=');
    let value = rest.join('=').trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) value = value.slice(1, -1);
    out[key.trim()] = value;
  }
  return out;
}

function loadEnv() {
  const values = {};
  for (const root of [ORIGINAL_ROOT, ROOT]) {
    for (const name of ['.env', '.env.local', '.env.e2e.local']) Object.assign(values, readEnvFile(path.join(root, name)));
  }
  Object.assign(values, process.env);
  return values;
}

function parseArgs(argv) {
  const args = { taskType: 'BUILD_VERIFICATION', taskId: `nexus-hermes-${Date.now()}`, timeoutMs: 10 * 60_000, runtimeDir: DEFAULT_RUNTIME_DIR };
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = argv[i + 1];
    if (arg === '--task-type') { args.taskType = next; i += 1; }
    else if (arg === '--task-id') { args.taskId = next; i += 1; }
    else if (arg === '--timeout-ms') { args.timeoutMs = Number(next); i += 1; }
    else if (arg === '--runtime-dir') { args.runtimeDir = next; i += 1; }
  }
  return args;
}

function runCommand(command, args, options = {}) {
  const started = Date.now();
  return new Promise((resolve) => {
    const { timeoutMs, ...spawnOptions } = options;
    const child = spawn(command, args, { cwd: ROOT, env: process.env, stdio: ['ignore', 'pipe', 'pipe'], ...spawnOptions });
    let stdout = '';
    let stderr = '';
    let settled = false;
    let timer = null;
    if (timeoutMs) {
      timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        child.kill('SIGTERM');
        setTimeout(() => {
          if (!child.killed) child.kill('SIGKILL');
        }, 1000).unref?.();
        resolve({ command: [command, ...args].join(' '), exitCode: null, timedOut: true, durationMs: Date.now() - started, stdout, stderr });
      }, timeoutMs);
    }
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      resolve({ command: [command, ...args].join(' '), exitCode: 127, durationMs: Date.now() - started, stdout, stderr: `${stderr}\n${error.message}`.trim() });
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      resolve({ command: [command, ...args].join(' '), exitCode: code ?? 1, durationMs: Date.now() - started, stdout, stderr });
    });
  });
}

async function probeOfficialHermes(runtimeDir) {
  const hermes = path.join(runtimeDir, '.venv', 'bin', 'hermes');
  if (!fs.existsSync(hermes)) {
    return { configured: false, reachable: false, version: null, detail: 'hermes executable missing' };
  }
  const result = await runCommand(hermes, ['--version'], { cwd: runtimeDir });
  const firstLine = result.stdout.split(/\r?\n/).find(Boolean) || result.stderr.split(/\r?\n/).find(Boolean) || '';
  return {
    configured: true,
    reachable: result.exitCode === 0,
    version: firstLine,
    detail: result.exitCode === 0 ? 'version probe succeeded' : `version probe failed exit ${result.exitCode}`,
  };
}

function getVerificationCommands(taskType) {
  if (taskType === 'RUN_TEST_SUITE') {
    return [
      ['npm', ['run', 'typecheck']],
      ['npm', ['test', '--', '--run']],
      ['npm', ['run', 'build']],
    ];
  }
  if (taskType === 'BUILD_VERIFICATION') {
    return [
      ['npm', ['run', 'typecheck']],
      ['npm', ['run', 'build']],
    ];
  }
  return [['git', ['status', '--short']]];
}

async function ensureProcess(sb) {
  const row = {
    process_key: PROCESS_KEY,
    name: 'Official Hermes Runtime Adapter',
    description: 'Local-only governed bridge from Nexus process requests to an isolated official Hermes Agent runtime.',
    system: 'hermes',
    entry_point: 'scripts/hermes_runtime/nexus_hermes_runtime_adapter.mjs',
    trigger_type: 'manual',
    enabled: true,
    execution_mode: 'bounded_local_adapter',
    owner: 'nexus',
    approval_policy: 'task_type_allowlist',
    max_runtime_seconds: 900,
    max_retries: 1,
    is_mock: false,
    metadata: {
      adapterVersion: HERMES_RUNTIME_ADAPTER_VERSION,
      officialHermesTarget: OFFICIAL_HERMES_TARGET,
      allowedTaskTypes: Array.from(ALLOWED_TASK_TYPES),
      prohibitedTaskTypes: Array.from(PROHIBITED_TASK_TYPES),
    },
  };
  const { data, error } = await sb.from('nexus_process_definitions').upsert(row, { onConflict: 'process_key' }).select('id').single();
  if (error) throw error;
  return data.id;
}

async function createRun(sb, processId, args, metadata) {
  const existing = await sb.from('nexus_process_runs').select('id,status,metadata').eq('idempotency_key', args.taskId).maybeSingle();
  if (existing.data?.id) {
    return { duplicate: true, run: existing.data };
  }
  const { data, error } = await sb.from('nexus_process_runs').insert({
    process_id: processId,
    idempotency_key: args.taskId,
    status: 'RUNNING',
    started_at: new Date().toISOString(),
    heartbeat_at: new Date().toISOString(),
    triggered_by: 'local_certification_adapter',
    trace_id: args.taskId,
    metadata,
  }).select('id').single();
  if (error) throw error;
  return { duplicate: false, run: data };
}

async function updateRun(sb, runId, patch) {
  const { error } = await sb.from('nexus_process_runs').update({ heartbeat_at: new Date().toISOString(), ...patch }).eq('id', runId);
  if (error) throw error;
}

function sourceChangedBeforeAfter(before, after) {
  const ignoredPrefixes = ['?? reports/', '?? test-results/', '?? NEXUS_', '?? .env.e2e.local'];
  const normalized = (text) => text.split(/\r?\n/).filter(Boolean).filter((line) => !ignoredPrefixes.some((prefix) => line.startsWith(prefix))).join('\n');
  return normalized(before) !== normalized(after);
}

async function main() {
  const args = parseArgs(process.argv);
  if (PROHIBITED_TASK_TYPES.has(args.taskType)) {
    throw new Error(`prohibited task type: ${args.taskType}`);
  }
  if (!ALLOWED_TASK_TYPES.has(args.taskType)) {
    throw new Error(`unsupported task type: ${args.taskType}`);
  }

  const env = loadEnv();
  const url = env.SUPABASE_URL || env.VITE_SUPABASE_URL;
  const serviceKey = env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) throw new Error('Supabase service credentials unavailable for local adapter registry writes');
  const sb = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false } });

  fs.mkdirSync(REPORT_DIR, { recursive: true });
  const officialProbe = await probeOfficialHermes(args.runtimeDir);
  const before = await runCommand('git', ['status', '--short']);
  const processId = await ensureProcess(sb);
  const start = await createRun(sb, processId, args, {
    taskType: args.taskType,
    adapterVersion: HERMES_RUNTIME_ADAPTER_VERSION,
    officialHermes: officialProbe,
    workspace: ROOT,
    maxRuntimeMs: args.timeoutMs,
  });
  if (start.duplicate) {
    console.log(JSON.stringify({ result: 'DUPLICATE_TASK', taskId: args.taskId, runId: start.run.id, status: start.run.status }, null, 2));
    return;
  }

  const runId = start.run.id;
  const commands = getVerificationCommands(args.taskType);
  const outputs = [];
  let timedOut = false;
  let itemsFailed = 0;
  for (const [command, commandArgs] of commands) {
    await updateRun(sb, runId, { status: 'RUNNING' });
    const result = await runCommand(command, commandArgs, { timeoutMs: args.timeoutMs });
    if (result?.timedOut) {
      timedOut = true;
      itemsFailed += 1;
      outputs.push({ command: [command, ...commandArgs].join(' '), exitCode: null, timedOut: true });
      break;
    }
    outputs.push(result);
    if (result.exitCode !== 0) itemsFailed += 1;
  }
  const after = await runCommand('git', ['status', '--short']);
  const changed = sourceChangedBeforeAfter(before.stdout, after.stdout);
  if (changed) itemsFailed += 1;

  const reportPath = path.join(REPORT_DIR, `${args.taskId}.json`);
  const report = {
    taskId: args.taskId,
    taskType: args.taskType,
    adapterVersion: HERMES_RUNTIME_ADAPTER_VERSION,
    officialHermes: officialProbe,
    startedStatus: before.stdout,
    endedStatus: after.stdout,
    sourceChanged: changed,
    commands: outputs.map((output) => ({
      command: output.command,
      exitCode: output.exitCode,
      timedOut: Boolean(output.timedOut),
      durationMs: output.durationMs,
      stdoutTail: String(output.stdout || '').slice(-4000),
      stderrTail: String(output.stderr || '').slice(-4000),
    })),
  };
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);

  const status = timedOut ? 'TIMED_OUT' : itemsFailed ? 'FAILED' : 'SUCCEEDED';
  await updateRun(sb, runId, {
    status,
    completed_at: new Date().toISOString(),
    items_attempted: commands.length + 1,
    items_succeeded: commands.length + 1 - itemsFailed,
    items_failed: itemsFailed,
    output_location: reportPath,
    error_code: status === 'SUCCEEDED' ? null : (timedOut ? 'TASK_TIMEOUT' : 'COMPLETION_CONTRACT_FAILED'),
    error_message: status === 'SUCCEEDED' ? null : 'One or more deterministic completion-contract checks failed.',
    metadata: { ...report, reportPath },
  });

  console.log(JSON.stringify({ result: status, taskId: args.taskId, runId, reportPath, officialHermes: officialProbe.version }, null, 2));
  if (status !== 'SUCCEEDED') process.exit(1);
}

main().catch((error) => {
  console.error(`nexus hermes runtime adapter failed: ${error.message}`);
  process.exit(1);
});
