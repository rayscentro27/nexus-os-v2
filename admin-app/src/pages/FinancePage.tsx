import React, { useState } from 'react';
import {
  DollarSign,
  PieChart,
  CheckCircle2,
  CreditCard,
  ShieldAlert,
  Cpu,
  Sliders,
  Wallet,
  Bot,
  ArrowUpRight,
  ExternalLink,
  Package,
  AlertTriangle
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { UnavailableState } from '../components/live/UnavailableState';
type FinanceTab =
  | 'overview'
  | 'spend-approvals'
  | 'ai-models'
  | 'bills'
  | 'capital-simulator';

export const FinancePage: React.FC = () => {
  const {
    approvals,
    commerceOffers,
    credentials,
    approveDecision,
    navigateToObject,
    sendMessage,
    setIsNovaDrawerOpen,
    liveAreas,
  } = useNexus();

  const [activeTab, setActiveTab] = useState<FinanceTab>('overview');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3200);
  };

  // Authoritative finance-relevant approvals from single control-plane store
  const financeApprovals = approvals.filter(
    a =>
      a.type === 'Spend' ||
      a.type === 'Commerce go-live' ||
      a.type === 'Trading actions' ||
      a.department === 'Finance' ||
      a.costImpact !== '$0.00'
  );
  const pendingFinanceApprovals = financeApprovals.filter(a => a.status === 'PENDING');
  const liveFinance = liveAreas.finance || {};

  const holidayOffer = commerceOffers[0];
  const plaidCred = credentials.find(c => c.id === 'cred-plaid');
  const stripeCred = credentials.find(c => c.id === 'cred-stripe');

  return (
    <div className="space-y-4 pb-10">
      {toastMessage && (
        <div className="fixed top-14 right-6 z-50 animate-in slide-in-from-top duration-200">
          <div className="bg-slate-900 text-white px-4 py-2.5 rounded-xl shadow-lg flex items-center gap-2 text-xs font-medium border border-slate-700">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Header + Primary Question */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Wallet className="w-4 h-4 text-emerald-600" />
            <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
              Finance &amp; Operating Economics
            </h1>
            <TruthBadge truth="ESTIMATED" label="Mixed Truth Ledger" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            What is Nexus spending, earning, forecasting, or requesting — with strict verified vs. estimated separation.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => {
              sendMessage('What did Nexus spend today and which spend approvals are waiting?');
              setIsNovaDrawerOpen(true);
            }}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 inline-flex items-center gap-1.5 cursor-pointer"
          >
            <Bot className="w-3.5 h-3.5" />
            Ask Nova
          </button>
        </div>
      </div>

      {/* Truthful 4-Card Executive Cash & Cost Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-medium text-slate-500">Verified Cash</span>
            <TruthBadge truth={plaidCred?.state === 'CONNECTED' ? 'VERIFIED' : 'NOT_CONNECTED'} />
          </div>
          <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">Not connected</div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            Banking (Plaid) is {plaidCred?.state || 'NOT_CONNECTED'} · No fabricated liquidity
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-medium text-slate-500">Verified Revenue</span>
            <TruthBadge
              truth={stripeCred?.state === 'CONNECTED' ? 'VERIFIED' : 'NOT_CONNECTED'}
            />
          </div>
          <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">
            {typeof liveFinance.verifiedRevenueUsd === 'number' ? `$${liveFinance.verifiedRevenueUsd.toFixed(2)}` : 'Not connected'}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            Stripe checkout {holidayOffer?.liveSales.checkoutStatus || 'BLOCKED'}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-medium text-slate-500">AI Spend (Today / 30D)</span>
            <TruthBadge truth="ESTIMATED" />
          </div>
          <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">
            Not connected
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            Provider usage and balances are not connected to durable usage records.
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-medium text-slate-500">Pending Spend Requests</span>
            <TruthBadge truth="PROPOSED" />
          </div>
          <div className="text-xl font-semibold text-amber-700 mt-1 tabular-nums">
            {pendingFinanceApprovals.length}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            Requires Ray sign-off before execution
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-1.5 flex items-center gap-1 overflow-x-auto shadow-2xs">
        {[
          { id: 'overview', label: 'Treasury & Unit Economics', icon: PieChart },
          {
            id: 'spend-approvals',
            label: `Spend & Go-Live Requests (${pendingFinanceApprovals.length})`,
            icon: ShieldAlert,
          },
          { id: 'ai-models', label: 'AI & Provider Costs (not connected)', icon: Cpu, unavailable: true },
          { id: 'bills', label: 'Bills & Grants (not connected)', icon: CreditCard, unavailable: true },
          { id: 'capital-simulator', label: 'Capital Simulator (not connected)', icon: Sliders, unavailable: true },
        ].map(tab => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              disabled={tab.unavailable}
              onClick={() => !tab.unavailable && setActiveTab(tab.id as FinanceTab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 whitespace-nowrap transition-colors ${tab.unavailable ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: TREASURY & COMMERCE UNIT ECONOMICS OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Verified Commerce Unit Economics (6:12 AM Mug) */}
          <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-semibold text-slate-900">
                  Commerce Unit Economics · {holidayOffer?.title}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => navigateToObject('business-hub', holidayOffer?.id, 'offer')}
                className="text-xs font-medium text-blue-600 hover:text-blue-700 inline-flex items-center gap-1 cursor-pointer"
              >
                Open Commerce <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {holidayOffer && (
              <div className="space-y-2.5 text-xs">
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Printify Base Cost</span>
                      <TruthBadge truth={holidayOffer.productTruth.baseCostTruth} />
                    </div>
                    <div className="text-base font-semibold text-slate-900 mt-1 tabular-nums">
                      ${holidayOffer.productTruth.baseCost.toFixed(2)}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">US 1st-Item Shipping</span>
                      <TruthBadge truth={holidayOffer.productTruth.firstItemShippingTruth} />
                    </div>
                    <div className="text-base font-semibold text-slate-900 mt-1 tabular-nums">
                      ${holidayOffer.productTruth.firstItemShipping.toFixed(2)}{' '}
                      <span className="text-[11px] font-normal text-slate-500">
                        (+${holidayOffer.productTruth.additionalItemShipping.toFixed(2)} add&apos;l)
                      </span>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Staged Retail Price</span>
                      <TruthBadge truth={holidayOffer.productTruth.stagedPriceTruth} />
                    </div>
                    <div className="text-base font-semibold text-slate-900 mt-1 tabular-nums">
                      ${holidayOffer.productTruth.stagedPrice.toFixed(2)}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Est. Gross Margin</span>
                      <TruthBadge truth={holidayOffer.productTruth.marginTruth} />
                    </div>
                    <div className="text-base font-semibold text-emerald-700 mt-1 tabular-nums">
                      ${holidayOffer.productTruth.estimatedGrossMarginDollar.toFixed(2)} (
                      {holidayOffer.productTruth.estimatedGrossMarginPct.toFixed(1)}%)
                    </div>
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-amber-50/70 border border-amber-200 text-amber-900 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium">
                      Storefront Mode: {holidayOffer.interestTest.mode} · Checkout{' '}
                      {holidayOffer.liveSales.checkoutStatus}
                    </div>
                    <div className="text-[11px] text-amber-800 mt-0.5">
                      {holidayOffer.liveSales.blockerReason}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Pending Spend & Approval Queue + Runway Guardrail */}
          <div className="lg:col-span-6 space-y-4">
            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <h2 className="text-sm font-semibold text-slate-900">
                  Authoritative Spend &amp; Budget Requests
                </h2>
                <button
                  type="button"
                  onClick={() => setActiveTab('spend-approvals')}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700 cursor-pointer"
                >
                  View all ({financeApprovals.length}) →
                </button>
              </div>

              {pendingFinanceApprovals.length === 0 ? (
                <p className="text-xs text-slate-500 py-2">
                  Zero pending spend approvals in queue.
                </p>
              ) : (
                <div className="space-y-2">
                  {pendingFinanceApprovals.slice(0, 3).map(apr => (
                    <div
                      key={apr.id}
                      className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-3"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-900 truncate">
                            {apr.title}
                          </span>
                          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">
                            {apr.costImpact}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5 truncate">
                          {apr.projectName} · {apr.blockedAction}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => navigateToObject('approvals', apr.id, 'approval')}
                        className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-xs font-medium text-slate-700 shrink-0 cursor-pointer"
                      >
                        Review
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Runway & Department Burn */}
            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-900">
                  Runway &amp; Burn Guardrail
                </h2>
                <TruthBadge truth="NOT_CONNECTED" label="Runway Not Proven" />
              </div>
              <p className="text-xs text-slate-600">{liveFinance.note || 'Runway and burn details are not connected.'}</p>
              <div className="grid grid-cols-3 gap-2 text-xs pt-1">
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-500">Est. Monthly Burn</div>
                  <div className="font-semibold text-slate-900 tabular-nums">
                    {typeof liveFinance.monthlyBurnUsd === 'number' ? `$${liveFinance.monthlyBurnUsd.toFixed(2)}` : 'Not connected'}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-500">Verified Revenue</div>
                  <div className="font-semibold text-slate-900 tabular-nums">{typeof liveFinance.verifiedRevenueUsd === 'number' ? `$${liveFinance.verifiedRevenueUsd.toFixed(2)}` : 'Not connected'}</div>
                </div>
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-500">Paid Ad Spend</div>
                  <div className="font-semibold text-slate-900 tabular-nums">Not connected</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: AUTHORITATIVE SPEND APPROVALS (SYNCED TO NEXUSCONTEXT) */}
      {activeTab === 'spend-approvals' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Spend, Budget &amp; Commercial Activation Approvals
              </h2>
              <p className="text-xs text-slate-500">
                Synchronized directly with the unified Approvals Desk and Nova operator state.
              </p>
            </div>
          </div>

          <div className="space-y-2.5">
            {financeApprovals.map(apr => (
              <div
                key={apr.id}
                className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-slate-900">{apr.title}</span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        apr.status === 'PENDING'
                          ? 'bg-amber-100 text-amber-800'
                          : apr.status === 'APPROVED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {apr.status}
                    </span>
                    <span className="text-xs font-medium text-blue-700">{apr.costImpact}</span>
                  </div>
                  <p className="text-xs text-slate-600">{apr.plainEnglishExplanation}</p>
                  <div className="text-[11px] text-slate-500">
                    Project: <strong>{apr.projectName}</strong> · Next: {apr.nextAction}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {apr.status === 'PENDING' && (
                    <button
                      type="button"
                      onClick={() => {
                        approveDecision(apr.id, 'Approved from Finance Operating Desk');
                        showToast(`Approved "${apr.title}"`);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium cursor-pointer"
                    >
                      Approve
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => navigateToObject('approvals', apr.id, 'approval')}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-xs font-medium text-slate-700 inline-flex items-center gap-1 cursor-pointer"
                  >
                    Open Desk <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'ai-models' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
          <UnavailableState>AI/provider usage data is not connected to a live source.</UnavailableState>
        </div>
      )}

      {activeTab === 'bills' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
          <UnavailableState>Bills, grants, and invoices data is not connected to a live source.</UnavailableState>
        </div>
      )}

      {activeTab === 'capital-simulator' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
          <UnavailableState>Capital simulation data is not connected to a live source.</UnavailableState>
        </div>
      )}

    </div>
  );
};
