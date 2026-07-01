import { describe,expect,it } from 'vitest';
import { routeHermesIntent } from '../src/lib/hermesIntentRouter';
import { orchestrateHermes } from '../src/lib/hermesOrchestrator';
import { thinkWithHermes } from '../src/lib/hermesBrain';
import { nexusCliCommandRegistry } from '../src/data/nexusCliCommandRegistry';

describe('Hermes conversation brain and orchestrator',()=>{
  it.each(['What’s your favorite food?','what is your favorite sport','tell me a joke','how are you','are you real'])('%s stays conversational without Supabase',message=>{
    const plan=orchestrateHermes(message,true); expect(plan.routing.route).toBe('casual'); expect(plan.shouldQuerySupabase).toBe(false); expect(plan.tool.tool).toBe('none');
    expect(thinkWithHermes(message,true).handled).toBe(true);
  });
  it('routes pending approvals to Supabase',()=>{const plan=orchestrateHermes('What approvals are pending?',true);expect(plan.routing.route).toBe('nexus_supabase');expect(plan.shouldQuerySupabase).toBe(true)});
  it.each(['Run a full Nexus audit','what is real and what is fake','what processes are running','is YouTube research running','what CLI tools do I have?'])('%s routes to operations evidence',message=>expect(routeHermesIntent(message,true).route).toBe('operations'));
  it('creates the first-class audit intent',()=>expect(routeHermesIntent('audit Nexus').intent).toBe('run_nexus_audit'));
  it('gates execution',()=>{const plan=orchestrateHermes('publish this externally');expect(plan.routing.route).toBe('execution');expect(plan.tool.requiresApproval).toBe(true);expect(plan.tool.allowed).toBe(false)});
  it('leaves ambiguity for one focused clarification',()=>expect(routeHermesIntent('can you handle that').route).toBe('ambiguous'));
  it('audit answer distinguishes proof and unproven state',()=>{const answer=thinkWithHermes('Run a full Nexus audit').text;expect(answer).toMatch(/processes have direct running proof/i);expect(answer).toMatch(/unproven/i);expect(answer).toMatch(/No process was started/i)});
  it('YouTube answer never claims running without proof',()=>expect(thinkWithHermes('Is YouTube research running?').text).toMatch(/not_proven_live/));
  it('CLI answer uses operations inventory',()=>expect(thinkWithHermes('What CLI tools do I have?').text).toMatch(/Available CLI tools:/));
  it('overnight failure answer does not infer from scheduler load state',()=>expect(thinkWithHermes('What failed overnight?').text).toMatch(/does not contain a verified consolidated overnight failure record/i));
});

describe('safe command registry',()=>{
  it('labels safe, approval, and blocked commands coherently',()=>{
    for(const command of nexusCliCommandRegistry){
      if(command.category==='SAFE_READ_ONLY') expect(command.approval_required).toBe(false);
      if(command.category==='APPROVAL_REQUIRED') expect(command.approval_required).toBe(true);
      if(command.category==='BLOCKED'){expect(command.approval_required).toBe(true);expect(command.blocked_reason).toBeTruthy()}
    }
  });
  it('blocks secret printing and destructive actions',()=>expect(nexusCliCommandRegistry.filter(x=>['print_env','delete_database','weaken_rls','external_actions'].includes(x.command_id)).every(x=>x.category==='BLOCKED')).toBe(true));
});
