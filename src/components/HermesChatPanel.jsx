import React, { useEffect, useRef, useState, useCallback } from 'react';
import { buildHermesResponse, hermesQuickPrompts } from '../data/hermesWorkroomData';
import { hermesStore } from '../lib/hermesChatStore';
import { recordActivity } from '../lib/hermesActivityJournal';
import { buildLiveSupabaseContext, buildWebSearchResponse } from '../lib/hermesLiveContext';
import { isSupabaseConfigured } from '../lib/supabaseClient';
import { orchestrateHermes } from '../lib/hermesOrchestrator';
import { hermesModelChat } from '../lib/hermesProviders';
import { getModelAvailability } from '../lib/hermesModelRoutingPolicy';
import { getRecentUsageSummary, getModelActivityAnswer, getUsageEntries, getTotalTokensUsed } from '../lib/hermesModelUsageLedger';
import { getCostAdvice, getCostReductionAnswer } from '../lib/hermesModelCostAdvisor';
import { estimateModelCallCost } from '../lib/hermesModelCostEstimator';
import HermesMessageBubble from './HermesMessageBubble';

const welcome = { id: 'welcome', role: 'hermes', text: 'I\'m Hermes, your CEO advisor. I can read live Supabase data when connected, and I use local bundled context as fallback. Web search and live model are not configured yet. Ask me about approvals, research, clients, opportunities, or any operating question.' };

