import React, { useState } from 'react';

export default function RayReviewCard({ card, decision, onDecision }) {
  const [feedback, setFeedback] = useState('');
  const current = decision?.status || card.status;
  return (
    <article className="nxos-review-card">
      <div className="nxos-card-head"><span className={`nxos-risk risk-${card.riskLevel}`}>{card.riskLevel} risk</span><span>{card.category}</span></div>
      <h3>{card.title}</h3>
      <p>{card.recommendation}</p>
      <dl><div><dt>Status</dt><dd>{current}</dd></div><div><dt>External action</dt><dd>{card.externalAction ? 'Yes — separately gated' : 'No'}</dd></div><div><dt>Source</dt><dd>{card.source}</dd></div><div><dt>Created</dt><dd>{card.createdAt}</dd></div></dl>
      <label className="nxos-field">Feedback<textarea value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="Optional direction for Hermes or the assigned specialist" /></label>
      <div className="nxos-actions">
        <button type="button" className="primary" onClick={() => onDecision(card, 'approved', feedback)}>Approve</button>
        <button type="button" onClick={() => onDecision(card, 'rejected', feedback)}>Reject</button>
        <button type="button" onClick={() => onDecision(card, 'held', feedback)}>Hold</button>
      </div>
      {decision && <div className="nxos-receipt"><strong>{decision.status}</strong> · Receipt {decision.receiptId}<br />{decision.nextStep}<br />Underlying action executed: no.</div>}
    </article>
  );
}
