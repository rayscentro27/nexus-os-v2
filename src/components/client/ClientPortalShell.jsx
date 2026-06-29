import React, { useEffect, useState } from 'react'
import {
  BadgeCheck, Bell, Building2, ChartNoAxesCombined, ChevronDown, FileText,
  Gauge, Home, Mail, Menu, Settings, Sparkles, UserRound, X,
} from 'lucide-react'
import { clientPortalData } from '../../data/clientPortalData'

export const clientRoutes = [
  { path: '/client/dashboard', label: 'Dashboard', icon: Home },
  { path: '/client/credit-repair', label: 'Credit Repair', icon: Gauge },
  { path: '/client/credit-profile-readiness', label: 'Credit Profile Readiness', icon: BadgeCheck },
  { path: '/client/business-profile-readiness', label: 'Business Profile Readiness', icon: Building2 },
  { path: '/client/business-opportunities', label: 'Business Opportunities', icon: ChartNoAxesCombined },
  { path: '/client/funding-readiness', label: 'Funding Readiness', icon: ChartNoAxesCombined },
  { path: '/client/documents', label: 'Documents', icon: FileText },
  { path: '/client/messages', label: 'Messages', icon: Mail, badge: 2 },
  { path: '/client/settings', label: 'Settings', icon: Settings },
]

export function ClientSidebar({ path, onNavigate, mobileOpen, onClose }) {
  return (
    <aside className={`client-sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="client-brand">
        <div className="client-logo-n" />
        <div><strong>NEXUS</strong><span>CLIENT PORTAL</span></div>
        <button className="client-mobile-close" onClick={onClose} aria-label="Close navigation"><X size={20} /></button>
      </div>
      <nav className="client-nav-list" aria-label="Client portal navigation">
        {clientRoutes.map(item => {
          const Icon = item.icon
          return (
            <button key={item.path} className={path === item.path ? 'active' : ''} onClick={() => onNavigate(item.path)}>
              <Icon size={19} /><span>{item.label}</span>{item.badge && <em>{item.badge}</em>}
            </button>
          )
        })}
      </nav>
      <div className="client-help-card">
        <Sparkles size={24} />
        <strong>Need a reviewed answer?</strong>
        <p>Nexus Guide can explain approved portal data or show what needs GoClear review.</p>
      </div>
    </aside>
  )
}

export function ClientTopBar({ onMenu }) {
  const profile = clientPortalData.clientProfile
  return (
    <header className="client-topbar">
      <button className="client-menu" onClick={onMenu} aria-label="Open navigation"><Menu size={21} /></button>
      <div className="client-welcome">Welcome back, {profile.name.replace(' (Demo)', '')} <span>Demo portal</span></div>
      <div className="client-top-actions">
        <a href="/" className="client-admin-link">Admin sign-in</a>
        <button className="client-icon-button" aria-label="Notifications"><Bell size={21} /><em>2</em></button>
        <div className="client-avatar"><UserRound size={21} /></div>
        <div className="client-profile-copy"><strong>{profile.name}</strong><span>{profile.membershipTier}</span></div>
        <ChevronDown size={16} />
      </div>
    </header>
  )
}

export function ClientPortalShell({ path, onNavigate, children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  useEffect(() => setMobileOpen(false), [path])
  return (
    <div className="client-portal">
      <ClientSidebar path={path} onNavigate={onNavigate} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <main className="client-main-shell">
        <ClientTopBar onMenu={() => setMobileOpen(true)} />
        <div className="client-page-content">{children}</div>
      </main>
      {mobileOpen && <button className="client-overlay" onClick={() => setMobileOpen(false)} aria-label="Close navigation overlay" />}
    </div>
  )
}
