import React, { useEffect, useMemo } from 'react';

const safeArray = (...values) => {
  for (const value of values) {
    if (Array.isArray(value)) return value;
  }
  return [];
};

const getField = (obj, names, fallback = '') => {
  if (!obj) return fallback;
  for (const name of names) {
    if (obj[name] !== undefined && obj[name] !== null && obj[name] !== '') {
      return obj[name];
    }
  }
  return fallback;
};

const normalize = (value) => String(value || '').toLowerCase();

const isCreditReportDocument = (doc) => {
  const text = [
    doc?.category,
    doc?.title,
    doc?.name,
    doc?.file_name,
    doc?.filename,
    doc?.document_type,
  ].map(normalize).join(' ');
  return text.includes('credit') && text.includes('report');
};

const isProofOfAddressDocument = (doc) => {
  const text = [
    doc?.category,
    doc?.title,
    doc?.name,
    doc?.file_name,
    doc?.filename,
    doc?.document_type,
  ].map(normalize).join(' ');
  return text.includes('proof_of_address') || text.includes('proof of address') || text.includes('address');
};

const isUploadedOrPending = (doc) => {
  const status = normalize(doc?.status || doc?.goclear_review_status);
  return ['uploaded', 'pending_review', 'under_review', 'approved', 'reviewed'].some((item) => status.includes(item));
};

const isLetterReady = (letter) => {
  const status = normalize(letter?.status);
  return [
    'draft',
    'specialist_review',
    'ray_review',
    'client_review',
    'client_approved',
    'approved_for_docupost',
  ].some((item) => status.includes(item));
};

const statusTone = {
  complete: 'crj-complete',
  current: 'crj-current',
  pending: 'crj-pending',
  blocked: 'crj-blocked',
};

function injectGoogleFont() {
  if (typeof document === 'undefined') return;
  const existing = document.querySelector('link[data-nexus-google-font="inter"]');
  if (existing) return;

  const preconnectOne = document.createElement('link');
  preconnectOne.rel = 'preconnect';
  preconnectOne.href = 'https://fonts.googleapis.com';
  preconnectOne.setAttribute('data-nexus-google-font', 'inter');

  const preconnectTwo = document.createElement('link');
  preconnectTwo.rel = 'preconnect';
  preconnectTwo.href = 'https://fonts.gstatic.com';
  preconnectTwo.crossOrigin = 'anonymous';
  preconnectTwo.setAttribute('data-nexus-google-font', 'inter');

  const font = document.createElement('link');
  font.rel = 'stylesheet';
  font.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap';
  font.setAttribute('data-nexus-google-font', 'inter');

  document.head.appendChild(preconnectOne);
  document.head.appendChild(preconnectTwo);
  document.head.appendChild(font);
}

function IconBubble({ children, tone = 'blue' }) {
  return <span className={`crj-icon crj-icon-${tone}`}>{children}</span>;
}

function ProgressStep({ index, label, sublabel, state }) {
  const className = statusTone[state] || statusTone.pending;
  return (
    <article className={`crj-step ${className}`}>
      <div className="crj-step-marker">
        {state === 'complete' ? '✓' : index}
      </div>
      <div>
        <strong>{label}</strong>
        <span>{sublabel}</span>
      </div>
    </article>
  );
}

function ActionRow({ number, title, detail, due, onClick }) {
  return (
    <button type="button" className="crj-action-row" onClick={onClick}>
      <span className="crj-action-number">{number}</span>
      <span className="crj-action-copy">
        <strong>{title}</strong>
        <small>{detail}</small>
        {due && <em>{due}</em>}
      </span>
      <span className="crj-chevron">›</span>
    </button>
  );
}

function ProgressBar({ label, value, tone = 'blue' }) {
  const safeValue = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="crj-progress-row">
      <div className="crj-progress-label">
        <span>{label}</span>
        <strong>{safeValue}%</strong>
      </div>
      <div className="crj-progress-track">
        <span className={`crj-progress-fill crj-fill-${tone}`} style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  );
}

