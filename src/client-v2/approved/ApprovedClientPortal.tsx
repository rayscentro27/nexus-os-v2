import { useEffect, useState } from 'react';
import ApprovedApp from './App';
import './portal-theme.css';
import './generated.css';
import { clearNexusPortalBridge, installNexusPortalBridge } from './nexusPortalBridge';
import type { TabType } from './types/portal';

const loading = <div className="h-screen flex items-center justify-center bg-slate-50 text-slate-600 text-sm">Preparing your client portal…</div>;

export function ApprovedClientPortal({ live, initialTab = 'dashboard' }: { live: boolean; initialTab?: TabType }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (live) installNexusPortalBridge();
    else clearNexusPortalBridge();
    setReady(true);
    return () => {
      if (live) clearNexusPortalBridge();
    };
  }, [live]);

  if (!ready) return loading;
  return <ApprovedApp initialTab={initialTab} />;
}
