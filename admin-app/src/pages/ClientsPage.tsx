import React, { useState } from 'react';
import {
  Search,
  ChevronRight,
  Activity,
  Eye,
  EyeOff,
  FolderKanban
} from 'lucide-react';
import { StatusBadge } from '../components/common/StatusBadge';
import { TruthBadge } from '../components/common/TruthBadge';
import { useNexus } from '../context/NexusContext';
import { ClientItem } from '../types';
import { GoClearClientPortalView } from '../components/clients/GoClearClientPortalView';
import { UnavailableState } from '../components/live/UnavailableState';

export const ClientsPage: React.FC = () => {
  const { sendMessage, navigateToObject, setIsNovaDrawerOpen, liveAreas } = useNexus();
  const liveClients = (liveAreas.clients || []) as ClientItem[];
  const [viewMode, setViewMode] = useState<'OPERATOR' | 'GOCLEAR_CLIENT_PREVIEW'>('OPERATOR');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedClassification, setSelectedClassification] = useState<'ALL' | 'PILOT' | 'DEMO'>('ALL');
  const [selectedClientId, setSelectedClientId] = useState<string>('');

  const getClassification = (client: ClientItem): 'PILOT' | 'DEMO' | 'UNKNOWN' => {
    const value = String((client as ClientItem & { classification?: string }).classification || '').toUpperCase();
    return value === 'PILOT' || value === 'DEMO' ? value : 'UNKNOWN';
  };

  const filteredClients = liveClients.filter(client => {
    const matchesSearch =
      client.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.tenant.toLowerCase().includes(searchTerm.toLowerCase());
    const cls = getClassification(client);
    return matchesSearch && (selectedClassification === 'ALL' || cls === selectedClassification);
  });

  const activeClient: ClientItem =
    filteredClients.find(c => c.id === selectedClientId) || filteredClients[0] || null;

  const pilotCount = liveClients.filter(c => getClassification(c) === 'PILOT').length;
  const demoCount = liveClients.filter(c => getClassification(c) === 'DEMO').length;

  if (liveClients.length === 0) {
    return <div className="space-y-4 pb-10"><div className="bg-white rounded-xl p-4 border border-slate-200/80 shadow-2xs"><div className="flex items-center gap-2"><h1 className="text-lg font-semibold text-slate-900">Clients &amp; Tenant Workspaces</h1><TruthBadge truth="NOT_CONNECTED" /></div><p className="text-xs text-slate-500 mt-0.5">Client and tenant records are shown only when returned by the durable Nexus read model.</p></div><div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4"><UnavailableState>Client and tenant data is not connected.</UnavailableState></div></div>;
  }

  return (
    <div className="space-y-4 pb-10">
      {/* Header */}
      <div className="bg-white rounded-xl p-4 border border-slate-200/80 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
              Clients &amp; Tenant Workspaces
            </h1>
            <TruthBadge truth={liveClients.length ? 'UNKNOWN' : 'NOT_CONNECTED'} label="Tenant classification source" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Client and tenant details are rendered from the Nexus read model; unsupported classification fields remain unknown.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2.5 py-1 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium">
            {pilotCount} Pilot Account
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-purple-50 border border-purple-200 text-purple-700 text-xs font-medium">
            {demoCount} Demo Workspaces
          </span>

          <div className="inline-flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-medium">
            <button
              type="button"
              onClick={() => setViewMode('OPERATOR')}
              className={`px-2.5 py-1 rounded-md inline-flex items-center gap-1 cursor-pointer ${
                viewMode === 'OPERATOR' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Operator
            </button>
            <button
              type="button"
              onClick={() => setViewMode('GOCLEAR_CLIENT_PREVIEW')}
              className={`px-2.5 py-1 rounded-md inline-flex items-center gap-1 cursor-pointer ${
                viewMode === 'GOCLEAR_CLIENT_PREVIEW'
                  ? 'bg-blue-600 text-white shadow-2xs'
                  : 'text-slate-600'
              }`}
            >
              <EyeOff className="w-3.5 h-3.5" />
              Preview GoClear Portal
            </button>
          </div>
        </div>
      </div>

      {viewMode === 'GOCLEAR_CLIENT_PREVIEW' ? (
        <GoClearClientPortalView
          client={activeClient}
          onExitPreview={() => setViewMode('OPERATOR')}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Left Directory */}
          <div className="lg:col-span-7 xl:col-span-8 bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden flex flex-col">
            <div className="p-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2 bg-slate-50/50">
              <div className="relative flex-1 min-w-[180px]">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  placeholder="Search clients, company, tenant..."
                  className="w-full pl-8 pr-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-hidden focus:border-blue-500"
                />
              </div>

              <div className="flex items-center gap-1 text-xs">
                {(
                  [
                    { id: 'ALL', label: `All (${CLIENTS_DATA.length})` },
                    { id: 'PILOT', label: `Pilot (${pilotCount})` },
                    { id: 'DEMO', label: `Demo / Sandbox (${demoCount})` },
                  ] as const
                ).map(tab => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setSelectedClassification(tab.id)}
                    className={`px-2.5 py-1 rounded-md font-medium cursor-pointer ${
                      selectedClassification === tab.id
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-600 hover:bg-slate-200/60'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase border-b border-slate-100">
                  <tr>
                    <th className="py-2 px-3">Client / Tenant</th>
                    <th className="py-2 px-3">Classification</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Progress</th>
                    <th className="py-2 px-3 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredClients.map(client => {
                    const isSelected = activeClient.id === client.id;
                    const cls = getClassification(client);
                    return (
                      <tr
                        key={client.id}
                        onClick={() => setSelectedClientId(client.id)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? 'bg-blue-50/70' : 'hover:bg-slate-50'
                        }`}
                      >
                        <td className="py-2.5 px-3">
                          <div className="font-medium text-slate-900">{client.name}</div>
                          <div className="text-[11px] text-slate-400">
                            {client.tenant}.nexusos.com
                          </div>
                        </td>
                        <td className="py-2.5 px-3">
                          <TruthBadge
                            truth={cls === 'PILOT' ? 'TEST' : cls === 'DEMO' ? 'DEMO' : 'UNKNOWN'}
                            label={cls === 'UNKNOWN' ? 'CLASSIFICATION UNKNOWN' : `${cls} TENANT`}
                          />
                        </td>
                        <td className="py-2.5 px-3">
                          <StatusBadge status={client.status} size="sm" />
                        </td>
                        <td className="py-2.5 px-3 font-medium text-slate-700">{client.progress}%</td>
                        <td className="py-2.5 px-3 text-right">
                          <ChevronRight
                            className={`w-4 h-4 inline ${
                              isSelected ? 'text-blue-600' : 'text-slate-300'
                            }`}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Dossier */}
          <div className="lg:col-span-5 xl:col-span-4 bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <div className="pb-3 border-b border-slate-100">
              <div className="flex items-center justify-between gap-2">
                <TruthBadge
                  truth={getClassification(activeClient) === 'PILOT' ? 'TEST' : getClassification(activeClient) === 'DEMO' ? 'DEMO' : 'UNKNOWN'}
                  label={getClassification(activeClient) === 'UNKNOWN' ? 'CLASSIFICATION UNKNOWN' : `${getClassification(activeClient)} TENANT`}
                />
                <StatusBadge status={activeClient.status} size="sm" />
              </div>
              <h2 className="text-base font-semibold text-slate-900 mt-2">{activeClient.name}</h2>
              <p className="text-xs text-slate-500">
                {activeClient.company} · {activeClient.segment}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <div className="text-[10px] text-slate-400 uppercase font-medium">Health</div>
                <div className="font-semibold text-slate-900 mt-0.5">{activeClient.health}</div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <div className="text-[10px] text-slate-400 uppercase font-medium">Billing Sync</div>
                <div className="font-semibold text-rose-700 mt-0.5">NOT CONNECTED</div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 text-xs space-y-1">
              <div className="font-medium text-slate-700">Tenant Host</div>
              <div className="font-mono text-blue-700">https://{activeClient.tenant}.nexusos.com</div>
            </div>

            {getClassification(activeClient) === 'PILOT' && (
              <button
                type="button"
                onClick={() => navigateToObject('projects', 'proj_goclear_pilot', 'project')}
                className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium inline-flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <FolderKanban className="w-3.5 h-3.5" />
                Open GoClear Pilot Project
              </button>
            )}

            <button
              type="button"
              onClick={() => {
                sendMessage(`Summarize onboarding & blocker state for ${activeClient.name}.`);
                setIsNovaDrawerOpen(true);
              }}
              className="w-full py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <Activity className="w-3.5 h-3.5" />
              Ask Nova About Client
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
