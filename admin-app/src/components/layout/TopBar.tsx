import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  Search,
  Bell,
  ChevronDown,
  Plus,
  Sparkles,
  Menu,
  X,
  AlertTriangle,
  FolderKanban,
  CheckSquare,
  Target,
  Palette,
  ShoppingBag,
  FileSearch,
  TrendingUp,
  Server,
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';
import { UserAvatar } from '../common/UserAvatar';
import { TruthBadge } from '../common/TruthBadge';
import { PageId } from '../../types';
import { INITIAL_STRATEGIES } from '../../data/tradingEngineData';

interface TopBarProps {
  onToggleMobileNav?: () => void;
}

const PAGE_LABELS: Record<PageId, string> = {
  'command-center': 'Overview',
  approvals: 'Approvals',
  projects: 'Projects',
  research: 'Research',
  marketing: 'Marketing',
  campaigns: 'Campaigns',
  creative: 'Creative',
  'business-hub': 'Commerce',
  finance: 'Finance',
  'trading-engine': 'Trading',
  systems: 'Systems',
  nova: 'Nova',
  clients: 'Clients',
  documents: 'Documents',
  'development-labs': 'Development / Labs',
  'upgrade-control': 'Upgrade Control',
  settings: 'Settings',
  operations: 'Systems',
  'existing-business': 'Existing Business Center',
  rea: 'REA Workspace',
};

