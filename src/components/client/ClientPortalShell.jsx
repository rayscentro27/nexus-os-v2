import React, { createContext, useContext, useEffect, useState } from 'react'
import {
  BadgeCheck, Bell, Building2, ChartNoAxesCombined, ChevronDown, FileText,
  Gauge, Home, Mail, Menu, Settings, Sparkles, UserRound, X, CircleCheck,
  Landmark, Lightbulb, MessageSquare, Star, Wallet, LogOut, CreditCard,
  Send, HelpCircle, User,
} from 'lucide-react'
import { clientPortalData } from '../../data/clientPortalData'
import { clientDataMode, shouldShowInternalDataBadge } from '../../data/clientDataMode'
import { supabase } from '../../lib/supabaseClient'
import { generateClientGuidance } from '../../clientPortal/clientGuidance'
import { loadClientPortalLiveData, loadClientProfileIntake, checkProfileIntakeComplete } from '../../lib/clientPortalDataAdapter'

export const PortalNavContext = createContext(() => {})
export const PortalLiveStatusContext = createContext({ status: 'idle', setStatus: () => {} })
export function usePortalNav() { return useContext(PortalNavContext) }
export function usePortalLiveStatus() { return useContext(PortalLiveStatusContext) }

export const journeySteps = [
  { path: '/client/dashboard', label: 'Home', icon: Home },
  { path: '/client/profile', label: 'Profile & Info', icon: User },
  { path: '/client/credit-profile', label: 'Credit Profile', icon: BadgeCheck },
  { path: '/client/credit-utilization', label: 'Credit Utilization', icon: Gauge },
  { path: '/client/documents', label: 'Documents', icon: FileText },
  { path: '/client/business-setup', label: 'Business Setup', icon: Building2 },
  { path: '/client/business-bankability', label: 'Business Bankability', icon: Landmark },
  { path: '/client/funding-readiness', label: 'Funding Readiness', icon: Wallet },
  { path: '/client/recommendations', label: 'Recommendations', icon: Lightbulb },
  { path: '/client/resources', label: 'Resources', icon: Star },
  { path: '/client/request-review', label: 'Request Review', icon: MessageSquare },
]

export const clientRoutes = journeySteps

function getJourneyProgress(path) {
  const idx = journeySteps.findIndex(s => s.path === path)
  return idx >= 0 ? idx + 1 : 1
}

export function ClientSidebar({ path, onNavigate }) {
  const profile = clientPortalData.clientProfile
  const { status: liveStatus = 'idle' } = usePortalLiveStatus()
  const liveStatusLabel = liveStatus === 'connected' ? 'Live data connected' : liveStatus === 'loading' ? 'Live data pending' : 'Demo/fallback data'
  return (
    <aside className="client-sidebar">
      <div className="client-sidebar-brand">
        <div className="client-logo-n" />
        <div><strong>Nexus</strong></div>
      </div>

      <nav className="client-sidebar-nav" aria-label="Client journey navigation">
        {journeySteps.map((step, i) => {
          const Icon = step.icon
          const isActive = path === step.path
          const isPast = journeySteps.findIndex(s => s.path === path) > i
          return (
            <button
              key={step.path}
              className={`client-sidebar-item ${isActive ? 'active' : ''} ${isPast ? 'past' : ''}`}
              onClick={() => onNavigate(step.path)}
            >
              <span className="client-sidebar-icon">
                {isPast ? <CircleCheck size={18} /> : <Icon size={18} />}
              </span>
              <span className="client-sidebar-label">{step.label}</span>
              {step.label === 'Messages' && <span className="client-sidebar-badge">2</span>}
            </button>
          )
        })}
      </nav>

      <div className="client-sidebar-footer">
        <button className="client-sidebar-item" onClick={async () => { await supabase?.auth.signOut(); window.location.assign('/client/login'); }}>
          <span className="client-sidebar-icon"><LogOut size={18} /></span>
          <span className="client-sidebar-label">Sign Out</span>
        </button>
        {shouldShowInternalDataBadge && (
          <div className="client-sidebar-data-badge" title={`Portal data mode: ${liveStatusLabel}`}>
            <span className="client-sidebar-data-badge-dot" />
            <span className="client-sidebar-data-badge-label">{liveStatusLabel}</span>
          </div>
        )}
      </div>
    </aside>
  )
}

