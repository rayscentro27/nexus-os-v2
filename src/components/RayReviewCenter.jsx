import React, { useMemo, useState } from 'react';
import RayReviewCard from './RayReviewCard';
import { rayReviewCards } from '../data/rayReviewData';
import ApprovalReceiptToast from './ApprovalReceiptToast';
import ApprovalReceiptViewer from './ApprovalReceiptViewer';

const STORAGE_KEY = 'nexus-ray-review-decisions-v2';
function loadDecisions() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch { return {}; } }

export default function RayReviewCenter() {
  const [decisions, setDecisions] = useState(loadDecisions);
  const [filter, setFilter] = useState('pending');
  const [recentReceipt, setRecentReceipt] = useState(null);
  const [viewedReceipt, setViewedReceipt] = useState(null);
  const cards = useMemo(() => rayReviewCards.filter((card) => filter === 'all' || (decisions[card.id]?.status || card.status) === filter), [decisions, filter]);
  function decide(card, status, feedback) {
    const createdAt = new Date().toISOString();
    const record = { receiptId: `NXR-${Date.now().toString(36).toUpperCase()}`, cardId: card.id, title: card.title, status, feedback, executionStatus: 'queued_for_execution', nextStep: status === 'approved' ? 'Queued for a separately gated executor or manual follow-up.' : status === 'held' ? 'No follow-up until Ray revisits this card.' : 'Proposal closed; no action will run.', createdAt };
    const next = { ...decisions, [card.id]: record };
    setDecisions(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setRecentReceipt(record);
  }
  function undo() { if (!recentReceipt) return; const next={...decisions}; delete next[recentReceipt.cardId]; setDecisions(next); localStorage.setItem(STORAGE_KEY,JSON.stringify(next)); setViewedReceipt(null); setRecentReceipt(null); }
  return <div className="nxos-stack">
    <div className="nxos-toolbar"><strong>{rayReviewCards.length} cards available</strong><div>{['pending', 'approved', 'rejected', 'held', 'all'].map((item) => <button type="button" className={filter === item ? 'active' : ''} onClick={() => setFilter(item)} key={item}>{item}</button>)}</div></div>
    <p className="nxos-notice">Decisions are stored in this browser and queued. Approval never executes charges, sends, inserts, publishing, disputes, or trades.</p>
    <ApprovalReceiptToast receipt={recentReceipt} onView={()=>setViewedReceipt(recentReceipt)} onUndo={undo} onClose={()=>setRecentReceipt(null)} />
    <div className="nxos-review-grid">{cards.map((card) => <RayReviewCard key={card.id} card={card} decision={decisions[card.id]} onDecision={decide} />)}</div>
    {!cards.length && <div className="nxos-empty">No cards match this filter.</div>}
    <ApprovalReceiptViewer receipt={viewedReceipt} onClose={()=>setViewedReceipt(null)} />
  </div>;
}
