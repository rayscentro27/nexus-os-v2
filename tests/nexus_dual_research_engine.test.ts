import { describe, it, expect } from 'vitest';
import { existsSync, readdirSync } from 'fs';
import { join } from 'path';

const ROOT = join(import.meta.dirname, '..');
const NEXUS_RESEARCH_INBOX = join(ROOT, 'nexus_research', 'research_inbox');
const HERMES_ALPHA_INBOX = join(ROOT, 'hermes_alpha', 'research_inbox');
const NEXUS_RESEARCH_REPORTS = join(ROOT, 'reports', 'nexus_research');
const HERMES_ALPHA_REPORTS = join(ROOT, 'reports', 'hermes_alpha');

const NEXUS_INBOX_CATEGORIES = [
  'credit_repair',
  'credit_utilization',
  'business_setup',
  'business_funding',
  'grants',
  'lenders',
  'affiliates',
  'compliance',
  'client_education',
  'manual_notes',
];

const ALPHA_INBOX_CATEGORIES = [
  'manual_notes',
  'marketing',
  'monetization',
  'notebooklm',
  'tools',
  'trading',
  'transcripts',
  'youtube',
];

describe('Dual Research Engine Separation', () => {
  it('Hermes Alpha and Nexus Research are separate directory trees', () => {
    const alphaExists = existsSync(HERMES_ALPHA_INBOX);
    const nexusExists = existsSync(NEXUS_RESEARCH_INBOX);
    expect(alphaExists).toBe(true);
    expect(nexusExists).toBe(true);
    expect(HERMES_ALPHA_INBOX).not.toBe(NEXUS_RESEARCH_INBOX);
  });

  it('Nexus Research inbox has all 10 categories', () => {
    for (const cat of NEXUS_INBOX_CATEGORIES) {
      const dir = join(NEXUS_RESEARCH_INBOX, cat);
      expect(existsSync(dir)).toBe(true);
    }
  });

  it('Hermes Alpha inbox has all 8 categories', () => {
    for (const cat of ALPHA_INBOX_CATEGORIES) {
      const dir = join(HERMES_ALPHA_INBOX, cat);
      expect(existsSync(dir)).toBe(true);
    }
  });

  it('Nexus and Alpha inbox categories do not overlap except manual_notes', () => {
    const overlap = NEXUS_INBOX_CATEGORIES.filter(c => ALPHA_INBOX_CATEGORIES.includes(c));
    // manual_notes is a legitimate shared category — both engines need manual operator notes
    expect(overlap).toEqual(['manual_notes']);
  });
});

describe('Alpha No-Supabase Guard', () => {
  it('Alpha research inbox README does not connect to Supabase', () => {
    const alphaReadme = join(HERMES_ALPHA_INBOX, 'README.md');
    if (existsSync(alphaReadme)) {
      const content = require('fs').readFileSync(alphaReadme, 'utf-8').toLowerCase();
      // The README may mention "supabase" as a prohibition ("do not add supabase exports")
      // but should not say to connect to or use Supabase
      expect(content).not.toContain('connect to supabase');
      expect(content).not.toContain('use supabase');
      expect(content).not.toContain('supabase connection');
    }
  });

  it('Alpha reports directory does not contain Nexus-specific reports', () => {
    if (existsSync(HERMES_ALPHA_REPORTS)) {
      const files = readdirSync(HERMES_ALPHA_REPORTS);
      const nexusFiles = files.filter(f => f.startsWith('nexus_'));
      expect(nexusFiles).toEqual([]);
    }
  });
});

