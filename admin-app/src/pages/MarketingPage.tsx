import React, { useState } from 'react';
import {
  Calendar,
  Share2,
  TrendingUp,
  MessageSquare,
  AlertTriangle,
  ArrowRight,
  Target,
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { UnavailableState } from '../components/live/UnavailableState';

const MARKETING_CONTENT_SCHEDULE: any[] = [];
const MARKETING_PUBLISHED_CONTENT: any[] = [];
const AUDIENCE_COMMENTS_DATA: any[] = [];
const AUDIENCE_INTELLIGENCE_SUMMARY = { topRecurringQuestions: [] as string[], topObjections: [] as string[] };
const ATTRIBUTION_PIPELINE: any[] = [];

type MarketingTab = 'overview' | 'schedule' | 'published' | 'audience' | 'attribution';

export const MarketingPage: React.FC = () => {
  const { liveAreas, navigateToObject } = useNexus();
  const marketingState = liveAreas.marketing || {};
  const campaigns = Array.isArray(marketingState.campaigns) ? marketingState.campaigns : [];
  const [activeTab, setActiveTab] = useState<MarketingTab>('overview');

  const waitingCampaigns = campaigns.filter(c => c.approvalStatus !== 'APPROVED');

  const filteredComments = AUDIENCE_COMMENTS_DATA;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Marketing
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Campaign strategy, channel readiness, publishing calendar, and audience response.
          </p>
        </div>

        <button
          type="button"
          onClick={() => navigateToObject('campaigns')}
          className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer shrink-0"
        >
          <Target className="w-3.5 h-3.5" />
          <span>Inspect All Campaigns ({campaigns.length})</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl w-fit max-w-full overflow-x-auto">
        {(
          [
            { id: 'overview', label: 'Strategy & Readiness' },
            { id: 'schedule', label: 'Schedule (not connected)' },
            { id: 'published', label: 'Published (not connected)' },
            { id: 'audience', label: 'Audience Response (not connected)' },
            { id: 'attribution', label: 'Attribution Funnel' },
          ] as const
        ).map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap cursor-pointer transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-slate-900 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Channel Readiness */}
          <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/90 p-5 space-y-4">
            <h2 className="text-sm font-bold text-slate-900">Channel Readiness</h2>
            <div className="divide-y divide-slate-100 text-xs">
              <div className="py-3 flex items-center justify-between gap-2">
                <div>
                  <div className="font-semibold text-slate-900">Facebook / Meta Business API</div>
                  <div className="text-slate-500 mt-0.5">Marketing provider state is not connected.</div>
                </div>
                <TruthBadge truth="NOT_CONNECTED" />
              </div>
              <div className="py-3 flex items-center justify-between gap-2">
                <div>
                  <div className="font-semibold text-slate-900">Postiz Social Scheduler</div>
                  <div className="text-slate-500 mt-0.5">Marketing provider state is not connected.</div>
                </div>
                <TruthBadge truth="NOT_CONNECTED" />
              </div>
              <div className="py-3 flex items-center justify-between gap-2">
                <div>
                  <div className="font-semibold text-slate-900">LinkedIn / X (Pilot Feeds)</div>
                  <div className="text-slate-500 mt-0.5">Marketing data not connected.</div>
                </div>
                <TruthBadge truth="NOT_CONNECTED" />
              </div>
            </div>
          </div>

          {/* Campaigns Awaiting Publication */}
          <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/90 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900">Campaigns &amp; Publication Gates</h2>
              <span className="text-xs text-slate-500">
                {waitingCampaigns.length} waiting approval
              </span>
            </div>

            <div className="divide-y divide-slate-100">
              {campaigns.map(cmp => (
                <div
                  key={cmp.id}
                  className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-slate-900">{cmp.name}</span>
                      <TruthBadge truth={cmp.truthClass} />
                    </div>
                    <div className="text-slate-500">
                      {cmp.projectName} · {cmp.channels.join(', ')}
                    </div>
                    <div className="text-[11px] text-slate-600">{cmp.resultsSummary}</div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {cmp.approvalId && (
                      <button
                        type="button"
                        onClick={() => navigateToObject('approvals', cmp.approvalId, 'approval')}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 text-white font-semibold cursor-pointer"
                      >
                        Approval Gate
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => navigateToObject('campaigns', cmp.id, 'campaign')}
                      className="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold cursor-pointer"
                    >
                      Detail
                    </button>
                  </div>
                </div>
              ))}
              {campaigns.length === 0 && <div className="py-3"><UnavailableState>Campaign records are not connected.</UnavailableState></div>}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'schedule' && (
        <div className="bg-white rounded-2xl border border-slate-200/90 divide-y divide-slate-100">
          {MARKETING_CONTENT_SCHEDULE.map(item => (
            <div
              key={item.id}
              className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
            >
              <div className="flex items-start gap-3">
                <Calendar className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-slate-900">{item.post_title}</span>
                    <TruthBadge truth={item.truth_class} />
                  </div>
                  <div className="text-slate-500 mt-0.5">
                    {item.platform} ({item.account_name}) · {item.scheduled_at} · {item.publish_state}
                  </div>
                  <p className="text-slate-600 mt-1">{item.caption}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => navigateToObject('creative', item.creative_asset_id, 'asset')}
                className="text-blue-600 font-semibold hover:underline shrink-0 cursor-pointer"
              >
                View Creative →
              </button>
            </div>
          ))}
          {MARKETING_CONTENT_SCHEDULE.length === 0 && <div className="p-4"><UnavailableState>Marketing schedule data is not connected.</UnavailableState></div>}
        </div>
      )}

      {activeTab === 'published' && (
        <div className="bg-white rounded-2xl border border-slate-200/90 divide-y divide-slate-100">
          {MARKETING_PUBLISHED_CONTENT.map(item => (
            <div key={item.id} className="p-4 space-y-2 text-xs">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  <Share2 className="w-4 h-4 text-slate-400" />
                  <span className="font-bold text-slate-900">{item.post_title}</span>
                  <TruthBadge truth={item.truth_class} />
                </div>
                <span className="text-slate-500">
                  {item.platform} · {item.published_at}
                </span>
              </div>
              <p className="text-slate-600">{item.caption}</p>
              {item.truth_class === 'NOT_CONNECTED' ? (
                <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                  <span>Facebook metrics unavailable (API NOT_CONNECTED).</span>
                </div>
              ) : (
                <div className="grid grid-cols-4 gap-2 pt-1 tabular-nums">
                  <div className="p-2 rounded-lg bg-slate-50">Reach: <strong>{item.metrics?.reach ?? '—'}</strong></div>
                  <div className="p-2 rounded-lg bg-slate-50">Impressions: <strong>{item.metrics?.impressions ?? '—'}</strong></div>
                  <div className="p-2 rounded-lg bg-slate-50">Clicks: <strong>{item.metrics?.clicks ?? '—'}</strong></div>
                  <div className="p-2 rounded-lg bg-slate-50">Leads: <strong>{item.metrics?.leads ?? '—'}</strong></div>
                </div>
              )}
            </div>
          ))}
          {MARKETING_PUBLISHED_CONTENT.length === 0 && <div className="p-4"><UnavailableState>Published campaign data is not connected.</UnavailableState></div>}
        </div>
      )}

      {activeTab === 'audience' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200/90 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
                <MessageSquare className="w-4 h-4 text-blue-600" />
                <span>Audience Comments</span>
              </div>
            </div>
            <div className="divide-y divide-slate-100">
              {filteredComments.map(c => (
                <div key={c.id} className="p-4 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">
                      {c.author} · <span className="font-normal text-slate-500">{c.author_title}</span>
                    </span>
                    <TruthBadge truth={c.truth_class} />
                  </div>
                  <p className="text-slate-700">{c.comment_text}</p>
                  <div className="text-[11px] text-slate-500">
                    {c.platform} · {c.classification} · {c.reply_status}
                  </div>
                </div>
              ))}
              {filteredComments.length === 0 && <div className="p-4"><UnavailableState>Audience response data is not connected.</UnavailableState></div>}
            </div>
          </div>

          <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/90 p-5 space-y-3 text-xs">
            <h3 className="text-sm font-bold text-slate-900">Recurring Signals</h3>
            <div>
              <div className="font-semibold text-slate-700 mb-1">Top Questions</div>
              <ul className="space-y-1 text-slate-600">
                {AUDIENCE_INTELLIGENCE_SUMMARY.topRecurringQuestions.map((q, i) => (
                  <li key={i}>• {q}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-semibold text-slate-700 mb-1">Top Objections</div>
              <ul className="space-y-1 text-slate-600">
                {AUDIENCE_INTELLIGENCE_SUMMARY.topObjections.map((o, i) => (
                  <li key={i}>• {o}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'attribution' && (
        <div className="bg-white rounded-2xl border border-slate-200/90 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              <span>Attribution Truth Funnel</span>
            </div>
            <TruthBadge truth="NOT_CONNECTED" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {ATTRIBUTION_PIPELINE.map((step, i) => (
              <div key={i} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 space-y-1.5 text-xs">
                <div className="flex items-center justify-between gap-1">
                  <span className="font-bold text-slate-900">{step.step}</span>
                  <ArrowRight className="w-3 h-3 text-slate-400" />
                </div>
                <div className="text-slate-600">{step.label}</div>
                <div className="font-semibold text-slate-900 tabular-nums">{step.metric}</div>
                <TruthBadge truth={step.status} />
              </div>
            ))}
            {ATTRIBUTION_PIPELINE.length === 0 && <UnavailableState>Attribution data is not connected.</UnavailableState>}
          </div>
        </div>
      )}
    </div>
  );
};
