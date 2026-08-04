#!/usr/bin/env node
import { createClient } from '@supabase/supabase-js';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { loadRuntimeEnv } from '../ops/nexusRuntimeEnv.mjs';

const ROOT = process.cwd();
const REPORT = path.join(ROOT, 'NEXUS_LIVE_BACKEND_CERTIFICATION.md');

function readEnvFile(file) {
  if (!fs.existsSync(file)) return {};
  const out = {};
  for (const raw of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [key, ...rest] = line.split('=');
    let value = rest.join('=').trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    out[key.trim()] = value;
  }
  return out;
}

function loadEnv() {
  const values = loadRuntimeEnv({ override: true });
  Object.assign(values, process.env);
  return values;
}

function maskEmail(email) {
  const [local, domain] = String(email).split('@');
  if (!domain) return '<masked>';
  return `${local.slice(0, 2)}***${local.slice(-1)}@${domain}`;
}

const env = loadEnv();
const supabaseUrl = env.SUPABASE_URL || env.VITE_SUPABASE_URL;
const anonKey = env.VITE_SUPABASE_ANON_KEY;
const serviceKey = env.SUPABASE_SERVICE_ROLE_KEY;

const accounts = [
  { key: 'CERT_ADMIN', label: 'nexus-cert-admin', role: 'admin', tenantId: 'nexus-cert-admin', clientId: null },
  { key: 'PERSONA_A', label: 'Persona A', role: 'client', tenantId: 'tenant-cert-persona-a', clientId: 'client-cert-persona-a' },
  { key: 'PERSONA_B', label: 'Persona B', role: 'client', tenantId: 'tenant-cert-persona-b', clientId: 'client-cert-persona-b' },
  { key: 'PERSONA_C', label: 'Persona C', role: 'client', tenantId: 'tenant-cert-persona-c', clientId: 'client-cert-persona-c' },
  { key: 'PERSONA_D', label: 'Persona D', role: 'client', tenantId: 'tenant-cert-persona-d', clientId: 'client-cert-persona-d' },
].map((account) => ({
  ...account,
  email: env[`E2E_${account.key}_EMAIL`],
  password: env[`E2E_${account.key}_PASSWORD`],
}));

const checks = [];
const sessions = new Map();
const uploadedPaths = [];

function record(area, check, result, evidence = '') {
  checks.push({ area, check, result, evidence });
  const printable = evidence ? ` ${evidence}` : '';
  console.log(`${result}: ${area} — ${check}${printable}`);
}

function expect(condition, area, check, evidence = '') {
  record(area, check, condition ? 'PASS' : 'FAIL', evidence);
}

function clientForSession(accessToken) {
  return createClient(supabaseUrl, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
    global: { headers: { Authorization: `Bearer ${accessToken}` } },
  });
}

async function signIn(account) {
  const client = createClient(supabaseUrl, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  const { data, error } = await client.auth.signInWithPassword({ email: account.email, password: account.password });
  if (error || !data.session?.access_token || !data.session?.refresh_token || !data.user?.id) {
    record('Auth', `${account.label} password login`, 'FAIL', error?.message || 'no session');
    return null;
  }
  sessions.set(account.key, { ...account, userId: data.user.id, session: data.session, client: clientForSession(data.session.access_token) });
  record('Auth', `${account.label} password login`, 'PASS', `user suffix ${data.user.id.slice(-8)} email ${maskEmail(account.email)}`);

  const restored = createClient(supabaseUrl, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
    global: { headers: { Authorization: `Bearer ${data.session.access_token}` } },
  });
  const { data: userData, error: userError } = await restored.auth.getUser(data.session.access_token);
  expect(!userError && userData.user?.id === data.user.id, 'Auth', `${account.label} session restoration`);

  const { error: badError } = await client.auth.signInWithPassword({ email: account.email, password: `${account.password}x-invalid` });
  expect(Boolean(badError), 'Auth', `${account.label} invalid-password denial`);
  await client.auth.signOut();
  return sessions.get(account.key);
}

