import React, { useEffect, useMemo, useState } from 'react';
import RayReviewCard from './RayReviewCard';
import { rayReviewCards } from '../data/rayReviewData';
import ApprovalReceiptToast from './ApprovalReceiptToast';
import ApprovalReceiptViewer from './ApprovalReceiptViewer';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';
import { createEvent } from '../lib/ledger';

const STORAGE_KEY = 'nexus-ray-review-decisions-v2';
function loadDecisions() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch { return {}; } }

function mapTaskRequestToCard(row) {
  const payload = row.payload || {};
  return {
    id: row.id,
    title: row.title || payload.title || 'Untitled task',
    category: row.task_type || 'general',
    riskLevel: row.sensitivity || 'public',
    status: row.status || 'pending',
    externalAction: false,
    recommendation: row.result_summary || payload.recommendation || 'Review and decide.',
    source: 'Supabase task_requests (' + String(row.id).slice(0, 8) + '...)',
    createdAt: row.created_at ? new Date(row.created_at).toLocaleDateString() : 'unknown',
    nextActionCommand: '',
    _liveSource: 'live_supabase',
    _supabaseTable: 'task_requests',
  };
}

function mapStaticCardToCard(row) {
  return {
    id: row.id,
    title: row.title,
    category: row.category,
    riskLevel: row.riskLevel,
    status: 'pending',
    externalAction: Boolean(row.externalAction),
    recommendation: row.recommendation,
    source: row.source,
    createdAt: row.createdAt,
    nextActionCommand: row.nextActionCommand,
    _liveSource: 'static',
  };
}

