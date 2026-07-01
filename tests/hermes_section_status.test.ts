import { describe, it, expect } from 'vitest';
import {
  getSectionStatus,
  getAllSectionStatuses,
  getSectionSummary,
  findSectionsByQuery,
  getResearchEngineStatus,
  getLiveSections,
  getStaticSections,
  getBlockedSections,
  isSectionStatusQuestion,
  buildSectionStatusAnswer,
} from '../src/lib/nexusSectionStatusRegistry';
import { routeModel } from '../src/lib/hermesModelRoutingPolicy';

describe('nexusSectionStatusRegistry', () => {
  describe('getSectionStatus', () => {
    it('returns a section by id', () => {
      const s = getSectionStatus('ray_review');
      expect(s).toBeDefined();
      expect(s!.name).toBe('Ray Review');
      expect(s!.status).toBe('live');
      expect(s!.source).toBe('supabase');
    });

    it('returns undefined for unknown id', () => {
      expect(getSectionStatus('nonexistent')).toBeUndefined();
    });
  });

  describe('getAllSectionStatuses', () => {
    it('returns all 14 sections', () => {
      const all = getAllSectionStatuses();
      expect(all.length).toBe(14);
    });

    it('each section has required fields', () => {
      const all = getAllSectionStatuses();
      for (const s of all) {
        expect(s.id).toBeTruthy();
        expect(s.name).toBeTruthy();
        expect(['live', 'static', 'mismatch', 'blocked', 'unknown']).toContain(s.status);
        expect(['supabase', 'local_static', 'mixed', 'none']).toContain(s.source);
        expect(['verified', 'unproven', 'no_proof']).toContain(s.proofLevel);
        expect(Array.isArray(s.tableNames)).toBe(true);
        expect(typeof s.rowCount).toBe('number');
        expect(typeof s.schedulerInstalled).toBe('boolean');
        expect(typeof s.schedulerRunning).toBe('boolean');
        expect(typeof s.supabaseWrites).toBe('boolean');
        expect(Array.isArray(s.blockers)).toBe(true);
      }
    });
  });

  describe('getSectionSummary', () => {
    it('returns correct counts', () => {
      const summary = getSectionSummary();
      expect(summary.live + summary.static + summary.mismatch + summary.blocked + summary.unknown).toBe(summary.total);
      expect(summary.total).toBe(14);
      expect(summary.live).toBe(6);
      expect(summary.static).toBe(8);
    });
  });

  describe('findSectionsByQuery', () => {
    it('finds section by name', () => {
      const results = findSectionsByQuery('ray review');
      expect(results.length).toBe(1);
      expect(results[0].id).toBe('ray_review');
    });

    it('finds section by id', () => {
      const results = findSectionsByQuery('research_engine');
      expect(results.length).toBe(1);
      expect(results[0].id).toBe('research_engine');
    });

    it('finds multiple matching sections', () => {
      const results = findSectionsByQuery('live supabase');
      expect(results.length).toBeGreaterThan(1);
    });

    it('returns empty for no match', () => {
      const results = findSectionsByQuery('xyznonexistent');
      expect(results.length).toBe(0);
    });
  });

  describe('getResearchEngineStatus', () => {
    it('returns research engine with YouTube details', () => {
      const s = getResearchEngineStatus();
      expect(s.id).toBe('research_engine');
      expect(s.status).toBe('live');
      expect(s.youtubeProofStatus).toBe('not_proven_live');
      expect(s.schedulerInstalled).toBe(true);
      expect(s.schedulerRunning).toBe(false);
      expect(s.supabaseWriteProof).toBe(true);
      expect(s.watchedChannels).toBe(4);
    });
  });

  describe('getLiveSections', () => {
    it('returns only live sections', () => {
      const live = getLiveSections();
      expect(live.length).toBe(6);
      for (const s of live) {
        expect(s.status).toBe('live');
      }
    });
  });

  describe('getStaticSections', () => {
    it('returns only static sections', () => {
      const stat = getStaticSections();
      expect(stat.length).toBe(8);
      for (const s of stat) {
        expect(s.status).toBe('static');
      }
    });
  });

  describe('getBlockedSections', () => {
    it('returns empty (no blocked sections)', () => {
      const blocked = getBlockedSections();
      expect(blocked.length).toBe(0);
    });
  });

  describe('isSectionStatusQuestion', () => {
    it('detects "is X live?"', () => {
      expect(isSectionStatusQuestion('is ray review live?')).toBe(true);
    });

    it('detects "is X working?"', () => {
      expect(isSectionStatusQuestion('is the research engine working?')).toBe(true);
    });

    it('detects "what is the status?"', () => {
      expect(isSectionStatusQuestion('what is the status of nexus?')).toBe(true);
    });

    it('detects "show proof"', () => {
      expect(isSectionStatusQuestion('show proof this is working')).toBe(true);
    });

    it('detects "what sections are live?"', () => {
      expect(isSectionStatusQuestion('what sections are live?')).toBe(true);
    });

    it('detects "what is blocked?"', () => {
      expect(isSectionStatusQuestion('what is blocked?')).toBe(true);
    });

    it('detects "what is scheduled?"', () => {
      expect(isSectionStatusQuestion('what is scheduled?')).toBe(true);
    });

    it('does not detect random questions', () => {
      expect(isSectionStatusQuestion('what is the weather today?')).toBe(false);
      expect(isSectionStatusQuestion('how do I make money?')).toBe(false);
    });
  });

  describe('buildSectionStatusAnswer', () => {
    it('answers "what sections are live?"', () => {
      const answer = buildSectionStatusAnswer('what sections are live?');
      expect(answer).toContain('Live sections');
      expect(answer).toContain('Ray Review');
      expect(answer).toContain('Business Opportunities');
    });

    it('answers "what sections are static?"', () => {
      const answer = buildSectionStatusAnswer('what sections are static?');
      expect(answer).toContain('Static sections');
      expect(answer).toContain('Trading Lab');
    });

    it('answers "what is blocked?"', () => {
      const answer = buildSectionStatusAnswer('what is blocked?');
      expect(answer).toContain('blockers');
    });

    it('answers "what is scheduled?"', () => {
      const answer = buildSectionStatusAnswer('what is scheduled?');
      expect(answer).toContain('Scheduled');
    });

    it('answers "show proof"', () => {
      const answer = buildSectionStatusAnswer('show proof this is working');
      expect(answer).toContain('Verified');
      expect(answer).toContain('Unproven');
    });

    it('answers "what is the status?"', () => {
      const answer = buildSectionStatusAnswer('what is the status?');
      expect(answer).toContain('Nexus OS status');
      expect(answer).toContain('live');
      expect(answer).toContain('static');
    });

    it('answers specific section "is ray review live?"', () => {
      const answer = buildSectionStatusAnswer('is ray review live?');
      expect(answer).toContain('Ray Review');
      expect(answer).toContain('LIVE');
      expect(answer).toContain('task_requests');
    });

    it('answers specific section "is the research engine working?"', () => {
      const answer = buildSectionStatusAnswer('is the research engine working?');
      expect(answer).toContain('Research Engine');
    });

    it('returns fallback for unrecognized query', () => {
      const answer = buildSectionStatusAnswer('something completely different');
      expect(answer).toContain('Nexus OS');
    });
  });
});