describe('Nexus Research Inbox Integrity', () => {
  it('Each Nexus inbox category has a README.md', () => {
    for (const cat of NEXUS_INBOX_CATEGORIES) {
      const readme = join(NEXUS_RESEARCH_INBOX, cat, 'README.md');
      expect(existsSync(readme)).toBe(true);
    }
  });

  it('Nexus inbox README files contain required safety warnings', () => {
    const requiredWarnings = [
      'no secrets',
      'ray review',
    ];

    for (const cat of NEXUS_INBOX_CATEGORIES) {
      const readme = join(NEXUS_RESEARCH_INBOX, cat, 'README.md');
      if (existsSync(readme)) {
        const content = require('fs').readFileSync(readme, 'utf-8').toLowerCase();
        for (const warning of requiredWarnings) {
          expect(content).toContain(warning);
        }
      }
    }
  });

  it('Nexus inbox README files prohibit fake artifacts', () => {
    for (const cat of NEXUS_INBOX_CATEGORIES) {
      const readme = join(NEXUS_RESEARCH_INBOX, cat, 'README.md');
      if (existsSync(readme)) {
        const content = require('fs').readFileSync(readme, 'utf-8').toLowerCase();
        // READMEs should indicate the inbox is intentionally empty
        const hasEmptyIndicator = content.includes('empty by design') || content.includes('no artifacts collected');
        expect(hasEmptyIndicator).toBe(true);
      }
    }
  });

  it('Nexus inbox README files do not create fake artifacts', () => {
    for (const cat of NEXUS_INBOX_CATEGORIES) {
      const catDir = join(NEXUS_RESEARCH_INBOX, cat);
      if (existsSync(catDir)) {
        const files = readdirSync(catDir).filter(f => f !== 'README.md');
        expect(files).toEqual([]);
      }
    }
  });

  it('Empty Nexus Research inbox is valid', () => {
    for (const cat of NEXUS_INBOX_CATEGORIES) {
      const catDir = join(NEXUS_RESEARCH_INBOX, cat);
      if (existsSync(catDir)) {
        const files = readdirSync(catDir).filter(f => f !== 'README.md');
        expect(files.length).toBe(0);
      }
    }
  });
});

describe('Credit/Funding Research Artifact Classification', () => {
  it('Credit repair research is classified separately from Alpha marketing research', () => {
    const nexusCreditDir = join(NEXUS_RESEARCH_INBOX, 'credit_repair');
    const alphaMktDir = join(HERMES_ALPHA_INBOX, 'marketing');
    expect(existsSync(nexusCreditDir)).toBe(true);
    expect(existsSync(alphaMktDir)).toBe(true);
    expect(nexusCreditDir).not.toBe(alphaMktDir);
  });

  it('Business funding research is classified separately from Alpha trading research', () => {
    const nexusFundingDir = join(NEXUS_RESEARCH_INBOX, 'business_funding');
    const alphaTradingDir = join(HERMES_ALPHA_INBOX, 'trading');
    expect(existsSync(nexusFundingDir)).toBe(true);
    expect(existsSync(alphaTradingDir)).toBe(true);
    expect(nexusFundingDir).not.toBe(alphaTradingDir);
  });

  it('Affiliate research is separate between Nexus and Alpha', () => {
    const nexusAffDir = join(NEXUS_RESEARCH_INBOX, 'affiliates');
    const alphaMonoDir = join(HERMES_ALPHA_INBOX, 'monetization');
    expect(existsSync(nexusAffDir)).toBe(true);
    expect(existsSync(alphaMonoDir)).toBe(true);
    expect(nexusAffDir).not.toBe(alphaMonoDir);
  });
});

describe('Approval Gate Requirements', () => {
  it('Client-facing output requires approval', () => {
    const approvalPolicy = join(NEXUS_RESEARCH_REPORTS, 'nexus_research_approval_gate_policy.md');
    expect(existsSync(approvalPolicy)).toBe(true);
    if (existsSync(approvalPolicy)) {
      const content = require('fs').readFileSync(approvalPolicy, 'utf-8');
      expect(content.toLowerCase()).toContain('ray review');
    }
  });

  it('Affiliate recommendations require approval', () => {
    const approvalPolicy = join(NEXUS_RESEARCH_REPORTS, 'nexus_research_approval_gate_policy.md');
    if (existsSync(approvalPolicy)) {
      const content = require('fs').readFileSync(approvalPolicy, 'utf-8').toLowerCase();
      expect(content).toContain('affiliate');
      expect(content).toContain('ray review');
    }
  });

  it('Funding recommendations cannot guarantee approval', () => {
    const approvalPolicy = join(NEXUS_RESEARCH_REPORTS, 'nexus_research_approval_gate_policy.md');
    if (existsSync(approvalPolicy)) {
      const content = require('fs').readFileSync(approvalPolicy, 'utf-8').toLowerCase();
      expect(content).toContain('guarantee');
    }
  });

  it('No send/publish/charge/trade actions are added', () => {
    const approvalPolicy = join(NEXUS_RESEARCH_REPORTS, 'nexus_research_approval_gate_policy.md');
    if (existsSync(approvalPolicy)) {
      const content = require('fs').readFileSync(approvalPolicy, 'utf-8').toLowerCase();
      expect(content).toContain('always blocked');
      expect(content).toContain('dispute sending');
      expect(content).toContain('lender applications');
      expect(content).toContain('payment collection');
    }
  });
});
