import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { NovaPanel } from './NovaPanel';
import { NewProjectModal } from '../modals/NewProjectModal';
import { NeedsRayDrawer } from '../common/NeedsRayDrawer';
import { useNexus } from '../../context/NexusContext';
import { Sparkles, X } from 'lucide-react';

interface AdminShellProps {
  children: React.ReactNode;
}

export const AdminShell: React.FC<AdminShellProps> = ({ children }) => {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const { isNovaDrawerOpen, setIsNovaDrawerOpen, isMobileNovaOpen, setIsMobileNovaOpen, currentPage } = useNexus();

  const drawerOpen = isNovaDrawerOpen || isMobileNovaOpen;
  const closeDrawer = () => {
    setIsNovaDrawerOpen(false);
    setIsMobileNovaOpen(false);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#F8FAFC]">
      {/* Desktop Left Sidebar */}
      <div className="hidden lg:block h-full">
        <Sidebar />
      </div>

      {/* Mobile / Tablet Left Sidebar Drawer */}
      {isMobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs"
            onClick={() => setIsMobileNavOpen(false)}
          />
          <div className="relative z-10 w-64 max-w-[80vw] h-full shadow-2xl">
            <Sidebar onNavigate={() => setIsMobileNavOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Center Area — full available width without permanent right Nova rail */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <TopBar onToggleMobileNav={() => setIsMobileNavOpen(true)} />

        <main className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 sm:p-6">
          <div className="w-full max-w-[1520px] mx-auto pb-10">{children}</div>
        </main>
      </div>

      {/* Contextual Slide-Over Nova Drawer (Opened via Ask Nova button, never squeezing pages) */}
      {drawerOpen && currentPage !== 'nova' && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs"
            onClick={closeDrawer}
          />
          <div className="relative z-10 w-96 max-w-[92vw] h-full shadow-2xl bg-white border-l border-slate-200 flex flex-col">
            <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between shrink-0">
              <span className="font-semibold text-sm text-slate-900 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-600" /> Nova Operator Drawer
              </span>
              <button
                type="button"
                onClick={closeDrawer}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
                title="Close Nova Drawer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <NovaPanel className="w-full h-full border-l-0" />
            </div>
          </div>
        </div>
      )}

      <NeedsRayDrawer />
      <NewProjectModal />
    </div>
  );
};
