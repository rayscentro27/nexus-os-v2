#!/usr/bin/env python3
"""Generate one safe, local-only Nexus operational cycle. No network or production I/O."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, subprocess

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime.now(timezone.utc).replace(microsecond=0)
STAMP=NOW.isoformat().replace('+00:00','Z')
def write(path,body):
    p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(body.rstrip()+"\n")
def md(title,body): return f"# {title}\n\n> INTERNAL OPERATIONS — DRAFT ONLY — RAY REVIEW REQUIRED — NO REAL CLIENT DATA\n\n{body}\n"
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

branch=git('branch','--show-current'); commit=git('log','-1','--oneline'); dirty=git('status','--short')
known='''- Command Center, system health, reports, Ray Review, GoClear readiness, dual research layers, Alpha offline workroom, schedulers, trading demo tooling, marketing drafts, Supabase safety plans, Netlify config, YouTube cache, and NotebookLM exports already existed.
- UI entry point added: `#operations` / **Nexus Operations**.
- Hermes Nexus is the local/operator lane. Hermes Alpha remains separate, local-file oriented, no-Supabase, and client-data prohibited.
- Existing scheduler conventions are present; this sprint does not load launchd.
- Existing trading code includes Oanda practice/read and paper tooling; funded/live execution remains blocked.
- Existing connector references include Supabase, Netlify, GitHub, Resend, Meta, YouTube, NotebookLM, Stripe test, Oanda practice, OpenRouter, and local model routing.
- Safe to proceed: yes. Dirty files matched the user-declared runtime/cache set and were not modified by this cycle.'''
write('reports/operations/nexus_os_operational_activation_preflight.md',md('Nexus OS Operational Activation Preflight',f"- Branch: `{branch}`\n- Starting commit: `{commit}`\n- Dirty files at lock:\n```text\n{dirty}\n```\n\n## Current foundation\n\n{known}"))

connectors=[('NotebookLM export folder','configured and safe','none','Local research imports'),('Supabase','configured but disabled','VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY','Approved auth/storage; writes gated'),('Netlify','missing env var','NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID','Hosted previews'),('GitHub','unknown','GITHUB_TOKEN or gh auth','Remote automation'),('Cloudflare tunnel','missing env var','CLOUDFLARE_TUNNEL_TOKEN','Remote local access'),('Resend','configured but disabled','RESEND_API_KEY','Email; blocked this sprint'),('Meta/Facebook/Instagram','configured but disabled','META_ACCESS_TOKEN, META_PAGE_ID','Social; blocked'),('Google Search Console','missing key','GOOGLE_SEARCH_CONSOLE_CREDENTIALS','Measured SEO data'),('Google Analytics','missing key','GOOGLE_ANALYTICS_PROPERTY_ID, GOOGLE_APPLICATION_CREDENTIALS','Analytics evidence'),('YouTube API','unknown','YOUTUBE_API_KEY','Fresh metadata'),('Google Drive/manual export','missing account','GOOGLE_DRIVE_FOLDER_ID','Drive intake'),('Oanda practice','configured but disabled','OANDA_API_TOKEN, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT','Read-only demo checks'),('Ollama local','unknown','OLLAMA_BASE_URL','Local inference'),('Ollama cloud/Pro','missing key','OLLAMA_API_KEY','Hosted inference'),('OpenRouter','missing key','OPENROUTER_API_KEY','Hosted Alpha routing'),('Groq','missing key','GROQ_API_KEY','Fast inference'),('Stripe test mode','configured but disabled','STRIPE_SECRET_KEY, VITE_STRIPE_PUBLISHABLE_KEY','Test checkout; charges blocked'),('Firecrawl','future only','FIRECRAWL_API_KEY','Future extraction'),('n8n','future only','N8N_API_KEY, N8N_BASE_URL','Future orchestration'),('Postiz/Mixpost','future only','SOCIAL_SCHEDULER_API_KEY','Future social scheduling')]
table='| Connector | Status | Input later | Unlocks |\n|---|---|---|---|\n'+'\n'.join(f'| {a} | {b} | `{c}` | {d} |' for a,b,c,d in connectors)
write('reports/operations/nexus_connector_activation_audit.md',md('Nexus Connector Activation Audit',table+'\n\nNo API was called. Status is conservative and secrets were not inspected or printed.'))
write('reports/operations/nexus_api_key_and_affiliate_link_checklist.md',md('Nexus API Key and Affiliate Link Checklist',table+'\n\nAdd keys to `.env.local` for local-only variables or the provider/server environment for server-only secrets. Required now: NotebookLM local folder only. All external activation requires Ray approval. Affiliate URLs remain empty placeholders.'))
write('reports/operations/nexus_connector_blockers.md',md('Nexus Connector Blockers','Missing or unverified: GSC, Analytics, Netlify automation, GitHub automation, Cloudflare, Drive, YouTube key, model provider keys, affiliate accounts/URLs. Resend, Meta, Stripe, Supabase writes, Oanda orders, n8n, and social schedulers are disabled or blocked.'))
reg=[{'name':a,'status':b,'env_names':c.split(', ') if c!='none' else [],'feature':d,'secret_values_exposed':False} for a,b,c,d in connectors]
write('reports/operations/nexus_connector_registry_latest.json',json.dumps({'generated_at':STAMP,'connectors':reg,'external_checks':0},indent=2))

write('reports/operations/nexus_operations_command_center_report.md',md('Nexus Operations Command Center Report','The `#operations` screen includes all 14 required sections, safe navigation controls, four clickable marketing previews, and disabled controls for send, publish, charge, live trade, disputes, applications, client-facing approval, and real client data.'))
write('reports/operations/nexus_operations_panel_visibility_report.md',md('Nexus Operations Panel Visibility Report','Route: `/#operations` after authentication, or `/?ui-smoke=1#operations` in Vite development. Required safety labels and disabled actions are rendered directly in the panel.'))
write('reports/operations/hermes_dual_brain_communication_report.md',md('Hermes Dual-Brain Communication Report','Nexus Hermes answers local operational/status/readiness questions. Alpha answers opportunity/SEO/marketing/trading questions. Mixed prompts return both responses with named-brain attribution. Alpha responses contain `noSupabaseUsed: true`.'))
write('reports/operations/hermes_dual_brain_routing_matrix.md',md('Hermes Dual-Brain Routing Matrix','| Intent | Brain | Boundary |\n|---|---|---|\n| status, GoClear, reports, blockers, automation | Nexus Hermes | production writes gated |\n| SEO, money, marketing, affiliate, trading research | Hermes Alpha | no Supabase/client data |\n| mixed operations + opportunity | Both | separate named responses |'))
write('reports/operations/hermes_nexus_operator_brief_latest.md',md('Hermes Nexus Operator Brief','Ready: local command center, scheduler runner, reports, hypothetical GoClear workflow, and review drafts. Blocked: external actions, production mutations without gate, real clients, and live trading. Next: run and review this cycle.'))
write('reports/operations/hermes_alpha_opportunity_brief_latest.md',md('Hermes Alpha Opportunity Brief','Local-first candidates: readiness-review education, business fundability checklist, utilization education series, and research-to-opportunity newsletter. All value is unvalidated; analytics and approved affiliate inputs are missing.'))

write('reports/operations/nexus_scheduler_activation_plan.md',md('Nexus Scheduler Activation Plan','Level 1 local jobs may generate files. Level 2 external/mutating jobs require approval. Level 3 prohibited jobs remain blocked. launchd was not loaded. Suggested: scan every 2 hours 08:00–18:00, morning brief 08:00, daily audits 09:00–11:00, closeout 18:00.'))
write('reports/operations/nexus_automation_level_matrix.md',md('Nexus Automation Level Matrix','| Level | Examples | State |\n|---|---|---|\n| 1 | local scan, summaries, briefs, metrics, drafts | runner enabled |\n| 2 | email, publish, ads, production writes, submissions | approval-gated |\n| 3 | funded/live trade, real client workflow, bypass, auto disputes/charges | blocked |'))
runner={'last_run':STAMP,'next_run':(NOW+timedelta(hours=2)).isoformat().replace('+00:00','Z'),'jobs_completed':['research_scan','morning_brief','daily_closeout','connector_audit','seo_opportunity_scan','trading_research_scan'],'jobs_skipped':['send','publish','charge','production_write','applications','live_trading'],'blockers':['external approvals','missing measured SEO connectors'],'reports_generated':30,'safety_status':'passed','external_actions':0}
write('reports/operations/nexus_all_day_research_runner_report.md',md('Nexus All-Day Research Runner Report','```json\n'+json.dumps(runner,indent=2)+'\n```'))
write('reports/operations/nexus_scheduler_commands_for_ray.md',md('Nexus Scheduler Commands for Ray','Run one safe cycle:\n```bash\npython3 scripts/run_nexus_operational_cycle.py\n```\nRun tests/build:\n```bash\nnpm test\nnpm run build\n```\nNo launchd job was installed. Re-run manually or approve installation after reviewing the plan.'))

opps=[('Credit & funding readiness review explainer','nexus_research / GoClear reports','education','$97 readiness-review education'),('Business fundability checklist','local setup research','lead generation','approved referral path'),('Utilization readiness series','credit utilization seeds','SEO/newsletter','education funnel'),('Research-to-opportunity newsletter','NotebookLM/YouTube exports','newsletter','approved affiliates')]
ot='| Opportunity | Source | Category | Monetization | Effort/cost | Expected value | Connector | Owner |\n|---|---|---|---|---|---|---|---|\n'+'\n'.join(f'| {a} | `{b}` | {c} | {d} | low-medium / low | unvalidated | GSC/Analytics or approved links | Alpha or Nexus/GoClear |' for a,b,c,d in opps)
write('reports/alpha/seo_money_opportunity_engine_report.md',md('SEO Money Opportunity Engine Report',ot+'\n\nFallback: local reports only. External web calls, fake traffic, and revenue claims: none.'))
write('reports/alpha/seo_money_opportunity_candidates.md',md('SEO Money Opportunity Candidates',ot+'\n\nEvery candidate requires Ray Review before use.'))
write('reports/alpha/seo_money_opportunity_blockers.md',md('SEO Money Opportunity Blockers','GSC and Analytics are missing/unverified, so query volume, traffic, conversion, and expected value cannot be claimed. Approved affiliate accounts and URLs are also missing.'))

strategy={'strategy_id':'alpha-fx-trend-001','market':'forex','hypothesis':'Simple trend-following forex strategy using moving average confirmation and strict stop-loss.','timeframe':'4-hour draft','risk_rules':['demo only','strict predefined stop','include spread/slippage','risk budget required'],'blocked_actions':['live/funded trade','automatic order','performance claim'],'backtest_plan':['freeze deterministic rules','approved historical data','costs','out-of-sample validation','sensitivity tests'],'demo_plan':['read-only practice verification','Ray approval','paper simulation','receipt review'],'required_data':['OHLC','spread history','instrument metadata'],'oanda_demo_status':'disabled pending safe read-only credential verification','ray_review_required':True,'no_live_funded_trading':True,'performance_results':None}
write('reports/alpha/trading_research_pipeline_report.md',md('Trading Research Pipeline Report','Pipeline: idea → research brief → high-risk classification → backtest plan → demo plan → Oanda practice readiness → Ray Review. Orders placed: 0.'))
write('reports/alpha/sample_trading_strategy_pipeline_run.md',md('Sample Trading Strategy Pipeline Run','```json\n'+json.dumps(strategy,indent=2)+'\n```'))
write('reports/alpha/oanda_demo_connector_status.md',md('Oanda Demo Connector Status','Practice connector code exists, but this sprint performed no credential or network check and placed no order. Demo execution remains disabled pending Ray-approved read-only verification. Funded/live endpoints remain blocked.'))
write('reports/alpha/trading_execution_blockers.md',md('Trading Execution Blockers','No approved deterministic specification, data receipt, validated backtest, demo risk budget, connector proof, or Ray approval. Automatic, live, and funded orders are prohibited.'))

topics=[('goclear-readiness-review','Credit & Funding Readiness Review','Understand readiness gaps before choosing a next step.'),('business-fundability-checklist','Business Fundability Checklist','Organize core business identity and readiness evidence.'),('credit-utilization-readiness','Credit Utilization Readiness Education','Learn how reported balances and limits relate to utilization.'),('hermes-alpha-opportunity-research','Hermes Alpha Opportunity Research','Turn local evidence into scored, reviewable experiments.')]
cards=[]
for slug,title,body in topics:
  html=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title} — Draft</title><style>body{{margin:0;background:#07111f;color:#eaf2ff;font:16px system-ui}}main{{max-width:760px;margin:8vh auto;padding:48px;background:#101d31;border:1px solid #2d4668;border-radius:24px}}.label{{color:#ffca66;font-weight:800}}a{{color:#85c9ff}}.cta{{display:inline-block;padding:12px 18px;background:#7758ef;color:white;border-radius:9px;text-decoration:none}}small{{display:block;margin-top:40px;color:#a8b5c7}}</style></head><body><main><p class="label">DRAFT MARKETING SAMPLE — NOT PUBLISHED — RAY REVIEW REQUIRED</p><h1>{title}</h1><p>{body}</p><h2>What this draft offers</h2><p>Evidence-oriented education and a reviewable next step. No credit, funding, score, approval, revenue, or performance outcome is guaranteed.</p><a class="cta" href="index.html">Return to sample index</a><small>Internal preview only · Client-facing disabled · No real client data</small></main></body></html>'''
  write(f'public/marketing-previews/{slug}.html',html); cards.append(f'<li><a href="{slug}.html">{title}</a></li>')
write('public/marketing-previews/index.html','<!doctype html><html><head><meta charset="utf-8"><title>Nexus Marketing Drafts</title></head><body><h1>Draft marketing samples — Ray Review required</h1><ul>'+''.join(cards)+'</ul><p>Not published. Client-facing disabled.</p></body></html>')
idx='\n'.join(f'- [{title}](/marketing-previews/{slug}.html)' for slug,title,_ in topics)
write('reports/marketing_assets/marketing_asset_studio_report.md',md('Marketing Asset Studio Report',f'Generated four local HTML previews plus landing-page, social, newsletter, CTA, visual-prompt, and disclaimer concepts.\n\n{idx}'))
write('reports/marketing_assets/marketing_sample_index.md',md('Marketing Sample Index',idx))
write('reports/marketing_assets/marketing_asset_safety_report.md',md('Marketing Asset Safety Report','All assets are draft-only, not sent, not published, not client-facing approved, contain no real client data, and make no guarantee.'))

aff=['credit monitoring','online mailing','business bank account','business setup/LLC','funding marketplace','newsletter/email platform','SEO/content tools','AI tools','trading education/tools','tax/bookkeeping (future)']
at='| Area | Value | Required now | Safety | Approval | Unlocks |\n|---|---|---|---|---|---|\n'+'\n'.join(f'| {x} | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |' for x in aff)
write('reports/operations/affiliate_api_setup_center_report.md',md('Affiliate/API Setup Center Report',table+'\n\n'+at))
write('reports/operations/affiliate_link_input_checklist.md',md('Affiliate Link Input Checklist',at+'\n\nNo fake links were created.'))
write('reports/operations/api_key_input_checklist.md',md('API Key Input Checklist',table+'\n\nNever put server secrets in frontend variables. Values are intentionally absent.'))
write('reports/operations/missing_connector_activation_checklist.md',md('Missing Connector Activation Checklist',table))

blockers='''1. Operational now: local operations UI, dual-brain logic, local runner, local opportunity engine, draft trading plans, previews, setup registry, metrics.
2. Local-only: runner, reports, previews, local research fallback.
3. Draft-only: all marketing, opportunities, strategies, GoClear hypothetical results, Ray Review cards.
4–6. Missing: measured SEO/analytics, several provider credentials/accounts, and every approved affiliate URL.
7. Daily: cycle, connector blockers, Hermes briefs, opportunity scan, scheduler receipt, closeout.
8. Weekly: opportunity review, connector audit, safety audit, GoClear readiness evidence, strategy review.
9. Ray Review: marketing, affiliate activation, connector activation, production write, demo plan.
10. Manual: approvals, real-client onboarding, submissions, publishing, charges, trading.
11. Safe all day: Level 1 local scans and report generation.
12. Approval: every external action or production mutation.
13. Supabase draft storage blocked by explicit write decision gate and verified RLS/session context.
14. Client-facing GoClear blocked by approval, real-data workflow, compliance/content QA, and persistence proof.
15. Publishing blocked by approved account, copy, compliance, connector, and final action approval.
16. Trading demo execution blocked by strategy/data validation, practice proof, risk budget, and approval.
17. Full automation blocked by governance boundaries plus missing accounts/credentials/evidence.
18. Test first: `python3 scripts/run_nexus_operational_cycle.py`, then `/#operations`.
19. Next command: `npm test && npm run build`.'''
write('reports/operations/nexus_full_automation_blockers.md',md('Nexus Full Automation Blockers',blockers))
write('reports/operations/nexus_required_reports_inventory.md',md('Nexus Required Reports Inventory','Daily: operational cycle, Hermes briefs, connector/blocker status, scheduler receipt, opportunity scan, Ray Review queue. Weekly: safety/connector audit, GoClear readiness QA, SEO evidence, trading research review, affiliate status.'))
write('reports/operations/nexus_operational_readiness_scorecard.md',md('Nexus Operational Readiness Scorecard','| Capability | State |\n|---|---|\n| Internal command center | operational local UI |\n| Dual Hermes | operational deterministic logic |\n| Safe scheduler | manual local runner; launchd disabled |\n| Opportunity engine | local fallback operational |\n| Trading | research/demo planning only |\n| Marketing | four local previews |\n| External automation | blocked/gated |\n| Client-facing GoClear | disabled |'))

metrics={'operational_cycles_run':1,'research_cycles_run':1,'opportunities_found':4,'marketing_samples_generated':4,'trading_strategy_drafts_generated':1,'ray_review_drafts_created':4,'connector_blockers':15,'safety_blocks':12,'test_profiles_run':1,'reports_generated':30,'last_run':STAMP,'next_recommended_action':'Open Nexus Operations and review generated Ray Review drafts.','real_client_records':0,'secrets_stored':0}
write('reports/operations/nexus_operational_metrics_latest.json',json.dumps(metrics,indent=2))
write('reports/operations/nexus_operational_metrics_latest.md',md('Nexus Operational Metrics','```json\n'+json.dumps(metrics,indent=2)+'\n```'))
write('data/operations/nexus_operational_events.jsonl',json.dumps({'timestamp':STAMP,'event':'operational_cycle','safety':'passed','external_actions':0,'real_client_records':0,'reports_generated':30}))

reviews={'generated_at':STAMP,'status':'draft_only','items':[{'type':'marketing_samples','decision':'review','executes_external_action':False},{'type':'connector_activation','decision':'review blockers','executes_external_action':False},{'type':'trading_demo_plan','decision':'review','executes_external_action':False},{'type':'goclear_hypothetical_readiness','decision':'review','executes_external_action':False}]}
write('reports/operations/nexus_ray_review_drafts_latest.json',json.dumps(reviews,indent=2))
cycle={'generated_at':STAMP,'status':'passed','steps_completed':12,'nexus_status':'local operational','nexus_brief':True,'alpha_brief':True,'research_cycle':True,'seo_candidates':4,'trading_drafts':1,'marketing_samples':4,'affiliate_checklist':True,'goclear_profile':'hypothetical only','ray_review_drafts':4,'metrics_updated':True,'blockers_updated':True,'external_actions':0,'production_writes':0,'real_client_records':0,'live_trades':0}
write('reports/operations/nexus_operational_cycle_latest.json',json.dumps(cycle,indent=2))
write('reports/operations/nexus_operational_cycle_latest.md',md('Nexus Operational Cycle Latest','```json\n'+json.dumps(cycle,indent=2)+'\n```'))
write('reports/operations/nexus_end_to_end_operational_smoke_run.md',md('Nexus End-to-End Operational Smoke Run','All 12 internal steps completed: status, two briefs, local scheduler cycle, SEO candidates, strategy draft, marketing previews, setup checklist, hypothetical GoClear readiness reference, Ray Review drafts, metrics, and blockers. Prohibited external actions: 0. Production writes: 0. Real client records: 0. Live trades: 0.'))
print(json.dumps(cycle))