export default function RayReviewCenter() {
  const [decisions, setDecisions] = useState(loadDecisions);
  const [filter, setFilter] = useState('pending');
  const [recentReceipt, setRecentReceipt] = useState(null);
  const [viewedReceipt, setViewedReceipt] = useState(null);
  const [liveCards, setLiveCards] = useState([]);
  const [dataSource, setDataSource] = useState({ source: 'loading', label: 'Loading...', error: null });
  const [persisting, setPersisting] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!supabase || !isSupabaseConfigured) {
        setLiveCards(rayReviewCards.map(mapStaticCardToCard));
        setDataSource({ source: 'static', label: 'Static snapshot · ' + rayReviewCards.length + ' cards · Supabase not configured', error: null });
        return;
      }
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) {
          setLiveCards(rayReviewCards.map(mapStaticCardToCard));
          setDataSource({ source: 'static', label: 'Static snapshot · ' + rayReviewCards.length + ' cards · No auth session', error: null });
          return;
        }
        const { data, error } = await supabase
          .from('task_requests')
          .select('*')
          .eq('task_type', 'ray_review_item')
          .order('created_at', { ascending: false })
          .limit(100);

        if (cancelled) return;

        if (error) {
          setLiveCards(rayReviewCards.map(mapStaticCardToCard));
          setDataSource({ source: 'static', label: 'Static snapshot · ' + rayReviewCards.length + ' cards · Query error: ' + error.message.slice(0, 50), error: error.message });
          return;
        }

        const rows = data || [];
        if (rows.length > 0) {
          const mapped = rows.map(mapTaskRequestToCard);
          setLiveCards(mapped);
          setDataSource({ source: 'live_supabase', label: 'Live Supabase · ' + mapped.length + ' cards from task_requests', error: null });
        } else {
          setLiveCards(rayReviewCards.map(mapStaticCardToCard));
          setDataSource({ source: 'static', label: 'Static snapshot · ' + rayReviewCards.length + ' cards · 0 rows in Supabase (using fallback)', error: null });
        }
      } catch (e) {
        if (cancelled) return;
        setLiveCards(rayReviewCards.map(mapStaticCardToCard));
        setDataSource({ source: 'static', label: 'Static snapshot · ' + rayReviewCards.length + ' cards · Connection error', error: String(e) });
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const cards = useMemo(() => liveCards.filter((card) => {
    const cardStatus = decisions[card.id] ? decisions[card.id].status : card.status;
    return filter === 'all' || cardStatus === filter;
  }), [liveCards, decisions, filter]);

  async function decide(card, status, feedback) {
    const createdAt = new Date().toISOString();
    const receiptId = 'NXR-' + Date.now().toString(36).toUpperCase();

    const record = {
      receiptId: receiptId, cardId: card.id, title: card.title, status: status, feedback: feedback,
      executionStatus: 'queued_for_execution',
      nextStep: status === 'approved' ? 'Queued for a separately gated executor or manual follow-up.'
        : status === 'held' ? 'No follow-up until Ray revisits this card.'
        : 'Proposal closed; no action will run.',
      createdAt: createdAt,
    };
    const next = Object.assign({}, decisions, {});
    next[card.id] = record;
    setDecisions(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));

    if (card._liveSource === 'live_supabase' && supabase && isSupabaseConfigured) {
      setPersisting(card.id);
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          const supabaseStatus = status === 'approved' ? 'done' : status === 'rejected' ? 'rejected' : 'in_progress';
          const { error: updateErr } = await supabase
            .from('task_requests')
            .update({ status: supabaseStatus, updated_at: createdAt })
            .eq('id', card.id);

          if (!updateErr) {
            await createEvent({
              lane: 'system',
              action: 'ray_review_' + status,
              status: 'success',
              title: status + ': ' + card.title,
              summary: feedback || 'Ray ' + status + ' this card via Ray Review.',
              payload: { receiptId: receiptId, cardId: card.id, decision: status },
            });
            record.source = 'live_supabase';
            record.supabaseTable = 'task_requests';
            record.supabaseRowId = card.id;
          } else {
            record.source = 'local_only';
            record.supabaseError = updateErr.message;
          }
        }
      } catch (e) {
        record.source = 'local_only';
        record.supabaseError = String(e);
      }
      setPersisting(null);
    } else {
      record.source = 'local_only';
    }

    setRecentReceipt(record);
  }

  function undo() {
    if (!recentReceipt) return;
    const next = Object.assign({}, decisions);
    delete next[recentReceipt.cardId];
    setDecisions(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setViewedReceipt(null);
    setRecentReceipt(null);
  }

  var pendingCount = cards.filter(function(c) { return (decisions[c.id] ? decisions[c.id].status : c.status) === 'pending'; }).length;

  return (
    <div className="nxos-stack">
      <div className="nxos-toolbar">
        <strong>{cards.length} cards · {dataSource.source === 'live_supabase' ? 'Live Supabase' : dataSource.source === 'static' ? 'Static snapshot' : 'Loading...'}</strong>
        <span className="nxos-source-label" style={{ fontSize: '0.8em', color: '#888', marginLeft: 8 }}>{dataSource.label}</span>
        <div>
          {['pending', 'approved', 'rejected', 'held', 'all'].map(function(item) {
            return <button type="button" className={filter === item ? 'active' : ''} onClick={function() { setFilter(item); }} key={item}>{item}</button>;
          })}
        </div>
      </div>
      <p className="nxos-notice">
        {dataSource.source === 'live_supabase'
          ? 'Decisions persist to Supabase (task_requests table) and are recorded as nexus_events. localStorage receipts are secondary proof only.'
          : 'Decisions are stored in this browser only (localStorage). Supabase is not connected for this view. Approval never executes charges, sends, inserts, publishing, disputes, or trades.'}
      </p>
      <ApprovalReceiptToast receipt={recentReceipt} onView={function() { setViewedReceipt(recentReceipt); }} onUndo={undo} onClose={function() { setRecentReceipt(null); }} />
      <div className="nxos-review-grid">
        {cards.map(function(card) {
          return (
            <RayReviewCard
              key={card.id}
              card={card}
              decision={decisions[card.id]}
              onDecision={decide}
              persisting={persisting === card.id}
            />
          );
        })}
      </div>
      {!cards.length && <div className="nxos-empty">No cards match this filter.</div>}
      <ApprovalReceiptViewer receipt={viewedReceipt} onClose={function() { setViewedReceipt(null); }} />
    </div>
  );
}
