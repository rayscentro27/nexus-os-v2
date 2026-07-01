export const nexusCliCommandRegistry = [
  ['git_status','Git status','git status --short --branch','SAFE_READ_ONLY','Shows repository state without changing it.','low',false,null,'Redact unexpected credential-like command arguments.'],
  ['git_log','Recent commits','git log --oneline -5','SAFE_READ_ONLY','Shows recent local commit summaries.','low',false,null,'Return at most five summaries.'],
  ['frontend_build','Frontend build','npm run build','SAFE_READ_ONLY','Compiles and bundles local source; no deployment.','low',false,null,'Return pass/fail and artifact names only.'],
  ['unit_tests','Unit tests','npx vitest run','SAFE_READ_ONLY','Runs the repository test suite.','low',false,null,'Return counts and failures; never dump env.'],
  ['launchd_inventory','Nexus launchd inventory','launchctl list | grep nexus','SAFE_READ_ONLY','Reads launchd labels; load state is not process proof.','low',false,null,'No environment output.'],
  ['process_inventory','Nexus process inventory','ps aux | grep nexus','SAFE_READ_ONLY','Reads Nexus-related process metadata.','low',false,null,'Truncate commands and redact tokens.'],
  ['report_inventory','Report inventory','ls reports','SAFE_READ_ONLY','Lists approved report filenames.','low',false,null,'Do not read .env or secret files.'],
  ['operations_collector','Operations collector','python3 scripts/ops/collect_nexus_operations_status.py','SAFE_READ_ONLY','Writes sanitized local operations reports from read-only checks.','low',false,null,'Presence-only env checks; no values.'],
  ['supabase_counts','Safe Supabase counts','authenticated RLS count summaries','SAFE_READ_ONLY','Allows tenant-scoped counts through existing authenticated/RLS paths.','medium',false,null,'Counts/summaries only; no service role in frontend.'],
  ['seed_supabase','Seed Supabase','approved seed script','APPROVAL_REQUIRED','Persistent production-like write requires explicit review.','high',true,null,'Preview tenant/table/count before approval.'],
  ['start_scheduler','Start scheduler','launchctl load <approved plist>','APPROVAL_REQUIRED','Changes background execution state.','high',true,null,'Show label, cadence, logs, rollback.'],
  ['stop_scheduler','Stop scheduler','launchctl unload <approved plist>','APPROVAL_REQUIRED','Stops background work.','high',true,null,'Show affected label and current proof.'],
  ['deploy','Deploy','git push / netlify deploy','APPROVAL_REQUIRED','Changes production software.','high',true,null,'Require build/test evidence and explicit target.'],
  ['web_research','Run web research','approved research task','APPROVAL_REQUIRED','May use external providers or quotas.','medium',true,null,'State provider, quota, and citation rules.'],
  ['print_env','Print environment secrets','cat .env','BLOCKED','Secret disclosure is prohibited.','critical',true,'Never expose environment values.','Report variable-name presence only.'],
  ['delete_database','Delete database rows','delete/truncate database','BLOCKED','Destructive database actions are prohibited from Hermes.','critical',true,'Destructive SQL is blocked.','No execution.'],
  ['weaken_rls','Weaken RLS','disable or bypass RLS','BLOCKED','Tenant isolation must remain enforced.','critical',true,'RLS weakening is blocked.','No execution.'],
  ['external_actions','External sends/actions','send/publish/charge/trade/dispute','BLOCKED','Hermes cannot directly perform irreversible external actions.','critical',true,'Direct execution is blocked; use reviewed workflows.','No execution.'],
].map(([command_id,label,command_preview,category,explanation,risk,approval_required,blocked_reason,safe_output_rules]) => ({command_id,label,command_preview,category,explanation,risk,approval_required,blocked_reason,safe_output_rules}));

export function findNexusCommand(commandId) {
  return nexusCliCommandRegistry.find(item => item.command_id === commandId) || null;
}