describe('hermesModelRoutingPolicy — section status routing', () => {
  it('routes "is ray review live?" to no_model', () => {
    const decision = routeModel('is ray review live?');
    expect(decision.route).toBe('no_model');
  });

  it('routes "what sections are live?" to no_model', () => {
    const decision = routeModel('what sections are live?');
    expect(decision.route).toBe('no_model');
  });

  it('routes "show proof this is working" to no_model', () => {
    const decision = routeModel('show proof this is working');
    expect(decision.route).toBe('no_model');
  });

  it('routes "what is blocked?" to no_model', () => {
    const decision = routeModel('what is blocked?');
    expect(decision.route).toBe('no_model');
  });

  it('routes "what is scheduled?" to no_model', () => {
    const decision = routeModel('what is scheduled?');
    expect(decision.route).toBe('no_model');
  });

  it('routes "is the research engine live?" to no_model', () => {
    const decision = routeModel('is the research engine live?');
    expect(decision.route).toBe('no_model');
  });

  it('routes cost questions to no_model', () => {
    expect(routeModel('what did that model call cost?').route).toBe('no_model');
    expect(routeModel('how can we reduce token cost?').route).toBe('no_model');
    expect(routeModel('was that model call necessary?').route).toBe('no_model');
    expect(routeModel('are you using a live model?').route).toBe('no_model');
    expect(routeModel('what model did you use?').route).toBe('no_model');
  });

  it('still routes strategy to primary_model', () => {
    const decision = routeModel('what strategy should we use for marketing?');
    expect(decision.route).toBe('primary_model');
  });

  it('still routes execution to blocked_or_gated', () => {
    const decision = routeModel('send email to client');
    expect(decision.route).toBe('blocked_or_gated');
  });
});
