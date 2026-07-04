import type {AlphaProviderName} from './alphaProviderStatus';
export type AlphaCostMode='cheap'|'fast'|'strategy'|'search'|'deep';
export type AlphaUsageRecord={date:string;localCalls:number;hostedCalls:number;searchCalls:number;estimatedInputTokens:number;estimatedOutputTokens:number;estimatedSpendUsd:number|null;blockedDeepCalls:number;fallbackCount:number;cacheHits:number;providers:Partial<Record<AlphaProviderName,number>>};
const KEY='nexus-alpha-usage-v2',MODE_KEY='nexus-alpha-cost-mode-v1';
export const MAX_HOSTED_CALLS_FALLBACK=25,MAX_SEARCH_RESULTS=5,MAX_SEARCH_CALLS_PER_DAY=10;
const day=()=>new Date().toISOString().slice(0,10);const fresh=():AlphaUsageRecord=>({date:day(),localCalls:0,hostedCalls:0,searchCalls:0,estimatedInputTokens:0,estimatedOutputTokens:0,estimatedSpendUsd:null,blockedDeepCalls:0,fallbackCount:0,cacheHits:0,providers:{}});
export function loadAlphaUsage():AlphaUsageRecord{try{const x=JSON.parse(localStorage.getItem(KEY)||'null');return x?.date===day()?x:fresh()}catch{return fresh()}}
function save(x:AlphaUsageRecord){localStorage.setItem(KEY,JSON.stringify(x));return x}
export function getAlphaCostMode():AlphaCostMode{try{return (localStorage.getItem(MODE_KEY) as AlphaCostMode)||'cheap'}catch{return 'cheap'}}
export function setAlphaCostMode(mode:AlphaCostMode){localStorage.setItem(MODE_KEY,mode)}
export function recordLocal(provider:AlphaProviderName='deterministic_local'){const x=loadAlphaUsage();x.localCalls++;x.providers[provider]=(x.providers[provider]||0)+1;return save(x)}
export function recordHosted(provider:AlphaProviderName='groq',input=0,output=0,estimatedUsd?:number){const x=loadAlphaUsage();x.hostedCalls++;x.estimatedInputTokens+=input;x.estimatedOutputTokens+=output;x.providers[provider]=(x.providers[provider]||0)+1;if(typeof estimatedUsd==='number')x.estimatedSpendUsd=(x.estimatedSpendUsd||0)+estimatedUsd;return save(x)}
export function recordSearch(cacheHit=false){const x=loadAlphaUsage();if(cacheHit)x.cacheHits++;else x.searchCalls++;return save(x)}
export function recordFallback(){const x=loadAlphaUsage();x.fallbackCount++;return save(x)}
export function recordDeepBlocked(){const x=loadAlphaUsage();x.blockedDeepCalls++;return save(x)}
export function canHosted(max=MAX_HOSTED_CALLS_FALLBACK){return loadAlphaUsage().hostedCalls<max}
export function canSearch(){return loadAlphaUsage().searchCalls<MAX_SEARCH_CALLS_PER_DAY}
export function providerAllowedForMode(provider:AlphaProviderName,mode:AlphaCostMode){if(mode==='cheap')return provider==='deterministic_local'||provider==='ollama_local';if(mode==='fast')return provider==='groq'||provider==='deterministic_local'||provider==='ollama_local';if(mode==='strategy'||mode==='search')return true;return false}
export function getAlphaUsageSummary(maxHosted=MAX_HOSTED_CALLS_FALLBACK){const x=loadAlphaUsage();return {...x,maxHosted,maxSearch:MAX_SEARCH_CALLS_PER_DAY,totalTokens:x.estimatedInputTokens+x.estimatedOutputTokens,estimatedSpendLabel:x.estimatedSpendUsd===null?'unknown estimate':`$${x.estimatedSpendUsd.toFixed(4)} estimated`,deepModeUnlocked:false,policy:'One message = max 1 hosted call + 1 search call; no autonomous loops.'}}
// Backward-compatible names for existing callers.
export const recordAlphaLocalCall=recordLocal;export const recordAlphaHostedCall=recordHosted;export const recordAlphaSearchCall=recordSearch;export const canMakeHostedCall=canHosted;export const canMakeSearchCall=canSearch;export const getAlphaCostSummary=getAlphaUsageSummary;
