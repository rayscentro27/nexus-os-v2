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
        expect(['live', 'static', 'mismatch', 'blocked', 'unknown', 'report_snapshot']).toContain(s.status);
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
      expect(summary.live + summary.static + summary.mismatch + summary.blocked + summary.unknown + summary.report_snapshot).toBe(summary.total);
      expect(summary.total).toBe(14);
      expect(summary.live).toBe(6);
      expect(summary.report_snapshot).toBe(4);
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
      expect(stat.length).toBe(4);
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

  it('routes process status questions to no_model', () => {
    expect(routeModel('what processes are active?').route).toBe('no_model');
    expect(routeModel('what processes are available?').route).toBe('no_model');
    expect(routeModel('what tools do we have?').route).toBe('no_model');
    expect(routeModel('what reports do we have?').route).toBe('no_model');
    expect(routeModel('what settings are missing?').route).toBe('no_model');
    expect(routeModel('what automations are running?').route).toBe('no_model');
    expect(routeModel('what schedulers are loaded?').route).toBe('no_model');
    expect(routeModel('what is broken?').route).toBe('no_model');
    expect(routeModel('what needs approval?').route).toBe('no_model');
  });

  it('routes YouTube/trading/credit questions to no_model', () => {
    expect(routeModel('is youtube research running?').route).toBe('no_model');
    expect(routeModel('is trading lab running?').route).toBe('no_model');
    expect(routeModel('is credit and funding live?').route).toBe('no_model');
    expect(routeModel('can you place a trade?').route).toBe('blocked_or_gated');
    expect(routeModel('can you publish this post?').route).toBe('blocked_or_gated');
  });

  it('routes "what should i work on next" to no_model', () => {
    expect(routeModel('what should i work on next?').route).toBe('no_model');
  });
});

describe('Phase 2 section status answers', () => {
  it('answers "what processes are active?"', () => {
    const answer = buildSectionStatusAnswer('what processes are active?');
    expect(answer).toContain('Active');
  });

  it('answers "what tools do we have?"', () => {
    const answer = buildSectionStatusAnswer('what tools do we have?');
    expect(answer).toContain('CLI');
  });

  it('answers "what reports do we have?"', () => {
    const answer = buildSectionStatusAnswer('what reports do we have?');
    expect(answer).toContain('Reports');
  });

  it('answers "what settings are missing?"', () => {
    const answer = buildSectionStatusAnswer('what settings are missing?');
    expect(answer).toContain('Settings');
  });

  it('answers "what is broken?"', () => {
    const answer = buildSectionStatusAnswer('what is broken?');
    expect(answer).toContain('Blocked');
  });

  it('answers "what needs approval?"', () => {
    const answer = buildSectionStatusAnswer('what needs approval?');
    expect(answer).toContain('Approval');
  });

  it('no fake live claims — credit_funding is static', () => {
    const s = getSectionStatus('credit_funding');
    expect(s!.status).not.toBe('live');
    expect(s!.proofLevel).toBe('no_proof');
  });

  it('no fake live claims — trading_lab is static', () => {
    const s = getSectionStatus('trading_lab');
    expect(s!.status).not.toBe('live');
  });

  it('no fake live claims — youtube not proven', () => {
    const s = getResearchEngineStatus();
    expect(s.youtubeProofStatus).toBe('not_proven_live');
  });

  it('system_health is report_snapshot not live', () => {
    const s = getSectionStatus('system_health');
    expect(s!.status).toBe('report_snapshot');
  });

  it('automation is report_snapshot not live', () => {
    const s = getSectionStatus('automation');
    expect(s!.status).toBe('report_snapshot');
  });
});

describe('YouTube-specific status answers', () => {
  it('YouTube question does not return generic matching sections', () => {
    const answer = buildSectionStatusAnswer('is youtube research running?');
    expect(answer).toContain('NOT PROVEN LIVE');
    expect(answer).not.toMatch(/^Matching sections:/);
  });

  it('YouTube answer says not_proven_live unless process/log/write proof exists', () => {
    const answer = buildSectionStatusAnswer('is youtube research running and writing to Supabase?');
    expect(answer).toContain('NOT PROVEN LIVE');
    expect(answer).toContain('no active PID proof');
    expect(answer).toContain('Next safe action');
  });

  it('YouTube answer includes scheduler proof details', () => {
    const answer = buildSectionStatusAnswer('are transcripts being fetched?');
    expect(answer).toContain('Scheduler installed');
    expect(answer).toContain('Scheduler loaded');
    expect(answer).toContain('Process active');
    expect(answer).toContain('Last output');
  });

  it('YouTube routes to no_model', () => {
    expect(routeModel('is youtube research running?').route).toBe('no_model');
    expect(routeModel('are transcripts being fetched?').route).toBe('no_model');
    expect(routeModel('is the YouTube scheduler active?').route).toBe('no_model');
    expect(routeModel('what is the YouTube proof?').route).toBe('no_model');
  });

  it('YouTube is detected as section status question', () => {
    expect(isSectionStatusQuestion('is youtube research running?')).toBe(true);
    expect(isSectionStatusQuestion('are transcripts being fetched?')).toBe(true);
  });
});