function LetterCard({ letter, index, onReview, onSend }) {
  const recipient = getField(letter, ['recipient_name', 'recipientName'], index === 0 ? 'Experian' : index === 1 ? 'Equifax' : 'TransUnion');
  const status = getField(letter, ['status'], 'draft');
  const itemCount = safeArray(letter?.dispute_items, letter?.items).length || safeArray(letter?.dispute_item_ids).length || 0;

  return (
    <article className="crj-letter-card">
      <div className="crj-letter-top">
        <div>
          <span className="crj-bureau-logo">{recipient}</span>
          <p>Dispute letter</p>
        </div>
        <span className="crj-pill crj-pill-blue">{status.replaceAll('_', ' ')}</span>
      </div>

      <dl className="crj-letter-details">
        <div>
          <dt>Primary items</dt>
          <dd>{itemCount || 'Pending'}</dd>
        </div>
        <div>
          <dt>Mail method</dt>
          <dd>DocuPost / Certified</dd>
        </div>
      </dl>

      <div className="crj-letter-actions">
        <button type="button" className="crj-btn crj-btn-light" onClick={onReview}>
          Review draft
        </button>
        <button type="button" className="crj-btn crj-btn-primary" onClick={onSend}>
          Send with DocuPost
        </button>
      </div>
    </article>
  );
}

function EmptyLetterCard({ onUpload }) {
  return (
    <article className="crj-empty-card">
      <IconBubble tone="purple">✍</IconBubble>
      <strong>No dispute letters are ready yet</strong>
      <p>
        Upload your credit report and supporting documents. Your GoClear specialist will review the file,
        identify dispute items, and prepare draft letters for your approval.
      </p>
      <button type="button" className="crj-btn crj-btn-primary" onClick={onUpload}>
        Upload credit report
      </button>
    </article>
  );
}

