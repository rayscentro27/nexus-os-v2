import React, { useState, useCallback } from 'react';
import { INTAKE_SECTIONS, INTAKE_CONSENT_LANGUAGE } from '../lib/readinessReviewIntake';

/**
 * Nexus OS v2 — Readiness Review Client Intake UI.
 *
 * Collects intake answers for the $97 Credit & Funding Readiness Review.
 * Uses local mock state — no live persistence, no external sends.
 * All outputs are drafts only.
 */

export function ReadinessReviewIntake({ onComplete, onCancel }) {
  const [answers, setAnswers] = useState({});
  const [currentSection, setCurrentSection] = useState(0);
  const [consentGiven, setConsentGiven] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const section = INTAKE_SECTIONS[currentSection];
  const totalSections = INTAKE_SECTIONS.length;

  const handleFieldChange = useCallback((key, value) => {
    setAnswers(prev => ({ ...prev, [key]: value }));
  }, []);

  const handleNext = () => {
    if (currentSection < totalSections - 1) setCurrentSection(currentSection + 1);
  };

  const handlePrev = () => {
    if (currentSection > 0) setCurrentSection(currentSection - 1);
  };

  const handleSubmit = () => {
    if (!consentGiven) return;
    setSubmitted(true);
    onComplete?.({ answers, consentGiven: true, submittedAt: new Date().toISOString() });
  };

  if (submitted) {
    return (
      <div className="readiness-intake-container">
        <div className="readiness-intake-header">
          <h2>Intake Complete</h2>
          <p className="readiness-intake-badge">Draft — Not Delivered</p>
        </div>
        <div className="readiness-intake-success">
          <p>Thank you. Your responses have been collected locally.</p>
          <p>No data has been sent, stored remotely, or shared with any third party.</p>
          <p>Ray will review your intake and prepare your readiness report.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="readiness-intake-container" data-testid="readiness-intake">
      <div className="readiness-intake-header">
        <h2>$97 Credit & Funding Readiness Review</h2>
        <p className="readiness-intake-badge">Client Intake — Local Draft Mode</p>
        <p className="readiness-intake-disclaimer">This is a readiness review, not legal or financial advice. No credit bureau, bank, or lender APIs are connected.</p>
      </div>

      <div className="readiness-intake-progress">
        <div className="readiness-intake-progress-bar">
          <div style={{ width: `${((currentSection + 1) / totalSections) * 100}%` }} />
        </div>
        <span>{currentSection + 1} of {totalSections}: {section.label}</span>
      </div>

      <div className="readiness-intake-section" data-testid="intake-section">
        <h3>{section.label}</h3>
        <p className="readiness-intake-section-desc">{section.description}</p>
        {section.fields.map(field => (
          <div key={field.key} className="readiness-intake-field">
            <label>
              {field.label}
              {field.required && <span className="required">*</span>}
            </label>
            {field.helpText && <p className="field-help">{field.helpText}</p>}
            {field.type === 'text' && (
              <input
                type="text"
                value={answers[field.key] || ''}
                onChange={e => handleFieldChange(field.key, e.target.value)}
                data-testid={`field-${field.key}`}
              />
            )}
            {field.type === 'number' && (
              <input
                type="number"
                value={answers[field.key] || ''}
                onChange={e => handleFieldChange(field.key, e.target.value)}
                data-testid={`field-${field.key}`}
              />
            )}
            {field.type === 'select' && (
              <select
                value={answers[field.key] || ''}
                onChange={e => handleFieldChange(field.key, e.target.value)}
                data-testid={`field-${field.key}`}
              >
                <option value="">Select...</option>
                {field.options?.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            )}
            {field.type === 'boolean' && (
              <div className="readiness-intake-boolean">
                <label>
                  <input
                    type="checkbox"
                    checked={!!answers[field.key]}
                    onChange={e => handleFieldChange(field.key, e.target.checked)}
                    data-testid={`field-${field.key}`}
                  />
                  {field.label}
                </label>
              </div>
            )}
            {field.type === 'checklist' && (
              <div className="readiness-intake-checklist">
                {field.options?.map(opt => (
                  <label key={opt} className="checklist-item">
                    <input
                      type="checkbox"
                      checked={Array.isArray(answers[field.key]) && answers[field.key].includes(opt)}
                      onChange={e => {
                        const current = Array.isArray(answers[field.key]) ? answers[field.key] : [];
                        handleFieldChange(field.key, e.target.checked ? [...current, opt] : current.filter(x => x !== opt));
                      }}
                    />
                    {opt}
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="readiness-intake-nav">
        <button onClick={handlePrev} disabled={currentSection === 0}>Previous</button>
        {currentSection < totalSections - 1 ? (
          <button onClick={handleNext}>Next</button>
        ) : (
          <div className="readiness-intake-consent">
            <label className="consent-checkbox">
              <input
                type="checkbox"
                checked={consentGiven}
                onChange={e => setConsentGiven(e.target.checked)}
                data-testid="consent-checkbox"
              />
              <span>I have read and agree to the following:</span>
            </label>
            <pre className="consent-text">{INTAKE_CONSENT_LANGUAGE}</pre>
            <button onClick={handleSubmit} disabled={!consentGiven} data-testid="submit-intake">
              Submit Intake
            </button>
          </div>
        )}
      </div>

      {onCancel && (
        <button className="readiness-intake-cancel" onClick={onCancel}>Cancel</button>
      )}
    </div>
  );
}

export default ReadinessReviewIntake;
