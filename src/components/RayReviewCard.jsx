import React, { useState } from 'react';

export default function RayReviewCard({ card, decision, onDecision, persisting }) {
  const [feedback, setFeedback] = useState('');
  const current = decision ? decision.status : card.status;
  const sourceLabel = card._liveSource === 'live_supabase' ? 'Live Supabase' : 'Static snapshot';
  return (
    <article className="nxos-review-card">
      <div className="nxos-card-head">
        <span className={'nxos-risk risk-' + card.riskLevel}>{card.riskLevel} risk</span>
        <span>{card.category}</span>
        <span className="nxos-source-tag" style={{ fontSize: '0.7em', color: '#888', marginLeft: 'auto' }}>
          {card._liveSource === 'live_supabase' ? '\u{1F534} Live' : '\u26AA Static'}
        </span>
      </div>
      <h3>{card.title}</h3>
      <p>{card.recommendation}</p>
      <dl>
        <div><dt>Status</dt><dd>{current}</dd></div>
        <div><dt>External action</dt><dd>{card.externalAction ? 'Yes \u2014 separately gated' : 'No'}</dd></div>
        <div><dt>Source</dt><dd>{card.source}</dd></div>
        <div><dt>Data source</dt><dd>{sourceLabel}</dd></div>
        <div><dt>Created</dt><dd>{card.createdAt}</dd></div>
      </dl>
      <label className="nxos-field">Feedback<textarea value={feedback} onChange={function(event) { setFeedback(event.target.value); }} placeholder="Optional direction for Hermes or the assigned specialist" /></label>
      <div className="nxos-actions">
        <button type="button" className="primary" disabled={persisting} onClick={function() { onDecision(card, 'approved', feedback); }}>
          {persisting ? 'Saving...' : 'Approve'}
        </button>
        <button type="button" disabled={persisting} onClick={function() { onDecision(card, 'rejected', feedback); }}>
          {persisting ? 'Saving...' : 'Reject'}
        </button>
        <button type="button" disabled={persisting} onClick={function() { onDecision(card, 'held', feedback); }}>
          {persisting ? 'Saving...' : 'Hold'}
        </button>
      </div>
      {decision && (
        <div className="nxos-receipt">
          <strong>{decision.status}</strong> {'\u00B7'} Receipt {decision.receiptId}
          {decision.source && <span> {'\u00B7'} Source: {decision.source}</span>}
          {decision.supabaseTable && <span> {'\u00B7'} Table: {decision.supabaseTable}</span>}
          {decision.supabaseRowId && <span> {'\u00B7'} Row: {String(decision.supabaseRowId).slice(0, 8)}...</span>}
          <br />{decision.nextStep}
          <br />Underlying action executed: no.
          {decision.supabaseError && <span style={{ color: '#c00' }}> {'\u00B7'} Persist error: {String(decision.supabaseError).slice(0, 60)}</span>}
        </div>
      )}
    </article>
  );
}
