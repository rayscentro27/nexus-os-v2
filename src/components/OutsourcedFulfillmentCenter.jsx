// Outsourced Fulfillment Center — MANUAL CONTROLLED BRIDGE.
// CRJ / DisputeForMe performs outsourced credit-dispute fulfillment.
// Nexus coordinates, tracks, verifies, and gates. There is NO automated CRJ API
// connection yet: this view supports controlled manual updates only.
// All case rows below are SYNTHETIC demo records, never real client data.
import React, { useState } from 'react'
import { Send, ShieldCheck, ClipboardList } from 'lucide-react'
import { buildComplianceEnrollmentView, COMPLIANCE_FOUNDATION_NOTE } from '../lib/clientComplianceModel'

export const FULFILLMENT_WORKFLOW_STATES = [
  'Awaiting Intake',
  'Ready for Handoff',
  'Submitted to Provider',
  'Provider Reviewing',
  'Round Prepared',
  'Round Mailed',
  'Waiting for Results',
  'New Report Required',
  'Results Received',
  'Verification Required',
  'Billing Review',
  'Round Complete',
  'Escalated',
]

const toneForState = (state) => {
  const map = {
    'Awaiting Intake': 'amber',
    'Ready for Handoff': 'blue',
    'Submitted to Provider': 'blue',
    'Provider Reviewing': 'violet',
    'Round Prepared': 'blue',
    'Round Mailed': 'violet',
    'Waiting for Results': 'blue',
    'New Report Required': 'red',
    'Results Received': 'green',
    'Verification Required': 'amber',
    'Billing Review': 'amber',
    'Round Complete': 'green',
    Escalated: 'red',
  }
  return map[state] || 'blue'
}

const demoCases = [
  {
    id: 'CRJ-SYN-001',
    clientRef: 'Persona A (synthetic)',
    provider: 'CRJ / DisputeForMe',
    providerCaseId: '—',
    round: 0,
    status: 'Awaiting Intake',
    submitted: '—',
    mailed: '—',
    expectedReview: '—',
    transmitted: [],
    missing: ['Starting credit report', 'Proof of address'],
    vendorNotes: 'No handoff yet — awaiting client intake documents.',
    sla: 'Idle',
    cost: '$0.00',
    nextAuthorizedAction: 'Await starting credit report; then move to Ready for Handoff.',
  },
  {
    id: 'CRJ-SYN-002',
    clientRef: 'Persona B (synthetic)',
    provider: 'CRJ / DisputeForMe',
    providerCaseId: '—',
    round: 1,
    status: 'Ready for Handoff',
    submitted: '—',
    mailed: '—',
    expectedReview: '—',
    transmitted: ['Credit report (parsed)'],
    missing: ['Ambiguous account documentation'],
    vendorNotes: 'Report analyzed. Case ready for controlled handoff after documentation review.',
    sla: 'On track',
    cost: '$0.00',
    nextAuthorizedAction: 'Complete documentation review, then manually record provider submission.',
  },
]

