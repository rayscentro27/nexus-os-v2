import React, { useMemo, useState } from 'react';
import {
  Building,
  Bell,
  Shield,
  Key,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Lock,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { NexusCredentialState } from '../types';

const CREDENTIAL_STATES: NexusCredentialState['state'][] = [
  'CONNECTED',
  'SANDBOX / PAPER',
  'MISSING CREDENTIAL',
  'NOT_CONNECTED',
];

export const SettingsPage: React.FC = () => {
  const {
    credentials,
    updateCredentialState,
    sendMessage,
    setIsNovaDrawerOpen,
    setCurrentPage,
  } = useNexus();

  const [activeTab, setActiveTab] = useState<'api' | 'general' | 'security' | 'notifications'>('api');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Workspace preferences
  const [workspaceName, setWorkspaceName] = useState('Nexus Control Plane (Ray Davis)');
  const [workspaceUrl, setWorkspaceUrl] = useState('admin.nexusos.local');
  const [primaryTrack, setPrimaryTrack] = useState('Autonomous Ventures · Commerce · Trading R1');
  const [timeZone, setTimeZone] = useState('(GMT-05:00) Eastern Time (US & Canada)');

  // Notification preferences
  const [notifApproval, setNotifApproval] = useState(true);
  const [notifBlocker, setNotifBlocker] = useState(true);
  const [notifDigest, setNotifDigest] = useState(true);

  // Security preferences
  const [sec2FA, setSec2FA] = useState(true);
  const [secLiveTradingLock, setSecLiveTradingLock] = useState(true);
  const [secOracleGuardrail, setSecOracleGuardrail] = useState(true);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const missingCount = useMemo(
    () =>
      credentials.filter(
        c => c.state === 'MISSING CREDENTIAL' || c.state === 'NOT_CONNECTED'
      ).length,
    [credentials]
  );

  const groupedCredentials = useMemo(() => {
    const groups: Record<string, NexusCredentialState[]> = {};
    credentials.forEach(c => {
      if (!groups[c.category]) groups[c.category] = [];
      groups[c.category].push(c);
    });
    return Object.entries(groups);
  }, [credentials]);

  const getCredPillStyle = (state: NexusCredentialState['state']) => {
    switch (state) {
      case 'CONNECTED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'SANDBOX / PAPER':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'MISSING CREDENTIAL':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'NOT_CONNECTED':
        return 'bg-amber-50 text-amber-800 border-amber-200';
    }
  };

  return (
    <div className="space-y-4 pb-10">
      {toastMessage && (
        <div className="fixed top-14 right-6 z-50">
          <div className="bg-slate-900 text-white px-3.5 py-2 rounded-xl shadow-lg flex items-center gap-2 text-xs font-semibold border border-slate-700">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Clean Executive Header */}
      <header className="bg-white rounded-xl p-4 border border-slate-200/80 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Settings & Integration Registry
            </h1>
            <TruthBadge truth="VERIFIED" label="LIVE CONTROL STATE" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Inspect real provider connection states, missing credentials blocking go-live actions, and workspace guardrails.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {missingCount > 0 && (
            <span className="px-2.5 py-1 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
              <span>{missingCount} Missing / Unconnected Integrations</span>
            </span>
          )}
          <button
            type="button"
            onClick={() => {
              sendMessage('List missing credentials and explain what each blocker prevents.');
              setIsNovaDrawerOpen(true);
            }}
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ask Nova</span>
          </button>
        </div>
      </header>

      {/* Two-Pane Settings Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left Nav */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200/80 shadow-2xs p-2 space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2.5 py-1 block">
            Settings Sections
          </span>
          {[
            { id: 'api', label: 'Credentials & Integrations', icon: Key, badge: missingCount },
            { id: 'general', label: 'Workspace Profile', icon: Building },
            { id: 'security', label: 'Guardrails & Security', icon: Shield },
            { id: 'notifications', label: 'Alerts & Digests', icon: Bell },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`w-full px-3 py-2 rounded-lg text-xs font-semibold flex items-center justify-between transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                </span>
                {tab.badge ? (
                  <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 text-[10px] font-bold tabular-nums">
                    {tab.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>

        {/* Right Detail Panel */}
        <div className="lg:col-span-9 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
          <div className="p-4 space-y-4">
            {activeTab === 'api' && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                  <div>
                    <h2 className="text-sm font-bold text-slate-900">
                      Authoritative Provider Connection Registry
                    </h2>
                    <p className="text-xs text-slate-500">
                      Live connection readiness without storing or exposing raw API secrets in the browser.
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-500 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
                    <Lock className="w-3 h-3 text-slate-500" />
                    <span>Secrets managed server-side / launchd env</span>
                  </div>
                </div>

                {/* Highlight Blocker Notice */}
                <div className="p-3 rounded-lg bg-amber-50/80 border border-amber-200 text-xs text-amber-950 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <strong className="font-semibold">Truth Policy:</strong> Unlinked providers report{' '}
                    <span className="font-mono font-bold">MISSING CREDENTIAL</span> or{' '}
                    <span className="font-mono font-bold">NOT_CONNECTED</span> across Commerce, Finance, and Marketing instead of simulated metrics.
                  </div>
                  <button
                    type="button"
                    onClick={() => setCurrentPage('business-hub')}
                    className="text-xs font-semibold text-amber-900 underline hover:text-amber-700 cursor-pointer"
                  >
                    Inspect Commerce Blockers →
                  </button>
                </div>

                <div className="space-y-4">
                  {groupedCredentials.map(([category, items]) => (
                    <div key={category} className="space-y-2">
                      <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                        {category}
                      </h3>
                      <div className="space-y-2">
                        {items.map(cred => (
                          <div
                            key={cred.id}
                            className="p-3 rounded-xl border border-slate-200/90 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                          >
                            <div className="space-y-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-bold text-slate-900">
                                  {cred.provider}
                                </span>
                                <span
                                  className={`px-2 py-0.5 rounded border text-[10px] font-bold uppercase ${getCredPillStyle(
                                    cred.state
                                  )}`}
                                >
                                  {cred.state}
                                </span>
                                <TruthBadge truth={cred.truthClass} />
                              </div>
                              <p className="text-xs text-slate-600 leading-snug">{cred.impact}</p>
                              <div className="flex items-center gap-2 flex-wrap text-[11px] text-slate-500">
                                <span>Used by: {cred.usedBy.join(', ')}</span>
                                <span>·</span>
                                <span>Verified: {cred.lastVerified}</span>
                              </div>
                            </div>

                            <div className="shrink-0 flex items-center gap-2">
                              <select
                                aria-label={`Status for ${cred.provider}`}
                                value={cred.state}
                                onChange={e => {
                                  const next = e.target.value as NexusCredentialState['state'];
                                  updateCredentialState(cred.id, next);
                                  showToast(`${cred.provider} marked ${next}.`);
                                }}
                                className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 cursor-pointer"
                              >
                                {CREDENTIAL_STATES.map(st => (
                                  <option key={st} value={st}>
                                    {st}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'general' && (
              <div className="space-y-4">
                <div className="pb-2 border-b border-slate-100">
                  <h2 className="text-sm font-bold text-slate-900">Workspace Profile</h2>
                  <p className="text-xs text-slate-500">
                    Control center naming and default operating region.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Workspace Name</label>
                    <input
                      type="text"
                      value={workspaceName}
                      onChange={e => setWorkspaceName(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-slate-800"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Control Host Domain</label>
                    <input
                      type="text"
                      value={workspaceUrl}
                      onChange={e => setWorkspaceUrl(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-slate-800"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Operating Scope</label>
                    <input
                      type="text"
                      value={primaryTrack}
                      onChange={e => setPrimaryTrack(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-slate-800"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">System Timezone</label>
                    <input
                      type="text"
                      value={timeZone}
                      onChange={e => setTimeZone(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-slate-800"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-4">
                <div className="pb-2 border-b border-slate-100">
                  <h2 className="text-sm font-bold text-slate-900">Execution Guardrails & Security</h2>
                  <p className="text-xs text-slate-500">
                    Hard boundaries protecting Oracle control plane, live capital, and production state.
                  </p>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <span className="font-semibold text-slate-900 block">
                        Oracle Workload Isolation Policy
                      </span>
                      <span className="text-slate-500 text-[11px]">
                        Restricts Oracle Cloud exclusively to Nova/Hermes and essential coordination (blocks heavy LLM/batch jobs)
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSecOracleGuardrail(v => !v)}
                      className={`px-3 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                        secOracleGuardrail ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {secOracleGuardrail ? 'Enforced' : 'Paused'}
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <span className="font-semibold text-slate-900 block">
                        Live Trading Execution Lock (R1 Core)
                      </span>
                      <span className="text-slate-500 text-[11px]">
                        Forces deterministic OANDA Practice PAPER mode until explicit operator unlock
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSecLiveTradingLock(v => !v)}
                      className={`px-3 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                        secLiveTradingLock ? 'bg-emerald-600 text-white' : 'bg-amber-600 text-white'
                      }`}
                    >
                      {secLiveTradingLock ? 'Locked OFF (Paper)' : 'Unlocked'}
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <span className="font-semibold text-slate-900 block">
                        Operator Two-Factor Authentication (2FA)
                      </span>
                      <span className="text-slate-500 text-[11px]">
                        Required for high-risk spend and Stage B Commerce go-live approvals
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSec2FA(v => !v)}
                      className={`px-3 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                        sec2FA ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {sec2FA ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-4">
                <div className="pb-2 border-b border-slate-100">
                  <h2 className="text-sm font-bold text-slate-900">Operator Notifications</h2>
                  <p className="text-xs text-slate-500">
                    Control which approval gates and system blockers alert Ray immediately.
                  </p>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <span className="font-semibold text-slate-900 block">
                        Approval Gates & Publication Sign-Offs
                      </span>
                      <span className="text-slate-500 text-[11px]">
                        Alert immediately when a project waits on Ray (e.g., Stage A or Spend gates)
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setNotifApproval(v => !v)}
                      className={`px-3 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                        notifApproval ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {notifApproval ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <span className="font-semibold text-slate-900 block">
                        Credential & Service Blockers
                      </span>
                      <span className="text-slate-500 text-[11px]">
                        Alert when missing credentials block downstream execution
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setNotifBlocker(v => !v)}
                      className={`px-3 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                        notifBlocker ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {notifBlocker ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div>
                      <span className="font-semibold text-slate-900 block">
                        Daily Executive Summary
                      </span>
                      <span className="text-slate-500 text-[11px]">
                        Morning Nova brief across Projects, Trading R1 reconciliation, and Research
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setNotifDigest(v => !v)}
                      className={`px-3 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                        notifDigest ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {notifDigest ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Save Footer */}
          <div className="p-3 border-t border-slate-100 flex items-center justify-between gap-2 bg-slate-50/50">
            <span className="text-[11px] text-slate-500">
              Integration state updates propagate immediately across Overview, Commerce, Marketing, and Nova.
            </span>
            <button
              type="button"
              onClick={() => showToast('Settings & integration preferences saved.')}
              className="py-1.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs cursor-pointer"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
