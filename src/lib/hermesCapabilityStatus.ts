/**
 * Hermes Capability Status — single source for ALL capability answers.
 *
 * Every chat surface must use this for:
 *  - "what can you do" answers
 *  - "are you connected" / "model status" / "supabase status" answers
 *  - Capability badges in UI
 *  - Capability check during routing
 *
 * NEVER check capabilities in multiple places. This is the ONLY source.
 */

import { isSupabaseConfigured } from './supabaseClient';
import { getModelAvailability } from './hermesModelRoutingPolicy';

export type CapabilityStatus = 'live' | 'available' | 'not-configured' | 'not-deployed' | 'blocked-by-auth' | 'blocked-by-RLS';

export interface Capability {
  name: string;
  status: CapabilityStatus;
  detail: string;
  userFacing: string;
}

export interface CapabilityReport {
  supabase: Capability;
  liveModel: Capability;
  webSearch: Capability;
  trading: Capability;
  youtubeResearch: Capability;
  creditAndFunding: Capability;
  marketingDrafts: Capability;
  execution: Capability;
  conversationMemory: Capability;
  capabilities: Capability[];
  badgeText: string;
  overallStatus: 'all-live' | 'partially-live' | 'not-live';
}

/** Get the full capability report. */
export function getCapabilityReport(): CapabilityReport {
  const model = getModelAvailability();
  const supabaseConfigured = isSupabaseConfigured;
  const chatEnabled = (import.meta.env?.VITE_HERMES_CHAT_ENABLED as string) === 'true';

  const supabase: Capability = {
    name: 'Supabase Database',
    status: supabaseConfigured ? 'live' : 'not-configured',
    detail: supabaseConfigured
      ? 'Supabase client is configured with anon key. Live read queries work when authenticated.'
      : 'VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are not set.',
    userFacing: supabaseConfigured
      ? 'I have live Supabase read access for supported tables when you are authenticated.'
      : 'I do not have live Supabase access. I use local bundled data.',
  };

  const liveModel: Capability = {
    name: 'Live AI Model',
    status: model.configured ? 'live' : 'not-configured',
    detail: model.configured
      ? `Using ${model.model} via ${model.provider}. Cost-capped and logged.`
      : 'VITE_HERMES_CHAT_ENABLED is not true.',
    userFacing: model.configured
      ? `I have a live AI model (${model.model}) for strategic reasoning.`
      : 'I do not have a live AI model. I reason from local context, Supabase data, and reports.',
  };

  const webSearch: Capability = {
    name: 'Web Search',
    status: 'not-deployed',
    detail: 'The hermes-search edge function exists but is not deployed to Supabase.',
    userFacing: 'I cannot search the internet yet. Web search requires deploying the hermes-search edge function.',
  };

  const trading: Capability = {
    name: 'Trading',
    status: 'not-configured',
    detail: 'No live broker API key. Trading is paper/demo only. Live trading is always blocked.',
    userFacing: 'I cannot execute live trades. Trading is paper/demo only. Any real trading requires explicit approval.',
  };

  const youtubeResearch: Capability = {
    name: 'YouTube Research',
    status: 'not-deployed',
    detail: 'Scripts exist (runYouTubeResearch, getYouTubeTranscript, runYouTubeChannelPoll) but no process/log/write proof of execution.',
    userFacing: 'I cannot fetch YouTube transcripts or poll channels yet. The scripts exist but are not proven to execute.',
  };

  const creditAndFunding: Capability = {
    name: 'Credit & Funding',
    status: 'not-configured',
    detail: 'No dedicated Supabase table. Section shows static data from creditFundingData.js.',
    userFacing: 'I use local bundled credit/funding data. No live Supabase table exists yet for this section.',
  };

  const marketingDrafts: Capability = {
    name: 'Marketing Drafts',
    status: 'not-configured',
    detail: 'No dedicated Supabase table. Section shows static data.',
    userFacing: 'I use local bundled marketing data. No live Supabase table exists yet for this section.',
  };

  const execution: Capability = {
    name: 'Execution (send/publish/trade/deploy)',
    status: 'blocked-by-auth',
    detail: 'All execution requires explicit Ray approval via the Ray Review gate. No direct sends, charges, or deployments.',
    userFacing: 'I cannot send, publish, trade, or deploy without your explicit approval. Everything goes through the Ray Review gate.',
  };

  const conversationMemory: Capability = {
    name: 'Conversation Memory',
    status: chatEnabled ? 'live' : 'not-configured',
    detail: chatEnabled
      ? 'Conversation history is tracked within the session. Follow-up references like "number 3" and "that one" resolve against recent context.'
      : 'No conversation memory — each message is independent.',
    userFacing: chatEnabled
      ? 'I remember our conversation within this session. You can refer back to items I listed.'
      : 'I do not have conversation memory across messages.',
  };

  const capabilities = [supabase, liveModel, webSearch, trading, youtubeResearch, creditAndFunding, marketingDrafts, execution, conversationMemory];

  const liveCount = capabilities.filter(c => c.status === 'live').length;
  const totalCount = capabilities.length;

  let overallStatus: CapabilityReport['overallStatus'] = 'not-live';
  if (liveCount === totalCount) overallStatus = 'all-live';
  else if (liveCount > 0) overallStatus = 'partially-live';

  // Badge text for UI
  let badgeText = 'Local context only';
  if (liveCount === 3 && supabaseConfigured && model.configured) {
    badgeText = 'Live Supabase + Model Ready';
  } else if (supabaseConfigured && model.configured) {
    badgeText = 'Live Supabase + Model Ready';
  } else if (supabaseConfigured) {
    badgeText = 'Live Supabase Ready';
  } else if (model.configured) {
    badgeText = 'Model Ready';
  }

  return {
    supabase,
    liveModel,
    webSearch,
    trading,
    youtubeResearch,
    creditAndFunding,
    marketingDrafts,
    execution,
    conversationMemory,
    capabilities,
    badgeText,
    overallStatus,
  };
}

