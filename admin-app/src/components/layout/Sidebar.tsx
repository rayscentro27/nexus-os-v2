import React, { useState } from 'react';
import {
  LayoutDashboard,
  CheckSquare,
  FolderKanban,
  Search,
  Megaphone,
  Target,
  Palette,
  ShoppingBag,
  Wallet,
  TrendingUp,
  Server,
  Sparkles,
  Building2,
  Cpu,
  Users,
  FileText,
  FlaskConical,
  ShieldCheck,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { PageId, NexusDepartmentName } from '../../types';
import { useNexus } from '../../context/NexusContext';
import { BrandLogo } from '../common/BrandLogo';

interface SidebarProps {
  className?: string;
  onNavigate?: () => void;
}

interface NavDef {
  id: PageId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  depts?: NexusDepartmentName[];
  staticSub?: string;
}

const PRIMARY_NAV: NavDef[] = [
  { id: 'command-center', label: 'Overview', icon: LayoutDashboard },
  { id: 'approvals', label: 'Approvals', icon: CheckSquare },
  { id: 'projects', label: 'Projects', icon: FolderKanban },
  { id: 'existing-business', label: 'Existing Business', icon: Building2 },
  { id: 'research', label: 'Research', icon: Search, depts: ['Research'] },
  { id: 'rea', label: 'REA', icon: Cpu },
  { id: 'marketing', label: 'Marketing', icon: Megaphone, depts: ['Marketing', 'Distribution'] },
  { id: 'campaigns', label: 'Campaigns', icon: Target, depts: ['Distribution'] },
  { id: 'creative', label: 'Creative', icon: Palette, depts: ['Creative'] },
  { id: 'business-hub', label: 'Commerce', icon: ShoppingBag, depts: ['Commerce'] },
  { id: 'finance', label: 'Finance', icon: Wallet, depts: ['Finance'] },
  { id: 'trading-engine', label: 'Trading', icon: TrendingUp, depts: ['Trading'], staticSub: 'Paper' },
  { id: 'systems', label: 'Systems', icon: Server, depts: ['Systems'] },
  { id: 'nova', label: 'Nova', icon: Sparkles },
];

const SECONDARY_NAV: NavDef[] = [
  { id: 'clients', label: 'Clients', icon: Users },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'development-labs', label: 'Development / Labs', icon: FlaskConical, depts: ['Development / Labs'] },
  { id: 'upgrade-control', label: 'Upgrade Control', icon: ShieldCheck, depts: ['Upgrade Control'] },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ className = '', onNavigate }) => {
  const { currentPage, setCurrentPage, approvals, pendingApprovalsCount, distributedSystems } = useNexus();
  const [collapsed, setCollapsed] = useState(false);

  const handleSelectPage = (id: PageId) => {
    setCurrentPage(id);
    if (onNavigate) onNavigate();
  };

  const getBadge = (item: NavDef) => {
    if (item.id === 'approvals') {
      if (pendingApprovalsCount > 0) {
        const hasHigh = approvals.some(a => a.status === 'PENDING' && a.priority === 'HIGH');
        return { text: `${pendingApprovalsCount}`, alert: true, high: hasHigh };
      }
      return { text: '0', alert: false, high: false };
    }

    if (item.id === 'systems') {
      const blocked = distributedSystems.filter(s => s.status === 'BLOCKED' || s.status === 'DEGRADED').length;
      const pendingSys = approvals.filter(a => a.status === 'PENDING' && a.department === 'Systems').length;
      const total = blocked + pendingSys;
      if (total > 0) return { text: `${total}`, alert: true, high: blocked > 0 };
    }

    if (item.depts && item.depts.length > 0) {
      const matching = approvals.filter(
        a => a.status === 'PENDING' && item.depts!.includes(a.department)
      );
      if (matching.length > 0) {
        return {
          text: `${matching.length}`,
          alert: true,
          high: matching.some(a => a.priority === 'HIGH'),
        };
      }
    }

    if (item.staticSub) {
      return { text: item.staticSub, alert: false, high: false };
    }

    return null;
  };

  const renderNavItem = (item: NavDef) => {
    const isActive =
      currentPage === item.id || (item.id === 'systems' && currentPage === 'operations');
    const Icon = item.icon;
    const badge = getBadge(item);

    return (
      <button
        key={item.id}
        type="button"
        onClick={() => handleSelectPage(item.id)}
        title={collapsed ? item.label : undefined}
        className={`w-full flex items-center ${
          collapsed ? 'justify-center px-2' : 'justify-between px-3'
        } py-2 rounded-xl text-[13px] font-medium transition-colors cursor-pointer whitespace-nowrap ${
          isActive
            ? 'bg-blue-50 text-blue-700 font-semibold ring-1 ring-blue-200/80'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
        }`}
      >
        <span className="flex items-center gap-2.5 min-w-0">
          <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
          {!collapsed && <span className="truncate">{item.label}</span>}
        </span>

        {!collapsed && badge && (
          <span
            className={`px-1.5 py-0.5 rounded-md text-[10px] font-semibold tabular-nums shrink-0 ${
              badge.alert
                ? badge.high
                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                  : 'bg-amber-50 text-amber-800 border border-amber-200'
                : isActive
                ? 'bg-blue-100 text-blue-700'
                : 'bg-slate-100 text-slate-600'
            }`}
          >
            {badge.text}
          </span>
        )}
      </button>
    );
  };

  return (
    <aside
      className={`${
        collapsed ? 'w-[68px]' : 'w-60'
      } shrink-0 bg-white border-r border-slate-200/80 flex flex-col justify-between p-3 h-full overflow-y-auto custom-scrollbar select-none transition-all duration-200 ${className}`}
    >
      <div>
        {/* Brand + Collapse Toggle */}
        <div className="flex items-center justify-between px-1.5 pt-1 pb-3 mb-2 border-b border-slate-100">
          {!collapsed && (
            <div className="cursor-pointer min-w-0" onClick={() => handleSelectPage('command-center')}>
              <BrandLogo />
            </div>
          )}
          <button
            type="button"
            onClick={() => setCollapsed(prev => !prev)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer shrink-0"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeftOpen className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Core Operations */}
        {!collapsed && (
          <div className="px-3 mb-1.5 text-[11px] font-semibold text-slate-400">
            Operations
          </div>
        )}
        <nav className="space-y-0.5">{PRIMARY_NAV.map(renderNavItem)}</nav>

        {/* Governance & Support */}
        <div className="mt-4 pt-3 border-t border-slate-100">
          {!collapsed && (
            <div className="px-3 mb-1.5 text-[11px] font-semibold text-slate-400">
              Governance &amp; Support
            </div>
          )}
          <nav className="space-y-0.5">{SECONDARY_NAV.map(renderNavItem)}</nav>
        </div>
      </div>

      {/* Quiet Footer Control State */}
      {!collapsed && (
        <div className="mt-4 pt-3 border-t border-slate-100 px-2 text-[11px] text-slate-500 flex items-center justify-between">
          <span className="font-medium text-slate-600">Nexus Control</span>
          <span className="tabular-nums text-slate-400">Light OS</span>
        </div>
      )}
    </aside>
  );
};
