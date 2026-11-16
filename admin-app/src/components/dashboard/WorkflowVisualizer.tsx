import React, { useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Sparkles,
  Building2,
  DollarSign,
  Briefcase,
  ShieldCheck,
  Search,
  ExternalLink,
  ChevronRight,
  Layers,
  FileText,
  UserCheck,
  Check,
  X,
  Zap,
  Activity,
  Award
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';
import { INITIAL_OPPORTUNITIES, INITIAL_FUNDING_CASES } from '../../data/businessHubData';

export interface WorkflowGate {
  id: string;
  order: number;
  name: string;
  shortName: string;
  owner: string;
  roleType: 'EXECUTOR' | 'RECOMMENDER' | 'ANALYST' | 'STRATEGIC_AUTHORITY';
  description: string;
  icon: typeof Search;
  color: string;
  activePulseColor: string;
}

export const WORKFLOW_GATES: WorkflowGate[] = [
  {
    id: 'RESEARCH',
    order: 1,
    name: 'Research',
    shortName: '01. Research',
    owner: 'Research Heartbeat',
    roleType: 'ANALYST',
    description: 'Intelligence ingestion, questionnaire completion, gap analysis. Exits upon formal handoff.',
    icon: Search,
    color: 'border-blue-400 bg-blue-50/70 text-blue-800',
    activePulseColor: 'bg-blue-400'
  },
  {
    id: 'ATLAS',
    order: 2,
    name: 'Atlas / Opportunities',
    shortName: '02. Atlas',
    owner: 'Atlas Recommender',
    roleType: 'RECOMMENDER',
    description: 'Opportunity scoring, business model blueprint, lowest-cost entry synthesis.',
    icon: Briefcase,
    color: 'border-indigo-400 bg-indigo-50/70 text-indigo-800',
    activePulseColor: 'bg-indigo-400'
  },
  {
    id: 'CREATION',
    order: 3,
    name: 'Business Creation',
    shortName: '03. Creation',
    owner: 'Creation & Governance',
    roleType: 'EXECUTOR',
    description: 'Entity readiness, bankability checklist, defensible NAICS code alignment (if required).',
    icon: Building2,
    color: 'border-purple-400 bg-purple-50/70 text-purple-800',
    activePulseColor: 'bg-purple-400'
  },
  {
    id: 'FINANCE',
    order: 4,
    name: 'Finance',
    shortName: '04. Finance',
    owner: 'Finance Department',
    roleType: 'EXECUTOR',
    description: 'Unit economics, pro-forma P&L, capital requirements analysis.',
    icon: DollarSign,
    color: 'border-emerald-400 bg-emerald-50/70 text-emerald-800',
    activePulseColor: 'bg-emerald-400'
  },
  {
    id: 'CLYDE',
    order: 5,
    name: 'Clyde / Funding',
    shortName: '05. Clyde',
    owner: 'Clyde Recommender',
    roleType: 'RECOMMENDER',
    description: 'Non-binary funding eligibility matching, tier progression (if capital required).',
    icon: ShieldCheck,
    color: 'border-amber-400 bg-amber-50/70 text-amber-800',
    activePulseColor: 'bg-amber-400'
  },
  {
    id: 'RAY',
    order: 6,
    name: 'Ray Strategic Sign-Off',
    shortName: '06. Ray Gate',
    owner: 'Ray (Owner)',
    roleType: 'STRATEGIC_AUTHORITY',
    description: 'Final strategic approval, capital deployment authorization, operational launch.',
    icon: UserCheck,
    color: 'border-rose-400 bg-rose-50/70 text-rose-900',
    activePulseColor: 'bg-rose-500'
  }
];

export interface VisualProjectItem {
  id: string;
  title: string;
  gate: string;
  gateOrder: number;
  owner: string;
  status: string;
  nextAction: string;
  recommenderNote?: string;
  type: 'OPPORTUNITY' | 'FUNDING' | 'HANDOFF';
  lane: 'NEXUS' | 'CLIENT';
  timeInStage: string;
  authorized?: boolean;
}

export const WorkflowVisualizer: React.FC<{
  onSelectProject?: (projectId: string) => void;
  compact?: boolean;
}> = ({ onSelectProject, compact = false }) => {
  const { setCurrentPage, completeQuest } = useNexus();
  const [selectedGateId, setSelectedGateId] = useState<string>('RAY');
  const [activeLane, setActiveLane] = useState<'ALL' | 'NEXUS' | 'CLIENT'>('ALL');
  const [selectedItem, setSelectedItem] = useState<VisualProjectItem | null>(null);
  const [isRayModalOpen, setIsRayModalOpen] = useState(false);
  const [rayGuidanceText, setRayGuidanceText] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Group items by gate with dynamic authorization updates
  const [localItems, setLocalItems] = useState<Record<string, VisualProjectItem[]>>({
    RESEARCH: [
      {
        id: 'res-01',
        title: 'B2B Compliance SaaS Feeder (Notebook #12)',
        gate: 'RESEARCH',
        gateOrder: 1,
        owner: 'Research Heartbeat',
        status: 'QUESTIONNAIRE_COMPLETE',
        nextAction: 'Ready for formal handoff to Atlas',
        recommenderNote: 'Gap analysis closed. 4 source videos transcribed and synthesized.',
        type: 'OPPORTUNITY',
        lane: 'NEXUS',
        timeInStage: '18m'
      },
      {
        id: 'res-02',
        title: 'Forex London Breakout Algo Feeder',
        gate: 'RESEARCH',
        gateOrder: 1,
        owner: 'Research Heartbeat',
        status: 'RESEARCH_REQUIRED',
        nextAction: 'Evaluating slippage metrics across 3 brokers',
        recommenderNote: 'Awaiting backtest dataset normalization in Trading Engine.',
        type: 'OPPORTUNITY',
        lane: 'NEXUS',
        timeInStage: '45m'
      }
    ],
    ATLAS: INITIAL_OPPORTUNITIES.map((opp, idx) => ({
      id: opp.id,
      title: opp.opportunity,
      gate: 'ATLAS',
      gateOrder: 2,
      owner: opp.currentOwner,
      status: opp.currentState,
      nextAction: opp.nextAction,
      recommenderNote: `Atlas recommends: ${opp.atlasRecommendation.recommendedAction}`,
      type: 'OPPORTUNITY' as const,
      lane: 'NEXUS' as const,
      timeInStage: `${idx + 1}h`
    })),
    CREATION: [
      {
        id: 'cre-01',
        title: 'GoClear Logistics & Environmental Corp',
        gate: 'CREATION',
        gateOrder: 3,
        owner: 'Business Creation Desk',
        status: 'BANKABILITY_AUDIT',
        nextAction: 'Establish professional domain email & register 410000 NAICS',
        recommenderNote: 'Accurate classification verified. Tier-1 business credit pending 2 tradelines.',
        type: 'OPPORTUNITY',
        lane: 'CLIENT',
        timeInStage: '2d'
      },
      {
        id: 'cre-02',
        title: 'Nexus Data & Signal LLC (Entity #2)',
        gate: 'CREATION',
        gateOrder: 3,
        owner: 'Business Creation Desk',
        status: 'GOOD_STANDING_VERIFIED',
        nextAction: 'Open secondary operating bank account with Chase',
        recommenderNote: 'DUNS assigned, EIN active, EIN-matched commercial phone verified.',
        type: 'OPPORTUNITY',
        lane: 'NEXUS',
        timeInStage: '1d'
      }
    ],
    FINANCE: [
      {
        id: 'fin-01',
        title: 'Autonomous Content Repurposing Studio',
        gate: 'FINANCE',
        gateOrder: 4,
        owner: 'Finance Department',
        status: 'FINANCE_REVIEW',
        nextAction: 'Pro-forma 12-month margin stress test under $0 initial spend',
        recommenderNote: 'Cost-free entry tier validated: $0 monthly overhead using open weights.',
        type: 'OPPORTUNITY',
        lane: 'NEXUS',
        timeInStage: '3h'
      },
      {
        id: 'fin-02',
        title: 'GoClear Fleet Working Capital Model',
        gate: 'FINANCE',
        gateOrder: 4,
        owner: 'Finance Department',
        status: 'PRO_FORMA_APPROVED',
        nextAction: 'Handoff to Clyde for non-binary lender matching',
        recommenderNote: 'DSCR 1.82x supports $100k-$150k SBA 7(a) working capital facility.',
        type: 'FUNDING',
        lane: 'CLIENT',
        timeInStage: '5h'
      }
    ],
    CLYDE: INITIAL_FUNDING_CASES.map((fc, idx) => ({
      id: fc.id,
      title: `${fc.lenderProgram} · ${fc.product}`,
      gate: 'CLYDE',
      gateOrder: 5,
      owner: 'Clyde Recommender',
      status: fc.currentFit,
      nextAction: fc.exactNextAction,
      recommenderNote: `Clyde recommends: ${fc.product} (${fc.potentialAmount} potential). ${fc.improvableRequirements.length > 0 ? `Needs: ${fc.improvableRequirements[0]}` : 'Ready for submission.'}`,
      type: 'FUNDING' as const,
      lane: fc.lane === 'CLIENT / GOCLEAR' ? 'CLIENT' as const : 'NEXUS' as const,
      timeInStage: `${idx * 2 + 1}h`
    })),
    RAY: [
      {
        id: 'ray-01',
        title: 'Vertical AI SDR for Regional Contractors',
        gate: 'RAY',
        gateOrder: 6,
        owner: 'Ray Strategic Authority',
        status: 'RAY_REVIEW_REQUIRED',
        nextAction: 'Approve $1,500 initial outreach API budget and go-to-market plan',
        recommenderNote: 'Atlas + Finance recommend immediate launch. Expected payback 28 days.',
        type: 'OPPORTUNITY',
        lane: 'NEXUS',
        timeInStage: '2h',
        authorized: false
      },
      {
        id: 'ray-02',
        title: 'Chase Ink Business Preferred ($25,000)',
        gate: 'RAY',
        gateOrder: 6,
        owner: 'Ray Strategic Authority',
        status: 'WAITING ON RAY',
        nextAction: 'Authorize application submission with existing Chase banking relationship',
        recommenderNote: 'Clyde recommends submission. 840 personal score, 3 years in business, 100% requirements met.',
        type: 'FUNDING',
        lane: 'NEXUS',
        timeInStage: '4h',
        authorized: false
      }
    ]
  });

  const selectedGate = WORKFLOW_GATES.find(g => g.id === selectedGateId) || WORKFLOW_GATES[5];
  const itemsInSelectedGate = (localItems[selectedGateId] || []).filter(item => {
    if (activeLane === 'ALL') return true;
    return item.lane === activeLane;
  });

  const handleAuthorizeRay = (item: VisualProjectItem) => {
    setLocalItems(prev => {
      const rayList = prev.RAY.map(i =>
        i.id === item.id
          ? {
              ...i,
              status: 'AUTHORIZED & PROMOTED',
              nextAction: 'Strategic authorization granted by Ray. Handed to production execution.',
              authorized: true
            }
          : i
      );
      return { ...prev, RAY: rayList };
    });

    if (selectedItem?.id === item.id) {
      setSelectedItem(prev =>
        prev
          ? {
              ...prev,
              status: 'AUTHORIZED & PROMOTED',
              nextAction: 'Strategic authorization granted by Ray. Handed to production execution.',
              authorized: true
            }
          : null
      );
    }

    setIsRayModalOpen(false);
    completeQuest('quest-command-master', 150);
    showToast(`✓ Strategic Authorization Confirmed for ${item.title}! +150 XP`);
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden flex flex-col relative select-none">
      {/* Toast Feedback */}
      {toastMessage && (
        <div className="absolute top-3 right-4 z-50 animate-in fade-in slide-in-from-top duration-200">
          <div className="bg-slate-900 text-white px-3 py-1.5 rounded-lg shadow-xl text-xs font-bold border border-emerald-500/50 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Top Bar / Principle Header */}
      <div className="px-3.5 py-2.5 bg-slate-900 text-white flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-black tracking-tight text-white uppercase">
                Canonical Workflow Visualizer
              </span>
              <span className="text-[10px] px-2 py-0.2 rounded font-mono font-bold bg-slate-800 text-cyan-300 border border-slate-700">
                Workflow = Authority
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">
              Research → Atlas (Opps) → Business Creation → Finance → Clyde (Funding) → Ray (Strategic Authority)
            </p>
          </div>
        </div>

        {/* Operating Model Legend Tags */}
        <div className="flex items-center gap-1.5 flex-wrap text-[9px] font-mono">
          <span className="px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800/60">
            AI = Recommender
          </span>
          <span className="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/60">
            Departments = Executors
          </span>
          <span className="px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800/60 font-bold">
            Ray = Final Authority
          </span>
        </div>
      </div>

      {/* Swimlane Filter Strip & Stepper Spine */}
      <div className="p-3 bg-slate-50 border-b border-slate-200 flex flex-col gap-2.5 shrink-0">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1">
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              <span>Operating Swimlane:</span>
            </span>
            {(['ALL', 'NEXUS', 'CLIENT'] as const).map(lane => (
              <button
                key={lane}
                type="button"
                onClick={() => setActiveLane(lane)}
                className={`px-2 py-0.5 rounded-md text-[10px] font-bold cursor-pointer transition-colors ${
                  activeLane === lane
                    ? 'bg-slate-900 text-white shadow-2xs'
                    : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
                }`}
              >
                {lane === 'ALL' ? 'All Streams' : lane === 'NEXUS' ? 'Nexus Track (Ray Decides)' : 'Client Track (GoClear / Client Decides)'}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSelectedGateId('RAY')}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-black font-mono flex items-center gap-1 cursor-pointer transition-all border ${
                selectedGateId === 'RAY'
                  ? 'bg-rose-600 text-white border-rose-700 shadow-xs'
                  : 'bg-white text-rose-700 border-rose-200 hover:bg-rose-50'
              }`}
            >
              <UserCheck className="w-3 h-3" />
              <span>Gate 06: Ray Sign-Off Queue ({(localItems.RAY || []).length})</span>
            </button>

            <button
              type="button"
              onClick={() => setCurrentPage('business-hub')}
              className="flex items-center gap-1 text-[11px] font-bold text-blue-600 hover:text-blue-800 bg-white hover:bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200 cursor-pointer transition-colors"
            >
              <span>Business Hub</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* THE 6 INTERACTIVE GATES WITH ANIMATED FLOW SPINE */}
        {/* ------------------------------------------------------------- */}
        <div className="relative">
          {/* Visual Connector Spine Line behind the gates */}
          <div className="hidden md:block absolute top-1/2 left-4 right-4 h-0.5 -translate-y-1/2 bg-slate-200 -z-0" />

          <div className="grid grid-cols-2 md:grid-cols-6 gap-2 relative z-10">
            {WORKFLOW_GATES.map((gate, index) => {
              const count = (localItems[gate.id] || []).filter(item => activeLane === 'ALL' || item.lane === activeLane).length;
              const isSelected = selectedGateId === gate.id;
              const Icon = gate.icon;

              return (
                <button
                  key={gate.id}
                  type="button"
                  onClick={() => {
                    setSelectedGateId(gate.id);
                    setSelectedItem(null);
                  }}
                  className={`relative p-2.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? `${gate.color} ring-2 ring-blue-500/40 shadow-sm font-semibold`
                      : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <span className="text-[9px] font-mono font-bold text-slate-400">
                        GATE 0{gate.order}
                      </span>
                      <span className="px-1.5 py-0.2 rounded-full text-[9px] font-black bg-slate-100 text-slate-800 border border-slate-200">
                        {count}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 font-bold text-xs">
                      <Icon className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{gate.name}</span>
                    </div>
                  </div>

                  <div className="mt-2 pt-1 border-t border-slate-200/60 flex items-center justify-between text-[9px] text-slate-500">
                    <span className="truncate font-mono">{gate.owner}</span>
                    {isSelected && <ChevronRight className="w-3 h-3 text-blue-600 shrink-0" />}
                  </div>

                  {/* Flow Pulse Indicator */}
                  {index < WORKFLOW_GATES.length - 1 && (
                    <div className="hidden md:flex absolute -right-2 top-1/2 -translate-y-1/2 z-20 pointer-events-none items-center justify-center">
                      <div className="w-4 h-4 rounded-full bg-white border border-slate-300 shadow-2xs flex items-center justify-center">
                        <ArrowRight className="w-2.5 h-2.5 text-slate-500" />
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Gate Inspection Panel & Detail Drawer */}
      <div className="p-3.5 flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Gate Project List (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-2 min-h-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-black text-slate-900 uppercase tracking-wider">
                Current Projects At Gate: {selectedGate.name}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                ({itemsInSelectedGate.length} active)
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              Role: {selectedGate.roleType}
            </span>
          </div>

          <p className="text-xs text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-200 leading-relaxed">
            <strong>Gate Policy:</strong> {selectedGate.description}
          </p>

          <div className="space-y-2 overflow-y-auto max-h-80 pr-1 custom-scrollbar">
            {itemsInSelectedGate.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl">
                No active projects currently at this gate for the selected filter.
              </div>
            ) : (
              itemsInSelectedGate.map(item => {
                const isItemActive = selectedItem?.id === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                      isItemActive
                        ? 'border-blue-500 bg-blue-50/50 shadow-xs ring-1 ring-blue-400'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-bold text-xs text-slate-900">
                            {item.title}
                          </span>
                          <span
                            className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${
                              item.lane === 'CLIENT'
                                ? 'bg-purple-100 text-purple-800 border border-purple-200'
                                : 'bg-blue-100 text-blue-800 border border-blue-200'
                            }`}
                          >
                            {item.lane}
                          </span>
                          <span className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border ${
                            item.authorized
                              ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                              : 'bg-slate-100 text-slate-600 border-slate-200'
                          }`}>
                            {item.status}
                          </span>
                        </div>

                        {/* 6-Stage Gate Stepper Indicator Dots */}
                        <div className="flex items-center gap-1 pt-0.5">
                          <span className="text-[8px] font-mono text-slate-400 mr-1">Progress:</span>
                          {[1, 2, 3, 4, 5, 6].map(step => {
                            const isCompleted = step < item.gateOrder || item.authorized;
                            const isCurrent = step === item.gateOrder && !item.authorized;
                            return (
                              <div
                                key={step}
                                className={`w-2 h-2 rounded-full transition-all ${
                                  isCompleted
                                    ? 'bg-emerald-500'
                                    : isCurrent
                                    ? 'bg-blue-600 ring-2 ring-blue-300 animate-pulse'
                                    : 'bg-slate-200'
                                }`}
                                title={`Gate 0${step}`}
                              />
                            );
                          })}
                          <span className="text-[8px] font-mono text-slate-500 ml-1">
                            In Stage: {item.timeInStage}
                          </span>
                        </div>

                        <p className="text-[11px] text-slate-600">
                          <strong>Next Action:</strong> {item.nextAction}
                        </p>
                      </div>

                      {/* Right Action / Authorize Button for Ray Gate */}
                      <div className="flex items-center gap-1 shrink-0">
                        {item.gate === 'RAY' && !item.authorized && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedItem(item);
                              setIsRayModalOpen(true);
                            }}
                            className="px-2 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-[10px] font-black cursor-pointer shadow-xs active:scale-95 transition-all flex items-center gap-1"
                          >
                            <UserCheck className="w-3 h-3" />
                            <span>Sign Off</span>
                          </button>
                        )}

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onSelectProject) onSelectProject(item.id);
                            setCurrentPage('business-hub');
                          }}
                          className="p-1 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                          title="View in Business Hub"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {item.recommenderNote && (
                      <div className="mt-2 text-[10px] text-slate-500 bg-slate-50 p-1.5 rounded border border-slate-200/80 font-mono">
                        {item.recommenderNote}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Detail Card & Strategic Authorization Dossier (5 cols) */}
        <div className="lg:col-span-5 flex flex-col justify-between bg-slate-50/80 p-3 rounded-xl border border-slate-200">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <span className="text-xs font-black text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                {selectedItem ? 'Selected Project Gate Dossier' : 'Gate Authority & Principles'}
              </span>
              <span className="text-[9px] font-mono text-slate-400">
                Canonical Handoff Rules
              </span>
            </div>

            {selectedItem ? (
              <div className="mt-3 space-y-2.5">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block font-mono">Project Title</span>
                  <p className="text-xs font-bold text-slate-900">{selectedItem.title}</p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="bg-white p-2 rounded-lg border border-slate-200">
                    <span className="text-[9px] font-bold text-slate-400 uppercase block font-mono">Current Owner</span>
                    <span className="font-semibold text-slate-800">{selectedItem.owner}</span>
                  </div>
                  <div className="bg-white p-2 rounded-lg border border-slate-200">
                    <span className="text-[9px] font-bold text-slate-400 uppercase block font-mono">Status</span>
                    <span className={`font-bold ${selectedItem.authorized ? 'text-emerald-700' : 'text-blue-700'}`}>
                      {selectedItem.status}
                    </span>
                  </div>
                </div>

                <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                  <span className="text-[9px] font-bold text-slate-400 uppercase block font-mono">Next Mandatory Action</span>
                  <p className="text-xs text-slate-800 font-medium mt-0.5">{selectedItem.nextAction}</p>
                </div>

                {selectedItem.recommenderNote && (
                  <div className="bg-amber-50/80 p-2.5 rounded-lg border border-amber-200/80">
                    <span className="text-[9px] font-bold text-amber-900 uppercase block flex items-center gap-1 font-mono">
                      <Sparkles className="w-2.5 h-2.5 text-amber-600" /> Analyst / Recommender Synthesis
                    </span>
                    <p className="text-[11px] text-amber-950 mt-0.5 leading-relaxed">
                      {selectedItem.recommenderNote}
                    </p>
                  </div>
                )}

                {/* If selected item is at Gate 06 (Ray Sign-Off) */}
                {selectedItem.gate === 'RAY' && !selectedItem.authorized && (
                  <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 space-y-2">
                    <div className="flex items-center gap-1.5 text-rose-900 font-bold text-xs">
                      <UserCheck className="w-3.5 h-3.5 text-rose-600" />
                      <span>Ray Strategic Sign-Off Required</span>
                    </div>
                    <p className="text-[10.5px] text-rose-800">
                      This project has passed all automated and analytical gates. Only Ray Davis can authorize capital allocation and production launch.
                    </p>
                    <button
                      type="button"
                      onClick={() => setIsRayModalOpen(true)}
                      className="w-full py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-black text-xs transition-all shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>Open Ray Strategic Authorization Modal</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-3 space-y-2 text-xs text-slate-600">
                <div className="p-2.5 rounded-lg bg-white border border-slate-200 space-y-1">
                  <span className="font-bold text-slate-900 block text-xs">No Intermediate Downstream Loops</span>
                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    Once Research closes information gaps and completes the fixed questionnaire, ownership formally transfers to Atlas, Clyde, or Finance. Research does NOT remain in downstream execution loops.
                  </p>
                </div>

                <div className="p-2.5 rounded-lg bg-white border border-slate-200 space-y-1">
                  <span className="font-bold text-slate-900 block text-xs">Non-Binary AI Recommendations</span>
                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    Neither Atlas nor Clyde autonomously approve transactions or commitments. Atlas recommends business models; Clyde recommends funding products.
                  </p>
                </div>

                <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 space-y-1 text-emerald-950">
                  <span className="font-bold block text-xs">Final Authority</span>
                  <p className="text-[11px] leading-relaxed">
                    For Client Cases (GoClear): <strong>Final Decision = Client</strong>.<br />
                    For Nexus Cases: <strong>Final Decision = Ray</strong>.
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-3 pt-2.5 border-t border-slate-200 flex items-center justify-between">
            <span className="text-[10px] text-slate-500 font-mono">Durable State: Supabase</span>
            <button
              type="button"
              onClick={() => setCurrentPage('business-hub')}
              className="text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
            >
              Open Full Business Hub →
            </button>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* IN-PLACE RAY STRATEGIC AUTHORIZATION MODAL */}
      {/* ========================================================================= */}
      {isRayModalOpen && selectedItem && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-lg w-full border border-slate-200 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-4 py-3 bg-gradient-to-r from-rose-900 to-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-rose-600/30 border border-rose-500/40">
                  <UserCheck className="w-5 h-5 text-rose-400" />
                </div>
                <div>
                  <h3 className="font-black text-sm uppercase tracking-wide">
                    Executive Strategic Authorization
                  </h3>
                  <p className="text-[10px] text-rose-200 font-mono">
                    Authority: Ray Davis (Sole Strategic Owner)
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsRayModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                <span className="text-[10px] font-bold text-slate-400 uppercase block font-mono">Subject Project</span>
                <h4 className="font-black text-slate-900 text-sm mt-0.5">{selectedItem.title}</h4>
                <div className="flex items-center gap-2 mt-1.5 text-[10px] font-mono">
                  <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-bold">
                    Lane: {selectedItem.lane}
                  </span>
                  <span className="text-slate-500">Gate: 06 (Ray Strategic Sign-Off)</span>
                </div>
              </div>

              {selectedItem.recommenderNote && (
                <div className="bg-amber-50 p-3 rounded-xl border border-amber-200 text-amber-950">
                  <span className="text-[10px] font-bold text-amber-800 uppercase block font-mono">
                    Recommender Synthesis (Atlas / Clyde)
                  </span>
                  <p className="text-[11px] mt-1 leading-relaxed">
                    {selectedItem.recommenderNote}
                  </p>
                </div>
              )}

              {/* Ray Guidance Input */}
              <div>
                <label className="text-[11px] font-bold text-slate-700 block mb-1">
                  Owner Directives / Launch Guidance (Optional):
                </label>
                <textarea
                  value={rayGuidanceText}
                  onChange={(e) => setRayGuidanceText(e.target.value)}
                  placeholder="e.g. Approved with strict $1.5k cap. Re-verify conversion metrics after 14 days."
                  rows={2}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-rose-500/30 resize-none font-sans"
                />
              </div>

              <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-950 text-[10.5px]">
                <strong>Operating Impact:</strong> Approving this gate unblocks downstream execution immediately. Worker daemons will begin production provisioning.
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsRayModalOpen(false)}
                className="px-3 py-1.5 rounded-lg text-slate-600 hover:text-slate-800 font-bold text-xs cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleAuthorizeRay(selectedItem)}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs transition-all shadow-sm active:scale-95 cursor-pointer flex items-center gap-1.5"
              >
                <Check className="w-4 h-4" />
                <span>Confirm Sign-Off as Ray (+150 XP)</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