export default function HermesChatPanel({ activeSpecialist = 'Hermes CEO Advisor', activePage = null, visibleItems = [], selectedItem = null, availableActions = [], onPlanCreated, onReviewCreated, onSpecialistRequested }) {
  const [messages, setMessages] = useState(() => {
    const stored = hermesStore.getMessages();
    if (stored.length > 0) return stored.map((m, i) => ({ id: `stored-${i}`, role: m.role === 'user' ? 'ray' : 'hermes', text: m.text }));
    return [welcome];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const end = useRef(null);

  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

  const send = useCallback(async (text = input) => {
    const clean = (text || '').trim();
    if (!clean) return;

    // Get sync response first
    const result = buildHermesResponse(clean, activeSpecialist, activePage, {
      visibleItems,
      selectedItem,
      availableActions,
    });

    const now = Date.now();
    const userMsg = { id: `${now}-ray`, role: 'ray', text: clean };
    let responseText = result.text;
    let liveSource = null;
    let modelSource = null;

    // Check for model status questions — answer directly from local data
    const lower = clean.toLowerCase();
    if (/\b(are you using a live model|what model did you use|how are you controlling token|what is using tokens|can you use ollama|can you use openrouter|did you use a model|what did that model call cost|how can we reduce token cost|was that model call necessary|what route did you use|what did that answer cost)\b/i.test(lower)) {
      const avail = getModelAvailability();
      const recentEntries = getUsageEntries().slice(-5);
      const lastModelCall = recentEntries.filter(e => e.wasModelCalled).pop();
      if (/\b(are you using a live model|did you use a model)\b/i.test(lower)) {
        if (!avail.configured) {
          responseText = `No, the Hermes model is not configured yet. All my answers come from local context and Supabase data.`;
        } else if (lastModelCall) {
          responseText = `Yes, I used the model for the last relevant question. Provider: ${lastModelCall.modelProvider}. Model: ${lastModelCall.modelName}. For simple status questions like this, I use local context to save tokens.`;
        } else {
          responseText = `The model gateway is configured (${avail.provider}), but no model call has been made yet in this session. I answer most questions from local context without spending tokens.`;
        }
      } else if (/\bwhat model did you use\b/i.test(lower)) {
        if (lastModelCall) {
          const costInfo = lastModelCall.costKnown
            ? `Estimated cost: $${(lastModelCall.estimatedTotalCostUsd || 0).toFixed(4)}.`
            : `Cost: pricing not configured.`;
          responseText = `Last model call: Provider: ${lastModelCall.modelProvider}. Model: ${lastModelCall.modelName}. Route: ${lastModelCall.route}. Tokens: ~${lastModelCall.estimatedInputTokens} in, ~${lastModelCall.estimatedOutputTokens} out. ${costInfo}`;
        } else {
          responseText = `No model has been called yet in this session. All answers are from local context.`;
        }
      } else if (/\bhow are you controlling token|what is using tokens\b/i.test(lower)) {
        const { input, output, calls, totalCostUsd } = getTotalTokensUsed();
        const usage = getRecentUsageSummary(3);
        const costStr = totalCostUsd > 0 ? `\n• Total estimated cost: $${totalCostUsd.toFixed(4)}` : '';
        responseText = `Token cost controls:\n• Routing policy decides if a question needs a model (most don't)\n• Context is packed within budget (max 6000 tokens for primary model)\n• Output is capped at 1200 tokens\n• Background jobs default to no model\n• Usage is logged locally with cost estimates${costStr}\n\nTotal this session: ${calls} calls, ~${input} input tokens, ~${output} output tokens.\n\nRecent usage:\n${usage}`;
      } else if (/\bwhat did that model call cost\b/i.test(lower) || /\bwhat did that answer cost\b/i.test(lower)) {
        if (lastModelCall) {
          const cost = estimateModelCallCost({
            provider: lastModelCall.modelProvider,
            model: lastModelCall.modelName,
            estimatedInputTokens: lastModelCall.estimatedInputTokens,
            estimatedOutputTokens: lastModelCall.estimatedOutputTokens,
            route: lastModelCall.route,
          });
          const advice = getCostAdvice({
            route: lastModelCall.route,
            reason: lastModelCall.skippedReason || lastModelCall.promptType,
            provider: lastModelCall.modelProvider,
            model: lastModelCall.modelName,
            estimatedInputTokens: lastModelCall.estimatedInputTokens,
            estimatedOutputTokens: lastModelCall.estimatedOutputTokens,
            wasModelCalled: lastModelCall.wasModelCalled,
          });
          responseText = `Last model call:\n• Provider: ${lastModelCall.modelProvider}\n• Model: ${lastModelCall.modelName}\n• Route: ${lastModelCall.route}\n• Tokens: ~${lastModelCall.estimatedInputTokens} in, ~${lastModelCall.estimatedOutputTokens} out\n• Estimated cost: ${cost.displayCost}\n• Duration: ${lastModelCall.durationMs}ms\n\n${advice.summary}`;
        } else {
          responseText = `No model call has been made yet in this session, so no tokens have been spent. Cost: $0.00.`;
        }
      } else if (/\bhow can we reduce token cost\b/i.test(lower)) {
        responseText = getCostReductionAnswer();
      } else if (/\bwas that model call necessary\b/i.test(lower)) {
        if (lastModelCall) {
          const advice = getCostAdvice({
            route: lastModelCall.route,
            reason: lastModelCall.skippedReason || lastModelCall.promptType,
            provider: lastModelCall.modelProvider,
            model: lastModelCall.modelName,
            estimatedInputTokens: lastModelCall.estimatedInputTokens,
            estimatedOutputTokens: lastModelCall.estimatedOutputTokens,
            wasModelCalled: lastModelCall.wasModelCalled,
          });
          responseText = `Last model call necessity:\n• Route: ${lastModelCall.route}\n• Was necessary: ${advice.wasNecessary ? 'Yes' : 'No'}\n• Cheaper alternative: ${advice.cheaperAlternative}\n\n${advice.summary}`;
        } else {
          responseText = `No model call has been made yet in this session.`;
        }
      } else if (/\bwhat route did you use\b/i.test(lower)) {
        if (lastModelCall) {
          responseText = `Last route: ${lastModelCall.route}\n• Reason: ${lastModelCall.whyRouteChosen || lastModelCall.skippedReason || lastModelCall.promptType}\n• Cheaper alternative: ${lastModelCall.cheaperAlternativeRoute || 'none'}\n• Model called: ${lastModelCall.wasModelCalled ? 'yes' : 'no'}`;
        } else {
          responseText = `No route has been used yet in this session.`;
        }
      } else if (/\bcan you use ollama\b/i.test(lower)) {
        responseText = avail.configured
          ? `Yes, Ollama is available as a fallback provider. The Mac Mini has qwen2.5:0.5b and gemma3:1b installed. Ollama is used as a fallback when OpenRouter is unavailable, not as the primary model.`
          : `Ollama is installed on the Mac Mini and the Edge Function supports it as a fallback provider, but the Hermes model is not configured yet.`;
      } else if (/\bcan you use openrouter\b/i.test(lower)) {
        responseText = avail.configured
          ? `Yes, OpenRouter is the primary model path. The OPENROUTER_API_KEY is present in Supabase Edge Function secrets.`
          : `OpenRouter is the recommended primary model path, but HERMES_MODEL is not set yet. The OPENROUTER_API_KEY is present.`;
      }
      modelSource = 'local_status';
    }

    // Enrich with live data for Supabase/web queries (only if no model status answer)
    if (!modelSource) {
      const orchestration = orchestrateHermes(clean, Boolean(activePage));
      const isSupabaseQuery = orchestration.shouldQuerySupabase;
      const isWebQuery = orchestration.shouldQueryWeb;

      if (isSupabaseQuery) {
        setLoading(true);
        try {
          const liveCtx = await buildLiveSupabaseContext(clean);
          if (liveCtx.liveData) {
            responseText = orchestration.routing.intent === 'run_nexus_audit' ? `${responseText}\n\n${liveCtx.text}` : liveCtx.text;
            liveSource = liveCtx.source;
          }
        } catch (e) { /* Keep sync response on error */ }
        setLoading(false);
      }

      if (isWebQuery) {
        setLoading(true);
        try {
          const webResult = await buildWebSearchResponse(clean);
          responseText = webResult.text;
          liveSource = webResult.source;
        } catch (e) { /* Keep sync response on error */ }
        setLoading(false);
      }

      // Try routed model chat for higher-value questions (only if no sync answer yet)
      if (!responseText || responseText === result.text) {
        const modelResult = await hermesModelChat(clean, {
          visibleItems,
          selectedItem,
          pageSummary: activePage || undefined,
        });
        if (modelResult.source === 'model' && modelResult.text) {
          responseText = modelResult.text;
          modelSource = 'model';
        } else if (modelResult.source === 'model_fallback_local' && modelResult.text) {
          responseText = modelResult.text;
          modelSource = 'model_fallback_local';
        }
        // no_model_route and blocked_or_gated: keep local answer
      }
    }

    const hermesMsg = {
      id: `${now}-hermes`,
      role: 'hermes',
      text: responseText,
      source: modelSource || liveSource || result.source,
    };
    setMessages(current => {
      const next = [...current, userMsg, hermesMsg];
      hermesStore.saveMessages(next.map(m => ({ role: m.role === 'ray' ? 'user' : 'hermes', text: m.text })));
      return next;
    });
    setInput('');
    if (result.queued) onPlanCreated?.({ id: `plan-${now}`, prompt: clean, specialist: result.specialist, status: 'queued_local_safe', createdAt: new Date().toISOString() });
  }, [input, activeSpecialist, activePage, visibleItems, selectedItem, availableActions, onPlanCreated]);

  const clearHistory = useCallback(() => {
    hermesStore.clearHistory();
    setMessages([welcome]);
  }, []);

  const statusLabel = isSupabaseConfigured ? 'Live Supabase' : 'Local context';
  const modelAvail = getModelAvailability();
  const modelStatus = modelAvail.configured ? 'Model Ready' : 'No model';
  const badgeLabel = isSupabaseConfigured && modelAvail.configured
    ? 'Live Supabase + Model Ready'
    : isSupabaseConfigured
    ? 'Live Supabase + Local Context'
    : 'Local Context';
  return <section className="nxos-chat-panel">
    <header><div><strong>{activeSpecialist}</strong><small>Ray's private CEO Advisor · {badgeLabel}</small></div><span className="nxos-live"><i /> {loading ? 'Querying...' : statusLabel}</span></header>
    <div className="nxos-chat-log" aria-live="polite">{messages.map((message) => <HermesMessageBubble key={message.id} message={message} onDelegate={(item) => onPlanCreated?.({ id:`plan-${Date.now()}`,prompt:item.text,specialist:activeSpecialist,status:'queued_local_safe' })} onReview={onReviewCreated} onSpecialist={onSpecialistRequested} />)}<div ref={end} /></div>
    <div className="nxos-chat-compose"><textarea aria-label="Message Hermes" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask Hermes about Supabase, research, approvals, or anything…" /><button type="button" className="primary" disabled={loading} onClick={() => send()}>{loading ? 'Loading...' : 'Send'}</button></div>
    <div className="nxos-quick-prompts"><span>Try asking</span>{['can you check Supabase', 'what approvals are pending', 'can you search the internet', 'how do we make money today'].map((prompt) => <button type="button" key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}</div>
    <div className="nxos-chat-actions"><button type="button" onClick={clearHistory}>Clear conversation</button></div>
  </section>;
}
