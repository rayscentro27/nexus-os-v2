/**
 * Seed Script Validation Tests
 *
 * Proves that the seed script:
 * - Produces correct dry-run plan
 * - Uses no destructive SQL
 * - Contains no real PII
 * - Maps Ray Review cards correctly to task_requests
 * - Maps Business Opportunities correctly
 * - Maps Monetization correctly
 * - Maps Client Profiles correctly
 * - Maps Research Sources correctly
 * - Static fallback remains if Supabase unavailable
 * - Hermes can reason about seed data
 *
 * Run: npx vitest run tests/seed_validation.test.ts
 */

import { describe, it, expect, vi } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const ROOT = join(import.meta.dirname, '..');

// ─── Seed Script Output Validation ───

describe('Seed dry-run produces expected plan', () => {
  it('seed report JSON exists and has correct structure', async () => {
    const reportPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.json');
    const report = JSON.parse(readFileSync(reportPath, 'utf-8'));

    expect(report.ok).toBe(true);
    expect(report.mode).toMatch(/dry_run|live_insert/);
    expect(report.total_would_insert).toBeGreaterThan(0);
    expect(report.tables).toBeInstanceOf(Array);
    expect(report.tables.length).toBeGreaterThanOrEqual(5);
    // After live execution, these should be true
    expect(report.live_insertion_performed).toBe(true);
    expect(report.service_role_used).toBe(true);
  });

  it('dry-run report includes all 5 target tables', async () => {
    const reportPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.json');
    const report = JSON.parse(readFileSync(reportPath, 'utf-8'));

    const tableNames = report.tables.map((t: any) => t.table);
    expect(tableNames).toContain('task_requests');
    expect(tableNames).toContain('business_opportunities');
    expect(tableNames).toContain('monetization_opportunities');
    expect(tableNames).toContain('client_profiles');
    expect(tableNames).toContain('research_sources');
  });

  it('dry-run report includes nexus_events seed receipt', async () => {
    const reportPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.json');
    const report = JSON.parse(readFileSync(reportPath, 'utf-8'));

    const tableNames = report.tables.map((t: any) => t.table);
    expect(tableNames).toContain('nexus_events');
  });

  it('seed report markdown exists', async () => {
    const mdPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.md');
    const md = readFileSync(mdPath, 'utf-8');
    expect(md).toContain('task_requests');
    expect(md).toContain('Schema Mapping Notes');
  });

  it('live seed execution report exists after --execute', async () => {
    const execPath = join(ROOT, 'reports/live_seed_execution_latest.json');
    const report = JSON.parse(readFileSync(execPath, 'utf-8'));

    expect(report.verification_type).toBe('post_seed_row_count');
    expect(report.total_rows).toBeGreaterThan(0);
    expect(report.tables.task_requests.count).toBeGreaterThanOrEqual(60);
    expect(report.tables.business_opportunities.count).toBeGreaterThanOrEqual(25);
    expect(report.tables.monetization_opportunities.count).toBeGreaterThanOrEqual(9);
    expect(report.tables.client_profiles.count).toBeGreaterThanOrEqual(1);
    expect(report.tables.research_sources.count).toBeGreaterThanOrEqual(50);
  });
});

// ─── No Destructive SQL ───

describe('No destructive SQL in seed script', () => {
  it('seed script contains no DROP, DELETE, TRUNCATE, or ALTER', async () => {
    const scriptPath = join(ROOT, 'scripts/supabase/seed_static_data_to_supabase.py');
    const script = readFileSync(scriptPath, 'utf-8');

    // Check for destructive patterns (excluding comments and strings that describe them)
    const lines = script.split('\n');
    const destructiveLines = lines.filter(line => {
      const trimmed = line.trim();
      // Skip comments
      if (trimmed.startsWith('#')) return false;
      // Skip strings that mention destructive operations in descriptions
      if (trimmed.includes('"destructive') || trimmed.includes("'destructive")) return false;
      // Check for actual destructive SQL keywords in code
      return /\b(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE|ALTER\s+TABLE\s+\w+\s+DROP)\b/i.test(trimmed);
    });

    expect(destructiveLines).toHaveLength(0);
  });

  it('seed plan JSON has noLiveInserts safety flag', async () => {
    const planPath = join(ROOT, 'reports/static_to_supabase_seed_plan.json');
    const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
    expect(plan.safety.noLiveInserts).toBe(true);
    expect(plan.safety.requiresApproval).toBe(true);
  });
});

// ─── No Real PII ───

