import operations from '../../reports/nexus_operations_status_latest.json';
import processInventory from '../../reports/nexus_process_inventory_latest.json';
import schedulerInventory from '../../reports/nexus_scheduler_inventory_latest.json';
import cliInventory from '../../reports/nexus_cli_inventory_latest.json';
import youtubeInventory from '../../reports/nexus_youtube_research_status_latest.json';
import hermesOperations from '../../reports/hermes_operations_status_latest.json';

type InventoryItem = { name:string; status:string; checked_at:string; hermes_readable_summary:string; safe_next_action:string; loaded?:boolean; available?:boolean; };
const ageHours=(stamp:string)=>Math.max(0,(Date.now()-new Date(stamp).getTime())/36e5);
export function operationsFreshness(){const hours=ageHours(operations.checked_at);return {checkedAt:operations.checked_at,ageHours:hours,stale:hours>24};}
export function answerOperationsQuestion(message:string):string{
  const text=message.toLowerCase(); const fresh=operationsFreshness(); const stale=fresh.stale?`The audit is stale (${fresh.checkedAt}); rerun the collector. `:'';
  const processes=processInventory.items as InventoryItem[]; const schedulers=schedulerInventory.items as InventoryItem[]; const clis=cliInventory.items as InventoryItem[]; const youtube=(youtubeInventory.items as InventoryItem[])[0];
  const source=`\n\nSource: Mac Mini read-only operations audit checked ${fresh.checkedAt}. Safe refresh: python3 scripts/ops/collect_nexus_operations_status.py`;
  if(/youtube/.test(text)) return `${stale}YouTube research status is ${youtube.status}. ${youtube.hermes_readable_summary} Safe next step: ${youtube.safe_next_action}${source}`;
  if(/cli tools|cli inventory/.test(text)) {const available=clis.filter(x=>x.available).map(x=>x.name);return `${stale}Available CLI tools: ${available.join(', ')||'none proven'}. Availability does not prove authentication or permission.${source}`;}
  if(/process|background jobs|what is running/.test(text)) return `${stale}${processes.length} Nexus-related processes had direct ps proof: ${processes.slice(0,8).map(x=>x.hermes_readable_summary).join('; ')||'none'}.${source}`;
  if(/failed overnight/.test(text)) return `${stale}The latest collector does not contain a verified consolidated overnight failure record. It found process, scheduler, and log timestamps only. Check the daily/evening launchd error logs and rerun the collector; I will not infer success or failure from a loaded plist.${source}`;
  if(/token|env/.test(text)) return `${stale}Known token/rate limits are ${operations.token_rate_limits.status}; I will not guess. Environment presence is recorded by variable name only, never value.${source}`;
  if(/wrote to supabase|supabase write/.test(text)) return `${stale}The existing Hermes operations report (${hermesOperations.generated_at}) records ${hermesOperations.supabase_writes.last_24h} summarized writes in 24h across ${hermesOperations.supabase_writes.tables_written.join(', ')}. Treat this as report evidence; authenticated live queries are the authority.${source}`;
  const running=processes.length; const loaded=schedulers.filter(x=>x.loaded).length; const unproven=(youtube?.status==='not_proven_live'?1:0);
  return `${stale}Nexus audit summary: ${running} processes have direct running proof; ${schedulers.length} launchd jobs are installed (${loaded} loaded, but load state alone is not running proof); ${unproven} highlighted research area is unproven. The existing Hermes operations snapshot lists ${Object.keys(hermesOperations.live_sections).length} live Supabase sections, but authenticated live queries remain the authority. Static/report-only evidence includes cached metadata, package scripts, and generated reports. Safe next actions: inspect recent logs, refresh this collector, and review blockers in Ray Review. No process was started or changed.${source}`;
}
