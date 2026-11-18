import React from 'react';
import { NexusProvider, useNexus } from './context/NexusContext';
import { AdminShell } from './components/layout/AdminShell';

import { CommandCenterPage } from './pages/CommandCenterPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ResearchPage } from './pages/ResearchPage';
import { MarketingPage } from './pages/MarketingPage';
import { CampaignsPage } from './pages/CampaignsPage';
import { CreativePage } from './pages/CreativePage';
import { BusinessHubPage } from './pages/BusinessHubPage';
import { FinancePage } from './pages/FinancePage';
import { TradingEnginePage } from './pages/TradingEnginePage';
import { SystemsPage } from './pages/SystemsPage';
import { NovaExecutiveConsolePage } from './pages/NovaExecutiveConsolePage';
import { ClientsPage } from './pages/ClientsPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { DevelopmentLabsPage } from './pages/DevelopmentLabsPage';
import { UpgradeControlPage } from './pages/UpgradeControlPage';
import { SettingsPage } from './pages/SettingsPage';
import { OperationsPage } from './pages/OperationsPage';
import { ExistingBusinessPage } from './pages/ExistingBusinessPage';
import { ReaPage } from './pages/ReaPage';
import { LivePageBanner, LiveGate } from './components/live/LivePageBanner';

const PageRenderer: React.FC = () => {
  const { currentPage } = useNexus();
  return (
    <>
      <LiveGate />
      <LivePageBanner page={currentPage} />
      <PageBody />
    </>
  );
};

const PageBody: React.FC = () => {
  const { currentPage } = useNexus();

  switch (currentPage) {
    case 'command-center':
      return <CommandCenterPage />;
    case 'approvals':
      return <ApprovalsPage />;
    case 'projects':
      return <ProjectsPage />;
    case 'research':
      return <ResearchPage />;
    case 'marketing':
      return <MarketingPage />;
    case 'campaigns':
      return <CampaignsPage />;
    case 'creative':
      return <CreativePage />;
    case 'business-hub':
      return <BusinessHubPage />;
    case 'finance':
      return <FinancePage />;
    case 'trading-engine':
      return <TradingEnginePage />;
    case 'systems':
      return <SystemsPage />;
    case 'nova':
      return <NovaExecutiveConsolePage />;
    case 'clients':
      return <ClientsPage />;
    case 'documents':
      return <DocumentsPage />;
    case 'development-labs':
      return <DevelopmentLabsPage />;
    case 'upgrade-control':
      return <UpgradeControlPage />;
    case 'operations':
      return <OperationsPage />;
    case 'settings':
      return <SettingsPage />;
    case 'existing-business':
      return <ExistingBusinessPage />;
    case 'rea':
      return <ReaPage />;
    default:
      return <CommandCenterPage />;
  }
};

export default function App() {
  return (
    <NexusProvider>
      <AdminShell>
        <PageRenderer />
      </AdminShell>
    </NexusProvider>
  );
}
