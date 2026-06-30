#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; RUNTIME=ROOT/'reports/runtime'; MANUAL=ROOT/'reports/manual_publish'
REPORTS=['operating_activation_master_latest.md','ui_hermes_repair_master_latest.md','oanda_vibe_notebooklm_master_latest.md','revenue_dashboard_latest.md','ray_review_queue_latest.md','hermes_advisor_inbox_latest.md','research_to_money_pipeline_latest.md','safe_internal_scheduler_verification_latest.md','cli_capability_registry_latest.md','nexus_100_step_activation_status_latest.md','global_blocker_resolution_matrix_latest.md','operating_frontend_status_latest.md']
CONTEXT={'scheduler':'two launchd cycles installed','ray_review_cards':64,'offers':9,'research_candidates':50,'actionable_candidates':26,'confirmed_revenue':0,'oanda':'practice verified; no open positions','vibe':'paper bridge proven','notebooklm':'watched-folder fallback; approved export missing','resend':'blocked by domain/key mismatch','fake_customer':'approval-gated; live flag off','goal':'automation, communication, and monetization'}
def load_context():
 sources=[]
 for name in REPORTS:
  p=MANUAL/name
  if p.exists(): sources.append({'report':name,'available':True,'excerpt':p.read_text(errors='ignore')[:1200]})
  else: sources.append({'report':name,'available':False,'excerpt':''})
 return {**CONTEXT,'sources':sources,'sources_available':sum(x['available'] for x in sources)}
def classify(message):
 m=message.lower()
 for intent,pattern in [('greeting',r'good morning|hello|^hi\b|^hey\b'),('casual',r'did you sleep|how are you|sleep well'),('next_steps',r'what should i do next|next move|priority'),('delegation',r'100 steps|delegate|turn this into'),('money',r'money|revenue|offer'),('credit',r'credit|funding|client readiness'),('trading',r'trad|oanda|vibe'),('blockers',r'block'),('status',r'status|summary|system|report')]:
  if re.search(pattern,m): return intent
 return 'strategic_conversation'
def advisor_response(message,ctx=None):
 ctx=ctx or load_context(); intent=classify(message)
 responses={
 'greeting':"Good morning, Ray. Nexus is awake and the operating cycle is in place. The big thing today is not more setup—it is getting the approval path and money path moving. I’d start with the fake customer/payment journey, then Resend, then the top research-to-money candidates. I can turn that into a work plan or delegate it to the specialists.",
 'casual':"I don’t sleep, but I did keep the operating picture ready. Right now I’m watching the scheduler, Ray Review, money actions, and the remaining blockers. The system is close—now we need to move from reports to execution.",
 'next_steps':f"The next move is execution discipline, Ray. My top three priorities are: prove the fake-customer and Stripe test journey; fix Resend; then choose the first few of the {ctx['actionable_candidates']} immediately actionable research-to-money candidates. I can delegate preparation to Client Success, Automation, and Monetization. You still need to approve the persistent insert, payment completion, and every external send.",
 'delegation':"I’ll treat this as an operating program, not one giant task. I’ll summarize the outcome, group it into phases, separate safe work from approvals and blockers, route it to the right specialists, and create the task requests and Ray Review decisions. Nothing risky executes from the plan itself.",
 'money':"The closest money path is the $97 readiness review. The work now is proving the journey: synthetic customer, live dashboard read, and Stripe test completion. After that, connect the strongest research candidates to the $97, $297, and $497 offer ladder.",
 'credit':"I’m routing this to Credit and Funding. They’ll identify readiness gaps, documents, bankability issues, and a client-safe answer. They will not send a dispute, contact a bureau, or submit an application.",
 'trading':"Oanda practice access and the Vibe paper bridge are proven, with zero open positions. Keep reads and paper analysis running; keep recurring execution behind Ray Review. Live trading remains blocked.",
 'blockers':"The blockers that matter are Resend’s domain/key mismatch, the unapproved fake-customer insert, the live-data flag, and missing YouTube/NotebookLM source files. Resend and the customer journey come first because they block communication and revenue proof.",
 'status':f"Nexus has two operating cycles, {ctx['ray_review_cards']} review cards, {ctx['offers']} offers, and {ctx['research_candidates']} research-to-money candidates. Confirmed revenue is $0. The system is operational; the next value comes from clearing approvals, not producing more status files.",
 'strategic_conversation':"I hear the strategic intent, Ray. I would judge this by three questions: does it move revenue, remove an operating blocker, or create safe leverage? Give me the outcome you want and I’ll shape the work, route it, and isolate the decisions only you should make."
 }
 return {'intent':intent,'response':responses[intent],'mode':'local_contextual_advisor','delegation_required':intent=='delegation','external_action_performed':False}
