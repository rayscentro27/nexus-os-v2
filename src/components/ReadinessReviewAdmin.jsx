import React, { useState, useCallback, useMemo } from 'react';
import { INTAKE_SECTIONS } from '../lib/readinessReviewIntake';
import { SCORE_SECTIONS, READINESS_TIERS, calculateOverallScore, getReadinessTier, scoreSection } from '../lib/readinessReviewScorecard';

/**
 * Nexus OS v2 — Readiness Review Admin Review UI.
 *
 * Admin-facing review screen for the $97 Credit & Funding Readiness Review.
 * Allows Ray to view intake, score manually, add notes, and prepare drafts.
 * All outputs are drafts only — no external sends.
 */

export function ReadinessReviewAdmin({ intakeAnswers = {}, onComplete }) {
  const [adminNotes, setAdminNotes] = useState('');
  const [creditScores, setCreditScores] = useState({});
  const [fundingScores, setFundingScores] = useState({});
  const [blockers, setBlockers] = useState([]);
  const [nextSteps, setNextSteps] = useState([]);
  const [upgradePath, setUpgradePath] = useState('');
  const [specialistLane, setSpecialistLane] = useState('');
  const [activeTab, setActiveTab] = useState('intake');
  const [draftPrepared, setDraftPrepared] = useState(false);

  const handleCreditScoreChange = useCallback((key, value) => {
    setCreditScores(prev => ({ ...prev, [key]: Number(value) || 0 }));
  }, []);

  const handleFundingScoreChange = useCallback((key, value) => {
    setFundingScores(prev => ({ ...prev, [key]: Number(value) || 0 }));
  }, []);

  const allScores = useMemo(() => ({ ...creditScores, ...fundingScores }), [creditScores, fundingScores]);

  const overallScore = useMemo(() => calculateOverallScore(allScores), [allScores]);
  const overallTier = useMemo(() => getReadinessTier(overallScore), [overallScore]);

  const creditSectionScores = useMemo(() => {
    return SCORE_SECTIONS.slice(0, 4).map(s => ({
      ...s,
      score: scoreSection(s, creditScores),
    }));
  }, [creditScores]);

  const fundingSectionScores = useMemo(() => {
    return SCORE_SECTIONS.slice(4).map(s => ({
      ...s,
      score: scoreSection(s, fundingScores),
    }));
  }, [fundingScores]);

  const handleBlockerToggle = (blocker) => {
    setBlockers(prev => prev.includes(blocker) ? prev.filter(b => b !== blocker) : [...prev, blocker]);
  };

  const handleNextStepToggle = (step) => {
    setNextSteps(prev => prev.includes(step) ? prev.filter(s => s !== step) : [...prev, step]);
  };

  const handlePrepareDraft = () => {
    setDraftPrepared(true);
    onComplete?.({
      intakeAnswers,
      creditScores,
      fundingScores,
      overallScore,
      overallTier: overallTier.tier,
      adminNotes,
      blockers,
      nextSteps,
      upgradePath,
      specialistLane,
      preparedAt: new Date().toISOString(),
    });
  };

  const commonBlockers = [
    'No credit report available',
    'Utilization above 30%',
    'Multiple hard inquiries',
    'Active collections',
    'No LLC or corporation',
    'No EIN or DUNS number',
    'No business bank account',
    'No business website or email',
    'Missing formation documents',
    'Insufficient revenue history',
  ];

  const commonNextSteps = [
    'Pull credit reports from all three bureaus',
    'Reduce credit card utilization below 30%',
    'Dispute inaccurate negative items',
    'Establish LLC and obtain EIN',
    'Apply for DUNS number',
    'Open dedicated business bank account',
    'Create professional business website',
    'Build vendor tradeline relationships',
    'Prepare financial documents for funding',
    'Schedule follow-up readiness review',
  ];

  return (
    <div className="readiness-admin-container" data-testid="readiness-admin">
      <div className="readiness-admin-header">
        <h2>Admin Review — $97 Readiness Review</h2>
        <p className="readiness-admin-badge">Draft Mode — No External Actions</p>
      </div>

      <div className="readiness-admin-tabs">
        {['intake', 'scoring', 'notes', 'draft'].map(tab => (
          <button
            key={tab}
            className={activeTab === tab ? 'active' : ''}
            onClick={() => setActiveTab(tab)}
            data-testid={`tab-${tab}`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'intake' && (
        <div className="readiness-admin-intake" data-testid="admin-intake-view">
          <h3>Client Intake Responses</h3>
          {INTAKE_SECTIONS.map(section => (
            <div key={section.id} className="intake-section-review">
              <h4>{section.label}</h4>
              {section.fields.map(field => (
                <div key={field.key} className="intake-field-review">
                  <span className="field-label">{field.label}:</span>
                  <span className="field-value" data-testid={`intake-value-${field.key}`}>
                    {intakeAnswers[field.key] !== undefined
                      ? Array.isArray(intakeAnswers[field.key])
                        ? intakeAnswers[field.key].join(', ')
                        : String(intakeAnswers[field.key])
                      : <em className="missing-value">Not provided</em>
                    }
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'scoring' && (
        <div className="readiness-admin-scoring" data-testid="admin-scoring-view">
          <div className="scoring-overall">
            <h3>Overall Readiness Score</h3>
            <div className="score-display" data-testid="overall-score">
              <span className="score-number">{overallScore}</span>
              <span className="score-tier" data-testid="overall-tier">{overallTier.label}</span>
            </div>
          </div>

          <div className="scoring-sections">
            <div className="scoring-credit">
              <h4>Credit Readiness</h4>
              {creditSectionScores.map(s => (
                <div key={s.id} className="score-section-row">
                  <span>{s.label}</span>
                  <span className="section-score">{s.score}/100</span>
                </div>
              ))}
              {SCORE_SECTIONS.slice(0, 4).flatMap(s => s.factors).map(factor => (
                <div key={factor.key} className="score-factor-input">
                  <label>{factor.label} (max {factor.maxScore})</label>
                  <input
                    type="number"
                    min="0"
                    max={factor.maxScore}
                    value={creditScores[factor.key] || ''}
                    onChange={e => handleCreditScoreChange(factor.key, e.target.value)}
                    data-testid={`credit-score-${factor.key}`}
                  />
                </div>
              ))}
            </div>

            <div className="scoring-funding">
              <h4>Business Funding Readiness</h4>
              {fundingSectionScores.map(s => (
                <div key={s.id} className="score-section-row">
                  <span>{s.label}</span>
                  <span className="section-score">{s.score}/100</span>
                </div>
              ))}
              {SCORE_SECTIONS.slice(4).flatMap(s => s.factors).map(factor => (
                <div key={factor.key} className="score-factor-input">
                  <label>{factor.label} (max {factor.maxScore})</label>
                  <input
                    type="number"
                    min="0"
                    max={factor.maxScore}
                    value={fundingScores[factor.key] || ''}
                    onChange={e => handleFundingScoreChange(factor.key, e.target.value)}
                    data-testid={`funding-score-${factor.key}`}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'notes' && (
        <div className="readiness-admin-notes" data-testid="admin-notes-view">
          <h3>Admin Notes</h3>
          <textarea
            value={adminNotes}
            onChange={e => setAdminNotes(e.target.value)}
            placeholder="Add notes about this client's readiness..."
            rows={6}
            data-testid="admin-notes"
          />

          <h4>Top Blockers</h4>
          <div className="blocker-list" data-testid="blocker-list">
            {commonBlockers.map(blocker => (
              <label key={blocker} className="blocker-item">
                <input
                  type="checkbox"
                  checked={blockers.includes(blocker)}
                  onChange={() => handleBlockerToggle(blocker)}
                />
                {blocker}
              </label>
            ))}
          </div>

          <h4>Recommended Next Steps</h4>
          <div className="next-steps-list" data-testid="next-steps-list">
            {commonNextSteps.map(step => (
              <label key={step} className="next-step-item">
                <input
                  type="checkbox"
                  checked={nextSteps.includes(step)}
                  onChange={() => handleNextStepToggle(step)}
                />
                {step}
              </label>
            ))}
          </div>

          <h4>Upgrade Path</h4>
          <select value={upgradePath} onChange={e => setUpgradePath(e.target.value)} data-testid="upgrade-path">
            <option value="">Select upgrade path...</option>
            <option value="none">No upgrade recommended</option>
            <option value="297_assistant">$297 Credit Assistant Plan</option>
            <option value="monthly_sub">Monthly Readiness Subscription</option>
            <option value="both">Both — Assistant + Monthly</option>
          </select>

          <h4>Specialist Handoff</h4>
          <select value={specialistLane} onChange={e => setSpecialistLane(e.target.value)} data-testid="specialist-lane">
            <option value="">No specialist needed</option>
            <option value="credit">Credit Specialist</option>
            <option value="funding">Funding Specialist</option>
          </select>
        </div>
      )}

      {activeTab === 'draft' && (
        <div className="readiness-admin-draft" data-testid="admin-draft-view">
          <h3>Prepare Drafts</h3>
          <p className="draft-notice">All drafts below are local only. Nothing has been sent, saved remotely, or delivered to the client.</p>

          <div className="draft-actions">
            <button onClick={handlePrepareDraft} data-testid="prepare-draft">
              Prepare Full Report Draft
            </button>
          </div>

          {draftPrepared && (
            <div className="draft-summary" data-testid="draft-summary">
              <h4>Draft Prepared</h4>
              <ul>
                <li>Overall Score: {overallScore} ({overallTier.label})</li>
                <li>Blockers: {blockers.length} identified</li>
                <li>Next Steps: {nextSteps.length} recommended</li>
                <li>Upgrade Path: {upgradePath || 'None'}</li>
                <li>Specialist: {specialistLane || 'None'}</li>
              </ul>
              <p className="draft-status">Status: <strong>Draft — Not delivered</strong></p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ReadinessReviewAdmin;
