import { describe,expect,it } from 'vitest';
import { readFileSync } from 'node:fs';
import operations from '../reports/nexus_operations_status_latest.json';
import processes from '../reports/nexus_process_inventory_latest.json';
import schedulers from '../reports/nexus_scheduler_inventory_latest.json';
import clis from '../reports/nexus_cli_inventory_latest.json';
import youtube from '../reports/nexus_youtube_research_status_latest.json';
import brain from '../reports/hermes_second_brain_index_latest.json';

const required=['name','category','status','source','checked_at','proof','limitations','hermes_readable_summary','safe_next_action','gated_actions'];
describe('operations collector reports',()=>{
  it('creates typed report items',()=>{for(const item of [...processes.items,...schedulers.items,...clis.items,...youtube.items])for(const key of required)expect(item).toHaveProperty(key)});
  it('never serializes env values',()=>{for(const entry of Object.values(operations.env_presence)){expect(entry).toHaveProperty('value_redacted',true);expect(entry).not.toHaveProperty('value')}});
  it('contains no recognizable secret values',()=>{const raw=[operations,processes,schedulers,clis,youtube].map(JSON.stringify).join('');expect(raw).not.toMatch(/eyJ[A-Za-z0-9_-]{20,}\./);expect(raw).not.toMatch(/(?:sk|sb)_live_[A-Za-z0-9_-]{12,}/i)});
  it('does not infer scheduler execution from loaded state',()=>{for(const item of schedulers.items)expect(item.hermes_readable_summary).not.toMatch(/is running/i)});
  it('marks YouTube unproven without combined proof',()=>{const item=youtube.items[0];if(!(item.running_now&&item.supabase_write_proof))expect(item.status).toBe('not_proven_live')});
  it('includes available CLI tools',()=>expect(clis.items.some(x=>x.available)).toBe(true));
  it('performs no Supabase summary write',()=>expect(operations.supabase_summary_write.performed).toBe(false));
});

describe('second brain index',()=>{
  it('is bounded and indexes operations/reports',()=>{expect(brain.item_count).toBeGreaterThan(0);expect(brain.item_count).toBeLessThanOrEqual(400);expect(brain.items.some(x=>x.source_type==='operations')).toBe(true)});
  it('skips secret sources and values',()=>{const raw=JSON.stringify(brain);expect(raw).not.toMatch(/\.env(?:\.|\")/);expect(raw).not.toMatch(/eyJ[A-Za-z0-9_-]{20,}\./)});
});

describe('frontend execution safety',()=>{
  it('does not add shell/process execution to frontend Hermes modules',()=>{const files=['src/lib/hermesBrain.ts','src/lib/hermesOrchestrator.ts','src/lib/hermesIntentRouter.ts','src/lib/hermesToolRouter.ts','src/lib/hermesOperationsContext.ts'];const raw=files.map(x=>readFileSync(x,'utf8')).join('\n');expect(raw).not.toMatch(/child_process|execSync|spawn\(|subprocess|shell:/)});
});
