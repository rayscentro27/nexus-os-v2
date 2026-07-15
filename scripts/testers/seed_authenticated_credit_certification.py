#!/usr/bin/env python3
"""Storage-backed synthetic credit-report seed; uses the real Documents Vault metadata contract."""
import argparse, json, os, ssl, sys, time, urllib.error, urllib.request, subprocess
from pathlib import Path
import certifi

ROOT=Path(__file__).resolve().parents[2]; SSL=ssl.create_default_context(cafile=certifi.where())
PERSONAS={'a':'nexus-persona-a-browser@goclear.test','b':'nexus-persona-b-browser@goclear.test','c':'nexus-persona-c-browser@goclear.test'}
FIXTURE_DIR=ROOT/'data/runtime/authenticated_credit_fixtures'
def envfile(path):
 d={}
 if path.exists():
  for line in path.read_text().splitlines():
   if '=' in line and not line.startswith('#'):
    k,v=line.split('=',1);d[k]=v.strip().strip('"').strip("'")
 return d
def req(url,key,path,method='GET',body=None,raw=None,headers=None):
 h={'apikey':key,'Authorization':f'Bearer {key}'};h.update(headers or {})
 data=raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
 r=urllib.request.Request(url.rstrip('/')+path,data=data,headers=h,method=method)
 return urllib.request.urlopen(r,context=SSL,timeout=45).read()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--persona',choices=PERSONAS,default='a');ap.add_argument('--follow-up',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
 e={**envfile(ROOT/'.env'),**os.environ};url=e.get('SUPABASE_URL') or e.get('VITE_SUPABASE_URL');key=e.get('SUPABASE_SERVICE_ROLE_KEY')
 if not url or not key: print('FAIL: required server environment unavailable');return 1
 fixture=FIXTURE_DIR/f'synthetic_persona_{a.persona}_{"followup" if a.follow_up else "initial"}.pdf'
 if not fixture.exists():
  command=[sys.executable,str(ROOT/'scripts/testers/generate_authenticated_credit_fixtures.py'),'--persona',a.persona,'--out',str(FIXTURE_DIR)]
  if a.follow_up: command.append('--follow-up')
  subprocess.run(command,check=True,capture_output=True)
 users=json.loads(req(url,key,'/auth/v1/admin/users?per_page=1000'))['users'];user=next((x for x in users if x.get('email','').lower()==PERSONAS[a.persona]),None)
 if not user: print('FAIL: synthetic Auth user is not provisioned');return 1
 membership=json.loads(req(url,key,f"/rest/v1/tenant_memberships?user_id=eq.{user['id']}&select=tenant_id,client_id&limit=1"))
 if not membership: print('FAIL: synthetic user has no tenant/client bootstrap membership');return 1
 tenant,client=membership[0]['tenant_id'],membership[0]['client_id'];title=f'synthetic_persona_{a.persona}_three_bureau_report_{"followup_v3" if a.follow_up else "v3"}.pdf'
 existing=json.loads(req(url,key,f'/rest/v1/client_documents?tenant_id=eq.{tenant}&client_id=eq.{client}&title=eq.{title}&select=id&limit=1'))
 if existing: print(json.dumps({'ok':True,'reused':True,'document_id':existing[0]['id'],'persona':a.persona}));return 0
 if a.dry_run: print(json.dumps({'ok':True,'dry_run':True,'persona':a.persona,'storage_bucket':'client-documents'}));return 0
 path=f"{user['id']}/{int(time.time()*1000)}_{title}";req(url,key,f'/storage/v1/object/client-documents/{path}','POST',raw=fixture.read_bytes(),headers={'Content-Type':'application/pdf','x-upsert':'false'})
 docid=f"{user['id']}_{int(time.time()*1000)}";row={'id':docid,'tenant_id':tenant,'client_id':client,'category':'credit_report','title':title,'summary':f'Client portal upload from synthetic certification — {title} (application/pdf) stored at {path}','status':'uploaded','priority':'normal','risk_level':'low','automation_level':'automatic_analysis_queue','client_visible':True,'approval_required':False,'goclear_review_status':'not_required','source':'client_portal_upload','source_concept':'authenticated_certification','recommended_next_action':'Analysis queues automatically after upload'}
 req(url,key,'/rest/v1/client_documents','POST',body=row,headers={'Content-Type':'application/json','Prefer':'return=representation'})
 print(json.dumps({'ok':True,'persona':a.persona,'document_id':docid,'storage_uploaded':True,'metadata_created':True}))
 return 0
if __name__=='__main__':sys.exit(main())