export default function CreditRepairJourneyView({
  liveData = {},
  creditRepair = {},
  onNavigate,
}) {
  useEffect(() => {
    injectGoogleFont();
  }, []);

  const go = (path) => {
    if (typeof onNavigate === 'function') {
      onNavigate(path);
      return;
    }
    if (typeof window !== 'undefined') {
      window.location.assign(path);
    }
  };

  const model = useMemo(() => {
    const profile = liveData.profile || liveData.clientProfile || creditRepair.profile || {};
    const documents = safeArray(
      liveData.documents,
      liveData.clientDocuments,
      liveData.client_documents,
      creditRepair.documents
    );
    const reviews = safeArray(
      liveData.creditReportReviews,
      liveData.credit_report_reviews,
      creditRepair.reviews
    );
    const disputeItems = safeArray(
      liveData.creditDisputeItems,
      liveData.credit_dispute_items,
      creditRepair.disputeItems
    );
    const letters = safeArray(
      liveData.creditDisputeLetters,
      liveData.credit_dispute_letters,
      creditRepair.letters
    );
    const mailJobs = safeArray(
      liveData.docupostMailJobs,
      liveData.docupost_mail_jobs,
      creditRepair.mailJobs
    );

    const businessName = getField(profile, ['business_name', 'businessName']);
    const legalName = getField(profile, ['legal_name', 'legalName', 'name', 'full_name']);
    const phone = getField(profile, ['phone', 'phone_number']);
    const profileComplete = Boolean((businessName || legalName) && phone);

    const creditReportUploaded = documents.some((doc) => isCreditReportDocument(doc) && isUploadedOrPending(doc));
    const proofOfAddressUploaded = documents.some((doc) => isProofOfAddressDocument(doc) && isUploadedOrPending(doc));

    const reviewStarted = reviews.length > 0 || disputeItems.length > 0 || letters.length > 0;
    const itemsReady = disputeItems.length > 0;
    const lettersReady = letters.some(isLetterReady);
    const approvedToSend = letters.some((letter) => ['client_approved', 'approved_for_docupost', 'docupost_queued', 'docupost_mailed', 'docupost_delivered'].includes(normalize(letter.status)));
    const mailTracking = mailJobs.length > 0 || letters.some((letter) => normalize(letter.status).includes('docupost'));

    const journey = [
      {
        key: 'profile',
        label: 'Profile Complete',
        sublabel: profileComplete ? 'Completed' : 'Needed',
        state: profileComplete ? 'complete' : 'current',
      },
      {
        key: 'upload',
        label: 'Upload Credit Report',
        sublabel: creditReportUploaded ? 'Completed' : 'Next step',
        state: creditReportUploaded ? 'complete' : profileComplete ? 'current' : 'pending',
      },
      {
        key: 'review',
        label: 'Specialist Review',
        sublabel: reviewStarted ? 'In progress' : 'Pending',
        state: reviewStarted ? 'complete' : creditReportUploaded ? 'current' : 'pending',
      },
      {
        key: 'items',
        label: 'Dispute Items',
        sublabel: itemsReady ? `${disputeItems.length} identified` : 'Pending',
        state: itemsReady ? 'complete' : reviewStarted ? 'current' : 'pending',
      },
      {
        key: 'letters',
        label: 'Draft Letters',
        sublabel: lettersReady ? `${letters.length} ready` : 'Pending',
        state: lettersReady ? 'current' : itemsReady ? 'current' : 'pending',
      },
      {
        key: 'approve',
        label: 'Approve & Send',
        sublabel: approvedToSend ? 'Approved' : 'Pending',
        state: approvedToSend ? 'complete' : lettersReady ? 'current' : 'pending',
      },
      {
        key: 'track',
        label: 'Track Results',
        sublabel: mailTracking ? 'Tracking' : 'Pending',
        state: mailTracking ? 'current' : 'pending',
      },
    ];

    const profileScore = profileComplete ? 100 : businessName || legalName ? 60 : 25;
    const disputePrepScore = creditReportUploaded ? reviewStarted ? 80 : 45 : 15;
    const lettersScore = lettersReady ? 75 : itemsReady ? 45 : 0;
    const mailScore = mailTracking ? 40 : approvedToSend ? 20 : 0;

    return {
      profile,
      documents,
      reviews,
      disputeItems,
      letters,
      mailJobs,
      journey,
      profileComplete,
      creditReportUploaded,
      proofOfAddressUploaded,
      reviewStarted,
      itemsReady,
      lettersReady,
      approvedToSend,
      mailTracking,
      profileScore,
      disputePrepScore,
      lettersScore,
      mailScore,
    };
  }, [liveData, creditRepair]);

  const nextActions = [
    !model.profileComplete && {
      title: 'Complete Profile & Business Info',
      detail: 'Your specialist needs your contact and business basics before preparing funding or dispute work.',
      due: 'Recommended first',
      path: '/client/profile',
    },
    !model.creditReportUploaded && {
      title: 'Upload your credit report',
      detail: 'Upload the latest report so GoClear can identify possible dispute items.',
      due: 'Needed for specialist review',
      path: '/client/documents',
    },
    model.creditReportUploaded && !model.reviewStarted && {
      title: 'Request GoClear review',
      detail: 'Ask the specialist team to review your uploaded credit report.',
      due: 'Next review step',
      path: '/client/request-review',
    },
    model.lettersReady && {
      title: 'Review draft dispute letters',
      detail: 'Approve, request edits, or prepare DocuPost send authorization.',
      due: 'Ready now',
      path: '/client/dispute-review',
    },
    !model.proofOfAddressUploaded && {
      title: 'Upload proof of address',
      detail: 'A current proof of address helps support your dispute and funding readiness profile.',
      due: 'Helpful supporting document',
      path: '/client/documents',
    },
  ].filter(Boolean).slice(0, 3);

  const visibleLetters = model.letters.slice(0, 3);

  return (
    <main className="crj-page">
      <style>{creditRepairJourneyStyles}</style>

      <section className="crj-hero">
        <div>
          <p className="crj-eyebrow">GoClear Credit Repair</p>
          <h1>Credit Repair Journey</h1>
          <p>
            A guided credit process that shows what you do, what your specialist does,
            when letters are ready, and when DocuPost can mail from home.
          </p>
        </div>
        <div className="crj-hero-actions">
          <span className="crj-live-badge">● Live workflow</span>
          <button type="button" className="crj-btn crj-btn-light" onClick={() => go('/client/funding-readiness')}>
            View Funding Readiness
          </button>
        </div>
      </section>

      <section className="crj-timeline-card">
        <div className="crj-section-heading">
          <div>
            <h2>Journey progress</h2>
            <p>Each step moves your profile closer to dispute readiness and funding readiness.</p>
          </div>
          <button type="button" className="crj-btn crj-btn-light" onClick={() => go('/client/documents')}>
            Upload documents
          </button>
        </div>

        <div className="crj-steps">
          {model.journey.map((step, index) => (
            <ProgressStep
              key={step.key}
              index={index + 1}
              label={step.label}
              sublabel={step.sublabel}
              state={step.state}
            />
          ))}
        </div>
      </section>

      <section className="crj-grid crj-grid-three">
        <article className="crj-card">
          <div className="crj-section-heading">
            <div>
              <h2>Your next actions</h2>
              <p>{nextActions.length} priority action{nextActions.length === 1 ? '' : 's'}</p>
            </div>
          </div>

          <div className="crj-action-list">
            {nextActions.length > 0 ? (
              nextActions.map((action, index) => (
                <ActionRow
                  key={action.title}
                  number={index + 1}
                  title={action.title}
                  detail={action.detail}
                  due={action.due}
                  onClick={() => go(action.path)}
                />
              ))
            ) : (
              <div className="crj-empty-small">
                <strong>No client action needed right now.</strong>
                <p>Your GoClear specialist is reviewing the next step.</p>
              </div>
            )}
          </div>
        </article>

        <article className="crj-card">
          <div className="crj-section-heading">
            <div>
              <h2>Progress overview</h2>
              <p>Live or derived status based on profile, documents, reviews, and letters.</p>
            </div>
          </div>

          <div className="crj-progress-stack">
            <ProgressBar label="Credit Profile" value={model.profileScore} tone="teal" />
            <ProgressBar label="Dispute Prep" value={model.disputePrepScore} tone="blue" />
            <ProgressBar label="Letters Ready" value={model.lettersScore} tone="purple" />
            <ProgressBar label="Mail Tracking" value={model.mailScore} tone="orange" />
          </div>
        </article>

        <article className="crj-card crj-docupost">
          <IconBubble tone="blue">⌂</IconBubble>
          <h2>Send from home</h2>
          <p>
            Nexus prepares drafts for review. Your specialist verifies the facts, then you approve
            the letters before DocuPost mailing is requested.
          </p>

          <ul className="crj-check-list">
            <li>Specialist review required first</li>
            <li>Client approval required before sending</li>
            <li>DocuPost status and tracking stay in Nexus</li>
          </ul>

          <button type="button" className="crj-btn crj-btn-primary" onClick={() => go('/client/dispute-review')}>
            Review letters
          </button>
        </article>
      </section>

      <section className="crj-grid crj-grid-two">
        <article className="crj-card crj-wide">
          <div className="crj-section-heading">
            <div>
              <h2>Draft letters</h2>
              <p>Review draft letters, request edits, and authorize DocuPost only after approval.</p>
            </div>
            <span className="crj-pill crj-pill-blue">{model.letters.length} letter{model.letters.length === 1 ? '' : 's'}</span>
          </div>

          <div className="crj-letter-grid">
            {visibleLetters.length > 0 ? (
              visibleLetters.map((letter, index) => (
                <LetterCard
                  key={letter.id || `${letter.recipient_name}-${index}`}
                  letter={letter}
                  index={index}
                  onReview={() => go('/client/dispute-review')}
                  onSend={() => go('/client/dispute-review')}
                />
              ))
            ) : (
              <EmptyLetterCard onUpload={() => go('/client/documents')} />
            )}
          </div>
        </article>

        <aside className="crj-card crj-guidance-card">
          <div className="crj-section-heading">
            <div>
              <h2>Nexus guidance</h2>
              <p>Advisory only — GoClear review is required before external action.</p>
            </div>
          </div>

          <div className="crj-guidance-list">
            <div>
              <strong>{model.profileComplete ? 'Profile is ready' : 'Complete profile first'}</strong>
              <p>
                {model.profileComplete
                  ? 'Your profile has enough basics for the credit repair journey.'
                  : 'Add your profile and business information so the specialist has the right client record.'}
              </p>
            </div>
            <div>
              <strong>{model.creditReportUploaded ? 'Credit report uploaded' : 'Upload credit report'}</strong>
              <p>
                {model.creditReportUploaded
                  ? 'GoClear can use the uploaded report for specialist review.'
                  : 'Upload your latest report in Documents. Nexus will help route it for review.'}
              </p>
            </div>
            <div>
              <strong>Funding readiness impact</strong>
              <p>
                Credit cleanup supports fundability, but funding readiness also depends on profile,
                business setup, bankability, and supporting documents.
              </p>
            </div>
          </div>

          <button type="button" className="crj-btn crj-btn-light crj-full" onClick={() => go('/client/funding-readiness')}>
            See funding readiness impact
          </button>
        </aside>
      </section>

      <section className="crj-footer-note">
        <IconBubble tone="green">✓</IconBubble>
        <div>
          <strong>Approval-gated sending</strong>
          <p>
            Nexus may draft dispute letters, but no DocuPost mailing request should be created until
            specialist review and client approval are complete.
          </p>
        </div>
      </section>
    </main>
  );
}