/** Get a plain-English answer for capability questions. */
export function answerCapabilityQuestion(message: string): string | null {
  const lower = message.toLowerCase();
  const report = getCapabilityReport();

  // "what can you do" / "what are your capabilities"
  if (/what can you do|what are your capabilities|what do you have access|what tools do you have/.test(lower)) {
    const liveCaps = report.capabilities.filter(c => c.status === 'live');
    const configuredCaps = report.capabilities.filter(c => c.status !== 'not-configured' && c.status !== 'not-deployed');
    const blockedCaps = report.capabilities.filter(c => c.status === 'blocked-by-auth' || c.status === 'blocked-by-RLS');

    let answer = 'Here is what I can do right now:\n\n';
    if (liveCaps.length > 0) {
      answer += `**Live:** ${liveCaps.map(c => c.name).join(', ')}\n`;
    } else {
      answer += '**Live:** local conversation routing, approved report snapshots, browser time/date, and safety-policy interpretation\n';
    }
    if (configuredCaps.length > 0 && configuredCaps.length !== liveCaps.length) {
      answer += `**Configured but limited:** ${configuredCaps.filter(c => !liveCaps.includes(c)).map(c => `${c.name} — ${c.detail}`).join(', ')}\n`;
    }
    if (blockedCaps.length > 0) {
      answer += `**Needs your login:** ${blockedCaps.map(c => c.name).join(', ')}\n`;
    }
    answer += `\nAll execution (send, publish, trade, deploy) goes through your approval gate. I never act without your explicit confirmation.`;
    return answer;
  }

  // "are you connected" / "supabase status"
  if (/are you connected|using supabase|use supabase|supabase status|database status|what is your supabase/.test(lower)) {
    return report.supabase.userFacing;
  }

  // "model" / "are you using a live model" / "openrouter"
  if (/\b(model|openrouter|live model|ai model)\b/.test(lower)) {
    return report.liveModel.userFacing;
  }

  // "web search" / "search the internet" / "google"
  if (/web search|search the internet|google|bing|search online/.test(lower)) {
    return report.webSearch.userFacing;
  }

  // "can you trade" / "trading status"
  if (/can you trade|trading status|live trading|broker/.test(lower)) {
    return report.trading.userFacing;
  }

  // "youtube" / "transcript"
  if (/youtube|transcript|video fetch|channel poll/.test(lower)) {
    return report.youtubeResearch.userFacing;
  }

  // "holding back" / "why so limited" / "why can't you"
  if (/holding back|why so limited|why can'?t you|where.*answers|gated/.test(lower)) {
    const missing = report.capabilities.filter(c => c.status === 'not-configured' || c.status === 'not-deployed');
    if (missing.length === 0) return 'I am not holding back. All capabilities are live and working.';
    return `I am not holding back — I simply do not have: ${missing.map(c => c.name).join(', ')}. ${report.execution.userFacing}`;
  }

  return null;
}

export function answerModelCapabilityWithoutTrace(): string {
  const model = getModelAvailability();
  if (model.configured) return `I do not have a previous routing record available for the last answer. In general, Hermes is configured to use ${model.model.replace(/ \(.*\)$/, '')} through OpenRouter when model reasoning is allowed. Simple casual, status, trace, and source questions usually do not use the model.`;
  return 'I do not have a previous routing record available for the last answer, and this browser does not currently prove that the strategic model is configured. Simple casual, status, trace, and source questions do not use the model.';
}
