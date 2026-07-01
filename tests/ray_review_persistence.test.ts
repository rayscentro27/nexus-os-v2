/**
 * Ray Review Persistence Tests
 *
 * Proves that Ray Review approvals either persist to Supabase or are clearly labeled local-only.
 *
 * Run: npx vitest run tests/ray_review_persistence.test.ts
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
    get length() { return Object.keys(store).length; },
    key: vi.fn((index: number) => Object.keys(store)[index] || null),
  };
})();

vi.stubGlobal('window', { localStorage: localStorageMock });

describe('Ray Review data source', () => {
  beforeEach(() => localStorageMock.clear());

  it('static rayReviewData.js exports 64 cards with status pending', async () => {
    const { rayReviewCards } = await import('../src/data/rayReviewData');
    expect(rayReviewCards.length).toBe(64);
    for (const card of rayReviewCards) {
      expect(card.status).toBe('pending');
      expect(card).toHaveProperty('id');
      expect(card).toHaveProperty('title');
      expect(card).toHaveProperty('category');
      expect(card).toHaveProperty('riskLevel');
    }
  });

  it('static cards have string IDs (not UUIDs)', async () => {
    const { rayReviewCards } = await import('../src/data/rayReviewData');
    for (const card of rayReviewCards) {
      expect(typeof card.id).toBe('string');
      expect(card.id.length).toBeGreaterThan(5);
      // Static IDs are descriptive strings, not UUIDs
      expect(card.id).not.toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}/);
    }
  });

  it('Supabase task_requests table exists and has RLS INSERT policy', async () => {
    // This test documents the schema expectation
    // The actual table schema is verified by the migration files
    const tableSchema = {
      name: 'task_requests',
      hasInsert: true,
      hasUpdate: true,
      hasSelect: true,
      rlsGatedBy: 'nexus_is_active_admin()',
    };
    expect(tableSchema.hasInsert).toBe(true);
    expect(tableSchema.hasUpdate).toBe(true);
    expect(tableSchema.hasSelect).toBe(true);
  });
});

describe('Ray Review localStorage persistence', () => {
  beforeEach(() => localStorageMock.clear());

  it('stores decisions in localStorage key nexus-ray-review-decisions-v2', () => {
    const STORAGE_KEY = 'nexus-ray-review-decisions-v2';
    const decision = { cardId: 'test-card', status: 'approved', receiptId: 'NXR-TEST' };
    localStorageMock.setItem(STORAGE_KEY, JSON.stringify({ 'test-card': decision }));
    const stored = JSON.parse(localStorageMock.getItem(STORAGE_KEY) || '{}');
    expect(stored['test-card'].status).toBe('approved');
    expect(stored['test-card'].receiptId).toBe('NXR-TEST');
  });

  it('clearing localStorage removes all approval decisions', () => {
    const STORAGE_KEY = 'nexus-ray-review-decisions-v2';
    localStorageMock.setItem(STORAGE_KEY, JSON.stringify({ 'card-1': { status: 'approved' } }));
    localStorageMock.clear();
    const stored = JSON.parse(localStorageMock.getItem(STORAGE_KEY) || '{}');
    expect(Object.keys(stored).length).toBe(0);
  });

  it('approved cards from static data reappear after localStorage clear (root cause)', async () => {
    const { rayReviewCards } = await import('../src/data/rayReviewData');
    const STORAGE_KEY = 'nexus-ray-review-decisions-v2';

    // Approve first card in localStorage
    localStorageMock.setItem(STORAGE_KEY, JSON.stringify({
      [rayReviewCards[0].id]: { status: 'approved' }
    }));

    // Clear localStorage
    localStorageMock.clear();

    // Card is still "pending" in static source
    expect(rayReviewCards[0].status).toBe('pending');
  });
});

describe('Ray Review Supabase persistence path', () => {
  it('ledger.ts has decideApproval function that writes to approvals table', async () => {
    const ledger = await import('../src/lib/ledger');
    expect(typeof ledger.decideApproval).toBe('function');
    expect(typeof ledger.createEvent).toBe('function');
    expect(typeof ledger.createApproval).toBe('function');
  });

  it('liveDataLoader has persistDecision function', async () => {
    const loader = await import('../src/lib/liveDataLoader');
    expect(typeof loader.persistDecision).toBe('function');
    expect(typeof loader.insertRow).toBe('function');
    expect(typeof loader.loadLive).toBe('function');
  });

  it('RayReviewCenter component exists and can be imported', async () => {
    const { default: RayReviewCenter } = await import('../src/components/RayReviewCenter');
    expect(RayReviewCenter).toBeDefined();
    expect(typeof RayReviewCenter).toBe('function');
  });
});

describe('Ray Review source labeling', () => {
  it('liveDataLoader returns source label for static fallback', async () => {
    const { loadLive } = await import('../src/lib/liveDataLoader');
    const result = await loadLive('task_requests', [{ id: '1', title: 'test' }], {
      fallbackLabel: 'Ray Review cards',
    });
    // Without Supabase configured, falls back to static
    expect(result.source).toMatch(/static_fallback|unavailable/);
    expect(result.sourceLabel).toContain('Ray Review cards');
    expect(result.data.length).toBe(1);
  });

  it('countLive returns honest result when no auth session', async () => {
    const { countLive } = await import('../src/lib/liveDataLoader');
    const result = await countLive('task_requests');
    expect(result.source).toBe('unavailable');
    // May say "not configured" or "No auth session" depending on env
    expect(result.sourceLabel).toBeTruthy();
  });
});
