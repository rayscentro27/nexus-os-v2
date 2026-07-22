import {useEffect,useMemo,useState} from 'react';
import {ALPHA_MODES,type AlphaConversationMode} from '../hermes/alpha/hermesAlphaModeRouter';
import {respondAsAlpha} from '../hermes/alpha/hermesAlphaConversationEngine';
import {fetchAlphaProviderStatus,runAlphaProviderBridge} from '../hermes/alpha/alphaProviderBridge';
import {defaultAlphaProviderStatus,type AlphaProviderName} from '../hermes/alpha/alphaProviderStatus';
import {clearAlphaMemory,exportAlphaSession,loadAlphaMemory,saveAlphaMemory,type AlphaMessage} from '../hermes/alpha/hermesAlphaLocalMemory';
import {alphaWebSearch,isCurrentQuestion,searchOffMessage} from '../hermes/alpha/alphaWebSearch';
import {alphaUrlReview,extractUrl,isUrlReviewRequest} from '../hermes/alpha/alphaUrlReview';
import {canHosted,canSearch,canUrlReview,getAlphaCostMode,getAlphaUsageSummary,providerAllowedForMode,recordDeepBlocked,recordFallback,recordHosted,recordLocal,recordSearch,recordUrlReview,setAlphaCostMode,type AlphaCostMode} from '../hermes/alpha/alphaCostController';
import {buildTrace,traceSummary,type AlphaRouteTrace,type AlphaWebProvider,type AlphaWebStatus} from '../hermes/alpha/alphaRouteTrace';

const PROVIDER_KEY='nexus-alpha-provider-v1',SEARCH_KEY='nexus-alpha-search-enabled-v1',URL_REVIEW_KEY='nexus-alpha-url-review-enabled-v1',PREF_VERSION_KEY='nexus-alpha-preference-version';
function alphaModelFirstMode(){const env=import.meta.env as Record<string,string|undefined>;const mode=env.VITE_ALPHA_MODEL_FIRST_MODE||'OFF';return ['SHADOW','RAY_ONLY_PILOT','ACTIVE'].includes(mode)?mode:'OFF'}
function loadProvider():AlphaProviderName{try{const saved=localStorage.getItem(PROVIDER_KEY) as AlphaProviderName|null;if(saved)return saved;return alphaModelFirstMode()==='OFF'?'deterministic_local':'openrouter'}catch{return alphaModelFirstMode()==='OFF'?'deterministic_local':'openrouter'}}
function preferredHostedProvider(status:typeof defaultAlphaProviderStatus,selected:AlphaProviderName):AlphaProviderName{if(selected!=='deterministic_local'&&status.providers[selected]?.available)return selected;if(status.providers.openrouter.available)return 'openrouter';if(status.providers.groq.available)return 'groq';return 'deterministic_local'}
function alphaHistory(messages:AlphaMessage[]){return messages.slice(-12).map(m=>({role:m.role==='alpha'?'assistant' as const:'user' as const,content:m.text.slice(0,900)}))}
function loadSearch(){try{return localStorage.getItem(SEARCH_KEY)==='true'}catch{return false}}
function loadUrlReview(){try{return localStorage.getItem(URL_REVIEW_KEY)==='true'}catch{return false}}

function urlReviewRecommendation(content:string,title:string,url:string):string{const excerpt=content.slice(0,1000).replace(/\n+/g,' ').replace(/\s+/g,' ');return `URL Review: ${title||url}

1. What this page is: ${title?`"${title}" at ${url}`:`Content from ${url}`}

2. Why it may matter for Nexus/GoClear/Alpha: Based on the extracted content, this page could represent a tool, service, or approach relevant to your ecosystem.

3. Monetization angle: Review the key offerings or models mentioned. Look for affiliate programs, API access, or partnership opportunities.

4. Risks / hype / compliance concerns: Check for unverified claims, regulatory issues, or platform reliability concerns.

5. Use now, save for later, or ignore: Determine if this fits current goals or warrants future investigation.

6. Suggested next action: Research further, validate claims, or archive for later reference.

Extracted content preview:
${excerpt}...`}

