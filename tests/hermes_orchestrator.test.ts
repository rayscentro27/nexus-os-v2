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
  it('approval fallback uses Ray Review snapshot, not stale zero-card bundled context',()=>{
    const answer=thinkWithHermes('What needs my approval next?',true).text;
    expect(answer).toMatch(/Ray Review needs attention/i);
    expect(answer).toMatch(/pending approval card/i);
    expect(answer).toMatch(/not using the old local zero-card fallback/i);
    expect(answer).not.toMatch(/0 cards waiting|zero cards waiting/i);
  });
  it.each(['Run a full Nexus audit','what is real and what is fake','What is live, what is static, and what is unproven?','what processes are running','Is YouTube research running and writing to Supabase?','what CLI tools do I have?'])('%s routes to operations evidence',message=>expect(routeHermesIntent(message,true).route).toBe('operations'));
  it('creates the first-class audit intent',()=>expect(routeHermesIntent('audit Nexus').intent).toBe('run_nexus_audit'));
  it('gates execution',()=>{const plan=orchestrateHermes('publish this externally');expect(plan.routing.route).toBe('execution');expect(plan.tool.requiresApproval).toBe(true);expect(plan.tool.allowed).toBe(false)});
  it('leaves ambiguity for one focused clarification',()=>expect(routeHermesIntent('can you handle that').route).toBe('ambiguous'));
  it('audit answer distinguishes proof and unproven state',()=>{const answer=thinkWithHermes('Run a full Nexus audit').text;expect(answer).toMatch(/processes have direct running proof/i);expect(answer).toMatch(/unproven/i);expect(answer).toMatch(/No process was started/i)});
  it('YouTube answer never claims running without proof',()=>expect(thinkWithHermes('Is YouTube research running?').text).toMatch(/not_proven_live/));
  it('YouTube running plus Supabase question is not answered as generic research rows',()=>{
    const plan=orchestrateHermes('Is YouTube research running and writing to Supabase?',true);
    expect(plan.routing.route).toBe('operations');
    expect(plan.shouldQuerySupabase).toBe(false);
    const answer=thinkWithHermes('Is YouTube research running and writing to Supabase?').text;
    expect(answer).toMatch(/not proven live/i);
    expect(answer).toMatch(/Supabase can have research rows/i);
    expect(answer).toMatch(/process proof/i);
  });
  it('CLI answer uses plain language inventory with auth and rate-limit caveat',()=>{const answer=thinkWithHermes('What CLI tools do I have available?').text;expect(answer).toMatch(/CLI tools available/i);expect(answer).toMatch(/does not prove authentication/i);expect(answer).toMatch(/rate-limit/i)});
  it('overnight failure answer does not infer from scheduler load state',()=>expect(thinkWithHermes('What failed overnight?').text).toMatch(/does not contain a verified consolidated overnight failure record/i));
  it('live/static/unproven audit question does not clarify',()=>{
    const answer=thinkWithHermes('What is live, what is static, and what is unproven?').text;
    expect(answer).toMatch(/Live/i);
    expect(answer).toMatch(/Static|static/i);
    expect(answer).toMatch(/Unproven|unproven/i);
    expect(answer).not.toMatch(/clarify|Which source/i);
  });
  it('process answer groups services instead of dumping raw paths',()=>{
    const answer=thinkWithHermes('What processes are running right now?').text;
    expect(answer).toMatch(/main groups/i);
    expect(answer).toMatch(/raw paths/i);
    expect(answer).not.toMatch(/\/usr\/local\/Cellar\/python/);
  });
  it('plain-language blocker explanations are used',()=>{
    expect(thinkWithHermes('What is installed but not proven?').text).toMatch(/does not prove the job ran successfully/i);
    expect(thinkWithHermes('Why are you holding back?').text).toMatch(/separating proven access from unproven access/i);
    expect(thinkWithHermes('Can you explain this report in plain language?').text).toMatch(/In plain language/i);
  });
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
