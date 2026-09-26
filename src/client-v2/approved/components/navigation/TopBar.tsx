import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { TabType } from '../../types/portal';

export const TopBar: React.FC = () => {
  const { activeTab, setActiveTab, setIsClydeOpen, isClydeOpen, profile } = usePortal();

  const navLinks: { label: string; tab: TabType }[] = [
    { label: 'Command', tab: 'dashboard' },
    { label: 'Credit', tab: 'credit-profile' },
    { label: 'Utilization', tab: 'credit-utilization' },
    { label: 'Vault', tab: 'documents' },
    { label: 'Bankability', tab: 'business-bankability' },
    { label: 'Funding', tab: 'funding-readiness' }
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200/80 bg-white/95 backdrop-blur-md shadow-xs">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Zone 1: Single Text Element Wordmark */}
        <a
          href="#dashboard"
          onClick={(e) => {
            e.preventDefault();
            setActiveTab('dashboard');
          }}
          className="text-lg font-black tracking-tight text-slate-900 flex items-center gap-2 group cursor-pointer"
        >
          <span className="w-2.5 h-2.5 rounded-full bg-[#00D2B4] shadow-[0_0_10px_rgba(0,210,180,0.6)]" />
          <span>GoClear</span>
          <span className="text-[11px] font-bold text-teal-700 tracking-wider uppercase ml-1 opacity-90">
            Ascent
          </span>
        </a>

        {/* Zone 2: 4-6 Clean Text Nav Links */}
        <nav className="hidden md:flex items-center gap-6 lg:gap-8 text-xs font-semibold">
          {navLinks.map((link) => {
            const isActive = activeTab === link.tab;
            return (
              <button
                key={link.tab}
                onClick={() => setActiveTab(link.tab)}
                className={`transition-colors whitespace-nowrap py-1 relative cursor-pointer ${
                  isActive
                    ? 'text-teal-700 font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {link.label}
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-teal-500 to-sky-500 rounded-full" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Zone 3: 1-2 Primary Actions with Clean Light Highlights */}
        <div className="flex items-center gap-2.5">
          {/* Clyde Copilot Button (Clean Light Highlight) */}
          <button
            onClick={() => setIsClydeOpen(!isClydeOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-teal-800 text-xs font-semibold transition-all shadow-xs active:scale-95 cursor-pointer"
            title="Open Clyde AI Financial Copilot"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-ping" />
            <span className="whitespace-nowrap">Ask Clyde AI</span>
          </button>

          {/* Underwriter Review Request CTA */}
          <button
            onClick={() => setActiveTab('request-review')}
            className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 text-white font-bold text-xs transition-all shadow-sm active:scale-95 whitespace-nowrap cursor-pointer"
          >
            Request Review
          </button>

          {/* Client Avatar (David Vance) */}
          <button
            onClick={() => setActiveTab('credit-profile')}
            className="relative ml-0.5 w-8 h-8 rounded-full ring-2 ring-teal-500/40 overflow-hidden shrink-0 hover:ring-teal-400 transition-all cursor-pointer"
            title={`${profile.name} · ${profile.companyName}`}
          >
            <img
              src={profile.avatarUrl}
              alt={profile.name}
              referrerPolicy="no-referrer"
              className="w-full h-full object-cover"
            />
          </button>
        </div>
      </div>
    </header>
  );
};
