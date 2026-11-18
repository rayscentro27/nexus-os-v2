import React, { useState } from 'react';
import {
  Briefcase,
  TrendingUp,
  ShieldCheck,
  Building2,
  DollarSign,
  Layers,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  ExternalLink,
  Search,
  Filter,
  Check,
  X,
  FileText,
  UserCheck,
  Info,
  ChevronRight,
  RefreshCw,
  FolderGit2,
  HelpCircle,
  Database,
  Award,
  ChevronDown,
  Lock,
  ArrowUpRight
} from 'lucide-react';
import {
  BusinessHubTab,
  OpportunityItem,
  FormalHandoffItem,
  FundingCaseItem,
  FundingProductBankItem,
  NAICSGovernanceProfile,
  BankabilityChecklistItem,
  FundingRecommendationState,
  VerificationEvidenceStatus,
  OpportunityWorkflowState
} from '../types';
// These panes have no connected live source; keep their existing structure empty.
const NO_LIVE_FORMAL_HANDOFFS: any[] = [];
const NO_LIVE_OPPORTUNITIES: any[] = [];
const NO_LIVE_BANKABILITY_CHECKLIST: any[] = [];
const NO_LIVE_NAICS_GOVERNANCE: NAICSGovernanceProfile[] = [];
const NO_LIVE_FUNDING_CASES: any[] = [];
const NO_LIVE_FUNDING_PRODUCTS: any[] = [];
const NO_LIVE_BUSINESS_CREDIT_PRODUCTS: any[] = [];
const NO_LIVE_OPPORTUNITY_COMPONENTS: any[] = [];
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { UnavailableState } from '../components/live/UnavailableState';
import { ASSETS } from '../data/assets';
import { ExecutiveDossierModal, DossierData } from '../components/common/ExecutiveDossierModal';
import { createDossierFromOpportunity, createDossierFromFundingCase } from '../data/dossierData';

type ExtendedBusinessHubTab = 'commerce' | BusinessHubTab;

