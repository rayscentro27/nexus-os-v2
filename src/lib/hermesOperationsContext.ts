import operations from '../../reports/nexus_operations_status_latest.json';
import processInventory from '../../reports/nexus_process_inventory_latest.json';
import schedulerInventory from '../../reports/nexus_scheduler_inventory_latest.json';
import cliInventory from '../../reports/nexus_cli_inventory_latest.json';
import youtubeInventory from '../../reports/nexus_youtube_research_status_latest.json';
import hermesOperations from '../../reports/hermes_operations_status_latest.json';
import { explainHermesBlocker } from './hermesBlockerExplainer';
import { processGroupsFromCommands, renderAdvisorResponse, summarizeCliAvailability, summarizeLiveStaticUnproven } from './hermesPlainLanguageAdvisor';

type InventoryItem = { name:string; status:string; checked_at:string; hermes_readable_summary:string; safe_next_action:string; proof?:string; loaded?:boolean; available?:boolean; command?:string; running_now?:boolean; scheduler_exists?:boolean; last_metadata_fetch?:string|null; last_transcript_fetch?:string|null; notebooklm_export_status?:string; supabase_write_proof?:boolean; rows_written_last_24h?:string|number; limitations?:string[]; };
const ageHours=(stamp:string)=>Math.max(0,(Date.now()-new Date(stamp).getTime())/36e5);
export function operationsFreshness(){const hours=ageHours(operations.checked_at);return {checkedAt:operations.checked_at,ageHours:hours,stale:hours>24};}
export function answerOperationsQuestion(message:string):string{
  const text=message.toLowerCase(); const fresh=operationsFreshness(); const stale=fresh.stale?`The audit is stale (${fresh.checkedAt}); rerun the collector. `:'';
  const processes=processInventory.items as InventoryItem[]; const schedulers=schedulerInventory.items as InventoryItem[]; const clis=cliInventory.items as InventoryItem[]; const youtube=(youtubeInventory.items as InventoryItem[])[0];
  const source=`\n\nSource: Mac Mini read-only operations audit checked ${fresh.checkedAt}. Safe refresh: python3 scripts/ops/collect_nexus_operations_status.py`;
  if(/youtube/.test(text)) {
    const running = youtube.running_now ? 'running now' : 'not running now';
    const loaded = youtube.loaded ? 'loaded' : 'not loaded';
    const scheduler = youtube.scheduler_exists ? `scheduler exists and is ${loaded}` : 'scheduler not proven';
    const transcript = youtube.last_transcript_fetch ? `last transcript fetch: ${youtube.last_transcript_fetch}` : 'transcript fetch proof is missing';
    const notebook = youtube.notebooklm_export_status ? `NotebookLM/export status: ${youtube.notebooklm_export_status}` : 'NotebookLM/export proof is missing';
    const writes = youtube.supabase_write_proof
      ? `a Supabase-ready/write-proof file exists, but fresh row counts are ${youtube.rows_written_last_24h ?? 'unknown'}`
      : 'fresh Supabase write proof is missing';
    return `${stale}YouTube research is not proven live (status: ${youtube.status}).\n\nPlain English: Supabase can have research rows while the YouTube watcher is not actively proven to be fetching videos, pulling transcripts, and writing new rows. ${explainHermesBlocker('youtube_not_proven_live')}\n\nProof I checked: ${scheduler}; process status: ${running}; last metadata fetch: ${youtube.last_metadata_fetch || 'unknown'}; ${transcript}; ${notebook}; ${writes}.\n\nWhat is missing: current process proof, recent success log proof, and fresh Supabase row-count/write proof from the watcher.\n\nSafe next action: ${youtube.safe_next_action}${source}`;
  }
  if(/cli tools|cli inventory/.test(text)) {
    const available=clis.filter(x=>x.available).map(x=>x.name);
    return `${stale}${renderAdvisorResponse(summarizeCliAvailability(available, fresh.checkedAt))}`;
  }
  if(/process|background jobs|what is running/.test(text)) {
    const groups=processGroupsFromCommands(processes.map(x=>x.command||x.hermes_readable_summary));
    return `${stale}I found ${processes.length} Nexus-related processes with direct process proof.\n\nPlain English: Nexus has active local processes running on the Mac Mini. The main groups are ${groups.join(', ') || 'Nexus services'}. I can show raw paths if you ask, but I am not dumping command paths by default because they are implementation detail.\n\nProof I checked: process inventory from ps, with PID and uptime proof for each item.\n\nSafe next action: inspect the latest logs for any group you care about; do not stop or restart anything from Hermes without approval.${source}`;
  }
  if(/failed overnight/.test(text)) return `${stale}The latest collector does not contain a verified consolidated overnight failure record. It found process, scheduler, and log timestamps only. Check the daily/evening launchd error logs and rerun the collector; I will not infer success or failure from a loaded plist.${source}`;
  if(/token|env/.test(text)) return `${stale}CLI tools are installed, but token/rate limits are ${operations.token_rate_limits.status}. ${explainHermesBlocker('token_rate_limits_unproven')} Environment presence is recorded by variable name only, never value.${source}`;
  if(/wrote to supabase|supabase write/.test(text)) return `${stale}The existing Hermes operations report (${hermesOperations.generated_at}) records ${hermesOperations.supabase_writes.last_24h} summarized writes in 24h across ${hermesOperations.supabase_writes.tables_written.join(', ')}. Treat this as report evidence; authenticated live queries are the authority.${source}`;
  if(/live.*static.*unproven|static.*unproven|real and what is fake|what is connected|not running|installed but not proven|report-only|report only/.test(text)) {
    const answer=summarizeLiveStaticUnproven({
      runningProcesses:processes.length,
      schedulerCount:schedulers.length,
      loadedSchedulers:schedulers.filter(x=>x.loaded).length,
      liveSections:Object.keys(hermesOperations.live_sections || {}),
      staticSections:Object.keys(hermesOperations.static_sections || {}),
      unproven:[youtube.status==='not_proven_live'?'YouTube research is not proven live':''].filter(Boolean),
      checkedAt:fresh.checkedAt,
    });
    return `${stale}${renderAdvisorResponse(answer)}\n\n${explainHermesBlocker('plist_loaded_only')}`;
  }
  if(/holding back|why.*hold/.test(text)) return `${stale}I’m not holding back; I’m separating proven access from unproven access.\n\nI can read live Supabase when the authenticated session is available, and I can read the latest Mac Mini operations audit. I cannot claim YouTube automation, web search, or live model reasoning until those have process, log, config, or provider proof.\n\nPlain English: if I have proof, I will say it is live. If I only have installed files, old rows, or a loaded plist, I will call it unproven.\n\nSafe next action: refresh the operations collector and verify the specific missing proof for the blocker you care about.${source}`;
  if(/explain.*plain language|plain language.*report|explain.*audit/.test(text)) return `${stale}In plain language: Nexus is partially live, not fully autonomous.\n\nWhat it means: the Mac Mini has active Nexus processes, Hermes has live/report context, and several Supabase-backed sections exist. The gap is proof of fresh automation: loaded schedulers and existing rows do not automatically prove a job ran successfully today.\n\nWhy it matters: this keeps us from fooling ourselves. We can use proven systems confidently and target the unproven parts without making fake claims.\n\nSafe next action: refresh the collector, inspect logs for the highest-value unproven automation, then use Ray Review for any action that changes state.${source}`;
  const running=processes.length; const loaded=schedulers.filter(x=>x.loaded).length; const unproven=(youtube?.status==='not_proven_live'?1:0);
  return `${stale}Nexus audit summary: ${running} processes have direct running proof; ${schedulers.length} launchd jobs are installed (${loaded} loaded, but load state alone is not running proof); ${unproven} highlighted research area is unproven. The existing Hermes operations snapshot lists ${Object.keys(hermesOperations.live_sections).length} live Supabase sections, but authenticated live queries remain the authority. Static/report-only evidence includes cached metadata, package scripts, and generated reports.\n\nPlain English: parts of Nexus are real and running, parts are connected to live Supabase data, and parts are still snapshots or installed jobs that need fresh proof.\n\nSafe next actions: inspect recent logs, refresh this collector, and review blockers in Ray Review. No process was started or changed.${source}`;
}
