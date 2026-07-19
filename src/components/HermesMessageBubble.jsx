import React from 'react';
import { isSafeHermesUiAction } from '../lib/hermesUiActions';
import { isSafeWorkroomAction } from '../lib/hermes/hermesWorkroomResponse';

function openSafeAction(action) {
  if (!isSafeHermesUiAction(action) || !action.href) return;
  window.location.hash = action.href.replace(/^#\/?/, '');
}

export default function HermesMessageBubble({ message, onDelegate, onAction }) {
  const legacyActions = Array.isArray(message.uiActions) ? message.uiActions.filter(isSafeHermesUiAction) : [];
  const workroomActions = Array.isArray(message.actions) ? message.actions.filter(isSafeWorkroomAction) : [];
  return <div className={`nxos-message ${message.role}`} data-hermes-mode={message.mode || ''} data-hermes-intent={message.intent || ''}>
    <strong>{message.role === 'ray' ? 'Ray' : 'Hermes'}</strong>
    <p>{message.text}</p>
    <div className="hermes-message-actions">
      {message.role === 'ray' && onDelegate && <button type="button" onClick={() => onDelegate(message)}>Delegate this</button>}
      {message.role === 'hermes' && <>
        {legacyActions.map((action, index) => <button type="button" key={`${action.actionType}-${action.approvalId || action.reportPath || index}`} onClick={() => openSafeAction(action)} title={action.summary}>{action.actionLabel}: {action.title}</button>)}
        {workroomActions.map((action) => <button type="button" key={action.id} disabled={!action.enabled} onClick={() => action.enabled && onAction?.(action, message)} title={action.requiresApproval ? 'Approval required before execution.' : undefined}>{action.label}</button>)}
      </>}
    </div>
  </div>;
}
