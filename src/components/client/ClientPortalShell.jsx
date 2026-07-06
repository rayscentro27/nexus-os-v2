import React, { useEffect, useState } from 'react'
import {
  BadgeCheck, Bell, Building2, ChartNoAxesCombined, ChevronDown, FileText,
  Gauge, Home, Mail, Menu, Settings, Sparkles, UserRound, X, CircleCheck,
  Landmark, Lightbulb, MessageSquare, Star, Wallet, LogOut,
} from 'lucide-react'
import { clientPortalData } from '../../data/clientPortalData'
import { clientDataMode, shouldShowInternalDataBadge } from '../../data/clientDataMode'
import { supabase } from '../../lib/supabaseClient'

export const journeySteps = [
  { path: '/client/dashboard', label: 'Home', icon: Home },
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

export function ClientTopNav({ path, onNavigate }) {
  return (
    <nav className="client-topnav" aria-label="Client journey navigation">
      {journeySteps.map((step, i) => {
        const Icon = step.icon
        const isActive = path === step.path
        const isPast = journeySteps.findIndex(s => s.path === path) > i
        return (
          <button key={step.path} className={`client-topnav-item ${isActive ? 'active' : ''} ${isPast ? 'past' : ''}`} onClick={() => onNavigate(step.path)}>
            <span className="client-topnav-num">{isPast ? <CircleCheck size={14} /> : i + 1}</span>
            <span className="client-topnav-label">{step.label}</span>
          </button>
        )
      })}
    </nav>
  )
}

export function ClientHeader({ path, onNavigate, onMenu }) {
  const profile = clientPortalData.clientProfile
  const step = getJourneyProgress(path)
  return (
    <header className="client-header">
      <div className="client-header-left">
        <button className="client-menu" onClick={onMenu} aria-label="Open navigation"><Menu size={21} /></button>
        <div className="client-brand-mark">
          <div className="client-logo-n" />
          <div><strong>NEXUS</strong><span>CLIENT PORTAL</span></div>
        </div>
      </div>
      <ClientTopNav path={path} onNavigate={onNavigate} />
      <div className="client-header-right">
        <span className="client-journey-badge">Step {step}/10</span>
        <span className="client-access-badge">{profile.membershipTier}</span>
        <button className="client-request-review-btn" onClick={() => onNavigate('/client/request-review')}>Request Review</button>
        <button className="client-icon-button" aria-label="Notifications"><Bell size={18} /><em>2</em></button>
        <button className="client-icon-button" aria-label="Sign out" onClick={async () => { await supabase?.auth.signOut(); window.location.assign('/goclear/login'); }}><LogOut size={18} /></button>
        <div className="client-avatar"><UserRound size={18} /></div>
      </div>
    </header>
  )
}

export function HermesGuidancePanel({ path }) {
  const guidance = getGuidanceForStep(path)
  return (
    <aside className="client-hermes-panel">
      <div className="client-hermes-header">
        <div className="client-hermes-avatar"><Sparkles size={22} /></div>
        <div><strong>Hermes Guidance</strong><span className="client-hermes-advisory">Advisory only — not a decision</span></div>
      </div>
      <div className="client-hermes-body">
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
  useEffect(() => setMobileOpen(false), [path])
  return (
    <div className="client-portal-premium">
      <ClientHeader path={path} onNavigate={onNavigate} onMenu={() => setMobileOpen(true)} />
      <div className="client-portal-body">
        <main className="client-main-content">{children}</main>
        <HermesGuidancePanel path={path} />
      </div>
      <ClientMobileSidebar path={path} onNavigate={onNavigate} open={mobileOpen} onClose={() => setMobileOpen(false)} />
    </div>
  )
}