async function runAuthAndRls() {
  for (const account of accounts) {
    if (!account.email || !account.password) {
      record('Auth', `${account.label} credentials configured`, 'BLOCKED', 'missing local env');
      continue;
    }
    await signIn(account);
  }

  const admin = sessions.get('CERT_ADMIN');
  const personaA = sessions.get('PERSONA_A');
  const personaB = sessions.get('PERSONA_B');
  const personaC = sessions.get('PERSONA_C');
  const personaD = sessions.get('PERSONA_D');
  if (!admin || !personaA || !personaB || !personaC || !personaD) return;

  const { data: adminRows, error: adminRowError } = await admin.client.from('admin_users').select('id,role,active').eq('id', admin.userId);
  expect(!adminRowError && adminRows?.[0]?.active === true, 'RLS', 'administrator can read active admin_users row');

  for (const persona of [personaA, personaB, personaC, personaD]) {
    const { data: membership, error: membershipError } = await persona.client
      .from('tenant_memberships')
      .select('tenant_id,client_id,role')
      .eq('user_id', persona.userId)
      .eq('tenant_id', persona.tenantId)
      .eq('client_id', persona.clientId)
      .maybeSingle();
    expect(!membershipError && membership?.role === 'client', 'RLS', `${persona.label} can read own tenant membership`, membership ? `tenant ${membership.tenant_id}` : '');
    persona.membership = membership;

    const { data: profile, error: profileError } = await persona.client
      .from('client_profiles')
      .select('tenant_id,client_id,client_visible')
      .eq('tenant_id', persona.tenantId)
      .eq('client_id', persona.clientId)
      .maybeSingle();
    expect(!profileError && profile?.client_id === persona.clientId, 'RLS', `${persona.label} can read own client profile`);

    const { data: adminVisible, error: clientAdminError } = await persona.client.from('admin_users').select('id').limit(5);
    expect(!clientAdminError && (adminVisible?.length || 0) === 0, 'RLS', `${persona.label} cannot read admin-only rows`);

    const { error: adminInsertError } = await persona.client
      .from('admin_users')
      .insert({ id: persona.userId, email: persona.email, role: 'admin', active: true });
    expect(Boolean(adminInsertError), 'RLS', `${persona.label} cannot insert admin_users`);
  }

  const crossPairs = [
    [personaA, personaB],
    [personaA, personaC],
    [personaB, personaA],
    [personaC, personaD],
    [personaD, personaA],
  ];
  for (const [reader, target] of crossPairs) {
    const targetClient = target.membership?.client_id;
    const { data, error } = await reader.client.from('client_profiles').select('client_id').eq('client_id', targetClient);
    expect(!error && (data?.length || 0) === 0, 'RLS', `${reader.label} cannot read ${target.label} profile`);
  }

  const anon = createClient(supabaseUrl, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  const { data: anonProfiles, error: anonError } = await anon.from('client_profiles').select('client_id').limit(5);
  expect(Boolean(anonError) || (anonProfiles?.length || 0) === 0, 'RLS', 'unauthenticated user cannot read protected client profiles');

  const { data: registryRows, error: registryError } = await admin.client.from('nexus_process_definitions').select('id').limit(5);
  expect(!registryError && Array.isArray(registryRows), 'RLS', 'administrator can read process registry');
  const { data: clientRegistryRows, error: clientRegistryError } = await personaA.client.from('nexus_process_definitions').select('id').limit(5);
  expect(!clientRegistryError && (clientRegistryRows?.length || 0) === 0, 'RLS', 'client cannot read process registry rows');
}

async function runStorage() {
  const admin = sessions.get('CERT_ADMIN');
  const personaA = sessions.get('PERSONA_A');
  const personaB = sessions.get('PERSONA_B');
  if (!admin || !personaA || !personaB) return;

  const aPath = `${personaA.userId}/certification/${Date.now()}-persona-a-credit-report.txt`;
  const bPath = `${personaB.userId}/certification/${Date.now()}-persona-b-bank-statement.txt`;
  const textBlob = new Blob(['Synthetic certification file. No real PII.'], { type: 'text/plain' });
  const { error: uploadAError } = await personaA.client.storage.from('client-documents').upload(aPath, textBlob, { contentType: 'text/plain', upsert: false });
  expect(!uploadAError, 'Storage', 'Persona A upload synthetic file', uploadAError?.message || aPath);
  if (!uploadAError) uploadedPaths.push(aPath);

  const { data: ownDownload, error: ownReadError } = await personaA.client.storage.from('client-documents').download(aPath);
  expect(!ownReadError && ownDownload, 'Storage', 'Persona A read own file');

  const { error: crossReadError } = await personaB.client.storage.from('client-documents').download(aPath);
  expect(Boolean(crossReadError), 'Storage', 'Persona B cannot read Persona A file');

  const { error: uploadBError } = await personaB.client.storage.from('client-documents').upload(bPath, textBlob, { contentType: 'text/plain', upsert: false });
  expect(!uploadBError, 'Storage', 'Persona B upload synthetic file', uploadBError?.message || bPath);
  if (!uploadBError) uploadedPaths.push(bPath);

  const { error: overwriteError } = await personaB.client.storage.from('client-documents').upload(aPath, textBlob, { contentType: 'text/plain', upsert: true });
  expect(Boolean(overwriteError), 'Storage', 'Persona B cannot overwrite Persona A file');

  const { error: duplicateError } = await personaA.client.storage.from('client-documents').upload(aPath, textBlob, { contentType: 'text/plain', upsert: false });
  expect(Boolean(duplicateError), 'Storage', 'duplicate upload without upsert is rejected');

  const invalidPath = `${personaA.userId}/certification/${Date.now()}-invalid.exe`;
  const { error: invalidMimeError } = await personaA.client.storage
    .from('client-documents')
    .upload(invalidPath, new Blob(['invalid'], { type: 'application/x-msdownload' }), { contentType: 'application/x-msdownload', upsert: false });
  expect(Boolean(invalidMimeError), 'Storage', 'invalid MIME rejected');

  const largePath = `${personaA.userId}/certification/${Date.now()}-oversized.txt`;
  const { error: largeError } = await personaA.client.storage
    .from('client-documents')
    .upload(largePath, new Blob([new Uint8Array(10 * 1024 * 1024 + 1)], { type: 'text/plain' }), { contentType: 'text/plain', upsert: false });
  expect(Boolean(largeError), 'Storage', 'oversized file rejected');

  const docId = `cert-${personaA.membership.client_id}-${Date.now()}-credit-report`;
  const { error: metadataError } = await personaA.client.from('client_documents').upsert({
    id: docId,
    tenant_id: personaA.membership.tenant_id,
    client_id: personaA.membership.client_id,
    category: 'credit_reports',
    classified_category: 'credit_reports',
    title: 'Synthetic credit report certification upload',
    summary: 'Synthetic metadata row created by live backend certification.',
    status: 'uploaded',
    client_visible: true,
    approval_required: true,
    source: 'client_portal_upload',
    payload: { synthetic: true, storagePath: aPath },
    classification_status: 'CLASSIFIED_HIGH_CONFIDENCE',
    classification_confidence: 0.92,
    classification_basis: { filename: true, mimeType: true, synthetic: true },
    review_state: 'ROUTED',
  }, { onConflict: 'id' });
  expect(!metadataError, 'Storage', 'classification metadata persisted', metadataError?.message || docId);

  const { data: docRows, error: docReadError } = await personaA.client
    .from('client_documents')
    .select('id,classification_status,classification_confidence,classified_category,review_state')
    .eq('id', docId);
  expect(!docReadError && docRows?.[0]?.classification_status === 'CLASSIFIED_HIGH_CONFIDENCE', 'Storage', 'classification metadata readable by owner');

  const { data: bDocRows, error: bDocReadError } = await personaB.client.from('client_documents').select('id').eq('id', docId);
  expect(!bDocReadError && (bDocRows?.length || 0) === 0, 'Storage', 'Persona B cannot read Persona A document metadata');

  const { data: adminDocRows, error: adminDocError } = await admin.client.from('client_documents').select('id').eq('id', docId);
  expect(!adminDocError && adminDocRows?.length === 1, 'Storage', 'administrator can read synthetic document metadata');
}

async function cleanupStorage() {
  if (!uploadedPaths.length || !serviceKey) return;
  const admin = createClient(supabaseUrl, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  await admin.storage.from('client-documents').remove(uploadedPaths);
}

function writeReport() {
  const totals = {
    total: checks.length,
    passed: checks.filter((c) => c.result === 'PASS').length,
    failed: checks.filter((c) => c.result === 'FAIL').length,
    blocked: checks.filter((c) => c.result === 'BLOCKED').length,
  };
  const lines = [
    '# Nexus Live Backend Certification',
    '',
    `Generated: ${new Date().toISOString()}`,
    `Result: ${totals.failed === 0 && totals.blocked === 0 ? 'PASS' : 'FAIL'}`,
    '',
    `Total checks: ${totals.total}`,
    `Passed: ${totals.passed}`,
    `Failed: ${totals.failed}`,
    `Blocked: ${totals.blocked}`,
    '',
    '| Area | Check | Result | Evidence |',
    '| --- | --- | --- | --- |',
    ...checks.map((c) => `| ${c.area} | ${c.check} | ${c.result} | ${(c.evidence || '').replace(/\|/g, '/')} |`),
    '',
    'No passwords, tokens, keys, or raw client data are included.',
  ];
  fs.writeFileSync(REPORT, `${lines.join('\n')}\n`);
  return totals;
}

async function main() {
  if (!supabaseUrl || !anonKey || !serviceKey) {
    record('Environment', 'Supabase URL, anon key, and service role configured', 'BLOCKED');
    writeReport();
    process.exit(1);
  }
  await runAuthAndRls();
  await runStorage();
  await cleanupStorage();
  const totals = writeReport();
  if (totals.failed || totals.blocked) process.exit(1);
}

main().catch((error) => {
  record('Runner', 'uncaught certification error', 'FAIL', error?.message || String(error));
  writeReport();
  process.exit(1);
});