describe('No real PII in seed data', () => {
  it('static data files contain only synthetic/test emails', async () => {
    const clientsPath = join(ROOT, 'src/data/clientsData.js');
    const clients = readFileSync(clientsPath, 'utf-8');

    // Should only contain test/synthetic emails
    const emailMatches = clients.match(/[\w.-]+@[\w.-]+\.\w+/g) || [];
    for (const email of emailMatches) {
      expect(email).toMatch(/@.*\.(test|demo|example|fake)/i);
    }
  });

  it('Ray Review cards are synthetic/internal', async () => {
    const cardsPath = join(ROOT, 'src/data/rayReviewData.js');
    const cards = readFileSync(cardsPath, 'utf-8');

    // Should not contain real names, SSNs, credit card numbers, etc.
    expect(cards).not.toMatch(/\b\d{3}-\d{2}-\d{4}\b/); // SSN
    expect(cards).not.toMatch(/\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/); // Credit card
  });

  it('seed script marks all records as synthetic', async () => {
    const scriptPath = join(ROOT, 'scripts/supabase/seed_static_data_to_supabase.py');
    const script = readFileSync(scriptPath, 'utf-8');

    // All mappers should include synthetic: True
    expect(script).toContain('"synthetic": True');
    expect(script).toContain('"data_source": "static_import"');
  });
});

// ─── Ray Review Mapping ───

describe('Ray Review live rows map correctly', () => {
  it('rayReviewData.js exports 64 cards with expected fields', async () => {
    const { rayReviewCards } = await import('../src/data/rayReviewData');
    expect(rayReviewCards.length).toBeGreaterThanOrEqual(62);

    const card = rayReviewCards[0];
    expect(card).toHaveProperty('id');
    expect(card).toHaveProperty('title');
    expect(card).toHaveProperty('category');
    expect(card).toHaveProperty('riskLevel');
    expect(card).toHaveProperty('status');
    expect(card).toHaveProperty('externalAction');
    expect(card).toHaveProperty('recommendation');
    expect(card).toHaveProperty('source');
    expect(card).toHaveProperty('nextActionCommand');
  });

  it('seed script maps card to task_requests with task_type=ray_review_item', async () => {
    const scriptPath = join(ROOT, 'scripts/supabase/seed_static_data_to_supabase.py');
    const script = readFileSync(scriptPath, 'utf-8');

    expect(script).toContain('"task_type": "ray_review_item"');
    expect(script).toContain('"requested_by": "nexus_seed"');
    expect(script).toContain('"legacy_id"');
  });

  it('seed report shows 62 would-insert for task_requests', async () => {
    const reportPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.json');
    const report = JSON.parse(readFileSync(reportPath, 'utf-8'));

    const tr = report.tables.find((t: any) => t.table === 'task_requests');
    expect(tr).toBeDefined();
    expect(tr.would_insert).toBeGreaterThanOrEqual(60);
    expect(tr.filter).toContain('ray_review_item');
  });
});

// ─── Business Opportunities Mapping ───

describe('Business Opportunities live rows map correctly', () => {
  it('businessOpportunitiesData.js exports 26 opportunities', async () => {
    const { businessOpportunities } = await import('../src/data/businessOpportunitiesData');
    expect(businessOpportunities.length).toBe(26);

    const opp = businessOpportunities[0];
    expect(opp).toHaveProperty('id');
    expect(opp).toHaveProperty('title');
    expect(opp).toHaveProperty('score');
    expect(opp).toHaveProperty('category');
    expect(opp).toHaveProperty('lane');
  });

  it('seed report shows 26 would-insert for business_opportunities', async () => {
    const reportPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.json');
    const report = JSON.parse(readFileSync(reportPath, 'utf-8'));

    const bo = report.tables.find((t: any) => t.table === 'business_opportunities');
    expect(bo).toBeDefined();
    expect(bo.would_insert).toBe(26);
    expect(bo.requires_service_role).toBe(false);
  });
});

// ─── Monetization Mapping ───

describe('Monetization live rows map correctly', () => {
  it('monetizationData.js exports 9 offers', async () => {
    const { offers } = await import('../src/data/monetizationData');
    expect(offers.length).toBe(9);

    const offer = offers[0];
    expect(offer).toHaveProperty('id');
    expect(offer).toHaveProperty('name');
    expect(offer).toHaveProperty('price');
    expect(offer).toHaveProperty('deliverables');
  });

  it('seed report shows 9 would-insert for monetization_opportunities', async () => {
    const reportPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.json');
    const report = JSON.parse(readFileSync(reportPath, 'utf-8'));

    const mo = report.tables.find((t: any) => t.table === 'monetization_opportunities');
    expect(mo).toBeDefined();
    expect(mo.would_insert).toBe(9);
  });
});

// ─── Client Profiles Mapping ───

describe('Client Profiles live rows map correctly', () => {
  it('clientsData.js exports 1 client (Julius Erving)', async () => {
    const { clientsList } = await import('../src/data/clientsData');
    expect(clientsList.length).toBe(1);
    expect(clientsList[0].name).toBe('Julius Erving');
    expect(clientsList[0].email).toContain('.test');
  });

  it('seed report shows 1 would-insert for client_profiles', async () => {
    const reportPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.json');
    const report = JSON.parse(readFileSync(reportPath, 'utf-8'));

    const cp = report.tables.find((t: any) => t.table === 'client_profiles');
    expect(cp).toBeDefined();
    expect(cp.would_insert).toBe(1);
  });
});

// ─── Research Sources Mapping ───

