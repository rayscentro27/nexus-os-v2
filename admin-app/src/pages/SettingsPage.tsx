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
import { TruthBadge } from '../components/common/TruthBadge';
import { UnavailableState } from '../components/live/UnavailableState';

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'api' | 'general' | 'security' | 'notifications'>('api');


  return (
    <div className="space-y-4 pb-10">
      {/* Clean Executive Header */}
      <header className="bg-white rounded-xl p-4 border border-slate-200/80 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Settings & Integration Registry
            </h1>
            <TruthBadge truth="NOT_CONNECTED" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Persisted provider and workspace settings are not connected.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button type="button" disabled className="px-3 py-1.5 rounded-lg bg-slate-100 text-slate-500 text-xs font-semibold inline-flex items-center gap-1.5 cursor-not-allowed">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Settings unavailable</span>
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
            { id: 'api', label: 'Credentials & Integrations', icon: Key },
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
              </button>
            );
          })}
        </div>

        {/* Right Detail Panel */}
        <div className="lg:col-span-9 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
          <div className="p-4">
            <UnavailableState>Persisted Settings state is not connected. Values shown here are unavailable.</UnavailableState>
          </div>
        </div>
      </div>
    </div>
  );
};