export const TopBar: React.FC<TopBarProps> = ({ onToggleMobileNav }) => {
  const {
    currentPage,
    searchQuery,
    setSearchQuery,
    setIsNewProjectModalOpen,
    pendingApprovalsCount,
    setIsNeedsRayDrawerOpen,
    notifications,
    unreadNotificationsCount,
    markNotificationRead,
    markAllNotificationsRead,
    navigateToObject,
    isNovaDrawerOpen,
    setIsNovaDrawerOpen,
    projects,
    approvals,
    campaigns,
    creativeAssets,
    commerceOffers,
    researchFindings,
    distributedSystems,
  } = useNexus();

  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  const searchRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchFocused(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];

    const items: {
      id: string;
      category: string;
      title: string;
      meta: string;
      page: PageId;
      kind?: 'approval' | 'project' | 'campaign' | 'asset' | 'offer';
      icon: React.ComponentType<{ className?: string }>;
    }[] = [];

    projects.forEach(p => {
      if (
        p.name.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q) ||
        (p.ventureId && p.ventureId.toLowerCase().includes(q)) ||
        (p.opportunityId && p.opportunityId.toLowerCase().includes(q))
      ) {
        items.push({
          id: p.id,
          category: 'Project',
          title: p.name,
          meta: `${p.id} · ${p.currentDepartment} · ${p.status}`,
          page: 'projects',
          kind: 'project',
          icon: FolderKanban,
        });
      }
    });

    approvals.forEach(a => {
      if (
        a.title.toLowerCase().includes(q) ||
        a.id.toLowerCase().includes(q) ||
        a.projectName.toLowerCase().includes(q) ||
        a.type.toLowerCase().includes(q)
      ) {
        items.push({
          id: a.id,
          category: 'Approval',
          title: a.title,
          meta: `${a.id} · ${a.type} · ${a.status}`,
          page: 'approvals',
          kind: 'approval',
          icon: CheckSquare,
        });
      }
    });

    campaigns.forEach(c => {
      if (
        c.name.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q) ||
        c.projectName.toLowerCase().includes(q)
      ) {
        items.push({
          id: c.id,
          category: 'Campaign',
          title: c.name,
          meta: `${c.projectName} · ${c.approvalStatus}`,
          page: 'campaigns',
          kind: 'campaign',
          icon: Target,
        });
      }
    });

    creativeAssets.forEach(ast => {
      if (
        ast.title.toLowerCase().includes(q) ||
        ast.id.toLowerCase().includes(q) ||
        ast.campaign_name.toLowerCase().includes(q)
      ) {
        items.push({
          id: ast.id,
          category: 'Creative Asset',
          title: ast.title,
          meta: `${ast.asset_type} · ${ast.approval_state}`,
          page: 'creative',
          kind: 'asset',
          icon: Palette,
        });
      }
    });

    commerceOffers.forEach(off => {
      if (
        off.title.toLowerCase().includes(q) ||
        off.externalProductId.toLowerCase().includes(q) ||
        off.variantId.toLowerCase().includes(q)
      ) {
        items.push({
          id: off.id,
          category: 'Commerce',
          title: off.title,
          meta: `Printify ${off.externalProductId} · ${off.interestTest.mode}`,
          page: 'business-hub',
          kind: 'offer',
          icon: ShoppingBag,
        });
      }
    });

    researchFindings.forEach(r => {
      if (r.title.toLowerCase().includes(q) || r.recommendation.toLowerCase().includes(q)) {
        items.push({
          id: r.id,
          category: 'Research',
          title: r.title,
          meta: `${r.sourceType} · ${r.confidence}`,
          page: 'research',
          icon: FileSearch,
        });
      }
    });

    INITIAL_STRATEGIES.forEach(s => {
      if (s.name.toLowerCase().includes(q) || s.universe.toLowerCase().includes(q)) {
        items.push({
          id: s.id,
          category: 'Trading Strategy',
          title: s.name,
          meta: `${s.universe} · ${s.timeframe} · ${s.stage}`,
          page: 'trading-engine',
          icon: TrendingUp,
        });
      }
    });

    distributedSystems.forEach(sys => {
      if (
        sys.name.toLowerCase().includes(q) ||
        sys.role.toLowerCase().includes(q) ||
        (sys.blocker && sys.blocker.toLowerCase().includes(q))
      ) {
        items.push({
          id: sys.id,
          category: 'System',
          title: sys.name,
          meta: `${sys.status} · ${sys.role}`,
          page: 'systems',
          icon: Server,
        });
      }
    });

    return items.slice(0, 12);
  }, [
    searchQuery,
    projects,
    approvals,
    campaigns,
    creativeAssets,
    commerceOffers,
    researchFindings,
    distributedSystems,
  ]);

  return (
    <header className="h-14 bg-white border-b border-slate-200/80 px-4 sm:px-6 flex items-center justify-between gap-4 sticky top-0 z-20 shrink-0">
      {/* Left: Mobile Menu + Current Page Title + Global Entity Search */}
      <div className="flex items-center gap-3 flex-1 min-w-0 max-w-2xl">
        <button
          type="button"
          onClick={onToggleMobileNav}
          className="lg:hidden p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors cursor-pointer"
          title="Open Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <span className="hidden sm:inline-block text-sm font-bold text-slate-900 whitespace-nowrap shrink-0 pr-2 border-r border-slate-200">
          {PAGE_LABELS[currentPage] || 'Nexus'}
        </span>

        {/* Global Search Input + Live Results Dropdown */}
        <div className="relative flex-1 min-w-0" ref={searchRef}>
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onFocus={() => setSearchFocused(true)}
            onChange={e => {
              setSearchQuery(e.target.value);
              setSearchFocused(true);
            }}
            placeholder="Search projects, IDs, approvals, campaigns, assets, Printify, or trading..."
            className="w-full pl-9 pr-8 py-1.5 bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-xs sm:text-sm text-slate-800 placeholder:text-slate-400 rounded-xl border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          {searchFocused && searchQuery.trim().length > 0 && (
            <div className="absolute left-0 right-0 mt-1.5 bg-white rounded-xl border border-slate-200 shadow-lg py-1.5 z-50 max-h-96 overflow-y-auto custom-scrollbar">
              {searchResults.length === 0 ? (
                <div className="px-4 py-4 text-xs text-slate-500 text-center">
                  No matching projects, approvals, assets, or strategies found for "{searchQuery}".
                </div>
              ) : (
                searchResults.map(res => {
                  const Icon = res.icon;
                  return (
                    <button
                      key={`${res.category}-${res.id}`}
                      type="button"
                      onClick={() => {
                        navigateToObject(res.page, res.id, res.kind);
                        setSearchFocused(false);
                      }}
                      className="w-full px-3.5 py-2 text-left hover:bg-slate-50 flex items-center gap-3 transition-colors cursor-pointer"
                    >
                      <Icon className="w-4 h-4 text-slate-400 shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-semibold text-slate-900 truncate">
                            {res.title}
                          </span>
                          <span className="text-[10px] font-medium text-slate-500 shrink-0">
                            {res.category}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 truncate font-mono">
                          {res.meta}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Zone: Needs Ray Queue, Notifications, Ask Nova Drawer, User, New Project */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Needs Ray Drawer Button */}
        <button
          type="button"
          onClick={() => setIsNeedsRayDrawerOpen(true)}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-xs font-semibold transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
            pendingApprovalsCount > 0
              ? 'bg-amber-50 hover:bg-amber-100 text-amber-900 border-amber-200'
              : 'bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200'
          }`}
          title="Open Quick Approval Queue"
        >
          <AlertTriangle
            className={`w-3.5 h-3.5 ${pendingApprovalsCount > 0 ? 'text-amber-600' : 'text-slate-400'}`}
          />
          <span className="hidden sm:inline">Needs Ray</span>
          <span className="px-1.5 py-0.2 rounded bg-white/80 text-slate-800 border border-slate-200/80 text-[10px] font-bold tabular-nums">
            {pendingApprovalsCount}
          </span>
        </button>

        {/* Notifications Bell */}
        <div className="relative" ref={notifRef}>
          <button
            type="button"
            onClick={() => setShowNotifications(prev => !prev)}
            className="relative p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors cursor-pointer"
            title="Operational Notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-white" />
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-96 max-w-[92vw] bg-white rounded-2xl border border-slate-200 shadow-xl p-3 z-50 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
                <span className="font-semibold text-slate-900 text-sm">
                  Notifications ({unreadNotificationsCount} unread)
                </span>
                <button
                  type="button"
                  onClick={markAllNotificationsRead}
                  className="text-[11px] text-blue-600 font-medium hover:underline cursor-pointer"
                >
                  Mark all read
                </button>
              </div>
              <div className="space-y-1.5 max-h-80 overflow-y-auto custom-scrollbar">
                {notifications.map(n => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => {
                      markNotificationRead(n.id);
                      navigateToObject(
                        n.targetPage,
                        n.targetEntityId,
                        n.targetPage === 'approvals'
                          ? 'approval'
                          : n.targetPage === 'projects'
                          ? 'project'
                          : n.targetPage === 'campaigns'
                          ? 'campaign'
                          : n.targetPage === 'creative'
                          ? 'asset'
                          : 'offer'
                      );
                      setShowNotifications(false);
                    }}
                    className={`w-full text-left p-2.5 rounded-xl border transition-colors cursor-pointer ${
                      n.read
                        ? 'bg-white border-slate-100 hover:bg-slate-50'
                        : 'bg-blue-50/50 border-blue-100 hover:bg-blue-50'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <span className="text-[10px] font-semibold text-slate-500">
                        {n.type.replace(/_/g, ' ')}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {n.truthClass && <TruthBadge truth={n.truthClass} />}
                        <span className="text-[10px] text-slate-400 tabular-nums">{n.timestamp}</span>
                      </div>
                    </div>
                    <div className="font-semibold text-slate-900 leading-snug">{n.title}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{n.detail}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Ask Nova Drawer Toggle */}
        {currentPage !== 'nova' && (
          <button
            type="button"
            onClick={() => setIsNovaDrawerOpen(!isNovaDrawerOpen)}
            className={`px-2.5 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
              isNovaDrawerOpen
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100'
            }`}
            title="Open Nova Operator Drawer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Ask Nova</span>
          </button>
        )}

        {/* User Menu */}
        <div className="relative" ref={userRef}>
          <button
            type="button"
            onClick={() => setShowUserMenu(prev => !prev)}
            className="flex items-center gap-2 p-1 sm:px-2 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <UserAvatar name="Ray Davis" size="sm" />
            <div className="hidden md:flex flex-col leading-tight">
              <span className="text-xs font-semibold text-slate-800 whitespace-nowrap">Ray Davis</span>
              <span className="text-[10px] text-slate-400 whitespace-nowrap">Owner</span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl border border-slate-200 shadow-lg p-1.5 z-50 text-xs">
              <div className="px-3 py-2 border-b border-slate-100 mb-1">
                <div className="font-semibold text-slate-800">Ray Davis</div>
                <div className="text-slate-400 text-[11px]">Owner · Strategic Authority</div>
              </div>
              <button
                type="button"
                onClick={() => {
                  navigateToObject('settings');
                  setShowUserMenu(false);
                }}
                className="w-full text-left px-3 py-1.5 rounded-lg hover:bg-slate-50 text-slate-700 cursor-pointer"
              >
                Credentials &amp; Settings
              </button>
              <button
                type="button"
                onClick={() => {
                  navigateToObject('nova');
                  setShowUserMenu(false);
                }}
                className="w-full text-left px-3 py-1.5 rounded-lg hover:bg-slate-50 text-slate-700 cursor-pointer"
              >
                Nova Console
              </button>
            </div>
          )}
        </div>

        {/* + New Project */}
        <button
          type="button"
          onClick={() => setIsNewProjectModalOpen(true)}
          className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer whitespace-nowrap shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">New Project</span>
        </button>
      </div>
    </header>
  );
};
