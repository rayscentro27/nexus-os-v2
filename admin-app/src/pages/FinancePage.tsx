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
import { CapitalAllocationSimulator } from '../components/dashboard/CapitalAllocationSimulator';
import { TruthBadge } from '../components/common/TruthBadge';
import {
  AI_PROVIDER_COSTS,
  TOTAL_AI_SPEND,
  TOKEN_MODEL_USAGE,
  DEPARTMENT_OPERATING_COSTS,
  BILLS_COMMITMENTS,
  BILLS_SUMMARY,
  INVOICE_LEDGER,
  GRANT_PIPELINE,
  RUNWAY_FORECAST,
  PROVIDER_BURNS
} from '../data/financeOperatingData';

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
          <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">$0.00</div>
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
          <div className="text-xl font-semibold text-slate-900 mt-1 tabular-nums">$0.00</div>
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
            ${TOTAL_AI_SPEND.today.toFixed(2)}{' '}
            <span className="text-xs font-normal text-slate-500">
              / ${TOTAL_AI_SPEND.thirtyDays.toFixed(2)}
            </span>
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            OpenRouter balance: $18.50 (Watchdog active)
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
          { id: 'ai-models', label: 'AI & Provider Costs', icon: Cpu },
          { id: 'bills', label: 'Bills, Grants & Demo Invoices', icon: CreditCard },
          { id: 'capital-simulator', label: 'Capital Simulator', icon: Sliders },
        ].map(tab => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as FinanceTab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 whitespace-nowrap transition-colors cursor-pointer ${
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
              <p className="text-xs text-slate-600">{RUNWAY_FORECAST.note}</p>
              <div className="grid grid-cols-3 gap-2 text-xs pt-1">
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-500">Est. Monthly Burn</div>
                  <div className="font-semibold text-slate-900 tabular-nums">
                    ${RUNWAY_FORECAST.monthlyBurn.toFixed(2)}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-500">Verified Revenue</div>
                  <div className="font-semibold text-slate-900 tabular-nums">$0.00</div>
                </div>
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-500">Paid Ad Spend</div>
                  <div className="font-semibold text-slate-900 tabular-nums">$0.00 (Locked)</div>
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

      {/* TAB 3: AI & PROVIDER COSTS */}
      {activeTab === 'ai-models' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-3">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-900">
                  AI Provider Metering &amp; Balances
                </h2>
                <TruthBadge truth="ESTIMATED" />
              </div>
              <span className="text-xs text-slate-500">
                30D Estimated Total: <strong className="text-slate-900">${TOTAL_AI_SPEND.thirtyDays.toFixed(2)}</strong>
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="py-2 px-3">Provider</th>
                    <th className="py-2 px-3">Workload</th>
                    <th className="py-2 px-3 text-right">Today</th>
                    <th className="py-2 px-3 text-right">7D</th>
                    <th className="py-2 px-3 text-right">30D</th>
                    <th className="py-2 px-3">Balance</th>
                    <th className="py-2 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {AI_PROVIDER_COSTS.map(p => (
                    <tr key={p.provider} className="hover:bg-slate-50/70">
                      <td className="py-2.5 px-3 font-medium text-slate-900">{p.provider}</td>
                      <td className="py-2.5 px-3 text-slate-600">{p.role}</td>
                      <td className="py-2.5 px-3 text-right font-mono">${p.today.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right font-mono">${p.sevenDays.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-medium">
                        ${p.thirtyDays.toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-slate-700">{p.currentBalance}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                            p.status === 'LOW BALANCE'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-900">Department Operating Costs</h3>
                <TruthBadge truth="ESTIMATED" />
              </div>
              <div className="space-y-2 text-xs">
                {DEPARTMENT_OPERATING_COSTS.map(d => (
                  <div
                    key={d.department}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100"
                  >
                    <div>
                      <div className="font-medium text-slate-900">{d.department}</div>
                      <div className="text-[11px] text-slate-500">{d.mainCostDriver}</div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="font-semibold text-slate-900">${d.monthCost.toFixed(2)}/mo</div>
                      <div className="text-[11px] text-slate-500">${d.todayCost.toFixed(2)} today</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-900">Token &amp; Provider Burn</h3>
                <TruthBadge truth="ESTIMATED" />
              </div>
              <div className="space-y-2 text-xs">
                {TOKEN_MODEL_USAGE.map(m => (
                  <div
                    key={m.model}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100"
                  >
                    <div>
                      <div className="font-medium text-slate-900 font-mono">{m.model}</div>
                      <div className="text-[11px] text-slate-500">
                        {m.provider} · {m.totalTokens}
                      </div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="font-semibold text-slate-900">${m.costMonth.toFixed(2)}/mo</div>
                      <div className="text-[11px] text-slate-500">${m.costToday.toFixed(2)} today</div>
                    </div>
                  </div>
                ))}
                {PROVIDER_BURNS.slice(0, 2).map(b => (
                  <div
                    key={b.provider}
                    className="p-2 rounded-lg bg-amber-50/50 border border-amber-100 flex items-center justify-between"
                  >
                    <span className="font-medium text-slate-800">
                      {b.provider} Burn Watch ({b.formattedBurn})
                    </span>
                    <span className="text-slate-600">{b.formattedBalance} remaining</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: BILLS, GRANTS & DEMO INVOICES */}
      {activeTab === 'bills' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">
                Recurring Subscriptions &amp; Bills (${BILLS_SUMMARY.dueNext30Days.toFixed(2)} / 30D)
              </h3>
              <TruthBadge truth="ESTIMATED" />
            </div>
            <div className="space-y-2 text-xs">
              {BILLS_COMMITMENTS.map(b => (
                <div
                  key={b.id}
                  className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between"
                >
                  <div>
                    <div className="font-medium text-slate-900">{b.vendor}</div>
                    <div className="text-[11px] text-slate-500">
                      Due {b.dueDate} · Owner: {b.departmentOwner}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-slate-900 font-mono">{b.formattedAmount}</div>
                    <div className="text-[10px] text-slate-500">{b.paymentStatus}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-6 space-y-4">
            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">
                  Client Invoice Ledger (Non-Production / Sandbox)
                </h3>
                <TruthBadge truth="DEMO" />
              </div>
              <div className="space-y-2 text-xs">
                {INVOICE_LEDGER.map(inv => (
                  <div
                    key={inv.id}
                    className="p-2.5 rounded-lg bg-purple-50/40 border border-purple-100 flex items-center justify-between"
                  >
                    <div>
                      <div className="font-medium text-slate-900">{inv.client}</div>
                      <div className="text-[11px] text-slate-500">
                        {inv.id} · Issued {inv.issuedDate}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <TruthBadge truth={inv.truthClass} />
                      <span className="font-mono font-semibold text-slate-900">
                        {inv.formattedAmount}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">
                  Non-Dilutive Grant Pipeline
                </h3>
                <TruthBadge truth="PROPOSED" />
              </div>
              {GRANT_PIPELINE.map(g => (
                <div
                  key={g.id}
                  className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-medium text-slate-900">{g.program}</div>
                    <div className="text-[11px] text-slate-500">
                      {g.status} · {g.probability}
                    </div>
                  </div>
                  <div className="font-mono font-semibold text-emerald-700">{g.formattedAmount}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: INTERACTIVE CAPITAL ALLOCATION SIMULATOR */}
      {activeTab === 'capital-simulator' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Capital Allocation &amp; Treasury Runway Simulator
              </h2>
              <p className="text-xs text-slate-500">
                What-if modeling tool for scenario planning (Estimated/Proposed projections).
              </p>
            </div>
            <TruthBadge truth="ESTIMATED" label="Interactive Scenario" />
          </div>
          <CapitalAllocationSimulator />
        </div>
      )}
    </div>
  );
};