describe('Trading safety answers', () => {
  it('trade execution request is blocked first', () => {
    const answer = buildSectionStatusAnswer('can you place a trade?');
    expect(answer).toMatch(/^No, I cannot place trades/);
    expect(answer).toContain('Live/funded trading is blocked');
    expect(answer).toContain('paper/demo only');
  });

  it('trading status separates process active from live trading', () => {
    const answer = buildSectionStatusAnswer('is trading lab running?');
    expect(answer).toContain('Trading process proof');
    expect(answer).toContain('Trading UI/workflow source');
    expect(answer).toContain('Trading mode');
    expect(answer).toContain('Live/funded trading');
    expect(answer).toContain('PAPER/DEMO ONLY');
    expect(answer).toContain('BLOCKED');
  });

  it('trading execution is blocked_or_gated in routing', () => {
    expect(routeModel('place a trade').route).toBe('blocked_or_gated');
    expect(routeModel('buy EUR/USD').route).toBe('blocked_or_gated');
    expect(routeModel('turn on live trading').route).toBe('blocked_or_gated');
    expect(routeModel('connect funded account').route).toBe('blocked_or_gated');
  });

  it('trading STATUS questions route to no_model', () => {
    expect(routeModel('is trading lab running?').route).toBe('no_model');
    expect(routeModel('is trading active?').route).toBe('no_model');
    expect(routeModel('is live trading enabled?').route).toBe('no_model');
  });

  it('trading status answer includes process proof', () => {
    const answer = buildSectionStatusAnswer('is trading active?');
    expect(answer).toContain('pid-588');
    expect(answer).toContain('DEMO');
    expect(answer).toContain('PAPER');
  });
});

describe('Improved process answers', () => {
  it('process answer includes counts and proof categories', () => {
    const answer = buildSectionStatusAnswer('what processes are active?');
    expect(answer).toContain('Active process (PID proof)');
    expect(answer).toContain('Recent output');
    expect(answer).toContain('Loaded only');
    expect(answer).toContain('Proof source');
    expect(answer).toContain('Next safe action');
  });

  it('process answer shows top examples', () => {
    const answer = buildSectionStatusAnswer('what processes are active?');
    expect(answer).toContain('hermes_agent');
    expect(answer).toContain('tradingview_router');
  });
});

describe('Improved tools/CLI answers', () => {
  it('tools answer includes safe/approval/blocked command categories', () => {
    const answer = buildSectionStatusAnswer('what tools do we have?');
    expect(answer).toContain('Safe read-only commands');
    expect(answer).toContain('Approval-required commands');
    expect(answer).toContain('Blocked commands');
  });

  it('tools answer includes tool count and installed list', () => {
    const answer = buildSectionStatusAnswer('what tools do we have?');
    expect(answer).toContain('11 tools inventoried');
    expect(answer).toContain('git');
    expect(answer).toContain('node');
  });

  it('tools answer includes frontend warning', () => {
    const answer = buildSectionStatusAnswer('what tools do we have?');
    expect(answer).toContain('frontend cannot execute shell commands');
  });

  it('tools answer includes proof level', () => {
    const answer = buildSectionStatusAnswer('what tools do we have?');
    expect(answer).toContain('Proof level');
  });
});

describe('Improved report answers', () => {
  it('reports answer includes count, categories, and proof source', () => {
    const answer = buildSectionStatusAnswer('what reports do we have?');
    expect(answer).toContain('62 reports');
    expect(answer).toContain('Categories');
    expect(answer).toContain('Most recent reports');
    expect(answer).toContain('Proof source');
    expect(answer).toContain('Next action');
  });

  it('reports answer includes category details', () => {
    const answer = buildSectionStatusAnswer('what reports do we have?');
    expect(answer).toContain('operations_status');
    expect(answer).toContain('hermes_ai');
    expect(answer).toContain('supabase_data');
  });
});

describe('Improved settings answers', () => {
  it('settings answer includes configured/missing groups', () => {
    const answer = buildSectionStatusAnswer('what settings are missing?');
    expect(answer).toContain('Configured');
    expect(answer).toContain('Missing');
    expect(answer).toContain('supabase');
    expect(answer).toContain('hermes_chat');
  });

  it('settings answer includes redaction note', () => {
    const answer = buildSectionStatusAnswer('what settings are missing?');
    expect(answer).toContain('Values are never exposed');
  });

  it('settings answer includes proof level and next action', () => {
    const answer = buildSectionStatusAnswer('what settings are missing?');
    expect(answer).toContain('safe_config_presence');
    expect(answer).toContain('Next safe action');
  });
});

describe('Improved broken/priorities answer', () => {
  it('broken answer groups by priority', () => {
    const answer = buildSectionStatusAnswer('what is broken?');
    expect(answer).toContain('Priority 1');
    expect(answer).toContain('Priority 2');
    expect(answer).toContain('Priority 3');
  });

  it('broken answer includes proof gap and next action for each', () => {
    const answer = buildSectionStatusAnswer('what is broken?');
    expect(answer).toContain('Proof gap');
    expect(answer).toContain('Next safe action');
    expect(answer).toContain('Credit & Funding');
    expect(answer).toContain('YouTube research');
    expect(answer).toContain('Reports');
  });
});

describe('Badge and status label', () => {
  it('header badge no longer says Local Advisor when model-ready', () => {
    // The badge is computed dynamically in HermesChatPanel.jsx
    // We verify the routing policy still routes status questions to no_model
    expect(routeModel('what is the status?').route).toBe('no_model');
  });

  it('all status/cost/process questions remain no_model', () => {
    expect(routeModel('is ray review live?').route).toBe('no_model');
    expect(routeModel('what processes are active?').route).toBe('no_model');
    expect(routeModel('what tools do we have?').route).toBe('no_model');
    expect(routeModel('what reports do we have?').route).toBe('no_model');
    expect(routeModel('what settings are missing?').route).toBe('no_model');
    expect(routeModel('what is broken?').route).toBe('no_model');
    expect(routeModel('is youtube research running?').route).toBe('no_model');
    expect(routeModel('what did that model call cost?').route).toBe('no_model');
    expect(routeModel('what model did you use?').route).toBe('no_model');
  });
});
