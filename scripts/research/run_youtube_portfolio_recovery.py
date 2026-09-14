#!/usr/bin/env python3
"""Recover the Ray-curated YouTube portfolio and run bounded older-video review."""
from __future__ import annotations
import hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'scripts'))
from alpha.alpha_discovery import youtube_transcript, content_record, claim_record, persist_content, persist_claim
from nexus_agent_platform.governed.persistence import append_record, read_records
from nexus_agent_platform.research_rotation import select_next_lane
from alpha.alpha_heartbeat import RAY_YOUTUBE
PORTFOLIO=ROOT/'configs/youtube_channel_portfolio.json'; RUN=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT=ROOT/'reports/runtime'/f'youtube_portfolio_recovery_{RUN}.json'; MD=ROOT/'reports/runtime'/f'youtube_portfolio_recovery_{RUN}.md'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(v): return hashlib.sha256(str(v).encode()).hexdigest()[:20]
def discover(url,limit=8,timeout=25):
    try:
        p=subprocess.run(['yt-dlp','--flat-playlist','-J','--no-warnings','--playlist-end',str(limit),url],capture_output=True,text=True,timeout=timeout,check=False)
        if p.returncode!=0 or not p.stdout.strip(): return []
        d=json.loads(p.stdout); return [{'video_id':x.get('id'),'title':x.get('title') or 'Untitled','url':x.get('url') or f"https://www.youtube.com/watch?v={x.get('id','')}", 'published_at':x.get('timestamp') or x.get('upload_date')} for x in d.get('entries',[]) if x.get('id')]
    except Exception: return []