export const BusinessHubPage: React.FC = () => {
  const { sendMessage, commerceOffers, navigateToObject } = useNexus();
  const [activeTab, setActiveTab] = useState<ExtendedBusinessHubTab>('commerce');
  const [dossierModalOpen, setDossierModalOpen] = useState(false);
  const [activeDossierData, setActiveDossierData] = useState<DossierData | null>(null);

  const handleOpenOppDossier = (opp: OpportunityItem) => {
    setActiveDossierData(createDossierFromOpportunity(opp));
    setDossierModalOpen(true);
  };

  const handleOpenFundingDossier = (fc: FundingCaseItem) => {
    setActiveDossierData(createDossierFromFundingCase(fc));
    setDossierModalOpen(true);
  };

  // Opportunities State
  const [opportunities, setOpportunities] = useState<OpportunityItem[]>(NO_LIVE_OPPORTUNITIES);
  const [selectedOppId, setSelectedOppId] = useState<string>(NO_LIVE_OPPORTUNITIES[0]?.id || '');
  const [oppSearch, setOppSearch] = useState('');
  const [oppFilter, setOppFilter] = useState<'ALL' | 'RAY_REVIEW_REQUIRED' | 'FINAL_SYNTHESIS' | 'FUNDING_REVIEW' | 'BUSINESS_PLAN_BUILD'>('ALL');

  // Business Creation State
  const [creationSubTab, setCreationSubTab] = useState<'NEW_BUSINESS' | 'EXISTING_AUDIT'>('NEW_BUSINESS');
  const [selectedNaicsProfile, setSelectedNaicsProfile] = useState<NAICSGovernanceProfile>({} as NAICSGovernanceProfile);

  // Funding / Clyde State
  const [fundingLane, setFundingLane] = useState<'CLIENT / GOCLEAR' | 'NEXUS / RAY'>('NEXUS / RAY');
  const [selectedFundingCaseId, setSelectedFundingCaseId] = useState<string>('fnd-n-001');

  // Knowledge Banks State
  const [knowledgeSubTab, setKnowledgeSubTab] = useState<'FUNDING_PRODUCT_BANK' | 'CREDIT_PRODUCT_BANK' | 'OPPORTUNITY_BANK' | 'COMPONENT_BANK'>('FUNDING_PRODUCT_BANK');
  const [evidenceFilter, setEvidenceFilter] = useState<'ALL' | VerificationEvidenceStatus>('ALL');

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const selectedOpp = opportunities.find(o => o.id === selectedOppId) || opportunities[0];
  const selectedFundingCase: any = undefined;

  // Telemetry Calculations
  const activeOpportunitiesCount = opportunities.length;
  const rayReviewOppCount = opportunities.filter(o => o.currentState === 'RAY_REVIEW_REQUIRED').length;
  const rayReviewFundingCount = NO_LIVE_FUNDING_CASES.filter(c => c.decisionAuthority === 'WAITING ON RAY' && c.currentFit === 'CURRENT MATCH').length;
  const totalRayRequiredCount = rayReviewOppCount + rayReviewFundingCount;
  const clientDecisionsRequiredCount = NO_LIVE_FUNDING_CASES.filter(c => c.decisionAuthority === 'WAITING ON CLIENT').length;

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-xs font-semibold shadow-xl border border-slate-700 flex items-center gap-2 animate-in fade-in duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* ======================================================================= */}
      {/* 1. TOP EXECUTIVE HEADER & GOVERNANCE BANNER                             */}
      {/* ======================================================================= */}
      <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-2xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center shadow-xs">
                <Briefcase className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold text-slate-900 tracking-tight">Business Hub</h1>
                  <span className="px-2 py-0.5 rounded-full bg-blue-50 border border-blue-200/70 text-blue-700 text-[11px] font-bold">
                    Atlas (Commercial) · Clyde (Funding)
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Connected Commercial Pipeline & Bankability Architecture · Workflow Governs Authority
                </p>
              </div>
            </div>
          </div>

          {/* Architectural Badge & Quick Stats */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs">
              <span className="text-slate-500 font-semibold">Workflow Authority:</span>
              <span className="font-extrabold text-slate-800">Ray (Final Decision)</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200/70 text-xs text-amber-800 font-bold">
              <Clock className="w-3.5 h-3.5 text-amber-600" />
              <span>Ray Review Required: Not connected</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-blue-50 border border-blue-200/70 text-xs text-blue-800 font-bold">
              <UserCheck className="w-3.5 h-3.5 text-blue-600" />
              <span>Client Decisions: Not connected</span>
            </div>
          </div>
        </div>

        {/* Operating Architecture Principles Strip */}
        <div className="mt-4 pt-3.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-600">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="font-bold text-slate-700">OPERATING MODEL:</span>
            <span>Workflow = Authority</span>
            <span className="text-slate-300">|</span>
            <span>AI = Analyst & Recommender</span>
            <span className="text-slate-300">|</span>
            <span>Supabase = Durable State</span>
            <span className="text-slate-300">|</span>
            <span>Ray = Final Strategic Authority</span>
          </div>

          <div className="flex items-center gap-2 text-slate-500">
            <span className="bg-slate-100 px-2 py-0.5 rounded text-[10px] font-mono font-bold text-slate-600">
              LIVE COMMERCE READ MODEL
            </span>
          </div>
        </div>
      </div>

      {/* ======================================================================= */}
      {/* 2. SUB-NAVIGATION TABS                                                  */}
      {/* ======================================================================= */}
      <div className="flex items-center justify-between border-b border-slate-200">
        <nav className="flex space-x-2 -mb-px overflow-x-auto">
          {[
            { id: 'commerce', label: 'COMMERCE & OFFERS', count: commerceOffers.length, icon: Briefcase },
            { id: 'overview', label: 'VENTURE PIPELINE (NOT CONNECTED)', count: null, icon: Layers, unavailable: true },
            { id: 'opportunities', label: 'OPPORTUNITIES (NOT CONNECTED)', count: null, icon: TrendingUp, unavailable: true },
            { id: 'creation', label: 'BANKABILITY & NAICS (NOT CONNECTED)', count: null, icon: Building2, unavailable: true },
            { id: 'funding', label: 'FUNDING (NOT CONNECTED)', count: null, icon: DollarSign, unavailable: true },
            { id: 'knowledge-banks', label: 'KNOWLEDGE BANKS (NOT CONNECTED)', count: null, icon: Layers, unavailable: true }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                disabled={tab.unavailable}
                onClick={() => !tab.unavailable && setActiveTab(tab.id as ExtendedBusinessHubTab)}
                className={`py-3 px-4 font-bold text-xs uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${tab.unavailable ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'} ${
                  isActive
                    ? 'border-blue-600 text-blue-600 bg-blue-50/40 rounded-t-lg'
                    : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
                {tab.count !== null && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      isActive ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* ======================================================================= */}
      {/* TAB 0: COMMERCE & OFFERS (PRODUCT TRUTH VS CLAIMS & STAGE GATES)        */}
      {/* ======================================================================= */}
      {activeTab === 'commerce' && (
        <div className="space-y-5">
          {commerceOffers.map(offer => (
            <div key={offer.id} className="space-y-5">
              {/* Product Hero Truth Card */}
              <div className="rounded-2xl bg-white border border-slate-200/90 p-5 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                <div className="lg:col-span-4 rounded-xl overflow-hidden border border-slate-200 bg-slate-100 aspect-4/3">
                  <img
                    src={ASSETS.holidayMugProduct}
                    alt={offer.title}
                    referrerPolicy="no-referrer"
                    className="w-full h-full object-cover"
                  />
                </div>

                <div className="lg:col-span-8 space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-slate-100">
                    <div>
                      <div className="text-[11px] font-mono text-slate-500">
                        Printify Product ID: {offer.externalProductId} · Variant: {offer.variantId}
                      </div>
                      <h2 className="text-lg font-bold text-slate-900 mt-0.5">{offer.title}</h2>
                      <p className="text-xs text-slate-500 mt-0.5">{offer.variantSpec}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => navigateToObject('projects', offer.projectId, 'project')}
                      className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 cursor-pointer"
                    >
                      Project: {offer.projectName} →
                    </button>
                  </div>

                  {/* Verified Unit Economics Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                      <div className="text-slate-500">Base Cost</div>
                      <div className="text-base font-bold text-slate-900 tabular-nums">
                        ${offer.productTruth.baseCost.toFixed(2)}
                      </div>
                      <TruthBadge truth={offer.productTruth.baseCostTruth} />
                    </div>
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                      <div className="text-slate-500">US Ship (1st / Addl)</div>
                      <div className="text-base font-bold text-slate-900 tabular-nums">
                        ${offer.productTruth.firstItemShipping.toFixed(2)} / ${offer.productTruth.additionalItemShipping.toFixed(2)}
                      </div>
                      <TruthBadge truth={offer.productTruth.firstItemShippingTruth} />
                    </div>
                    <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200/80 space-y-1">
                      <div className="text-slate-500">Staged Price</div>
                      <div className="text-base font-bold text-slate-900 tabular-nums">
                        ${offer.productTruth.stagedPrice.toFixed(2)}
                      </div>
                      <TruthBadge truth={offer.productTruth.stagedPriceTruth} />
                    </div>
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                      <div className="text-slate-500">Gross Margin (Pre-Ads)</div>
                      <div className="text-base font-bold text-slate-900 tabular-nums">
                        ${offer.productTruth.estimatedGrossMarginDollar.toFixed(2)} ({offer.productTruth.estimatedGrossMarginPct}%)
                      </div>
                      <TruthBadge truth={offer.productTruth.marginTruth} />
                    </div>
                  </div>

                  {/* Separation: Interest Test vs Live Sales */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-blue-950">Stage A · Interest Test</span>
                        <span className="px-2 py-0.5 rounded bg-white text-blue-800 border border-blue-200 font-semibold text-[10px]">
                          {offer.interestTest.mode}
                        </span>
                      </div>
                      <p className="text-blue-900">
                        Captures waitlist demand without accepting live card payments.
                      </p>
                      <button
                        type="button"
                        onClick={() => navigateToObject('approvals', offer.interestTest.stageAApprovalId, 'approval')}
                        className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold cursor-pointer"
                      >
                        Review Stage A Approval
                      </button>
                    </div>

                    <div className="p-3.5 rounded-xl bg-rose-50/80 border border-rose-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-rose-950">Stage B · Live Sales</span>
                        <span className="px-2 py-0.5 rounded bg-rose-600 text-white font-semibold text-[10px]">
                          {offer.liveSales.checkoutStatus}
                        </span>
                      </div>
                      <p className="text-rose-900">
                        <strong>Reason:</strong> {offer.liveSales.blockerReason}
                      </p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <button
                          type="button"
                          onClick={() => navigateToObject('approvals', offer.liveSales.stageBApprovalId, 'approval')}
                          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-semibold cursor-pointer"
                        >
                          Stage B Gate
                        </button>
                        <button
                          type="button"
                          onClick={() => navigateToObject('settings')}
                          className="px-3 py-1.5 rounded-lg bg-white border border-rose-300 text-rose-800 font-semibold cursor-pointer"
                        >
                          Stripe Credential State
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Product Truth vs Marketing Claims Verification Table */}
              <div className="rounded-2xl bg-white border border-slate-200/90 overflow-hidden">
                <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">
                    Product Truth vs Marketing Claims Verification
                  </h3>
                  <span className="text-xs text-slate-500">
                    Estimates and proposed prices never displayed as verified facts
                  </span>
                </div>
                <div className="divide-y divide-slate-100">
                  {offer.claimsVsTruth.map((row, idx) => (
                    <div
                      key={idx}
                      className="px-5 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                    >
                      <div>
                        <div className="font-semibold text-slate-900">{row.claim}</div>
                        <div className="text-slate-500 mt-0.5">{row.note}</div>
                      </div>
                      <TruthBadge truth={row.verification} size="sm" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
          {commerceOffers.length === 0 && <UnavailableState>No commerce records were returned by the live Nexus read model.</UnavailableState>}
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 1: OVERVIEW                                                         */}
      {/* ======================================================================= */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Executive KPI Grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
            <div className="rounded-2xl bg-white border border-slate-200/80 p-4 shadow-2xs">
              <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Active Opportunities</div>
              <div className="text-2xl font-black text-slate-900 mt-1">{activeOpportunitiesCount}</div>
              <div className="text-[11px] text-emerald-600 font-semibold mt-1 flex items-center gap-1">
                <span>Atlas Owned: 4</span>
              </div>
            </div>

            <div className="rounded-2xl bg-white border border-slate-200/80 p-4 shadow-2xs">
              <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Businesses in Creation</div>
              <div className="text-2xl font-black text-slate-900 mt-1">3</div>
              <div className="text-[11px] text-blue-600 font-semibold mt-1">
                <span>Bankability 94% Avg</span>
              </div>
            </div>

            <div className="rounded-2xl bg-white border border-slate-200/80 p-4 shadow-2xs">
              <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Funding Cases</div>
              <div className="text-sm font-semibold text-slate-500 mt-1">Not connected</div>
              <div className="text-[11px] text-indigo-600 font-semibold mt-1">
                <span>Clyde Match Engine</span>
              </div>
            </div>

            <div className="rounded-2xl bg-amber-50/70 border border-amber-200 p-4 shadow-2xs">
              <div className="text-[11px] font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-600" />
                <span>Ray Review Required</span>
              </div>
              <div className="text-sm font-semibold text-slate-500 mt-1">Not connected</div>
              <div className="text-[11px] text-amber-700 font-semibold mt-1">
                <span>Final Strategic Gate</span>
              </div>
            </div>

            <div className="rounded-2xl bg-blue-50/70 border border-blue-200 p-4 shadow-2xs">
              <div className="text-[11px] font-bold text-blue-800 uppercase tracking-wider flex items-center gap-1">
                <UserCheck className="w-3.5 h-3.5 text-blue-600" />
                <span>Client Decisions Req.</span>
              </div>
              <div className="text-sm font-semibold text-slate-500 mt-1">Not connected</div>
              <div className="text-[11px] text-blue-700 font-semibold mt-1">
                <span>GoClear Portal Queue</span>
              </div>
            </div>
          </div>

          {/* Visual Canonical Workflow Diagram */}
          <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-2xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <span>Canonical Business Workflow</span>
                  <span className="text-xs text-slate-400 font-normal">| Department Ownership at Handoff</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Research feeds initial packages; once handed off, owning department drives execution without intermediate loops.
                </p>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-slate-100 text-[11px] font-bold text-slate-700">
                End-to-End Governance
              </span>
            </div>

            {/* Workflow steps */}
            <div className="grid grid-cols-1 md:grid-cols-6 gap-2 relative">
              {[
                {
                  step: '01',
                  label: 'RESEARCH',
                  dept: 'Universal Feeder',
                  desc: 'Deterministic ingestion & closed gap questionnaire',
                  color: 'slate'
                },
                {
                  step: '02',
                  label: 'ATLAS',
                  dept: 'Opportunities',
                  desc: 'Business model, customer, & low-cost entry synthesis',
                  color: 'blue'
                },
                {
                  step: '03',
                  label: 'CREATION',
                  dept: 'If Required',
                  desc: 'Entity, bankability checklist, truthful NAICS',
                  color: 'indigo'
                },
                {
                  step: '04',
                  label: 'FINANCE',
                  dept: 'Treasury',
                  desc: 'Cash flow sensitivity, burn rate, & unit margins',
                  color: 'emerald'
                },
                {
                  step: '05',
                  label: 'CLYDE',
                  dept: 'Funding (If Capital Req)',
                  desc: 'Non-binary matching & lender verification',
                  color: 'sky'
                },
                {
                  step: '06',
                  label: 'RAY',
                  dept: 'Strategic Authority',
                  desc: 'Final authorization & execution approval',
                  color: 'amber'
                }
              ].map((s, idx) => (
                <div
                  key={s.step}
                  className={`p-3.5 rounded-xl border flex flex-col justify-between relative transition-all ${
                    s.color === 'amber'
                      ? 'bg-amber-50/70 border-amber-200 text-amber-900 ring-2 ring-amber-400/30'
                      : 'bg-slate-50 border-slate-200/80 text-slate-800'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 mb-1">
                      <span>STEP {s.step}</span>
                      {idx < 5 && <ArrowRight className="w-3.5 h-3.5 text-slate-400 hidden md:block" />}
                    </div>
                    <div className="text-xs font-black tracking-tight">{s.label}</div>
                    <div className="text-[10px] font-semibold text-blue-600 mt-0.5">{s.dept}</div>
                  </div>
                  <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">
                    {s.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Formal Handoffs Table */}
          <div className="rounded-2xl bg-white border border-slate-200/80 overflow-hidden shadow-2xs">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Recent Formal Handoffs
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Traceable department-to-department ownership transitions with verified timestamps
                </p>
              </div>
              <button
                type="button"
                onClick={() => showToast('Handoff audit ledger synchronized with Supabase durable state')}
                className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
                <span>Sync Durable Ledger</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2.5 px-4">From</th>
                    <th className="py-2.5 px-4">To</th>
                    <th className="py-2.5 px-4">Project / Package</th>
                    <th className="py-2.5 px-4">Owning Department</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4">Next Action</th>
                    <th className="py-2.5 px-4">Age</th>
                    <th className="py-2.5 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {NO_LIVE_FORMAL_HANDOFFS.map(h => (
                    <tr key={h.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4 font-bold text-slate-700">{h.from}</td>
                      <td className="py-3 px-4 font-bold text-blue-700">{h.to}</td>
                      <td className="py-3 px-4 font-semibold text-slate-900 max-w-xs truncate">
                        {h.project}
                      </td>
                      <td className="py-3 px-4 text-slate-600 font-medium">
                        {h.departmentOwner}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            h.status === 'READY FOR HANDOFF'
                              ? 'bg-amber-100 text-amber-800'
                              : h.status === 'HANDED OFF'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {h.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-600 text-[11px] max-w-sm truncate">
                        {h.nextAction}
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-mono text-[10px] whitespace-nowrap">
                        {h.age}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => {
                            if (h.to === 'Ray') {
                              setActiveTab('opportunities');
                              showToast(`Loaded ${h.project} for Ray strategic evaluation`);
                            } else if (h.to === 'Clyde') {
                              setActiveTab('funding');
                              showToast(`Routed to Clyde funding engine for ${h.project}`);
                            } else {
                              showToast(`Active owner: ${h.departmentOwner}`);
                            }
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center gap-1 cursor-pointer"
                        >
                          <span>Inspect</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 2: OPPORTUNITIES / ATLAS                                            */}
      {/* ======================================================================= */}
      {activeTab === 'opportunities' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Opportunity List & Filters (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-2xl bg-white border border-slate-200/80 p-4 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-blue-600" />
                  <span>Atlas Commercial Pipeline</span>
                </div>
                <span className="text-[11px] text-slate-500 font-semibold">{opportunities.length} Total</span>
              </div>

              {/* Search & Filter */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search opportunities or notebooks..."
                  value={oppSearch}
                  onChange={e => setOppSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>

              {/* Status filter chips */}
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: 'ALL', label: 'All' },
                  { id: 'RAY_REVIEW_REQUIRED', label: 'Ray Review Req.' },
                  { id: 'FINAL_SYNTHESIS', label: 'Final Synthesis' },
                  { id: 'FUNDING_REVIEW', label: 'Funding Review' },
                  { id: 'BUSINESS_PLAN_BUILD', label: 'Plan Build' }
                ].map(f => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setOppFilter(f.id as any)}
                    className={`px-2 py-0.5 rounded-lg text-[10px] font-bold transition-all cursor-pointer ${
                      oppFilter === f.id
                        ? 'bg-blue-600 text-white shadow-2xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Opportunities List Cards */}
            <div className="space-y-2.5">
              {opportunities
                .filter(o => {
                  if (oppFilter !== 'ALL' && o.currentState !== oppFilter) return false;
                  if (oppSearch && !o.opportunity.toLowerCase().includes(oppSearch.toLowerCase())) return false;
                  return true;
                })
                .map(opp => {
                  const isSelected = opp.id === selectedOppId;
                  return (
                    <div
                      key={opp.id}
                      onClick={() => setSelectedOppId(opp.id)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer text-left ${
                        isSelected
                          ? 'bg-blue-50/70 border-blue-400 shadow-xs ring-1 ring-blue-300'
                          : 'bg-white border-slate-200/80 hover:border-slate-300 hover:shadow-2xs'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[9px] font-extrabold uppercase tracking-wider ${
                            opp.currentState === 'RAY_REVIEW_REQUIRED'
                              ? 'bg-amber-100 text-amber-900 border border-amber-300'
                              : opp.currentState === 'FINAL_SYNTHESIS'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {opp.currentState.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[10px] font-semibold text-slate-400 font-mono">
                          {opp.entryTier.split(' ')[0]}
                        </span>
                      </div>

                      <h4 className="text-xs font-bold text-slate-900 mt-2 leading-snug">
                        {opp.opportunity}
                      </h4>

                      <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                        {opp.problem}
                      </p>

                      <div className="mt-3 pt-2.5 border-t border-slate-100/90 flex items-center justify-between text-[10px]">
                        <span className="text-slate-500 font-medium">Cap: {opp.capitalRequired}</span>
                        <span className="text-emerald-700 font-bold">Research {opp.researchCompleteness}%</span>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* Right Column: Atlas Recommendation Panel (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-2xs space-y-5">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 font-bold text-[10px]">
                      ATLAS RECOMMENDATION DOSSIER
                    </span>
                    <span className="text-xs font-mono text-slate-400">{selectedOpp.notebook}</span>
                  </div>
                  <h3 className="text-base font-extrabold text-slate-900 mt-1">
                    {selectedOpp.opportunity}
                  </h3>
                </div>

                <div className="text-right sm:text-right">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Strategic Principle</div>
                  <div className="text-xs font-extrabold text-indigo-700">Atlas Recommends · Ray Decides</div>
                </div>
              </div>

              {/* Core Parameters Table Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Target Customer</div>
                  <div className="font-semibold text-slate-800 mt-0.5">{selectedOpp.customer}</div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Business Model</div>
                  <div className="font-semibold text-slate-800 mt-0.5">{selectedOpp.businessModel}</div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Capital Required</div>
                  <div className="font-bold text-slate-900 mt-0.5">{selectedOpp.capitalRequired}</div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Lowest-Cost Entry</div>
                  <div className="font-semibold text-slate-800 mt-0.5">{selectedOpp.costFreeOption}</div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Business Hub Review</div>
                  <div className="font-bold text-emerald-600 mt-0.5">{selectedOpp.businessHubReview}</div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Finance Review</div>
                  <div className="font-bold text-emerald-600 mt-0.5">{selectedOpp.financeReview}</div>
                </div>
              </div>

              {/* Deep Analysis Sections */}
              <div className="space-y-3.5">
                {/* 1. WHY THIS COULD WORK */}
                <div className="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/80">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5 text-blue-700">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                    <span>Why This Could Work</span>
                  </h4>
                  <ul className="mt-2 space-y-1.5 text-xs text-slate-700">
                    {selectedOpp.atlasRecommendation.whyThisCouldWork.map((w, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-blue-500 font-bold">•</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* 2. WHAT NEXUS ALREADY HAS */}
                <div className="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/80">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5 text-indigo-700">
                    <Layers className="w-3.5 h-3.5 text-indigo-600" />
                    <span>What Nexus Already Has (Reusable Assets)</span>
                  </h4>
                  <ul className="mt-2 space-y-1.5 text-xs text-slate-700">
                    {selectedOpp.atlasRecommendation.whatNexusAlreadyHas.map((w, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-indigo-500 font-bold">•</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* 3. AFFILIATE / WHITE-LABEL OPTIONS & MARKETING */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-white border border-slate-200 text-xs">
                    <div className="text-[10px] font-bold text-slate-400 uppercase">White-Label / Reseller Options</div>
                    <p className="text-slate-700 mt-1 leading-relaxed">
                      {selectedOpp.atlasRecommendation.affiliateWhiteLabelOptions}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-white border border-slate-200 text-xs">
                    <div className="text-[10px] font-bold text-slate-400 uppercase">Marketing Approach</div>
                    <p className="text-slate-700 mt-1 leading-relaxed">
                      {selectedOpp.atlasRecommendation.marketingApproach}
                    </p>
                  </div>
                </div>

                {/* 4. RISKS */}
                <div className="p-3.5 rounded-xl bg-rose-50/60 border border-rose-200/70">
                  <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                    <span>Key Risks & Compliance Vectors</span>
                  </h4>
                  <ul className="mt-2 space-y-1 text-xs text-rose-800">
                    {selectedOpp.atlasRecommendation.risks.map((r, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-rose-500 font-bold">⚠️</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* 5. RECOMMENDED ACTION BANNER */}
                <div className="p-4 rounded-xl bg-gradient-to-r from-blue-900 to-indigo-950 text-white shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="text-[10px] font-bold text-blue-300 uppercase tracking-wider">
                      Atlas Recommendation
                    </div>
                    <div className="text-xs font-bold text-white mt-0.5">
                      {selectedOpp.atlasRecommendation.recommendedAction}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleOpenOppDossier(selectedOpp)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer border border-slate-700"
                    >
                      <FileText className="w-3.5 h-3.5 text-blue-400" />
                      <span>Executive Dossier</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => showToast(`Synthesizing Ray Strategic Brief for "${selectedOpp.opportunity}"`)}
                      className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
                    >
                      Submit to Ray
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 3: BUSINESS CREATION / BANKABILITY & NAICS GOVERNANCE               */}
      {/* ======================================================================= */}
      {activeTab === 'creation' && (
        <div className="space-y-6">
          {/* Sub-Tabs: New Business vs Existing Business Audit */}
          <div className="flex items-center justify-between">
            <div className="inline-flex p-1 rounded-xl bg-slate-100 border border-slate-200/80">
              <button
                type="button"
                onClick={() => setCreationSubTab('NEW_BUSINESS')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  creationSubTab === 'NEW_BUSINESS'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                NEW BUSINESS SETUP
              </button>
              <button
                type="button"
                onClick={() => setCreationSubTab('EXISTING_AUDIT')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  creationSubTab === 'EXISTING_AUDIT'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                EXISTING BUSINESS AUDIT (BANKABILITY)
              </button>
            </div>

            <span className="text-xs font-bold text-slate-500">
              Target Profile: Apex Data Intelligence LLC
            </span>
          </div>

          {/* CRITICAL MANDATORY GOVERNANCE NOTICE: Personal Credit Repair NOT Governed */}
          <div className="rounded-2xl bg-amber-50 border-2 border-amber-300 p-4 shadow-2xs">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-xl bg-amber-200 text-amber-900 flex items-center justify-center shrink-0 font-black">
                <AlertTriangle className="w-5 h-5 text-amber-800" />
              </div>
              <div>
                <h4 className="text-xs font-extrabold text-amber-900 uppercase tracking-wider">
                  PERSONAL CREDIT REPAIR: NOT YET GOVERNED
                </h4>
                <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                  Nexus OS identifies personal credit tier exclusively as an underwriting readiness factor. Nexus does
                  <strong> NOT </strong> execute automated credit-repair disputes, bureau challenge letters, or third-party credit repair filings.
                  Underwriting guidelines use stated founder scores for prime banking tiering only.
                </p>
              </div>
            </div>
          </div>

          {/* Bankability Checklist Grid */}
          <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-2xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  22-Point Institutional Bankability Matrix
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Prerequisites required for Tier 1 commercial lines without predatory broker markups
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs">
                  21 / 22 Criteria Verified
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {NO_LIVE_BANKABILITY_CHECKLIST.map(item => (
                <div
                  key={item.key}
                  className={`p-3.5 rounded-xl border flex flex-col justify-between ${
                    item.status === 'NOT_YET_GOVERNED'
                      ? 'bg-amber-50/50 border-amber-300'
                      : item.status === 'ACTION_REQUIRED'
                      ? 'bg-sky-50/50 border-sky-300'
                      : 'bg-slate-50/70 border-slate-200/80'
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-1">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        {item.category}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                          item.status === 'VERIFIED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : item.status === 'NOT_YET_GOVERNED'
                            ? 'bg-amber-200 text-amber-900'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {item.status.replace(/_/g, ' ')}
                      </span>
                    </div>

                    <h5 className="text-xs font-bold text-slate-900 mt-1.5">{item.label}</h5>
                    <p className="text-[11px] text-slate-600 mt-1 leading-snug">{item.detail}</p>

                    {item.notes && (
                      <div className="mt-2 p-1.5 rounded bg-white/80 border border-slate-200 text-[10px] text-slate-600 font-medium">
                        {item.notes}
                      </div>
                    )}
                  </div>

                  <div className="mt-2 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-400">
                    <span>Last checked: {item.lastChecked}</span>
                    <CheckCircle2
                      className={`w-3.5 h-3.5 ${
                        item.status === 'VERIFIED'
                          ? 'text-emerald-500'
                          : item.status === 'NOT_YET_GOVERNED'
                          ? 'text-amber-500'
                          : 'text-blue-500'
                      }`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* =================================================================== */}
          {/* 5. NAICS GOVERNANCE ENGINE (ACCURATE CLASSIFICATION FIRST)          */}
          {/* =================================================================== */}
          <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-2xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 font-bold text-[10px]">
                    NAICS GOVERNANCE ARCHITECTURE
                  </span>
                  <span className="text-xs font-bold text-slate-900">{selectedNaicsProfile.entityName}</span>
                </div>
                <h3 className="text-sm font-black text-slate-900 mt-1">
                  Accurate Classification First · Funding Optimization Second
                </h3>
              </div>

              <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-600 max-w-sm">
                <span className="font-bold text-slate-800">Compliance Standard:</span> Nexus OS never selects false low-risk NAICS codes. We compare legitimate classifications when more than one accurately describes the enterprise.
              </div>
            </div>

            {/* Current vs Actual Activity */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-[10px] font-bold text-slate-400 uppercase">Current NAICS on File</div>
                <div className="text-xs font-bold text-slate-800 mt-1 font-mono">
                  {selectedNaicsProfile.currentNaics}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  Initial registration code filed with state Articles of Organization
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-[10px] font-bold text-slate-400 uppercase">Actual Primary Business Activity</div>
                <div className="text-xs font-semibold text-slate-900 mt-1 leading-snug">
                  {selectedNaicsProfile.actualPrimaryBusinessActivity}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  Verified through active invoices, contracts, and depository transaction memos
                </div>
              </div>
            </div>

            {/* Truthfully Defensible Alternatives Comparison */}
            <div>
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
                Truthfully Defensible Alternative Classifications
              </h4>

              <div className="space-y-2.5">
                {selectedNaicsProfile.truthfullyDefensibleAlternatives.map((alt, idx) => (
                  <div
                    key={alt.code}
                    className="p-3.5 rounded-xl border border-slate-200 hover:border-blue-300 bg-white hover:bg-blue-50/30 transition-all flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-black text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
                          {alt.code}
                        </span>
                        <span className="font-bold text-slate-800">{alt.title}</span>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-bold">
                          Defensibility: {alt.defensibilityScore}%
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600">{alt.description}</p>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="text-[10px] font-bold text-slate-400">Funding Suitability</div>
                      <div className="text-[11px] font-bold text-blue-700">{alt.fundingSuitability}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommended NAICS & Implication */}
            <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-blue-800 uppercase tracking-wider">
                  Recommended Primary Code
                </span>
                <span className="px-2 py-0.5 rounded bg-blue-600 text-white font-mono font-bold text-[10px]">
                  541512
                </span>
              </div>
              <h5 className="font-extrabold text-slate-900 text-sm">{selectedNaicsProfile.recommendedNaics}</h5>
              <p className="text-slate-700 leading-relaxed text-[11px]">
                <strong>Why it fits:</strong> {selectedNaicsProfile.whyItFits}
              </p>
              <p className="text-slate-700 leading-relaxed text-[11px]">
                <strong>Funding implication:</strong> {selectedNaicsProfile.fundingImplication}
              </p>
              <p className="text-amber-800 leading-relaxed text-[11px]">
                <strong>Compliance governance:</strong> {selectedNaicsProfile.complianceConcerns}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 4: BUSINESS FUNDING / CLYDE (NON-BINARY MATCHING)                   */}
      {/* ======================================================================= */}
      {activeTab === 'funding' && (
        <div className="space-y-6">
          {/* Lane Selector Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl bg-white border border-slate-200/80 p-4 shadow-2xs">
            <div>
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Funding Engine</div>
              <h3 className="text-base font-black text-slate-900 flex items-center gap-2">
                <span>Clyde Commercial Underwriting Matching</span>
                <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 text-[10px] font-bold">
                  Non-Binary Fit Engine
                </span>
              </h3>
            </div>

            {/* Lane Selector */}
            <div className="inline-flex p-1 rounded-xl bg-slate-100 border border-slate-200/80">
              <button
                type="button"
                onClick={() => setFundingLane('CLIENT / GOCLEAR')}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  fundingLane === 'CLIENT / GOCLEAR'
                    ? 'bg-blue-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                CLIENT / GOCLEAR
              </button>
              <button
                type="button"
                onClick={() => setFundingLane('NEXUS / RAY')}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  fundingLane === 'NEXUS / RAY'
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                NEXUS / RAY
              </button>
            </div>
          </div>

          {/* Decision Authority Rule Strip */}
          <div className="p-3.5 rounded-xl bg-slate-900 text-white flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span className="font-bold">Clyde Role:</span>
              <span className="text-slate-300">Clyde <strong>RECOMMENDS</strong> underwriting fits · Clyde does <strong>NOT APPROVE</strong> or execute.</span>
            </div>

            <div className="flex items-center gap-2 font-mono text-[11px]">
              <span className="text-slate-400">Final Decision:</span>
              <span className="font-bold text-amber-300">
                {fundingLane === 'CLIENT / GOCLEAR' ? 'FINAL DECISION = CLIENT' : 'FINAL DECISION = RAY'}
              </span>
            </div>
          </div>

          {/* Funding Cases Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {NO_LIVE_FUNDING_CASES.filter(c => c.lane === fundingLane).map(fCase => {
              const isSelected = fCase.id === selectedFundingCaseId;

              // Color badges for non-binary states
              const fitColorMap: Record<FundingRecommendationState, string> = {
                'CURRENT MATCH': 'bg-emerald-100 text-emerald-900 border-emerald-300',
                'NEAR MATCH': 'bg-blue-100 text-blue-900 border-blue-300',
                'PATH TO ELIGIBILITY': 'bg-amber-100 text-amber-900 border-amber-300',
                'ALTERNATIVE PRODUCT MATCH': 'bg-purple-100 text-purple-900 border-purple-300',
                'NOT APPROPRIATE': 'bg-rose-100 text-rose-900 border-rose-300'
              };

              return (
                <div
                  key={fCase.id}
                  onClick={() => setSelectedFundingCaseId(fCase.id)}
                  className={`p-5 rounded-2xl border transition-all cursor-pointer text-left flex flex-col justify-between ${
                    isSelected
                      ? 'bg-white border-blue-500 shadow-md ring-2 ring-blue-200'
                      : 'bg-white border-slate-200/80 hover:border-slate-300 hover:shadow-2xs'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          {fCase.lenderProgram}
                        </span>
                        <h4 className="text-sm font-extrabold text-slate-900">{fCase.product}</h4>
                      </div>

                      <span
                        className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider border ${
                          fitColorMap[fCase.currentFit]
                        }`}
                      >
                        {fCase.currentFit}
                      </span>
                    </div>

                    {/* Potential Amount & Category */}
                    <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                      <div>
                        <div className="text-[10px] text-slate-400 font-bold uppercase">Potential Amount</div>
                        <div className="text-sm font-black text-slate-900">{fCase.potentialAmount}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-[10px] text-slate-400 font-bold uppercase">Evidence Status</div>
                        <div className="text-[11px] font-bold text-blue-600">{fCase.evidenceStatus}</div>
                      </div>
                    </div>

                    {/* Requirements Met vs Missing */}
                    <div className="space-y-2 text-xs">
                      <div>
                        <div className="text-[10px] font-bold text-emerald-700 uppercase">Requirements Met</div>
                        <ul className="mt-1 space-y-0.5 text-[11px] text-slate-600">
                          {fCase.requirementsMet.map((m, idx) => (
                            <li key={idx} className="flex items-start gap-1.5">
                              <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                              <span>{m}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {fCase.requirementsMissing.length > 0 && (
                        <div>
                          <div className="text-[10px] font-bold text-amber-700 uppercase">Missing / Improvable</div>
                          <ul className="mt-1 space-y-0.5 text-[11px] text-slate-600">
                            {fCase.requirementsMissing.map((m, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                                <span>{m}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Clyde Recommendation Note */}
                    <div className="p-2.5 rounded-lg bg-blue-50/60 border border-blue-100 text-[11px] text-blue-900 font-medium">
                      {fCase.recommendationNote}
                    </div>
                  </div>

                  {/* Footer Action & Authority */}
                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-[11px] font-bold text-amber-800">
                      {fCase.decisionAuthority}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenFundingDossier(fCase);
                        }}
                        className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs flex items-center gap-1 cursor-pointer"
                        title="Generate printable Underwriting Dossier"
                      >
                        <FileText className="w-3 h-3 text-blue-600" />
                        <span>Dossier</span>
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          showToast(`Application packet prepared for ${fCase.product}`);
                        }}
                        className="px-3 py-1 rounded-lg bg-slate-900 text-white font-bold text-xs hover:bg-slate-800 cursor-pointer"
                      >
                        Package Case
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 5: KNOWLEDGE BANKS                                                  */}
      {/* ======================================================================= */}
      {activeTab === 'knowledge-banks' && (
        <div className="space-y-6">
          {/* Sub-Tabs: 4 Banks */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="inline-flex p-1 rounded-xl bg-slate-100 border border-slate-200/80 overflow-x-auto">
              {[
                { id: 'FUNDING_PRODUCT_BANK', label: 'FUNDING PRODUCT BANK' },
                { id: 'CREDIT_PRODUCT_BANK', label: 'BUSINESS CREDIT PRODUCT BANK' },
                { id: 'OPPORTUNITY_BANK', label: 'OPPORTUNITY BANK' },
                { id: 'COMPONENT_BANK', label: 'COMPONENT BANK' }
              ].map(sub => (
                <button
                  key={sub.id}
                  type="button"
                  onClick={() => setKnowledgeSubTab(sub.id as any)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
                    knowledgeSubTab === sub.id
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {sub.label}
                </button>
              ))}
            </div>

            {/* Evidence status filters */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-slate-400 font-bold text-[10px] uppercase">Evidence:</span>
              {(['ALL', 'VERIFIED', 'CROSS-SUPPORTED', 'SOURCE CLAIM'] as const).map(ev => (
                <button
                  key={ev}
                  type="button"
                  onClick={() => setEvidenceFilter(ev)}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    evidenceFilter === ev ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {ev}
                </button>
              ))}
            </div>
          </div>

          {/* Sub-View 1: FUNDING PRODUCT BANK TABLE */}
          {knowledgeSubTab === 'FUNDING_PRODUCT_BANK' && (
            <div className="rounded-2xl bg-white border border-slate-200/80 overflow-hidden shadow-2xs">
              <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Funding Product Bank ({NO_LIVE_FUNDING_PRODUCTS.length} Audited Products)
                  </h4>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Live bureau pull rules, revenue thresholds, personal guarantee criteria, and verification refresh cadence
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-2.5 px-3">Lender / Product</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Limit Range</th>
                      <th className="py-2.5 px-3">Credit Requirements</th>
                      <th className="py-2.5 px-3">Bureaus</th>
                      <th className="py-2.5 px-3">Time in Biz / Rev</th>
                      <th className="py-2.5 px-3">PG / Collateral</th>
                      <th className="py-2.5 px-3">Rate & Fees</th>
                      <th className="py-2.5 px-3">Evidence</th>
                      <th className="py-2.5 px-3">Last Verified</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {NO_LIVE_FUNDING_PRODUCTS
                      .filter(p => evidenceFilter === 'ALL' || p.evidenceStatus === evidenceFilter)
                      .map(p => (
                        <tr key={p.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-3 px-3">
                            <div className="font-bold text-slate-900">{p.lender}</div>
                            <div className="text-[11px] text-slate-600">{p.product}</div>
                          </td>
                          <td className="py-3 px-3 font-semibold text-slate-700">{p.productType}</td>
                          <td className="py-3 px-3 font-mono font-bold text-slate-900">{p.limit}</td>
                          <td className="py-3 px-3 text-slate-600 text-[11px]">{p.creditRequirements}</td>
                          <td className="py-3 px-3 font-mono text-[10px] text-slate-600">{p.bureaus}</td>
                          <td className="py-3 px-3 text-[11px] text-slate-600">
                            <div>{p.timeInBusiness}</div>
                            <div className="text-slate-400 text-[10px]">{p.revenue}</div>
                          </td>
                          <td className="py-3 px-3 text-[11px] text-slate-600">{p.pgCollateral}</td>
                          <td className="py-3 px-3 text-[11px] text-slate-600">{p.rateFees}</td>
                          <td className="py-3 px-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${
                                p.evidenceStatus === 'VERIFIED'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : p.evidenceStatus === 'CROSS-SUPPORTED'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-amber-100 text-amber-800'
                              }`}
                            >
                              {p.evidenceStatus}
                            </span>
                          </td>
                          <td className="py-3 px-3 font-mono text-[10px] text-slate-400">{p.lastVerified}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Sub-View 2: BUSINESS CREDIT PRODUCT BANK */}
          {knowledgeSubTab === 'CREDIT_PRODUCT_BANK' && (
            <div className="space-y-4">
              {NO_LIVE_BUSINESS_CREDIT_PRODUCTS.map(tier => (
                <div key={tier.id} className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-2xs">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider text-blue-700">
                    {tier.tier}
                  </h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mt-3">
                    {tier.vendors.map((v, idx) => (
                      <div key={idx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-extrabold text-slate-900">{v.name}</span>
                          <span className="px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 font-bold text-[10px]">
                            {v.terms}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-600">
                          <span className="font-semibold text-slate-400">Bureau: </span>
                          <span className="font-bold text-slate-700">{v.bureau}</span>
                        </div>
                        <div className="text-[11px] text-slate-600">
                          <span className="font-semibold text-slate-400">Speed: </span>
                          <span>{v.speed}</span>
                        </div>
                        <p className="text-[10px] text-slate-500 pt-1 border-t border-slate-200/60 leading-relaxed">
                          {v.notes}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Sub-View 3: OPPORTUNITY BANK */}
          {knowledgeSubTab === 'OPPORTUNITY_BANK' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {NO_LIVE_OPPORTUNITIES.map(opp => (
                <div key={opp.id} className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-400">{opp.notebook}</span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-bold">
                      {opp.currentState}
                    </span>
                  </div>
                  <h4 className="text-sm font-extrabold text-slate-900">{opp.opportunity}</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">{opp.problem}</p>
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-slate-500 font-medium">{opp.businessModel}</span>
                    <span className="font-bold text-slate-900">{opp.capitalRequired}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Sub-View 4: OPPORTUNITY COMPONENT BANK */}
          {knowledgeSubTab === 'COMPONENT_BANK' && (
            <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-2xs space-y-4">
              <div>
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Opportunity Component Reusability Bank
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Pre-engineered software modules and workflows that minimize bootstrap capital required for new ventures
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {NO_LIVE_OPPORTUNITY_COMPONENTS.map((comp, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-extrabold text-slate-900">{comp.component}</span>
                      <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px]">
                        {comp.reuseReadiness}
                      </span>
                    </div>
                    <p className="text-slate-600 text-[11px] leading-relaxed">{comp.description}</p>
                    <div className="text-[10px] text-blue-700 font-semibold pt-1">
                      Nexus Foundation: {comp.nexusAsset}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Executive Dossier Modal */}
      {activeDossierData && (
        <ExecutiveDossierModal
          isOpen={dossierModalOpen}
          onClose={() => setDossierModalOpen(false)}
          data={activeDossierData}
        />
      )}
    </div>
  );
};