const creditRepairJourneyStyles = `
.crj-page {
  --crj-text: #10213f;
  --crj-muted: #657795;
  --crj-border: rgba(52, 89, 151, 0.16);
  --crj-soft: #f5f8fd;
  --crj-card: rgba(255,255,255,0.88);
  --crj-blue: #2563eb;
  --crj-cyan: #0ea5e9;
  --crj-teal: #14b8a6;
  --crj-purple: #7c3aed;
  --crj-orange: #f59e0b;
  --crj-green: #10b981;
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: var(--crj-text);
  padding: 28px;
  max-width: 1440px;
  margin: 0 auto;
}

.crj-page * {
  box-sizing: border-box;
}

.crj-hero,
.crj-timeline-card,
.crj-card,
.crj-footer-note {
  border: 1px solid var(--crj-border);
  background: var(--crj-card);
  box-shadow: 0 18px 50px rgba(42, 70, 118, 0.08);
  border-radius: 22px;
}

.crj-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  padding: 28px 30px;
  background:
    radial-gradient(circle at 85% 0%, rgba(14,165,233,0.18), transparent 32%),
    linear-gradient(135deg, rgba(255,255,255,0.96), rgba(241,248,255,0.92));
}

.crj-eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  font-weight: 900;
  color: var(--crj-blue);
}

.crj-hero h1 {
  margin: 0;
  font-size: clamp(28px, 3vw, 42px);
  line-height: 1;
  letter-spacing: -0.04em;
}

.crj-hero p,
.crj-section-heading p,
.crj-card p,
.crj-footer-note p {
  color: var(--crj-muted);
  line-height: 1.6;
}

.crj-hero p {
  margin: 12px 0 0;
  max-width: 720px;
}

.crj-hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.crj-live-badge,
.crj-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
  padding: 8px 12px;
  white-space: nowrap;
}

.crj-live-badge {
  color: #047857;
  background: rgba(16,185,129,0.12);
  border: 1px solid rgba(16,185,129,0.22);
}

.crj-pill-blue {
  background: linear-gradient(135deg, rgba(37,99,235,0.12), rgba(37,99,235,0.06));
  color: #1d4ed8;
  border: 1px solid rgba(37,99,235,0.15);
}

.crj-timeline-card,
.crj-card,
.crj-footer-note {
  margin-top: 20px;
  padding: 22px;
}

.crj-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.crj-section-heading h2 {
  margin: 0;
  font-size: 20px;
  letter-spacing: -0.02em;
}

.crj-section-heading p {
  margin: 5px 0 0;
  font-size: 13px;
}

.crj-steps {
  display: grid;
  grid-template-columns: repeat(7, minmax(130px, 1fr));
  gap: 10px;
}

.crj-step {
  min-height: 120px;
  border-radius: 18px;
  border: 1px solid var(--crj-border);
  background: #fff;
  padding: 18px 12px;
  text-align: center;
  display: grid;
  place-items: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.crj-step:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(37,99,235,0.08);
}

.crj-step-marker {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 20px;
  margin: 0 auto 4px;
  font-weight: 900;
  font-size: 20px;
  background: linear-gradient(135deg, #dbeafe, #eef2ff);
  color: var(--crj-blue);
  box-shadow: 0 12px 24px rgba(37,99,235,0.14);
}

.crj-step strong {
  display: block;
  font-size: 13px;
}

.crj-step span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--crj-muted);
  font-weight: 700;
}

.crj-step.crj-complete {
  border-color: rgba(16,185,129,0.28);
  background: linear-gradient(180deg, rgba(16,185,129,0.08), #fff);
}

.crj-step.crj-complete .crj-step-marker {
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  box-shadow: 0 12px 24px rgba(16,185,129,0.22);
}

.crj-step.crj-current {
  border-color: rgba(37,99,235,0.42);
  box-shadow: inset 0 0 0 1px rgba(37,99,235,0.18), 0 12px 24px rgba(37,99,235,0.12);
  background: linear-gradient(180deg, rgba(37,99,235,0.06), #fff);
}

.crj-step.crj-current .crj-step-marker {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
  box-shadow: 0 12px 24px rgba(37,99,235,0.22);
  animation: crj-pulse 2s ease-in-out infinite;
}

@keyframes crj-pulse {
  0%, 100% { box-shadow: 0 12px 24px rgba(37,99,235,0.22); }
  50% { box-shadow: 0 12px 32px rgba(37,99,235,0.36); }
}

.crj-grid {
  display: grid;
  gap: 20px;
}

.crj-grid-three {
  grid-template-columns: 1.05fr 1fr 0.95fr;
}

.crj-grid-two {
  grid-template-columns: 1.45fr 0.75fr;
}

.crj-action-list {
  display: grid;
  gap: 10px;
}

.crj-action-row {
  width: 100%;
  border: 1px solid var(--crj-border);
  background: #fff;
  border-radius: 16px;
  padding: 14px;
  display: grid;
  grid-template-columns: 44px 1fr 20px;
  gap: 12px;
  text-align: left;
  align-items: center;
  cursor: pointer;
  transition: 160ms ease;
  font: inherit;
  color: inherit;
}

.crj-action-row:hover {
  transform: translateY(-1px);
  border-color: rgba(37,99,235,0.35);
  box-shadow: 0 12px 28px rgba(37,99,235,0.08);
}

.crj-action-number {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: linear-gradient(135deg, #dbeafe, #eef2ff);
  color: var(--crj-blue);
  display: grid;
  place-items: center;
  font-weight: 900;
  font-size: 14px;
  box-shadow: 0 6px 14px rgba(37,99,235,0.1);
}

.crj-action-copy strong,
.crj-action-copy small,
.crj-action-copy em {
  display: block;
}

.crj-action-copy small {
  margin-top: 3px;
  color: var(--crj-muted);
  line-height: 1.45;
}

.crj-action-copy em {
  margin-top: 4px;
  color: #ea580c;
  font-style: normal;
  font-size: 12px;
  font-weight: 800;
}

.crj-chevron {
  color: var(--crj-blue);
  font-size: 24px;
}

.crj-progress-stack {
  display: grid;
  gap: 18px;
}

.crj-progress-label {
  display: flex;
  justify-content: space-between;
  font-weight: 800;
  font-size: 13px;
  margin-bottom: 8px;
}

.crj-progress-track {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #e8edf6;
}

.crj-progress-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.crj-fill-blue { background: linear-gradient(90deg, #2563eb, #3b82f6); }
.crj-fill-teal { background: linear-gradient(90deg, #0d9488, #14b8a6); }
.crj-fill-purple { background: linear-gradient(90deg, #7c3aed, #8b5cf6); }
.crj-fill-orange { background: linear-gradient(90deg, #ea580c, #f59e0b); }
.crj-fill-green { background: linear-gradient(90deg, #059669, #10b981); }

.crj-icon {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  font-weight: 900;
  font-size: 24px;
}

.crj-icon-blue { color: var(--crj-blue); background: linear-gradient(135deg, rgba(37,99,235,0.12), rgba(14,165,233,0.08)); box-shadow: 0 8px 18px rgba(37,99,235,0.1); }
.crj-icon-purple { color: var(--crj-purple); background: linear-gradient(135deg, rgba(124,58,237,0.12), rgba(167,139,250,0.08)); box-shadow: 0 8px 18px rgba(124,58,237,0.1); }
.crj-icon-green { color: var(--crj-green); background: linear-gradient(135deg, rgba(16,185,129,0.12), rgba(52,211,153,0.08)); box-shadow: 0 8px 18px rgba(16,185,129,0.1); }

.crj-docupost {
  background:
    radial-gradient(circle at top right, rgba(37,99,235,0.12), transparent 45%),
    #fff;
}

.crj-check-list {
  padding: 0;
  margin: 18px 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.crj-check-list li {
  color: var(--crj-text);
  font-weight: 700;
  font-size: 13px;
}

.crj-check-list li::before {
  content: '✓';
  color: var(--crj-green);
  font-weight: 900;
  margin-right: 8px;
}

.crj-btn {
  min-height: 42px;
  border-radius: 12px;
  border: 1px solid transparent;
  padding: 0 16px;
  font-family: inherit;
  font-weight: 900;
  cursor: pointer;
  transition: 160ms ease;
}

.crj-btn:hover {
  transform: translateY(-1px);
}

.crj-btn-primary {
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #14b8a6);
  box-shadow: 0 12px 28px rgba(37,99,235,0.18);
}

.crj-btn-light {
  color: var(--crj-blue);
  background: #fff;
  border-color: rgba(37,99,235,0.24);
}

.crj-full {
  width: 100%;
}

.crj-letter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(210px, 1fr));
  gap: 14px;
}

.crj-letter-card,
.crj-empty-card {
  border: 1px solid var(--crj-border);
  background: #fff;
  border-radius: 18px;
  padding: 16px;
}

.crj-letter-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.crj-bureau-logo {
  font-size: 22px;
  font-weight: 900;
  color: var(--crj-blue);
  letter-spacing: -0.03em;
}

.crj-letter-top p {
  margin: 6px 0 0;
  color: var(--crj-text);
  font-weight: 800;
}

.crj-letter-details {
  display: grid;
  gap: 8px;
  margin: 18px 0;
}

.crj-letter-details div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid #eef2f7;
  padding-top: 9px;
}

.crj-letter-details dt {
  color: var(--crj-muted);
  font-size: 12px;
}

.crj-letter-details dd {
  margin: 0;
  font-weight: 800;
  font-size: 12px;
}

.crj-letter-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.crj-empty-card {
  grid-column: 1 / -1;
  min-height: 220px;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 26px;
}

.crj-empty-card p {
  max-width: 560px;
}

.crj-empty-small {
  border: 1px dashed rgba(37,99,235,0.25);
  border-radius: 16px;
  padding: 18px;
  background: rgba(37,99,235,0.04);
}

.crj-empty-small p {
  margin: 6px 0 0;
}

.crj-guidance-list {
  display: grid;
  gap: 14px;
  margin-bottom: 18px;
}

.crj-guidance-list div {
  border-left: 3px solid rgba(37,99,235,0.25);
  padding-left: 12px;
}

.crj-guidance-list strong {
  display: block;
  margin-bottom: 4px;
}

.crj-guidance-list p {
  margin: 0;
  font-size: 13px;
}

.crj-footer-note {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(37,99,235,0.06));
}

.crj-footer-note strong {
  display: block;
  margin-bottom: 4px;
}

.crj-footer-note p {
  margin: 0;
}

@media (max-width: 1180px) {
  .crj-steps {
    grid-template-columns: repeat(4, minmax(140px, 1fr));
  }

  .crj-grid-three,
  .crj-grid-two {
    grid-template-columns: 1fr;
  }

  .crj-letter-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .crj-page {
    padding: 18px;
  }

  .crj-hero,
  .crj-section-heading {
    flex-direction: column;
  }

  .crj-hero-actions {
    justify-content: flex-start;
  }

  .crj-steps {
    grid-template-columns: 1fr;
  }

  .crj-letter-actions {
    grid-template-columns: 1fr;
  }
}
`;