export function ClientHeader({ path, onNavigate, onMenuToggle }) {
  const profile = clientPortalData.clientProfile
  const step = getJourneyProgress(path)
  return (
    <header className="client-header-premium">
      <div className="client-header-left">
        <button className="client-menu" aria-label="Menu" onClick={onMenuToggle} style={{ display: 'none' }}><Menu size={20} /></button>
        <div className="client-brand-mark">
          <div className="client-logo-n" />
          <div><strong>NEXUS</strong><span>CLIENT PORTAL</span></div>
        </div>
      </div>
      <div className="client-header-right">
        <span className="client-step-badge">Step {step}/10</span>
        <span className="client-membership-badge">{profile.membershipTier}</span>
        <button className="client-icon-btn" aria-label="Notifications" onClick={() => onNavigate('/client/resources')}><Bell size={18} /><em>2</em></button>
        <button className="client-icon-btn" aria-label="Messages" onClick={() => onNavigate('/client/resources')}><Mail size={18} /></button>
        <button className="client-icon-btn" aria-label="Help" onClick={() => onNavigate('/client/resources')}><HelpCircle size={18} /></button>
        <div className="client-avatar-sm">
          <span>{profile.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || 'U'}</span>
        </div>
      </div>
    </header>
  )
}

export function HermesGuidancePanel({ path, statuses }) {
  const guidance = getGuidanceForStep(path)
  const dynamicItems = statuses ? generateClientGuidance(statuses) : []
  return (
    <aside className="client-hermes-panel">
      <div className="client-hermes-header">
        <div className="client-hermes-avatar"><Sparkles size={22} /></div>
        <div><strong>Hermes Guidance</strong><span className="client-hermes-advisory">Advisory only — not a decision</span></div>
      </div>
      <div className="client-hermes-body">
        {dynamicItems.length > 0 ? (
          <>
            <div className="client-hermes-section">
              <strong>Your Priority Actions</strong>
              <ul>{dynamicItems.slice(0, 5).map(item => (
                <li key={item.id} style={{ marginBottom: 6 }}>
                  <strong style={{ color: item.priority === 'high' ? '#f59e0b' : item.priority === 'medium' ? '#3b82f6' : '#9ca3af' }}>{item.title}</strong>
                  <p style={{ margin: '2px 0 0', fontSize: 12, color: '#8fa3be' }}>{item.description}</p>
                </li>
              ))}</ul>
            </div>
          </>
        ) : (
          <>
            <div className="client-hermes-section">
              <strong>Current Step</strong>
              <p>{guidance.currentStep}</p>
            </div>
            <div className="client-hermes-section">
              <strong>What to do next</strong>
              <p>{guidance.nextAction}</p>
            </div>
            {guidance.missingItems.length > 0 && (
              <div className="client-hermes-section">
                <strong>Missing items</strong>
                <ul>{guidance.missingItems.map((item, i) => <li key={i}>{item}</li>)}</ul>
              </div>
            )}
            <div className="client-hermes-section">
              <strong>Readiness note</strong>
              <p>{guidance.readinessNote}</p>
            </div>
          </>
        )}
      </div>
      <div className="client-hermes-footer">
        <span className="client-safe-note">Hermes guidance is advisory. GoClear review is required before any application or external action.</span>
      </div>
    </aside>
  )
}

function getGuidanceForStep(path) {
  const map = {
    '/client/dashboard': {
      currentStep: 'Home — Your readiness overview',
      nextAction: 'Review your overall readiness score and complete the highest-priority open tasks.',
      missingItems: ['Upload current address proof', 'Complete professional domain email'],
      readinessNote: 'You are building momentum. Focus on the top two tasks this week.',
    },
    '/client/credit-profile': {
      currentStep: 'Credit Profile — Educational readiness score',
      nextAction: 'Review score factors and reduce utilization where practical.',
      missingItems: ['Utilization above target', 'Recent inquiries need time'],
      readinessNote: 'This is an educational readiness measure, not a FICO score.',
    },
    '/client/credit-utilization': {
      currentStep: 'Credit Utilization — Balance management',
      nextAction: 'Review revolving balances and create a pay-down plan.',
      missingItems: ['Current revolving balances not yet uploaded'],
      readinessNote: 'Lower utilization may improve funding readiness.',
    },
    '/client/documents': {
      currentStep: 'Documents — Upload and track readiness files',
      nextAction: 'Upload the two missing documents: address proof and revenue summary.',
      missingItems: ['Current address proof', 'Revenue summary'],
      readinessNote: 'Documents are required before GoClear review.',
    },
    '/client/business-setup': {
      currentStep: 'Business Setup — Entity and profile building',
      nextAction: 'Complete the professional domain email and verify entity records.',
      missingItems: ['Professional domain email', 'DUNS/bureau profile'],
      readinessNote: 'A consistent business profile improves review quality.',
    },
    '/client/business-bankability': {
      currentStep: 'Business Bankability — Banking and revenue readiness',
      nextAction: 'Open a business bank account and document the relationship.',
      missingItems: ['Business bank account', 'Revenue documentation'],
      readinessNote: 'Banking relationships support funding readiness.',
    },
    '/client/funding-readiness': {
      currentStep: 'Funding Readiness — Application readiness check',
      nextAction: 'Resolve the remaining blockers before requesting GoClear review.',
      missingItems: ['Utilization target', 'DUNS profile', 'Vendor accounts'],
      readinessNote: 'Avoid applying while blockers remain. GoClear review is required.',
    },
    '/client/recommendations': {
      currentStep: 'Recommendations — Matched paths and options',
      nextAction: 'Review the recommended paths matched to your current readiness.',
      missingItems: [],
      readinessNote: 'Recommendations are educational. No path is guaranteed.',
    },
    '/client/resources': {
      currentStep: 'Resources & Affiliates — Tools and services',
      nextAction: 'Review free and paid options for credit monitoring, mailing, and banking.',
      missingItems: [],
      readinessNote: 'Free options are listed first. Affiliate relationships are disclosed.',
    },
    '/client/request-review': {
      currentStep: 'Request Review — Submit for GoClear review',
      nextAction: 'Complete all open tasks, then request review.',
      missingItems: ['Complete open tasks before requesting'],
      readinessNote: 'Review requests are processed in order. Response time varies.',
    },
  }
  return map[path] || map['/client/dashboard']
}

