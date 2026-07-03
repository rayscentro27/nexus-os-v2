import React from 'react';
import { isSafeHermesUiAction } from '../lib/hermesUiActions';

function openSafeAction(action) {
  if (!isSafeHermesUiAction(action) || !action.href) return;
  window.location.hash = action.href.replace(/^#\/?/, '');
}

export default function HermesMessageBubble({ message, onDelegate, onReview, onSpecialist }) { return <div className={`nxos-message ${message.role}`}><strong>{message.role === 'ray' ? 'Ray' : 'Hermes'}</strong><p>{message.text}</p><div className="hermes-message-actions">{message.role === 'ray' && onDelegate && <button type="button" onClick={() => onDelegate(message)}>Delegate this</button>}{message.role === 'hermes' && <>{(message.uiActions || []).filter(isSafeHermesUiAction).map((action, index) => <button type="button" key={`${action.actionType}-${action.approvalId || action.reportPath || index}`} onClick={() => openSafeAction(action)} title={action.summary}>{action.actionLabel}: {action.title}</button>)}{onReview && <button type="button" onClick={() => onReview(message)}>Draft Ray Review request</button>}{onSpecialist && <button type="button" onClick={() => onSpecialist(message)}>Prepare specialist handoff</button>}</>}</div></div>; }