export default function HermesAlphaWorkspace({onOpenReports}:{onOpenReports?:()=>void}){
  const [messages,setMessages]=useState<AlphaMessage[]>(()=>loadAlphaMemory()); const [input,setInput]=useState(''); const [mode,setMode]=useState<AlphaConversationMode>('General Conversation');
  const [draft,setDraft]=useState<object|null>(null); const [providerStatus,setProviderStatus]=useState(defaultAlphaProviderStatus); const [provider,setProvider]=useState<AlphaProviderName>(loadProvider);
  const [providerNote,setProviderNote]=useState('Cost-safe deterministic fallback selected.'); const [searchEnabled,setSearchEnabled]=useState(loadSearch); const [urlReviewEnabled,setUrlReviewEnabled]=useState(loadUrlReview); const [costMode,setCostModeState]=useState<AlphaCostMode>(getAlphaCostMode);
  const [usage,setUsage]=useState(getAlphaUsageSummary); const [lastTrace,setLastTrace]=useState<AlphaRouteTrace|null>(null); const [sending,setSending]=useState(false);
  const opportunities=useMemo(()=>['GoClear teaser validation','Fundability checklist lead magnet','Voice-agent workflow audit','SEO education cluster','Research newsletter'],[]);

  useEffect(()=>{fetchAlphaProviderStatus().then(status=>{setProviderStatus(status);if(alphaModelFirstMode()!=='OFF'){const preferred=preferredHostedProvider(status,provider);try{const version=localStorage.getItem(PREF_VERSION_KEY);const staleLocal=localStorage.getItem(PROVIDER_KEY)==='deterministic_local'||getAlphaCostMode()==='cheap';if(preferred!=='deterministic_local'&&(!version||staleLocal)){localStorage.setItem(PREF_VERSION_KEY,'2');localStorage.setItem(PROVIDER_KEY,preferred);setProvider(preferred);setAlphaCostMode(preferred==='openrouter'?'strategy':'fast');setCostModeState(preferred==='openrouter'?'strategy':'fast');setProviderNote(`Migrated obsolete local-only Alpha preferences. ${preferred} is selected through the secure backend.`);return}}catch{}if(preferred!=='deterministic_local')setProviderNote(`${preferred} available through same-origin backend. Hosted model will be used unless fallback is required.`)}})},[]);
  useEffect(()=>{localStorage.setItem(PROVIDER_KEY,provider);localStorage.setItem(SEARCH_KEY,String(searchEnabled));localStorage.setItem(URL_REVIEW_KEY,String(urlReviewEnabled));window.dispatchEvent(new CustomEvent('alpha-status-change',{detail:{provider,providerReady:providerStatus.providers[provider]?.available??false,searchEnabled,urlReviewEnabled:urlReviewEnabled&&providerStatus.urlReview?.available}}))},[provider,providerStatus,searchEnabled,urlReviewEnabled]);
  useEffect(()=>localStorage.setItem(SEARCH_KEY,String(searchEnabled)),[searchEnabled]);
  function changeCostMode(value:AlphaCostMode){setAlphaCostMode(value);setCostModeState(value)}
  function changeProvider(value:AlphaProviderName){setProvider(value);if(value==='groq')changeCostMode('fast');else if(value==='openrouter')changeCostMode('strategy')}
  function changeSearch(enabled:boolean){setSearchEnabled(enabled);if(enabled)changeCostMode('search')}
  function changeUrlReview(enabled:boolean){setUrlReviewEnabled(enabled);if(enabled)changeCostMode('url_review')}

  async function send(){
    const prompt=input.trim(); if(!prompt||sending)return; setSending(true); setInput('');
    const local=respondAsAlpha(prompt,mode,Date.now()); const memoryUsed=messages.length>0; let text=local.text; let providerUsed:AlphaProviderName='deterministic_local'; let providerSource:AlphaRouteTrace['provider_source']='deterministic_local'; let model='deterministic-rules-v2'; let fallbackReason='';
    let webUsed=false,webProvider:AlphaWebProvider='none',webStatus:AlphaWebStatus=searchEnabled?'available':'disabled',webQuery='',webCount=0,searchEstimated=false; let searchContext='';
    let urlReviewUsed=false;let urlReviewStatus:AlphaWebStatus='disabled';

    const detectedUrl=extractUrl(prompt);
    const urlReviewRequest=isUrlReviewRequest(prompt);

    const hostedFirstProvider=alphaModelFirstMode()==='OFF'?'deterministic_local':preferredHostedProvider(providerStatus,provider);
    const historyForProvider=alphaHistory(messages);

    if(urlReviewRequest&&urlReviewEnabled&&canUrlReview()&&detectedUrl){
      recordUrlReview();
      const review=await alphaUrlReview(detectedUrl);
      urlReviewUsed=review.ok;
      urlReviewStatus=review.extractionStatus;
      if(review.ok&&review.content){
        text=urlReviewRecommendation(review.content,review.title||'',review.url);
        recordLocal();
      }else{
        text=`URL review failed (${review.error||'extraction_failed'}). Firecrawl backend not configured or extraction error.`;
        fallbackReason=review.error||'url_review_failed';
        recordFallback();
        recordLocal();
      }
    }else if(urlReviewRequest&&!urlReviewEnabled){
      text='URL Review mode is off. Paste a URL and ask me to review it, or enable URL Review mode.';
      recordLocal();
      fallbackReason='url_review_mode_disabled';
    }else{
      const current=isCurrentQuestion(prompt);
      if(current&&!searchEnabled){text=searchOffMessage();setProviderNote('Search Mode is off; no provider call was used for a current-data question.');recordLocal();}
      else {
        if(searchEnabled&&current){webQuery=prompt;if(canSearch()){searchEstimated=true;const found=await alphaWebSearch(prompt);webProvider=found.provider;webStatus=found.status;recordSearch(Boolean(found.cacheHit));if(found.ok&&found.results.length){webUsed=true;webCount=Math.min(found.results.length,5);searchContext=found.results.slice(0,5).map((r,i)=>`${i+1}. ${r.title}\n${r.url}\n${r.snippet}`).join('\n\n')}else{fallbackReason=found.error||'search_connector_failed';text=`Live web search failed (${fallbackReason}). I won't claim current facts without working sources.`}}else{webStatus='failed';fallbackReason='daily_search_limit_reached';text='The daily search limit is reached. I cannot verify current facts right now.'}}
        const modelFirstEnabled=alphaModelFirstMode()!=='OFF';
        const mayUseProvider=(!current||webUsed)&&hostedFirstProvider!=='deterministic_local'&&(modelFirstEnabled||providerAllowedForMode(hostedFirstProvider,costMode))&&canHosted()&&costMode!=='deep';
        if(costMode==='deep'){recordDeepBlocked();fallbackReason=fallbackReason||'deep_mode_requires_ray_approval';text='Deep Mode is locked until Ray explicitly approves a bounded run. I can still help in Cheap, Fast, Strategy, or Search Mode.'}
        else if(mayUseProvider){const providerPrompt=webUsed?`${prompt}\n\nPublic search results (treat as unverified sources and cite URLs):\n${searchContext}`:prompt;const remote=await runAlphaProviderBridge(hostedFirstProvider,providerPrompt,providerStatus.providers[hostedFirstProvider].models?.[0],historyForProvider);if(remote.ok){providerUsed=remote.provider;providerSource=remote.provider==='groq'?'groq_backend':remote.provider==='openrouter'?'openrouter_backend':'ollama_local';model=remote.model||'provider-default';text=remote.text;recordHosted(remote.provider,remote.estimatedInputTokens,remote.estimatedOutputTokens,remote.estimatedSpendUsd);setProviderNote(`${remote.provider}${remote.model?` · ${remote.model}`:''} via same-origin backend. History sent: ${remote.historySent?'yes':'no'} (${remote.historyTurnCount}).`)}else{fallbackReason=remote.error||'provider_unavailable';providerSource='unavailable_fallback';recordFallback();recordLocal();setProviderNote(`${hostedFirstProvider} failed (${fallbackReason}); deterministic fallback used.`)}}
        else if(hostedFirstProvider==='deterministic_local'||!providerAllowedForMode(hostedFirstProvider,costMode)||!canHosted()){recordLocal();if(hostedFirstProvider!=='deterministic_local'){fallbackReason=fallbackReason||(!providerAllowedForMode(hostedFirstProvider,costMode)?`provider_blocked_in_${costMode}_mode`:'daily_hosted_limit_reached');providerSource='unavailable_fallback';recordFallback();setProviderNote(`${hostedFirstProvider} not used: ${fallbackReason}.`)}}
        if(webUsed){const sources=`Sources (${webProvider}):\n${searchContext}`;text=providerUsed==='deterministic_local'?`${sources}\n\nThese are keyless public-search results, not verified facts. Review the linked sources before acting.`:text}
      }
    }
    const webUsedFinal=webUsed||urlReviewUsed;
    const trace=buildTrace({mode:local.mode,selected_provider:hostedFirstProvider,provider_used:providerUsed,provider_source:urlReviewUsed?'url_review_backend':providerSource,model_used:model,memory_used:providerUsed!=='deterministic_local'?historyForProvider.length>0:memoryUsed,memory_source:providerUsed!=='deterministic_local'&&historyForProvider.length>0?'session_memory':memoryUsed?'session_memory':'none',web_used:webUsedFinal,web_provider:urlReviewUsed?'firecrawl':webProvider,web_status:urlReviewUsed?urlReviewStatus:webStatus,web_query:detectedUrl||webQuery,web_result_count:webCount,reason_for_provider_selection:urlReviewUsed?'URL review mode triggered.':'Hosted model first when configured; deterministic engine is fallback only.',fallback_reason:fallbackReason,estimated_hosted_call:providerUsed==='groq'||providerUsed==='openrouter',estimated_search_call:searchEstimated,estimated_cost_label:providerUsed==='deterministic_local'?'local_free':'hosted_estimate'});
    const now=new Date().toISOString(),next=[...messages,{id:`ray-${Date.now()}`,role:'ray' as const,text:prompt,createdAt:now,mode},{id:trace.message_id,role:'alpha' as const,text,createdAt:now,mode:local.mode,trace}];setMessages(next);saveAlphaMemory(next);setMode(local.mode);setDraft(local.draft||null);setLastTrace(trace);setUsage(getAlphaUsageSummary());setSending(false);
  }
  function clear(){clearAlphaMemory();setMessages([]);setDraft(null);setLastTrace(null)}
  function download(){const blob=new Blob([exportAlphaSession(messages)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='hermes-alpha-local-session.json';a.click();URL.revokeObjectURL(url)}
  const actualProvider=alphaModelFirstMode()==='OFF'?'deterministic_local':preferredHostedProvider(providerStatus,provider);
  const actualProviderReady=providerStatus.providers[actualProvider]?.available??false;
  return <div className="nxos-stack" data-testid="hermes-alpha-workspace">
    <section className="glass panel"><div className="between"><div><p className="nx-muted">ALPHA IS SEPARATE FROM NEXUS HERMES</p><h2>Hermes Alpha · Strategy Brain</h2><p>Provider-aware strategy conversation. No Supabase, client data, or execution.</p></div><span className="pill pill-green">{actualProviderReady&&actualProvider!=='deterministic_local'?'Hosted Provider Ready':'Local Fallback'}</span></div><div><span className="pill pill-green">Selected: {provider}</span> <span className="pill pill-blue">Actual: {actualProvider}</span> <span className="pill pill-blue">Web Search: {searchEnabled?'On':'Off'}</span> <span className="pill pill-amber">No Supabase</span> <span className="pill pill-red">No client data · External actions disabled</span></div></section>
    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:12,alignItems:'start'}}>
      <section className="glass panel alpha-conversation-panel" data-testid="alpha-conversation-panel" style={{display:'flex',flexDirection:'column',height:'min(78vh,820px)',minHeight:520,overflow:'hidden'}}><div className="between"><h3>Conversation</h3><select aria-label="Alpha mode" value={mode} onChange={e=>setMode(e.target.value as AlphaConversationMode)}>{ALPHA_MODES.map(x=><option key={x}>{x}</option>)}</select></div>
        <div aria-label="Alpha conversation" style={{flex:'1 1 auto',minHeight:0,overflowY:'auto',display:'grid',alignContent:'start',gap:8,padding:'8px 2px'}}>{messages.length===0&&<div className="nx-soft" style={{padding:16}}>Ask Alpha about a strategy, opportunity, app, voice agent, affiliate idea, or paste a URL to review.</div>}{messages.map(m=><article key={m.id} className="nx-soft" style={{padding:12,marginLeft:m.role==='ray'?'12%':0,borderColor:m.role==='ray'?'#4372b8':'#7857d8'}}><strong>{m.role==='ray'?'Ray':'Hermes Alpha'} · {m.mode}</strong><p style={{whiteSpace:'pre-wrap'}}>{m.text}</p>{m.role==='alpha'&&m.trace&&<details style={{fontSize:11,marginTop:5,borderTop:'1px solid #333',paddingTop:5}}><summary style={{cursor:'pointer'}}>{traceSummary(m.trace)}</summary><pre style={{whiteSpace:'pre-wrap',fontSize:10}}>{JSON.stringify(m.trace,null,2)}</pre></details>}</article>)}</div>
        <div className="alpha-sticky-composer" data-testid="alpha-composer" style={{position:'sticky',bottom:0,zIndex:5,flex:'0 0 auto',background:'#10192b',borderTop:'1px solid #35425a',padding:'10px 0 0'}}><textarea data-testid="alpha-message-input" aria-label="Message Alpha" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void send()}}} rows={3} placeholder="Talk to Alpha or paste a URL to review…" style={{width:'100%',minHeight:86,resize:'vertical',display:'block'}}/><div className="action-row"><button data-testid="alpha-send-button" type="button" disabled={sending} onClick={()=>void send()}>{sending?'Thinking…':'Send to Alpha'}</button><button type="button" onClick={download}>Handoff / export</button><button type="button" onClick={clear}>Clear conversation</button><button type="button" onClick={onOpenReports}>Reports</button></div></div>
      </section>
      <aside className="side-stack" style={{maxHeight:'78vh',overflowY:'auto'}}>
        <section className="glass panel"><h3>Provider & Cost Controls</h3><label htmlFor="alpha-provider">Selected provider</label><select id="alpha-provider" value={provider} onChange={e=>changeProvider(e.target.value as AlphaProviderName)}>{Object.entries(providerStatus.providers).map(([name,detail])=><option key={name} value={name} disabled={!detail.available}>{name} — {detail.available?'available':'unavailable'}</option>)}</select><label htmlFor="alpha-cost-mode">Cost Mode</label><select id="alpha-cost-mode" value={costMode} onChange={e=>changeCostMode(e.target.value as AlphaCostMode)}><option value="cheap">Cheap Mode · local only</option><option value="fast">Fast Mode · Groq capped</option><option value="strategy">Strategy Mode · OpenRouter capped</option><option value="search">Search Mode · max 5 results</option><option value="url_review">URL Review Mode · Firecrawl</option><option value="deep">Deep Mode · approval required</option></select><label><input type="checkbox" checked={searchEnabled} onChange={e=>changeSearch(e.target.checked)}/> Enable backend web search</label><label><input type="checkbox" checked={urlReviewEnabled} onChange={e=>changeUrlReview(e.target.checked)}/> Enable URL Review (Firecrawl)</label><p><strong>Search connector:</strong> {providerStatus.webSearch.available?`${providerStatus.webSearch.provider} available`:'Connector missing'} — {providerStatus.webSearch.reason}</p><p><strong>URL review:</strong> {providerStatus.urlReview?.available?`${providerStatus.urlReview.provider} available`:'Disabled'} — {providerStatus.urlReview?.reason}</p><p>{providerNote}</p><small>Providers (Groq/OpenRouter) handle model calls. Web search (SearXNG) and URL review (Firecrawl) are extraction connectors. DuckDuckGo keyless was disabled after Node-runtime verification failed.</small>{Object.entries(providerStatus.providers).map(([name,detail])=><p key={name}><strong>{name}:</strong> {detail.available?'Available':'Gated'} — {detail.reason}</p>)}</section>
        <section className="glass panel"><h3>Usage Today</h3><p>Local calls: {usage.localCalls}</p><p>Hosted calls: {usage.hostedCalls}/{usage.maxHosted}</p><p>Search calls: {usage.searchCalls}/{usage.maxSearch}</p><p>URL review calls: {usage.urlReviewCalls||0}/{usage.maxUrlReviews||10}</p><p>Tokens: {usage.totalTokens||'unknown'}</p><p>Estimated spend: {usage.estimatedSpendLabel}</p><p>Fallbacks: {usage.fallbackCount} · Cache hits: {usage.cacheHits}</p><p>Deep Mode: locked · blocked {usage.blockedDeepCalls}</p><small>{usage.policy}</small></section>
        <section className="glass panel"><h3>Memory & Sources</h3><p>Memory: session/localStorage only</p><p>Reports: none used in this response path</p><p>Web: {searchEnabled?'available when current question is asked':'off'}</p><p>URL Review: {urlReviewEnabled&&providerStatus.urlReview?.available?'on':'off'}</p><p>Supabase: blocked</p><p>Client data: blocked</p></section>
        {lastTrace&&<section className="glass panel"><h3>Last Response Source</h3><p>{traceSummary(lastTrace)}</p></section>}
        <section className="glass panel"><h3>Opportunity Canvas</h3>{opportunities.map(x=><div className="nx-soft" style={{padding:8,marginBottom:5}} key={x}>{x}</div>)}</section>
        <section className="glass panel"><h3>Action Draft</h3><pre style={{whiteSpace:'pre-wrap',fontSize:11}}>{draft?JSON.stringify(draft,null,2):'Ask for a handoff or Ray Review draft.'}</pre></section>
      </aside>
    </div>
  </div>;
}
