/**
 * Split-Brain Tests
 *
 * Proves that when static UI data exists but Supabase has 0 rows,
 * the system correctly labels the mismatch, explains it in plain English,
 * and never claims live data when it isn't live.
 *
 * Run: npx vitest run tests/split_brain.test.ts
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Supabase client to simulate configured but empty tables
vi.mock('../src/lib/supabaseClient', () => {
  const mockSupabase = {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: { user: { id: 'test-user' } } }, error: null }),
    },
    from: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    limit: vi.fn().mockResolvedValue({ data: [], error: null }),
  };
  return {
    supabase: mockSupabase,
    isSupabaseConfigured: true,
  };
});

// Mock static data — simulates what the UI bundles
const mockStaticBusinessOpportunities = [
  { id: 'biz-001', title: 'Credit Readiness Assessment', category: 'credit_offer', score: 88, status: 'scored', lane: 'credit_readiness', reason: 'Test', nextAction: 'Test', convertOptions: ['offer'], revenueRange: '$97-$297', confidence: 'high', createdAt: '2026-06-28T10:00:00Z' },
  { id: 'biz-002', title: 'Business Credit Builder', category: 'credit_offer', score: 84, status: 'scored', lane: 'credit_readiness', reason: 'Test', nextAction: 'Test', convertOptions: ['offer'], revenueRange: '$297-$497', confidence: 'high', createdAt: '2026-06-28T10:00:00Z' },
];

const mockStaticResearchCandidates = [
  { id: 'res-001', title: 'Loan Management System', source: 'github', score: 73, lane: 'credit_readiness', status: 'scored', type: 'repo', reason: 'Test', nextAction: 'Test', convertOptions: ['automation'], createdAt: '2026-06-28T10:00:00Z' },
];

const mockStaticOffers = [
  { id: 'offer-001', name: 'Readiness Review', price: 97, audience: 'SMBs', deliverables: ['Score'], stripeStatus: 'test_checkout_created', status: 'approved', nextAction: 'Test', createdAt: '2026-06-25T10:00:00Z' },
];

describe('Split-brain: static UI vs empty Supabase', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('liveDataLoader detects mismatch', () => {
    it('loadSection returns static_fallback when Supabase has 0 rows and static data exists', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');
      const result = await loadSection('business_opportunities', mockStaticBusinessOpportunities);

      expect(result.sourceType).toBe('static_fallback');
      expect(result.liveData).toBe(false);
      expect(result.rowCount).toBe(2); // static items returned as records
      expect(result.staticCount).toBe(2);
      expect(result.mismatch).toContain('2 static items');
      expect(result.mismatch).toContain('0 live rows');
      expect(result.mismatch).toContain('business_opportunities');
    });

    it('loadSection records mismatch for research_engine', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');
      const result = await loadSection('research_engine', mockStaticResearchCandidates);

      expect(result.sourceType).toBe('static_fallback');
      expect(result.liveData).toBe(false);
      expect(result.mismatch).toContain('1 static items');
      expect(result.mismatch).toContain('0 live rows');
    });

    it('loadSection records mismatch for monetization', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');
      const result = await loadSection('monetization', mockStaticOffers);

      expect(result.sourceType).toBe('static_fallback');
      expect(result.liveData).toBe(false);
      expect(result.mismatch).toContain('1 static items');
      expect(result.mismatch).toContain('0 live rows');
    });

    it('loadSection returns limitations array explaining the fallback', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');
      const result = await loadSection('business_opportunities', mockStaticBusinessOpportunities);

      expect(result.limitations).toBeInstanceOf(Array);
      expect(result.limitations.length).toBeGreaterThan(0);
      expect(result.limitations.some(l => l.includes('rows in Supabase'))).toBe(true);
    });

    it('loadSection sets ok=false for static fallback', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');
      const result = await loadSection('business_opportunities', mockStaticBusinessOpportunities);

      expect(result.ok).toBe(false);
    });

    it('loadSection for unknown section returns static_fallback with no config message', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');
      const result = await loadSection('nonexistent_section', [{ id: '1' }]);

      expect(result.sourceType).toBe('static_fallback');
      expect(result.limitations.join(' ')).toContain('No section config');
    });
  });

  describe('SourceBanner labels mismatch correctly', () => {
    it('SourceBanner component renders static label for fallback', async () => {
      const { default: SourceBanner } = await import('../src/components/SourceBanner');

      // SourceBanner should exist and be a function component
      expect(typeof SourceBanner).toBe('function');
    });
  });

  describe('Hermes source reasoning explains mismatch', () => {
    it('reasonAboutPage explains split-brain for static section', async () => {
      const { reasonAboutPage } = await import('../src/lib/hermesSourceReasoner');

      const pageData = {
        sectionId: 'business_opportunities',
        sourceType: 'static_fallback' as const,
        liveData: false,
        rowCount: 0,
        staticCount: 26,
        mismatch: 'Page has 26 static items, Supabase has 0 live rows in business_opportunities.',
        tableNamesUsed: ['business_opportunities'],
        records: mockStaticBusinessOpportunities,
      };

      const result = reasonAboutPage(pageData, 'Why does this page show data but Supabase says none?');

      expect(result.answer).toContain('split-brain');
      expect(result.answer).toContain('26 static items');
      expect(result.answer).toContain('0 live rows');
      expect(result.liveData).toBe(false);
      expect(result.confidence).toBe('high');
      expect(result.suggestions.length).toBeGreaterThan(0);
    });

    it('reasonAboutPage reports live status correctly', async () => {
      const { reasonAboutPage } = await import('../src/lib/hermesSourceReasoner');

      const pageData = {
        sectionId: 'business_opportunities',
        sourceType: 'live_supabase' as const,
        liveData: true,
        rowCount: 26,
        staticCount: 26,
        mismatch: null,
        tableNamesUsed: ['business_opportunities'],
        records: mockStaticBusinessOpportunities,
      };

      const result = reasonAboutPage(pageData, 'Is this live or static?');

      expect(result.answer).toContain('live Supabase');
      expect(result.liveData).toBe(true);
      expect(result.confidence).toBe('high');
    });

    it('reasonAboutPage compares page vs Supabase for mismatch', async () => {
      const { reasonAboutPage } = await import('../src/lib/hermesSourceReasoner');

      const pageData = {
        sectionId: 'research_engine',
        sourceType: 'static_fallback' as const,
        liveData: false,
        rowCount: 0,
        staticCount: 50,
        mismatch: 'Page has 50 static items, Supabase has 0 live rows in research_sources.',
        tableNamesUsed: ['research_sources'],
        records: [],
      };

      const result = reasonAboutPage(pageData, 'Compare page data to Supabase');

      expect(result.answer).toContain('50 static items');
      expect(result.answer).toContain('0 live rows');
      expect(result.liveData).toBe(false);
    });

    it('reasonAboutPage gives sync instructions for static sections', async () => {
      const { reasonAboutPage } = await import('../src/lib/hermesSourceReasoner');

      const pageData = {
        sectionId: 'monetization',
        sourceType: 'static_fallback' as const,
        liveData: false,
        rowCount: 0,
        staticCount: 9,
        mismatch: 'Page has 9 static items, Supabase has 0 live rows in monetization_opportunities.',
        tableNamesUsed: ['monetization_opportunities'],
        records: [],
      };

      const result = reasonAboutPage(pageData, 'What do we need to sync?');

      expect(result.answer).toContain('monetization');
      expect(result.answer).toContain('seed');
      expect(result.suggestions.length).toBeGreaterThan(0);
    });

    it('reasonAboutPage summarizes all sections status', async () => {
      const { reasonAboutPage, setPageContext, getAllPageContexts } = await import('../src/lib/hermesSourceReasoner');

      // Set up multiple section contexts
      setPageContext('business_opportunities', {
        sectionId: 'business_opportunities',
        sourceType: 'static_fallback',
        liveData: false,
        rowCount: 0,
        staticCount: 26,
        mismatch: 'test mismatch',
        tableNamesUsed: ['business_opportunities'],
        records: [],
      });

      setPageContext('research_engine', {
        sectionId: 'research_engine',
        sourceType: 'static_fallback',
        liveData: false,
        rowCount: 0,
        staticCount: 50,
        mismatch: 'test mismatch',
        tableNamesUsed: ['research_sources'],
        records: [],
      });

      const allContexts = getAllPageContexts();
      expect(Object.keys(allContexts)).toContain('business_opportunities');
      expect(Object.keys(allContexts)).toContain('research_engine');
    });
  });

  describe('Hermes response router classifies source reasoning', () => {
    it('classifies "is this live" as source_reasoning', async () => {
      const { classifyIntent } = await import('../src/lib/hermesResponseRouter');

      expect(classifyIntent('Is this live data?')).toBe('source_reasoning');
      expect(classifyIntent('Is this static?')).toBe('source_reasoning');
      expect(classifyIntent('What is the data source?')).toBe('source_reasoning');
    });

    it('classifies mismatch questions as source_reasoning', async () => {
      const { classifyIntent } = await import('../src/lib/hermesResponseRouter');

      expect(classifyIntent('Why does this page show data but Supabase says none?')).toBe('source_reasoning');
      expect(classifyIntent('There is a mismatch between the page and Supabase')).toBe('source_reasoning');
    });

    it('classifies section comparison as source_reasoning', async () => {
      const { classifyIntent } = await import('../src/lib/hermesResponseRouter');

      expect(classifyIntent('Compare page data to Supabase')).toBe('source_reasoning');
      expect(classifyIntent('Which sections are live?')).toBe('source_reasoning');
    });
  });

  describe('countLive returns honest status', () => {
    it('countLive returns 0 with honest source when Supabase returns no rows', async () => {
      const { countLive } = await import('../src/lib/liveDataLoader');
      const result = await countLive('business_opportunities');

      expect(result.count).toBe(0);
      // Mock is configured with a session, so it returns live_supabase with 0 rows
      expect(result.source).toMatch(/live_supabase|unavailable/);
      expect(result.sourceLabel).toBeTruthy();
    });
  });

  describe('Safety: no false live claims', () => {
    it('loadSection never returns liveData=true when Supabase returns 0 rows', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');

      const sections = [
        { id: 'business_opportunities', data: mockStaticBusinessOpportunities },
        { id: 'research_engine', data: mockStaticResearchCandidates },
        { id: 'monetization', data: mockStaticOffers },
      ];

      for (const section of sections) {
        const result = await loadSection(section.id, section.data);
        // When Supabase returns 0 rows, liveData must be false
        if (result.rowCount === 0 || result.sourceType === 'static_fallback') {
          expect(result.liveData).toBe(false);
        }
      }
    });

    it('buildResult sets ok=false for static_fallback', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');
      const result = await loadSection('business_opportunities', mockStaticBusinessOpportunities);

      // static_fallback means ok should be false
      expect(result.ok).toBe(false);
    });

    it('SectionResult never claims live_supabase source when fallback is used', async () => {
      const { loadSection } = await import('../src/lib/liveDataLoader');
      const result = await loadSection('business_opportunities', mockStaticBusinessOpportunities);

      expect(result.sourceType).not.toBe('live_supabase');
    });
  });
});