export function ClientMobileSidebar({ path, onNavigate, open, onClose }) {
  return (
    <>
      <aside className={`client-sidebar-mobile ${open ? 'open' : ''}`}>
        <div className="client-brand">
          <div className="client-logo-n" />
          <div><strong>NEXUS</strong><span>CLIENT PORTAL</span></div>
          <button className="client-mobile-close" onClick={onClose} aria-label="Close"><X size={20} /></button>
        </div>
        <nav className="client-nav-list">
          {journeySteps.map(step => {
            const Icon = step.icon
            return (
              <button key={step.path} className={path === step.path ? 'active' : ''} onClick={() => { onNavigate(step.path); onClose() }}>
                <Icon size={18} /><span>{step.label}</span>
              </button>
            )
          })}
        </nav>
      </aside>
      {open && <button className="client-overlay" onClick={onClose} aria-label="Close overlay" />}
    </>
  )
}

export function ClientPortalShell({ path, onNavigate, children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [liveStatus, setLiveStatus] = useState('idle')
  const [livePortalData, setLivePortalData] = useState(null)
  const [profileIncomplete, setProfileIncomplete] = useState(false)
  useEffect(() => setMobileOpen(false), [path])

  useEffect(() => {
    if (!clientDataMode.liveSupabaseTestClientEnabled) return
    let cancelled = false
    loadClientPortalLiveData().then(result => {
      if (!cancelled && result.profile) {
        setLivePortalData(result)
        setLiveStatus('connected')
      }
    }).catch(() => {})
    loadClientProfileIntake().then(result => {
      if (!cancelled && result.source === 'supabase') {
        const check = checkProfileIntakeComplete(result.data)
        if (!check.complete) setProfileIncomplete(true)
      }
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  const docs = livePortalData?.documents || clientPortalData.documents
  const readiness = livePortalData?.scores?.reduce((acc, s) => {
    const key = s.score_type || s.category
    if (key) acc[key] = Number(s.score ?? 0)
    return acc
  }, {}) || clientPortalData.readinessScores
  const statuses = {
    creditReportUploaded: docs.uploadedDocuments?.some(d => /credit|report/i.test(d)) || false,
    addressVerified: docs.uploadedDocuments?.some(d => /address/i.test(d)) || false,
    identityVerified: docs.uploadedDocuments?.some(d => /id|identity|government/i.test(d)) || false,
    utilizationHigh: (readiness?.creditProfileReadiness || 0) < 60,
    negativeItemsIdentified: (readiness?.creditRepairProgress || 0) < 50,
    businessBankAccount: docs.uploadedDocuments?.some(d => /bank/i.test(d)) || false,
    revenueDocuments: docs.uploadedDocuments?.some(d => /revenue|statement/i.test(d)) || false,
    documentsComplete: docs.missingDocuments?.length === 0,
    adminReviewRequired: docs.underReviewDocuments?.length > 0,
    readinessScore: readiness?.fundingReadiness || 68,
    profileIncomplete,
  }

  const liveStatusLabel = liveStatus === 'connected' ? 'Live data connected' : liveStatus === 'loading' ? 'Live data pending' : 'Demo/fallback data'

  return (
    <PortalNavContext.Provider value={onNavigate}>
      <PortalLiveStatusContext.Provider value={{ status: liveStatus, setStatus: setLiveStatus }}>
        <div className="client-portal-premium">
          <ClientHeader path={path} onNavigate={onNavigate} onMenuToggle={() => setMobileOpen(true)} />
          <div className="client-portal-body">
            <ClientSidebar path={path} onNavigate={onNavigate} />
            <main className="client-main-content">{children}</main>
            <HermesGuidancePanel path={path} statuses={statuses} />
          </div>
          <ClientMobileSidebar path={path} onNavigate={onNavigate} open={mobileOpen} onClose={() => setMobileOpen(false)} />
        </div>
      </PortalLiveStatusContext.Provider>
    </PortalNavContext.Provider>
  )
}
