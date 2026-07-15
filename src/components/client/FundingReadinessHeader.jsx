import React from 'react'
import { getStageIndex } from '../../lib/clientJourneyModel'

const STAGE_ICONS = {
  credit_profile: '📋',
  credit_improvement: '📈',
  business_foundation: '🏢',
  business_bankability: '🏦',
  funding_readiness: '💰',
  review_plan: '✅',
}

const STATUS_COLORS = {
  complete: '#10b981',
  ready_to_review: '#3b82f6',
  in_progress: '#f59e0b',
  action_needed: '#f97316',
  not_started: '#6b7280',
  blocked: '#ef4444',
  insufficient_information: '#a855f7',
}

export function FundingReadinessHeader({ journey, onNavigate }) {
  const currentStage = journey.stages[journey.currentStage]
  const color = STATUS_COLORS[currentStage?.status] || '#6b7280'

  return (
    <div style={{
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
      border: '1px solid #334155',
      borderRadius: 12,
      padding: '12px 20px',
      marginBottom: 16,
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      flexWrap: 'wrap',
    }}>
      {/* Score */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{
          width: 44, height: 44, borderRadius: '50%',
          background: `conic-gradient(${color} ${journey.overallScore * 3.6}deg, #1e293b 0deg)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%', background: '#0f172a',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#f8fafc', fontSize: 13, fontWeight: 700,
          }}>
            {journey.overallScore}
          </div>
        </div>
        <div>
          <div style={{ color: '#94a3b8', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Funding Readiness</div>
          <div style={{ color: '#f8fafc', fontSize: 13, fontWeight: 600 }}>{currentStage?.displayName || 'Getting Started'}</div>
        </div>
      </div>

      {/* Progress dots */}
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        {(['credit_profile', 'credit_improvement', 'business_foundation', 'business_bankability', 'funding_readiness', 'review_plan']).map((sid) => {
          const stage = journey.stages[sid]
          const isActive = sid === journey.currentStage
          const isPast = getStageIndex(sid) < getStageIndex(journey.currentStage)
          const c = STATUS_COLORS[stage?.status] || '#6b7280'
          return (
            <div
              key={sid}
              title={`${stage?.displayName}: ${stage?.status?.replace(/_/g, ' ')}`}
              style={{
                width: isActive ? 24 : 10,
                height: 10,
                borderRadius: 5,
                background: isPast || stage?.status === 'complete' ? '#10b981' : isActive ? c : '#334155',
                transition: 'all 0.2s',
                cursor: 'pointer',
              }}
              onClick={() => onNavigate(stage?.nextActionRoute || '/client/dashboard')}
            />
          )
        })}
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 16, marginLeft: 'auto', fontSize: 12 }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ color: '#10b981', fontWeight: 700, fontSize: 16 }}>{journey.completedCount}</div>
          <div style={{ color: '#64748b', fontSize: 10 }}>Done</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ color: '#f59e0b', fontWeight: 700, fontSize: 16 }}>{journey.totalCount - journey.completedCount}</div>
          <div style={{ color: '#64748b', fontSize: 10 }}>Remaining</div>
        </div>
      </div>

      {/* Primary blocker or next action */}
      <div style={{ flexBasis: '100%', display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
        {journey.primaryBlocker ? (
          <span style={{ color: '#ef4444', fontSize: 12 }}>⚠ {journey.primaryBlocker}</span>
        ) : (
          <span style={{ color: '#94a3b8', fontSize: 12 }}>Next: {journey.nextBestAction}</span>
        )}
        <button
          onClick={() => onNavigate(journey.nextBestActionRoute)}
          style={{
            marginLeft: 'auto', padding: '4px 12px', borderRadius: 6,
            background: color, color: '#fff', border: 'none',
            fontSize: 11, fontWeight: 600, cursor: 'pointer',
          }}
        >
          Continue →
        </button>
      </div>
    </div>
  )
}