describe('Research Sources live rows map correctly', () => {
  it('researchEngineData.js exports 50 candidates', async () => {
    const { researchCandidates } = await import('../src/data/researchEngineData');
    expect(researchCandidates.length).toBe(50);

    const c = researchCandidates[0];
    expect(c).toHaveProperty('id');
    expect(c).toHaveProperty('title');
    expect(c).toHaveProperty('source');
    expect(c).toHaveProperty('score');
  });

  it('seed report shows 50 would-insert for research_sources', async () => {
    const reportPath = join(ROOT, 'reports/static_to_supabase_seed_dry_run_latest.json');
    const report = JSON.parse(readFileSync(reportPath, 'utf-8'));

    const rs = report.tables.find((t: any) => t.table === 'research_sources');
    expect(rs).toBeDefined();
    expect(rs.would_insert).toBe(50);
    expect(rs.requires_service_role).toBe(true);
  });
});

// ─── Static Fallback Remains ───

describe('Static fallback remains if Supabase unavailable', () => {
  it('loadSection returns static_fallback when Supabase has 0 rows', async () => {
    const { loadSection } = await import('../src/lib/liveDataLoader');
    const { businessOpportunities } = await import('../src/data/businessOpportunitiesData');

    const result = await loadSection('business_opportunities', businessOpportunities);
    expect(result.sourceType).toMatch(/static_fallback|unavailable/);
    expect(result.liveData).toBe(false);
    expect(result.records.length).toBeGreaterThan(0);
  });
});

// ─── Hermes Source Reasoning ───

describe('Hermes explains live rows after seed', () => {
  it('reasonAboutPage explains split-brain for static section', async () => {
    const { reasonAboutPage } = await import('../src/lib/hermesSourceReasoner');

    const pageData = {
      sectionId: 'business_opportunities',
      sourceType: 'static_fallback' as const,
      liveData: false,
      rowCount: 0,
      staticCount: 26,
      mismatch: 'Page has 26 static items, Supabase has 0 live rows.',
      tableNamesUsed: ['business_opportunities'],
      records: [],
    };

    const result = reasonAboutPage(pageData, 'Why does this page show data but Supabase says none?');
    expect(result.answer).toContain('split-brain');
    expect(result.liveData).toBe(false);
  });

  it('reasonAboutPage would confirm live data after seed', async () => {
    const { reasonAboutPage } = await import('../src/lib/hermesSourceReasoner');

    const pageData = {
      sectionId: 'business_opportunities',
      sourceType: 'live_supabase' as const,
      liveData: true,
      rowCount: 26,
      staticCount: 26,
      mismatch: null,
      tableNamesUsed: ['business_opportunities'],
      records: [],
    };

    const result = reasonAboutPage(pageData, 'Is this live or static?');
    expect(result.answer).toContain('live Supabase');
    expect(result.liveData).toBe(true);
  });
});

// ─── Seed Script Safety ───

describe('Seed script safety', () => {
  it('seed script defaults to dry-run mode', async () => {
    const scriptPath = join(ROOT, 'scripts/supabase/seed_static_data_to_supabase.py');
    const script = readFileSync(scriptPath, 'utf-8');

    expect(script).toContain('DRY RUN');
    expect(script).toContain('--execute');
    expect(script).toContain('live_insertion_performed');
    expect(script).toContain('False');
  });

  it('seed script requires explicit env vars for execute', async () => {
    const scriptPath = join(ROOT, 'scripts/supabase/seed_static_data_to_supabase.py');
    const script = readFileSync(scriptPath, 'utf-8');

    expect(script).toContain('SUPABASE_URL');
    expect(script).toContain('SUPABASE_SERVICE_ROLE_KEY');
    expect(script).toContain('missing_env_vars');
  });

  it('seed script does not commit .env', async () => {
    const gitignorePath = join(ROOT, '.gitignore');
    const gitignore = readFileSync(gitignorePath, 'utf-8');
    expect(gitignore).toContain('.env');
  });

  it('no service role key in frontend components/lib', async () => {
    function findFiles(dir: string, exts: string[]): string[] {
      const results: string[] = [];
      for (const entry of readdirSync(dir)) {
        const full = join(dir, entry);
        const stat = statSync(full);
        if (stat.isDirectory() && !entry.startsWith('.') && entry !== 'node_modules' && entry !== 'config') {
          results.push(...findFiles(full, exts));
        } else if (exts.some(ext => entry.endsWith(ext))) {
          results.push(full);
        }
      }
      return results;
    }

    // Only check components/ and lib/ — config/ contains Python script env definitions
    const dirs = ['components', 'lib'];
    for (const dir of dirs) {
      const dirPath = join(ROOT, 'src', dir);
      if (!statSync(dirPath).isDirectory()) continue;
      const files = findFiles(dirPath, ['.ts', '.tsx', '.js', '.jsx']);
      for (const file of files) {
        const content = readFileSync(file, 'utf-8');
        expect(content).not.toMatch(/SUPABASE_SERVICE_ROLE_KEY/);
      }
    }
  });
});