export default function OutsourcedFulfillmentCenter() {
  const [cases, setCases] = useState(demoCases)
  const [lastAction, setLastAction] = useState('')
  const compliance = buildComplianceEnrollmentView(null)

  const updateStatus = (caseId, status) => {
    setCases(prev => prev.map(c => (c.id === caseId ? { ...c, status } : c)))
    setLastAction(`Manual update recorded for ${caseId} → ${status}`)
  }

  const cell = { padding: '8px 10px', borderBottom: '1px solid #eef2f9', fontSize: 12, verticalAlign: 'top' }
  const headCell = { ...cell, fontWeight: 900, color: '#244993', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.04em' }

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      {/* Manual bridge banner */}
      <section className="glass panel" style={{ borderLeft: '4px solid #f59e0b' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <ShieldCheck size={20} style={{ color: '#f59e0b', flexShrink: 0, marginTop: 2 }} />
          <div>
            <h3 style={{ margin: '0 0 4px', fontSize: 15 }}>Manual Controlled Bridge — no automated CRJ API</h3>
            <p className="nx-muted" style={{ margin: 0, fontSize: 12, lineHeight: 1.45 }}>
              Nexus analyzes, verifies, and coordinates. CRJ / DisputeForMe performs outsourced dispute services.
              Every provider interaction is recorded manually here until verified API documentation exists.
              No dispute is submitted, mailed, or sent automatically from this portal.
            </p>
          </div>
        </div>
      </section>

      {/* Workflow state chips */}
      <section className="glass panel">
        <h3 style={{ margin: '0 0 10px', fontSize: 15 }}>Internal workflow states</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {FULFILLMENT_WORKFLOW_STATES.map(state => (
            <span key={state} className={`pill pill-${toneForState(state)}`}>{state}</span>
          ))}
        </div>
        <p className="nx-muted" style={{ margin: '10px 0 0', fontSize: 11 }}>
          Client-facing Credit Improvement shows only simplified states (awaiting intake, ready for review, in progress,
          waiting for results, new report needed, results received, verification in progress, round complete).
        </p>
      </section>

      {/* Case table */}
      <section className="glass panel" style={{ overflow: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <h3 style={{ margin: 0, fontSize: 15 }}>Fulfillment cases</h3>
          <span className="pill pill-amber">SYNTHETIC DEMO RECORDS — NO REAL CLIENT PII</span>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 1080 }}>
          <thead>
            <tr>
              {['Case', 'Provider', 'Provider case ID', 'Round', 'Status', 'Submitted', 'Mailed', 'Expected review', 'Missing items', 'Vendor notes', 'SLA', 'Cost', 'Next authorized action'].map(h => (
                <th key={h} style={headCell}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cases.map(c => (
              <tr key={c.id}>
                <td style={cell}><b>{c.clientRef}</b><div className="nx-muted" style={{ fontSize: 10 }}>{c.id}</div></td>
                <td style={cell}>{c.provider}</td>
                <td style={cell}>{c.providerCaseId}</td>
                <td style={cell}>{c.round}</td>
                <td style={cell}>
                  <select
                    value={c.status}
                    onChange={e => updateStatus(c.id, e.target.value)}
                    style={{ border: '1px solid #d7e4ff', borderRadius: 9, padding: '6px 8px', fontSize: 11, fontWeight: 800, background: '#fff', color: '#244993' }}
                  >
                    {FULFILLMENT_WORKFLOW_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td style={cell}>{c.submitted}</td>
                <td style={cell}>{c.mailed}</td>
                <td style={cell}>{c.expectedReview}</td>
                <td style={cell}>{c.missing.length ? c.missing.map(m => <div key={m}>• {m}</div>) : 'None'}</td>
                <td style={cell}>{c.vendorNotes}</td>
                <td style={cell}><span className={`pill pill-${c.sla === 'On track' ? 'green' : 'amber'}`}>{c.sla}</span></td>
                <td style={cell}>{c.cost}</td>
                <td style={cell}>{c.nextAuthorizedAction}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {lastAction && <p style={{ color: '#059669', fontWeight: 800, fontSize: 12, margin: '10px 0 0' }}>✓ {lastAction} (local memory only — persisted CRJ bridge is a later phase)</p>}
        <p className="nx-muted" style={{ margin: '10px 0 0', fontSize: 11 }}>
          Fields tracked per case: internal client ID · provider · provider case ID · current round · submission date ·
          mailing date · expected review date · documents transmitted · missing items · vendor notes · SLA status · cost ·
          next authorized action. Billing review only advances after outcome verification supports the charge.
        </p>
      </section>

      {/* Compliance & enrollment foundation */}
      <section className="glass panel">
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <ClipboardList size={20} style={{ color: '#1768F2', flexShrink: 0, marginTop: 2 }} />
          <div style={{ flex: 1 }}>
            <h3 style={{ margin: '0 0 4px', fontSize: 15 }}>Compliance & Enrollment foundation</h3>
            <p className="nx-muted" style={{ margin: '0 0 12px', fontSize: 12 }}>{COMPLIANCE_FOUNDATION_NOTE}</p>
            <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
              {compliance.disclosures.map(item => (
                <div key={item.key} style={{ border: '1px solid #e3ecfb', borderRadius: 14, background: '#fbfdff', padding: 10, display: 'grid', gap: 4 }}>
                  <b style={{ fontSize: 12 }}>{item.label}</b>
                  <span className={`pill pill-${item.status === 'signed' || item.status === 'provided' || item.status === 'authorized' ? 'green' : 'amber'}`}>{String(item.status).replaceAll('_', ' ')}</span>
                  <small className="nx-muted" style={{ fontSize: 10, lineHeight: 1.4 }}>{item.note}</small>
                </div>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginTop: 10 }}>
              {[
                ['Service agreement', compliance.serviceAgreementVersion ? `v${compliance.serviceAgreementVersion}` : 'No version recorded'],
                ['Cancellation deadline', compliance.cancellationDeadline || 'Not set'],
                ['Cancellation status', compliance.cancellationStatus.replaceAll('_', ' ')],
                ['Marketing source', compliance.marketingSource || 'Not recorded'],
              ].map(([label, value]) => (
                <div key={label} style={{ border: '1px solid #e3ecfb', borderRadius: 14, background: '#fbfdff', padding: 10 }}>
                  <small className="nx-muted" style={{ fontSize: 10, fontWeight: 800 }}>{label}</small>
                  <div style={{ fontSize: 13, fontWeight: 800, color: '#244993', marginTop: 3 }}>{value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="glass panel" style={{ borderLeft: '4px solid #1768F2' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <Send size={20} style={{ color: '#1768F2', flexShrink: 0, marginTop: 2 }} />
          <div>
            <h3 style={{ margin: '0 0 4px', fontSize: 15 }}>Phase boundary</h3>
            <p className="nx-muted" style={{ margin: 0, fontSize: 12, lineHeight: 1.45 }}>
              This sprint ships the <b>manual controlled bridge</b> only. An automated CRJ API connection will not be built
              until verified API documentation exists in the repo and Ray separately approves the integration.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