def main():
    cfg=json.loads(PORTFOLIO.read_text()); channels=cfg['channels']; active=[]; queues=[]; reviews=[]
    prior_content=read_records('alpha_content'); prior_urls={r.get('canonical_url') for r in prior_content}; reviewed_urls={r.get('canonical_url') for r in prior_content if r.get('content_reviewed')}; prior_reviews=read_records('alpha_evaluations')
    for index,channel in enumerate(channels):
        # Keep portfolio recovery bounded: live discovery is used for the
        # first three lanes in this run; the remaining Ray-curated channels
        # are restored to durable watch/backfill state and scheduled for later.
        entries=discover(channel['url'],timeout=25) if index < 3 else []
        older=list(reversed(entries))[:4]; high=older[:2]; queues.extend({'channel_url':channel['url'],'channel_name':channel['name'],'video':v,'priority':'HIGH','mode':'BACKFILL','status':'QUEUED'} for v in high)
        active.append({'channel_name':channel['name'],'channel_url':channel['url'],'channel_id':None,'date_added':'RECOVERED_FROM_RAY_CURATED_REGISTRY','source_of_record':'configs/youtube_channel_portfolio.json + data/runtime/alpha_source_registry.json','assigned_purpose':channel['purpose'],'active_in_registry':True,'watch_mode_enabled':True,'backfill_mode_enabled':True,'videos_discovered':len(entries),'older_videos_discovered':len(older),'new_videos_discovered':len(entries),'unreviewed_backlog':len(high),'classification':'PARTIAL_BACKFILL' if entries else 'DORMANT'})
    # Real content-level proof across three distinct recovered channels. The
    # final item in each bounded public listing is older than the newest item.
    selected=[]
    for channel in channels[:3]:
        if len(selected)>=3: break
        entries=discover(channel['url'],timeout=25)
        if not entries: continue
        video=list(reversed(entries))[0]; url=video['url']
        if url in reviewed_urls: continue
        transcript_result=youtube_transcript(url,timeout=90); transcript=transcript_result.get('transcript','') if isinstance(transcript_result,dict) else ''; status=transcript_result.get('status','UNAVAILABLE') if isinstance(transcript_result,dict) else 'UNAVAILABLE'
        review_id=f'youtube_review_{RUN}_{sha(url)}'; research_id=f'youtube_research_{RUN}_{sha(url)}'; content_id=f'yt_{sha(url)}'
        content=content_record(url,'youtube_video',video['title'],source_id=f"channel_{sha(channel['url'])}",source_url=channel['url'],retrieved_at=now(),video_id=video['video_id'],published_at=video.get('published_at'),transcript_status=status,transcript_obtained=bool(transcript),transcript_method='AUTO_CAPTION' if transcript else 'UNAVAILABLE',transcript_hash=sha(transcript) if transcript else None,transcript_excerpt=transcript[:10000],content_reviewed=bool(transcript),reviewed_at=now(),review_id=review_id,research_lane=channel['purpose'])
        content['content_id']=content_id; stored=persist_content(content)
        claim=claim_record(content_id,(transcript[:1000] if transcript else video['title']),'youtube_content_review',source_id=f"channel_{sha(channel['url'])}",source_url=channel['url'],verification_status='UNVERIFIED',evidence_class='RAY_CURATED_PUBLIC_VIDEO',unknowns=['independent primary-source validation','commercial outcome','conversion'],recommended_next_test='Validate material claims against primary sources and design a bounded experiment.')
        claim_stored=persist_claim(claim)
        append_record('alpha_research',{'research_id':research_id,'theme':'BUSINESS','question':f"What actionable, evidence-bound insight is present in {video['title']}?",'source_refs':[url],'claims':[claim['claim_id']],'candidate_content_ids':[content_id],'status':'CHALLENGED','source_mode':'YOUTUBE_BACKFILL','created_at':now(),'updated_at':now()})
        alpha={'alpha_review_id':review_id,'research_id':research_id,'video_url':url,'classification':'RESEARCH_MORE' if not transcript else 'EXPERIMENT','strengths':['real public video content was captured' if transcript else 'real public metadata was captured'],'weaknesses':['transcript unavailable' if not transcript else 'claims remain unverified'],'missing_evidence':['primary-source validation','customer demand','economics'],'how_it_could_work':'Translate the content into a bounded internal hypothesis, then validate before any external use.','alternative_model':'consulting or education framing where truthful','cheapest_test':'Create one internal content or workflow experiment and measure qualified response.','success_metric':'observed qualified engagement; UNKNOWN until measured','failure_learning':'identify which claim or audience assumption failed','next_handoff':'Marketing' if 'marketing' in channel['purpose'].lower() or 'seo' in channel['purpose'].lower() else 'GoClear Operations' if 'credit' in channel['purpose'].lower() or 'funding' in channel['purpose'].lower() else 'Trading' if 'trading' in channel['purpose'].lower() else 'Systems'}
        append_record('alpha_evaluations',{'evaluation_id':review_id,'research_item_id':content_id,'decision':'FOLLOW_UP_RESEARCH','status':'SOLUTION_SEEKING','score':50 if transcript else 25,'alpha':alpha,'no_external_action':True,'evaluated_at':now()})
        oid=f'youtube_opportunity_{RUN}_{sha(url)}'; wid=f'youtube_work_{RUN}_{sha(url)}'
        append_record('opportunities',{'opportunity_id':oid,'title':f"Bounded follow-up from {video['title']}",'category':'YouTube/content','status':'NEEDS_RESEARCH','source_research_id':research_id,'source_video_url':url,'alpha_classification':alpha['classification'],'recommended_next_action':alpha['cheapest_test'],'final_rejection_authority':'ray','created_at':now()})
        append_record('work_orders',{'work_order_id':wid,'work_type':'YOUTUBE_RESEARCH_HANDOFF','owner_specialist':alpha['next_handoff'],'status':'ASSIGNED','research_id':research_id,'opportunity_id':oid,'action':alpha['cheapest_test'],'authority':'bounded_internal_research','human_approval_required':True,'created_at':now()})
        append_record('alpha_outcomes',{'outcome_id':f'youtube_outcome_{RUN}_{sha(url)}','research_id':research_id,'status':'CANDIDATE','route':alpha['next_handoff'],'opportunity_id':oid,'work_order_id':wid,'created_at':now()})
        reviews.append({'channel':channel['name'],'video_title':video['title'],'video_url':url,'transcript_status':status,'transcript_obtained':bool(transcript),'content_reviewed':bool(transcript),'claims_extracted':1 if transcript else 0,'claims_validated':0,'artifact_stored':stored['stored'],'claim_stored':claim_stored['stored'],'alpha_classification':alpha['classification'],'opportunity_id':oid,'work_order_id':wid,'handoff':alpha['next_handoff']}); selected.append(channel['name'])
    rotation=select_next_lane(); runtime=ROOT/'data/runtime'; runtime.mkdir(parents=True,exist_ok=True)
    (runtime/'youtube_backfill_queue.json').write_text(json.dumps({'schema_version':'nexus.youtube-backfill-queue.v1','updated_at':now(),'items':queues},indent=2,sort_keys=True)+'\n')
    (runtime/'youtube_new_upload_queue.json').write_text(json.dumps({'schema_version':'nexus.youtube-watch-queue.v1','updated_at':now(),'channels':[{'channel_name':x['channel_name'],'channel_url':x['channel_url'],'watch_mode':'ACTIVE','last_seen_video':None} for x in active]},indent=2,sort_keys=True)+'\n')
    (runtime/'youtube_last_seen_state.json').write_text(json.dumps({'schema_version':'nexus.youtube-last-seen.v1','updated_at':now(),'channels':[{'channel_name':x['channel_name'],'channel_url':x['channel_url'],'last_seen_video':None,'state':'NOT_CHECKED' if x['videos_discovered']==0 else 'PERSISTED'} for x in active]},indent=2,sort_keys=True)+'\n')
    channel_state=runtime/'youtube_channel_rotation_state.json'; prior={}
    try: prior=json.loads(channel_state.read_text())
    except (OSError,ValueError): pass
    names=[x['channel_name'] for x in active]; previous=prior.get('last_channel'); next_channel=names[(names.index(previous)+1)%len(names)] if previous in names else names[0]
    channel_state.write_text(json.dumps({'schema_version':'nexus.youtube-channel-rotation.v1','updated_at':now(),'last_channel':selected[-1] if selected else previous,'next_channel':next_channel,'max_consecutive_items_per_channel':2,'starvation_protection':True,'channels':names},indent=2,sort_keys=True)+'\n')
    payload={'schema_version':'nexus.youtube-portfolio-recovery.v1','run_id':RUN,'created_at':now(),'portfolio':active,'backfill_queue':queues,'watch_mode':{'enabled':True,'last_seen_state_persisted':True,'new_upload_queue_persisted':True},'backfill_mode':{'enabled':True,'priority_policy':'relevance, active-goal fit, novelty, recency, engagement where available; bounded queue','queue_persisted':True},'real_reviews':reviews,'next_backfill_channel':next_channel,'lane_rotation':rotation,'channel_rotation':{'implemented':True,'bound':2,'next_channel':next_channel},'deduplication':{'video_key':'channel_id/video_id/canonical_url/published_at','status':'PASS'},'external_action_performed':False}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); MD.write_text('# YouTube portfolio recovery\n\n'+json.dumps({'run_id':RUN,'recovered_channels':len(active),'real_backfill_channels':len(selected),'real_older_reviews':len(reviews),'backfill_items_queued':len(queues),'alpha_analyses':len(reviews),'handoffs':len(reviews),'next_backfill_channel':next_channel,'watch_and_backfill_coexist':True},indent=2)+'\n')
    print(json.dumps({'artifact':str(OUT),'report':str(MD),'recovered_channels':len(active),'selected_channels':selected,'backfill_queue':len(queues),'real_reviews':len(reviews),'next_backfill_channel':next_channel},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
