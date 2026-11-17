#!/usr/bin/env python3
"""Resolve Oracle access from the single durable CURRENT authority record.

No aliases, HISTORY entries, agent keys, or alternate hosts are attempted
unless an operator explicitly invokes --recovery with a candidate tuple.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Callable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = REPOSITORY_ROOT / "docs/architecture/NEXUS_ORACLE_CONNECTION_AUTHORITY.json"
NOVA_SERVICE = "nova-telegram-oracle.service"
HERMES_CONTAINER = "nexus-hermes-0225"
R50_RELEASE = "/home/opc/.nexus/releases/nova-operator-v1-20261025-r50-routing-precedence"
EXPECTED_REMOTE_CHECK = r'''import json,socket,subprocess
def out(args):
 r=subprocess.run(args,capture_output=True,text=True,timeout=8)
 return r.stdout.strip() if r.returncode==0 else ""
print(json.dumps({"hostname":socket.gethostname(),"user":out(["whoami"]),
 "nova_service":out(["systemctl","--user","is-active","nova-telegram-oracle.service"]),
 "hermes_container":out(["podman","inspect","--format","{{.State.Status}}","nexus-hermes-0225"])}))'''
NOVA_UNIT_METADATA_SCRIPT = r'''import re,subprocess
r=subprocess.run(["systemctl","--user","cat","nova-telegram-oracle.service"],capture_output=True,text=True,timeout=8)
if r.returncode: raise SystemExit(r.returncode)
safe_env={"NOVA_CODE_ROOT","NOVA_REPO_ROOT","NOVA_RUNTIME_ENV","PYTHONPATH","NOVA_PRIMARY_RUNTIME","NEXUS_HERMES_MCP_CONTAINER"}
for line in r.stdout.splitlines():
 if line.startswith("# /") or line in {"[Unit]","[Service]"} or re.match(r"^(Requires|Wants|After|Before|ExecStart|WorkingDirectory|User|Restart|EnvironmentFile)=",line):
  print(line)
 elif line.startswith("Environment="):
  body=line.split("=",1)[1]; key=body.split("=",1)[0]
  print(line if key in safe_env else "Environment=[REDACTED]")'''
SAFE_COMMANDS = {
    ("hostname",),
    ("whoami",),
    ("uptime",),
    ("df", "-h", "/"),
    ("systemctl", "--user", "is-active", NOVA_SERVICE),
    ("systemctl", "--user", "is-active", "nexus-hermes-0225.service"),
    ("podman", "inspect", "--format", "{{.State.Status}}", HERMES_CONTAINER),
    ("ls", "-la", R50_RELEASE),
    ("find", "/home/opc/.nexus", "-maxdepth", "4", "-type", "f", "-name",
     "nova-operator-v1-20261025-r50-routing-precedence.tar.gz", "-print"),
    ("systemctl", "--user", "show", NOVA_SERVICE,
     "--property=MainPID,FragmentPath,DropInPaths,ExecStart"),
    ("python3", "-c", NOVA_UNIT_METADATA_SCRIPT),
    ("systemctl", "--user", "show", "nexus-hermes-0206.service",
     "--property=FragmentPath,MainPID"),
    ("systemctl", "--user", "cat", "nexus-hermes-0206.service"),
    ("systemctl", "--user", "cat", NOVA_SERVICE),
    ("systemctl", "--user", "cat", "nexus-hermes-0225.service"),
    ("systemctl", "--user", "status", "nexus-hermes-0225.service", "--no-pager", "-n", "20"),
    ("systemctl", "--user", "status", "nexus-hermes-0206.service", "--no-pager", "-n", "12"),
    ("ss", "-ltnp"),
    ("sh", "-lc", "podman logs --tail 120 nexus-hermes-0225 2>&1 | grep -Eio 'address already in use|permission denied|profile_mismatch|ModuleNotFoundError|ImportError|Traceback|bind.*failed|database is locked|failed to start|unsupported.*option|no such option|connection refused|api_server.*failed|provider.*error|request.*failed|signal [0-9]+' | sort | uniq -c"),
    ("podman", "top", "nexus-hermes-0225", "hpid", "pid", "user", "args"),
    ("podman", "inspect", "--format", "{{.ImageName}} {{.State.Status}}", HERMES_CONTAINER),
    ("podman", "inspect", "--format",
     "{{.ImageName}} {{.Config.User}} {{.HostConfig.NetworkMode}} {{json .Config.Entrypoint}} {{json .Config.Cmd}} {{json .Mounts}}",
     "nexus-hermes-0225"),
    ("podman", "inspect", "--format", "{{.ImageName}} {{.State.Status}}", "nexus-hermes-0225"),
    ("podman", "inspect", "--format", "{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.Error}}", "nexus-hermes-0225"),
    ("podman", "inspect", "--format", "{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.Error}}", "nexus-hermes-0225-debug"),
    ("sh", "-lc", "podman logs --tail 100 nexus-hermes-0225-debug 2>&1 | grep -Eio 'address already in use|permission denied|profile_mismatch|ModuleNotFoundError|ImportError|Traceback|bind.*failed|database is locked|failed to start' | sort | uniq -c"),
    ("podman", "inspect", "--format", "{{.HostConfig.Memory}} {{.HostConfig.MemorySwap}} {{.State.OOMKilled}} {{.State.ExitCode}}", "nexus-hermes-0225"),
    ("podman", "stats", "--no-stream", "--format", "{{.Name}} {{.MemUsage}} {{.CPUPerc}}", "nexus-hermes-0225"),
    ("podman", "exec", "nexus-hermes-0225", "sh", "-lc", "cat /sys/fs/cgroup/memory.events"),
    ("podman", "exec", "nexus-hermes-0225", "/opt/hermes/.venv/bin/hermes",
     "-p", "nova_nexus", "mcp", "test", "nexus_mcp_remote"),
    ("podman", "exec", "nexus-hermes-0225", "/opt/hermes/.venv/bin/hermes",
     "-p", "nova_nexus", "auth", "status", "openai-codex"),
    ("podman", "exec", "nexus-hermes-0225", "/opt/hermes/.venv/bin/hermes",
     "chat", "--help"),
    ("podman", "exec", "nexus-hermes-0225", "/opt/hermes/.venv/bin/hermes",
     "-p", "nova_nexus", "chat", "--help"),
    ("podman", "exec", "nexus-hermes-0206", "/opt/hermes/.venv/bin/hermes",
     "-p", "nova_nexus", "mcp", "test", "nexus_mcp_remote"),
    ("find", "/home/opc/.local/share/nexus-hermes-0225-candidate", "-maxdepth", "3", "-type", "f", "-printf", "%P\\n"),
    ("du", "-sh", "/home/opc/.local/share/nexus-hermes-0225-candidate"),
    ("ls", "-ld", "/home/opc/.local/share/nexus-hermes-0225-candidate", "/home/opc/.local/share/nexus-hermes-0225"),
    ("podman", "exec", "nexus-hermes-0225", "sh", "-lc",
     "find /opt/shared /opt/data -type f \\( -name auth.json -o -name auth.yaml -o -name codex.json \\) -print"),
    ("podman", "exec", "nexus-hermes-0225", "sh", "-lc",
     "printf '%s\\n' \"$HOME\" \"$HERMES_HOME\" \"$HERMES_PROFILE\" \"$CODEX_HOME\""),
    ("podman", "exec", "nexus-hermes-0225", "sh", "-lc", "env | cut -d= -f1 | sort"),
    ("podman", "exec", "nexus-hermes-0206", "sh", "-lc",
     "grep -c 'Authorization: Bearer' /opt/data/profiles/nova_nexus/config.yaml"),
    ("podman", "exec", "nexus-hermes-0225", "sh", "-lc",
     "grep -c 'Authorization: Bearer' /opt/data/profiles/nova_nexus/config.yaml"),
    ("awk", "-F=", "/^[A-Za-z_][A-Za-z0-9_]*(TOKEN|MCP)[A-Za-z0-9_]*=/ {print $1}",
     "/home/opc/.config/nexus-hermes-0206-cert/api.env"),
    ("podman", "exec", "nexus-hermes-0206", "sh", "-lc",
     "grep -Rli bearer /opt/data/profiles/nova_nexus --include=*.yaml --include=*.json --include=*.toml"),
    ("podman", "exec", "nexus-hermes-0206", "sh", "-lc",
     "awk 'tolower($0) ~ /authoriz/ {sub(/:.*/, \": [REDACTED]\"); print}' /opt/data/profiles/nova_nexus/config.yaml"),
    ("podman", "exec", HERMES_CONTAINER, "sh", "-lc",
     "ls -la /opt/data/profiles/nova_nexus"),
    ("podman", "exec", HERMES_CONTAINER, "/opt/hermes/.venv/bin/hermes", "auth", "--help"),
    ("podman", "exec", HERMES_CONTAINER, "/opt/hermes/.venv/bin/hermes", "auth", "status", "--help"),
    ("podman", "exec", HERMES_CONTAINER, "/opt/hermes/.venv/bin/hermes", "auth", "status", "openai-codex"),
    ("podman", "exec", HERMES_CONTAINER, "/opt/hermes/.venv/bin/hermes", "auth", "list"),
    # Read-only native-provider discovery; this confirms whether the dedicated
    # Research MCP is actually registered in the active Hermes profile.
    ("podman", "exec", HERMES_CONTAINER, "/opt/hermes/.venv/bin/hermes",
     "-p", "nova_nexus", "mcp", "test", "research"),
    # Native Hermes CLI help is read-only and establishes whether the active
    # profile has a supported configuration update command.
    ("podman", "exec", HERMES_CONTAINER, "/opt/hermes/.venv/bin/hermes", "--help"),
    ("podman", "exec", HERMES_CONTAINER, "/opt/hermes/.venv/bin/hermes", "config", "--help"),
    ("podman", "exec", HERMES_CONTAINER, "/opt/hermes/.venv/bin/hermes", "-p", "nova_nexus",
     "config", "get", "agent.max_turns"),
}
R50_VERIFY_SCRIPT = f'''import hashlib,json
from pathlib import Path
root=Path({R50_RELEASE!r})
manifest=root/"RELEASE_MANIFEST.sha256"
metadata=json.loads((root/"NOVA_RELEASE_METADATA.json").read_text())
entries=[]; mismatches=[]
for line in manifest.read_text().splitlines():
 if not line.strip(): continue
 digest,rel=line.split("  ",1); rel=Path(rel)
 if rel.is_absolute() or ".." in rel.parts: mismatches.append(str(rel)); continue
 path=root/rel
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest: mismatches.append(str(rel))
 entries.append(str(rel))
print(json.dumps({{"release_id":metadata.get("release_id"),"source_commit":metadata.get("source_commit"),
 "manifest_entries":len(entries),"manifest_mismatches":mismatches,
 "manifest_sha256":hashlib.sha256(manifest.read_bytes()).hexdigest(),
 "artifact_sha256":metadata.get("artifact_sha256") or metadata.get("release_sha256"),
 "release_source_hash":(root/"RELEASE_SOURCE_HASH").read_text().strip()}}))'''
HERMES_INVENTORY_SCRIPT = r'''import json,subprocess
container="nexus-hermes-0225"
script=r"""import json,re
from pathlib import Path
path=Path('/opt/data/profiles/nova_nexus/config.yaml')
out={'config_source':str(path),'config_present':path.is_file(),'provider_fields':[],'model_fields':[],'fallback_fields':[],'auth_method':'UNKNOWN','oauth_credential_present':False}
data={}
if path.is_file():
 try:
  import yaml
  data=yaml.safe_load(path.read_text()) or {}
 except Exception:
  data={}
 def walk(value,where=''):
  if isinstance(value,dict):
   for k,v in value.items():
    key=str(k).lower(); loc=(where+'.'+str(k)).strip('.')
    if isinstance(v,str) and key in {'provider','model','model_name','model_id','default_model'}:
     target='provider_fields' if key=='provider' else 'model_fields'
     out[target].append({'path':loc,'value':v[:120]})
    if isinstance(v,str) and key in {'fallback','fallback_model','fallback_provider'}:
     out['fallback_fields'].append({'path':loc,'value':v[:120]})
    if key in {'auth','auth_method','auth_type','authentication'} and isinstance(v,str):
     value=v.lower()
     if 'oauth' in value or 'codex' in value: out['auth_method']='CODEX_OAUTH'
     elif 'api' in value or 'key' in value: out['auth_method']='API_KEY'
    walk(v,loc)
  elif isinstance(value,list):
   for i,item in enumerate(value): walk(item,f'{where}[{i}]')
 walk(data)
auth=Path('/opt/data/profiles/nova_nexus/auth.json')
if auth.is_file():
 try:
  auth_data=json.loads(auth.read_text()); auth_keys=[]; token_paths=[]; modes=[]
  def scan(value,where=''):
   if isinstance(value,dict):
    for k,v in value.items():
     key=str(k); loc=(where+'.'+key).strip('.'); low=key.lower()
     auth_keys.append(loc)
     if any(part in low for part in ('token','api_key','secret','password')) and v:
      token_paths.append(loc)
     if low in {'auth_method','auth_type','auth_mode','provider','type'} and isinstance(v,str):
      val=v.lower()
      if any(x in val for x in ('oauth','codex','api_key','apikey')): modes.append(val)
     scan(v,loc)
   elif isinstance(value,list):
    for i,item in enumerate(value): scan(item,f'{where}[{i}]')
  scan(auth_data)
  out['auth_key_paths']=auth_keys[:50]
  out['credential_field_paths']=token_paths[:30]
  out['oauth_credential_present']=any(any(x in key.lower() for x in ('oauth','access_token','refresh_token','id_token')) for key in token_paths)
  if modes: out['auth_mode_hint']=sorted(set(modes))
 except Exception: pass
if out['oauth_credential_present'] and out['auth_method']=='UNKNOWN': out['auth_method']='OAUTH_CREDENTIAL_FILE'
envfile=Path('/opt/data/profiles/nova_nexus/.env')
safe_env={}; credential_keys=[]
if envfile.is_file():
 for line in envfile.read_text(errors='ignore').splitlines():
  match=re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)',line)
  if not match: continue
  key,value=match.group(1),match.group(2).strip().strip('"\'')
  if key in {'HERMES_NOVA_MODEL','OPENAI_MODEL','OPENROUTER_MODEL','MODEL','MODEL_NAME'} and value:
   safe_env[key]=value[:120]
  if any(part in key.lower() for part in ('token','api_key','secret','password')) and value:
   credential_keys.append(key)
out['profile_env_model_fields']=safe_env
out['credential_variable_names']=credential_keys[:30]
if credential_keys and out['auth_method']=='UNKNOWN': out['auth_method']='API_CREDENTIAL_IN_PROFILE_ENV'
codex_home=Path(__import__('os').environ.get('CODEX_HOME','/home/opc/.codex'))
codex_auth=codex_home/'auth.json'
out['codex_auth_source']=str(codex_auth)
out['codex_auth_present']=codex_auth.is_file()
if codex_auth.is_file():
 try:
  codex_data=json.loads(codex_auth.read_text()); paths=[]; modes=[]
  def scan_codex(value,where=''):
   if isinstance(value,dict):
    for k,v in value.items():
     key=str(k);loc=(where+'.'+key).strip('.');paths.append(loc)
     if key.lower() in {'auth_mode','auth_type','login_type','provider'} and isinstance(v,str):
      val=v.lower()
      if any(x in val for x in ('oauth','chatgpt','codex','api_key','apikey')): modes.append(val)
     scan_codex(v,loc)
   elif isinstance(value,list):
    for i,item in enumerate(value):scan_codex(item,f'{where}[{i}]')
  scan_codex(codex_data);out['codex_auth_key_paths']=paths[:50]
  out['codex_auth_mode_hints']=sorted(set(modes))
 except Exception: pass
print(json.dumps(out))"""
result=subprocess.run(['podman','exec',container,'python3','-c',script],capture_output=True,text=True,timeout=15)
if result.returncode: raise SystemExit(3)
print(result.stdout.strip())'''
NOVA_INVENTORY_SCRIPT = r'''import json,subprocess
pid_result=subprocess.run(['systemctl','--user','show','nova-telegram-oracle.service','--property=MainPID','--value'],capture_output=True,text=True,timeout=8)
pid=(pid_result.stdout or '').strip()
if not pid.isdigit() or pid=='0': raise SystemExit(3)
allowed={'NOVA_CODE_ROOT','NOVA_REPO_ROOT','HERMES_NOVA_MODEL','HERMES_PROFILE','NOVA_MODEL_PROVIDER','NOVA_MODEL_ROUTE'}
values={}
for item in open('/proc/'+pid+'/environ','rb').read().split(b'\0'):
 if b'=' not in item: continue
 key,value=item.split(b'=',1); name=key.decode(errors='ignore')
 if name in allowed: values[name]=value.decode(errors='replace')[:240]
cmd=open('/proc/'+pid+'/cmdline','rb').read().split(b'\0')
argv=[part.decode(errors='replace') for part in cmd if part]
print(json.dumps({'pid':pid,'argv0':argv[0] if argv else '',
 'entrypoint':argv[1] if len(argv)>1 else '',
 'release_root':next((v for k,v in values.items() if k=='NOVA_CODE_ROOT'),''),
 'repo_root':next((v for k,v in values.items() if k=='NOVA_REPO_ROOT'),''),
 'model':values.get('HERMES_NOVA_MODEL',''),'profile':values.get('HERMES_PROFILE',''),
 'provider':values.get('NOVA_MODEL_PROVIDER',''),'route':values.get('NOVA_MODEL_ROUTE','')}))'''

NOVA_DENIAL_INVENTORY_SCRIPT = r'''import json
from pathlib import Path
from datetime import datetime,timezone,timedelta
repo=Path('/home/opc/nexus-os-v2-source')
root=repo/'data'/'nova'/'missions'; rows=[]; cutoff=datetime.now(timezone.utc)-timedelta(days=7)
files=sorted((p for p in root.glob('*.json') if p.is_file()),key=lambda p:p.stat().st_mtime,reverse=True)[:250] if root.is_dir() else []
for path in files:
 try:
  data=json.loads(path.read_text(encoding='utf-8')); updated=str(data.get('updated_at') or data.get('created_at') or '')
  try: dt=datetime.fromisoformat(updated.replace('Z','+00:00'))
  except Exception: dt=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)
  if dt<cutoff: continue
  error=str(data.get('hermes_error') or data.get('error_code') or data.get('execution_error') or '')
  state=str(data.get('status') or data.get('state') or '')
  if error.startswith('governor_') or 'BLOCKER' in state or 'DELIVERY_FAILED'==state:
   rows.append({'mission_id':str(data.get('mission_id') or path.stem),'updated_at':updated,
    'state':state,'response_mode':str(data.get('response_mode') or ''),
    'denial_code':error if error.startswith('governor_') else '',
    'model':str(data.get('model_used') or ''),'provider':str(data.get('provider') or '')})
 except Exception: continue
print(json.dumps({'mission_dir':str(root),'files_checked':len(files),'recent_denials':rows[:30]}))'''

NOVA_ACCEPTANCE_EVIDENCE_SCRIPT = r'''import datetime,json,os,re,subprocess,sys
from pathlib import Path
repo=Path('/home/opc/nexus-os-v2-source')
runtime=repo/'data'/'runtime'
contexts=runtime/'nova_context_snapshots'
deliveries=runtime/'nova_telegram_delivery'
missions=repo/'data'/'nova'/'missions'
traces=Path('/home/opc/.nexus/state/nova/agent_traces')
expected=[
 'Check Nexus systems health.', 'Did it finish?', 'What did Systems find?',
 'Show me the receipt IDs for that health check.', 'Explain that result normally.',
 'Search the Research library for trading. Do not start new research.',
 'Anything interesting in there?', 'Where did that information come from?',
 'Tell me a joke.', 'Nova, what kind of car do you drive?']
def read(path):
 try:
  if path.is_file() and path.stat().st_size<=262144: return json.loads(path.read_text(encoding='utf-8'))
 except Exception: pass
 return {}
def flat(value, keys, depth=0):
 if depth>5 or not isinstance(value,dict): return {}
 out={k:value[k] for k in keys if k in value}
 for child in value.values():
  if isinstance(child,dict):
   found=flat(child,keys,depth+1)
   for k,v in found.items(): out.setdefault(k,v)
 return out
def safe_ids(value):
 if isinstance(value,list): return [str(v)[:160] for v in value[:30] if isinstance(v,(str,int))]
 if isinstance(value,(str,int)): return [str(value)[:160]]
 return []
def update_parts(uid):
 ctx=read(contexts/(str(uid)+'.json'))
 delivery=read(deliveries/(str(uid)+'.json'))
 mid=str(delivery.get('mission_id') or '')
 mission=read(missions/(mid+'.json')) if re.fullmatch(r'[A-Za-z0-9_-]{1,120}',mid) else {}
 text=str(ctx.get('current_text') or mission.get('original_message') or '').strip()
 return ctx,delivery,mission,text
def process_identity():
 result=subprocess.run(['systemctl','--user','show','nova-telegram-oracle.service','--property=MainPID','--value'],capture_output=True,text=True,timeout=5)
 pid=result.stdout.strip()
 if not pid.isdigit() or pid=='0': return {}
 try:
  argv=[x.decode(errors='replace') for x in Path('/proc',pid,'cmdline').read_bytes().split(b'\0') if x]
  env={}
  for item in Path('/proc',pid,'environ').read_bytes().split(b'\0'):
   if b'=' in item:
    k,v=item.split(b'=',1)
    if k in (b'NOVA_CODE_ROOT',b'NOVA_REPO_ROOT'): env[k.decode()]=v.decode(errors='replace')
  entry=argv[1] if len(argv)>1 else ''
  match=re.search(r'(/home/opc/\.nexus/releases/[^/]+)/scripts/nova/nova_telegram_worker\.py$',entry)
  release=match.group(1) if match else ''
  stat=Path('/proc',pid,'stat').read_text().split()
  ticks=int(stat[21]); hz=os.sysconf(os.sysconf_names['SC_CLK_TCK'])
  uptime=float(Path('/proc/uptime').read_text().split()[0])
  started=datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=max(0,uptime-ticks/hz))
  return {'pid':pid,'entrypoint':entry,'active_release':release,'code_root':env.get('NOVA_CODE_ROOT',''),
   'repo_root':env.get('NOVA_REPO_ROOT',''),'process_started_at':started.isoformat().replace('+00:00','Z')}
 except Exception: return {}
def trace_index():
 out={}
 try: files=sorted((p for p in traces.glob('nova_*.json') if p.is_file()),key=lambda p:p.stat().st_mtime,reverse=True)[:500]
 except Exception: files=[]
 for path in files:
  row=read(path); tid=str(row.get('trace_id') or path.stem.removeprefix('nova_'))
  for event in row.get('events',[]) if isinstance(row.get('events'),list) else []:
   meta=event.get('metadata') if isinstance(event,dict) else None
   uid=str(meta.get('update_id') or '') if isinstance(meta,dict) else ''
   if uid and uid not in out: out[uid]={'trace_id':tid,'events':[]}
   if uid: out[uid]['events'].append({'name':str(event.get('name') or ''),'timestamp':str(event.get('timestamp') or ''),
    'metadata':{k:meta[k] for k in ('intent_class','resolved_capability','resolved_engine','operation_class','used_existing_verified_result','referent_result_id','job_id','new_objective_created','new_job_created','mutation_count','approval_required','receipt_ids','provenance_refs','active_release') if k in meta}})
 return out,len(files)
def release_inventory():
 base=Path('/home/opc/.nexus/releases')
 drop=Path('/home/opc/.config/systemd/user/nova-telegram-oracle.service.d')
 names={
  'v14':('nova-operator-v1-20261029-r67-conversation-referent-candidate-v14','zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-r67-health-v14.conf'),
  'v15':('nova-operator-v1-20261029-r67-conversation-referent-candidate-v15','zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-r67-health-v15.conf'),
  'v16':('nova-operator-v1-20261029-r67-conversation-referent-candidate-v16','zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-r67-health-v16.conf')}
 rows=[]
 for version,(name,dropname) in names.items():
  root=base/name; manifest=root/'RELEASE_MANIFEST.sha256'; metadata=read(root/'NOVA_RELEASE_METADATA.json')
  matches=list(drop.glob('*r67-health-'+version+'.conf'))
  drop_path=matches[0] if len(matches)==1 else drop/'UNIQUE_DROPIN_NOT_FOUND'
  try: digest=__import__('hashlib').sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else ''
  except Exception: digest=''
  def mtime(path):
   try: return datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat().replace('+00:00','Z')
   except Exception: return ''
  parent=next((metadata[k] for k in ('rollback_parent','rollback_parent_release','parent_release','rollback_to','rollback_floor') if metadata.get(k)), '')
  rows.append({'label':version,'release_path':str(root),'systemd_dropin':str(drop_path),
   'dropin_present':drop_path.is_file(),'dropin_mtime':mtime(drop_path),
   'entrypoint':str(root/'scripts/nova/nova_telegram_worker.py'),'configured_code_root':'/home/opc/.nexus/releases/nova-operator-v1-20261029-r67-gateway-candidate-v1',
   'release_present':root.is_dir(),'manifest_hash':digest,'rollback_parent':str(parent)})
 return rows
try:
 args=json.loads(sys.argv[1])
 mode=args.get('mode')
 ids=args.get('update_ids') or []
 if mode in ('sequence','window','messages'):
  try:
   candidates={p.stem:p for root in (contexts,deliveries) for p in root.glob('*.json') if p.is_file() and p.stem.isdigit()}
   candidates=sorted(candidates.values(),key=lambda p:p.stat().st_mtime,reverse=True)[:1000]
  except Exception: candidates=[]
  matches=[]
  for p in candidates:
   ctx,delivery,mission,text=update_parts(p.stem)
   stamp=p.stat().st_mtime
   in_window=(mode not in ('window','messages') or (datetime.datetime.fromisoformat(args['start_time']).timestamp()<=stamp<=datetime.datetime.fromisoformat(args['end_time']).timestamp()))
   selected_text=(text in args.get('messages',[]) if mode=='messages' else text in expected)
   if in_window and selected_text: matches.append((int(p.stem),p,ctx))
  matches.sort(key=lambda item:item[0])
  if mode=='messages':
   selected=matches[-min(10,int(args.get('max_records',10))):]
  else:
   # Select the newest complete ordered occurrence; otherwise return only the newest ordered partial sequence.
   chosen=[]
   for index in range(len(matches)):
    trial=[]; next_expected=0; last_id=-1
    for item in matches[index:]:
     uid,p,row=item
     if uid<=last_id: continue
     if str(row.get('current_text') or '').strip()==expected[next_expected]:
      trial.append(item); last_id=uid; next_expected+=1
      if next_expected==len(expected): break
    if len(trial)>len(chosen): chosen=trial
    if len(chosen)==len(expected): break
   selected=chosen[:min(10,int(args.get('max_records',10)))]
 else:
  selected=[]
  for uid in ids[:10]:
   p=contexts/(uid+'.json')
   if not p.is_file(): p=deliveries/(uid+'.json')
   ctx,delivery,mission,text=update_parts(uid)
   if p.is_file() or delivery or mission: selected.append((int(uid),p,ctx))
 current=process_identity(); traces_by_update,trace_files=trace_index(); records=[]
 if mode=='session':
  session=str(args.get('session_id') or '')
  if not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',session): raise ValueError('invalid session')
  session_path=traces/'acceptance_sessions'/(session+'.jsonl')
  session_rows=[]
  if session_path.is_file() and session_path.stat().st_size<=2097152:
   for line in session_path.read_text(encoding='utf-8').splitlines()[-min(100,int(args.get('max_records',100))):]:
    if len(line.encode('utf-8'))>65536: continue
    try: row=json.loads(line)
    except Exception: continue
    if row.get('acceptance_session_id')==session: session_rows.append(row)
  print(json.dumps({'read_only':True,'mutation_count':0,'arbitrary_path_access':False,
   'arbitrary_command_execution':False,'secret_exposure':False,'bounded_query':True,
   'selection_mode':'session','acceptance_session_id':session,'records_scanned_max':len(session_rows),
   'records':session_rows[-min(100,int(args.get('max_records',100))):]}))
  raise SystemExit(0)
 for uid,p,ctx in selected:
  ctx,delivery,mission,user_text=update_parts(uid); mission_id=str(delivery.get('mission_id') or '')
  trace=traces_by_update.get(str(uid),{}); events=trace.get('events',[])
  md={}
  for event in events:
   if event.get('metadata'): md.update(event['metadata'])
  source={**mission,**md}
  fields=flat(source,('intent_class','resolved_capability','capability_id','selected_capability','resolved_engine','engine','operation_class','used_existing_verified_result','referent_result_id','referent_type','request_id','correlation_id','job_id','durable_job_id','new_objective_created','new_job_created','mutation_count','approval_required','receipt_ids','provenance_refs','active_release','status','response_mode','objective_id','objective_created'))
  response=str(delivery.get('response') or '')
  receipt_ids=safe_ids(fields.get('receipt_ids') or mission.get('receipt_ids'))
  if not receipt_ids: receipt_ids=__import__('re').findall(r'(?:Gateway receipt ID|Systems receipt ID|receipt ID)[:\s]+([A-Za-z0-9_-]+)',response,re.I)
  provenance=safe_ids(fields.get('provenance_refs') or mission.get('provenance_refs'))
  if not provenance: provenance=__import__('re').findall(r'\[evidence:\s*([^\]]+)\]',response,re.I)
  request_id=fields.get('request_id') or (re.search(r'Request ID[:\s]+([A-Za-z0-9_-]+)',response,re.I).group(1) if re.search(r'Request ID[:\s]+([A-Za-z0-9_-]+)',response,re.I) else '')
  mutation=fields.get('mutation_count')
  if mutation in ('',None):
   mm=re.search(r'Mutation count[:\s]+([0-9]+)',response,re.I); mutation=int(mm.group(1)) if mm else ''
  step_caps=[]
  for step in mission.get('steps',[]) if isinstance(mission.get('steps'),list) else []:
   if isinstance(step,dict):
    cap=step.get('capability_id') or step.get('selected_capability')
    if cap and str(cap) not in step_caps: step_caps.append(str(cap)[:180])
  recv=datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat().replace('+00:00','Z')
  referent=ctx.get('resolved_referent')
  if isinstance(referent,dict): referent=next((referent[k] for k in ('result_id','mission_id','job_id','case_id','objective_id','id') if referent.get(k)), '')
  records.append({'update_id':str(uid),'user_message':user_text[:1000],
   'nova_response':str(delivery.get('response') or '')[:4000],'received_at':recv,
   'intent_class':fields.get('intent_class',''),'resolved_capability':fields.get('resolved_capability') or fields.get('capability_id') or fields.get('selected_capability') or step_caps,
   'resolved_engine':fields.get('resolved_engine') or fields.get('engine',''),'operation_class':fields.get('operation_class',''),
   'used_existing_verified_result':fields.get('used_existing_verified_result',''),
   'referent_result_id':fields.get('referent_result_id') or referent or '',
   'referent_type':fields.get('referent_type') or ctx.get('reference_type') or '',
   'request_id':request_id,'correlation_id':fields.get('correlation_id') or delivery.get('correlation_id',''),
   'mission_id':mission_id,'mission_status':fields.get('status',''),'response_mode':fields.get('response_mode',''),
   'objective_id':fields.get('objective_id',''),'objective_created':fields.get('objective_created',''),
   'job_id':fields.get('job_id') or fields.get('durable_job_id') or '',
   'new_objective_created':fields.get('new_objective_created',''),
   'new_job_created':fields.get('new_job_created',''),'mutation_count':mutation,
   'approval_required':fields.get('approval_required',''),'receipt_ids':receipt_ids,'provenance_refs':provenance,
   'delivery_state':str(delivery.get('state') or ''),'telegram_message_id':safe_ids(delivery.get('message_ids')),
   'active_release':fields.get('active_release',''),'trace_id':trace.get('trace_id',''),
   'previous_update_id':ctx.get('previous_update_id',''),
   'previous_user_message':str(ctx.get('previous_user_text') or '')[:1000],
   'previous_nova_response':str(ctx.get('previous_assistant_text') or '')[:4000],
   'trace_events':events[:30]})
 systemd=[]
 try:
  jr=subprocess.run(['journalctl','--user','-u','nova-telegram-oracle.service','--since=-14days','--no-pager','-o','short-iso-precise','-n','1000'],capture_output=True,text=True,timeout=12)
  for line in jr.stdout.splitlines():
   low=line.lower()
   if any(x in low for x in ('started nexus nova telegram','stopped nexus nova telegram','main process exited','scheduled restart job')):
    action=next((x for x in ('started','stopped','main process exited','scheduled restart job') if x in low),'lifecycle')
    label=next((x for x in ('v14','v15','v16') if 'candidate-'+x in low or 'health-'+x in low),'')
    systemd.append({'timestamp':line[:35],'action':action,'release_label':label})
 except Exception: pass
 offset=read(runtime/'nova_telegram_last_update_id.json')
 print(json.dumps({'read_only':True,'mutation_count':0,'arbitrary_path_access':False,'arbitrary_command_execution':False,
  'secret_exposure':False,'bounded_query':True,'selection_mode':mode,'records_scanned_max':1000 if mode in ('sequence','window') else len(ids),
  'sequence_complete':len(records)==10 and [r['user_message'] for r in records]==expected,
  'records':records,'telegram_offset':{k:offset[k] for k in ('last_update_id','updated_at','last_advanced_at') if k in offset},
  'active_process':current,'release_candidates':release_inventory(),
  'systemd_lifecycle_events':systemd[-100:],'trace_files_scanned_max':trace_files}))
except Exception as exc:
 print(json.dumps({'read_only':True,'error_class':type(exc).__name__,'sequence_complete':False,'records':[]}));raise SystemExit(2)'''

NOVA_CONCURRENCY_INVENTORY_SCRIPT = r'''import json,os,subprocess,urllib.request,traceback,sqlite3,datetime
from pathlib import Path
try:
 repo=Path('/home/opc/nexus-os-v2-source')
 pid=subprocess.run(['systemctl','--user','show','nova-telegram-oracle.service','--property=MainPID','--value'],capture_output=True,text=True,timeout=8).stdout.strip()
 if not pid.isdigit() or pid=='0': raise RuntimeError('SERVICE_PID_UNAVAILABLE')
 env={}
 for item in open('/proc/'+pid+'/environ','rb').read().split(b'\0'):
  if b'=' not in item: continue
  key,value=item.split(b'=',1)
  if key in {b'SUPABASE_URL',b'VITE_SUPABASE_URL',b'SUPABASE_SERVICE_ROLE_KEY',b'NOVA_RUNTIME_ENV',b'NEXUS_GOVERNOR_DB'}: env[key.decode()]=value.decode(errors='ignore')
 governor_db=env.get('NEXUS_GOVERNOR_DB','')
 if governor_db and Path(governor_db).is_file():
  db=sqlite3.connect('file:'+governor_db+'?mode=ro',uri=True,timeout=3);db.row_factory=sqlite3.Row
  reservations=[dict(r) for r in db.execute("SELECT reservation_id,provider,service,job_type,budget_period,job_id,status,created_at,expires_at,reconciled_at FROM reservations WHERE provider='OPENAI_CODEX' AND status='ACTIVE' ORDER BY created_at LIMIT 50")]
  policies=[dict(r) for r in db.execute("SELECT service,job_type,budget_period,state,concurrency_limit,autonomous_usage_allowed,autonomous_spend_allowed,approval_required FROM policies WHERE provider='OPENAI_CODEX' ORDER BY service,job_type,budget_period LIMIT 50")]
  missions={};root=repo/'data'/'nova'/'missions'
  for row in reservations:
   job=str(row.get('job_id') or '');path=root/(job+'.json')
   if not path.is_file(): continue
   try:
    data=json.loads(path.read_text(encoding='utf-8'))
    missions[job]={'mission_state':str(data.get('status') or data.get('state') or ''),'mission_updated_at':str(data.get('updated_at') or data.get('created_at') or ''),'response_mode':str(data.get('response_mode') or ''),'denial_code':str(data.get('hermes_error') or data.get('error_code') or '')}
   except Exception: pass
  print(json.dumps({'backend':'LOCAL_SQLITE','backend_path':governor_db,'reservations':[{**row,**missions.get(str(row.get('job_id') or ''),{})} for row in reservations],
   'policies':policies,'now_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'request_content_printed':False,'credential_values_printed':False}));raise SystemExit(0)
 env_source=env.get('NOVA_RUNTIME_ENV') or '/home/opc/.config/nexus/runtime.env'
 if not env.get('SUPABASE_URL') or not env.get('SUPABASE_SERVICE_ROLE_KEY'):
  env_paths=[Path(env_source),Path('/home/opc/.config/nova-telegram.env')]
  for env_path in env_paths:
   if not env_path.is_file(): continue
   env_source=str(env_path)
   for line in env_path.read_text(encoding='utf-8',errors='ignore').splitlines():
    text=line.strip().removeprefix('export ').strip();key,sep,value=text.partition('=')
    if sep and key.strip() in {'SUPABASE_URL','VITE_SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY'}:
     env.setdefault(key.strip(),value.strip().strip('\\\"\\\''))
 base=(env.get('SUPABASE_URL') or env.get('VITE_SUPABASE_URL') or '').rstrip('/');token=env.get('SUPABASE_SERVICE_ROLE_KEY','')
 if not base or not token: raise RuntimeError('SERVICE_SUPABASE_CREDENTIALS_NOT_IN_PROCESS_ENV')
 def get(path):
  req=urllib.request.Request(base+'/rest/v1/'+path,headers={'apikey':token,'Authorization':'Bearer '+token,'Accept':'application/json'})
  with urllib.request.urlopen(req,timeout=15) as response: return json.loads(response.read(262145))
 reservations=get('nexus_resource_reservations?provider=eq.OPENAI_CODEX&status=eq.ACTIVE&select=reservation_id,provider,service,job_type,budget_period,job_id,status,created_at,expires_at,reconciled_at&order=created_at.asc&limit=50') or []
 policies=get('nexus_resource_policies?provider=eq.OPENAI_CODEX&select=service,job_type,budget_period,state,concurrency_limit,autonomous_usage_allowed,autonomous_spend_allowed,approval_required&limit=50') or []
 missions={};root=repo/'data'/'nova'/'missions'
 for row in reservations:
  job=str(row.get('job_id') or '');path=root/(job+'.json')
  if not path.is_file(): continue
  try:
   data=json.loads(path.read_text(encoding='utf-8'))
   missions[job]={'mission_state':str(data.get('status') or data.get('state') or ''),'mission_updated_at':str(data.get('updated_at') or data.get('created_at') or ''),'response_mode':str(data.get('response_mode') or ''),'denial_code':str(data.get('hermes_error') or data.get('error_code') or '')}
  except Exception: pass
 print(json.dumps({'reservations':[{**{k:row.get(k) for k in ('reservation_id','provider','service','job_type','budget_period','job_id','status','created_at','expires_at','reconciled_at')},**missions.get(str(row.get('job_id') or ''),{})} for row in reservations],
  'policies':[{k:row.get(k) for k in ('service','job_type','budget_period','state','concurrency_limit','autonomous_usage_allowed','autonomous_spend_allowed','approval_required')} for row in policies],
 'backend':'SUPABASE','now_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'credential_source':env_source,'request_content_printed':False,'credential_values_printed':False}))
except Exception as exc:
 frames=traceback.extract_tb(exc.__traceback__);frame=frames[-1] if frames else None
 print(json.dumps({'error_class':type(exc).__name__,'safe_status':getattr(exc,'code',None),'error_location':({'file':Path(frame.filename).name,'function':frame.name,'line':frame.lineno} if frame else None),'credential_source':locals().get('env_source'),'url_present':bool(locals().get('base')),'credential_present':bool(locals().get('token')),'message_content_printed':False,'credential_values_printed':False}))'''

EXPIRED_RESERVATION_RELEASE_SCRIPT = r'''import json,sqlite3,sys
reservation_id=sys.argv[1]
path='/home/opc/nexus-os-v2-source/data/runtime/resource_spend_governor.sqlite3'
db=sqlite3.connect('file:'+path+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
row=db.execute('SELECT reservation_id,provider,service,job_type,job_id,status,expires_at FROM reservations WHERE reservation_id=?',(reservation_id,)).fetchone()
if not row: print(json.dumps({'released':False,'reason':'RESERVATION_NOT_FOUND'}));raise SystemExit(2)
if row['provider']!='OPENAI_CODEX' or row['status']!='ACTIVE' or row['service']!='subscription_model' or row['job_type']!='NOVA_TELEGRAM_OWNER_TURN':
 print(json.dumps({'released':False,'reason':'EXACT_SCOPE_OR_STATE_MISMATCH'}));raise SystemExit(2)
expired=db.execute("SELECT julianday(?)<=julianday('now')",(row['expires_at'],)).fetchone()[0]
if not expired: print(json.dumps({'released':False,'reason':'RESERVATION_NOT_EXPIRED','job_id':row['job_id']}));raise SystemExit(2)
db.close()
sys.path.insert(0,'/home/opc/.nexus/releases/nova-operator-v1-20261025-r50-routing-precedence/scripts')
from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
store=LocalGovernorStore(path)
released=store.release(reservation_id)
with store.connect() as check:
 status=check.execute('SELECT status FROM reservations WHERE reservation_id=?',(reservation_id,)).fetchone()['status']
 active=check.execute("SELECT count(*) n FROM reservations WHERE provider='OPENAI_CODEX' AND status='ACTIVE'").fetchone()['n']
print(json.dumps({'released':released,'reservation_status_after':status,'active_codex_reservations_after':active,'job_id':row['job_id'],'request_content_printed':False}))'''


class AuthorityError(RuntimeError):
    pass


def load_authority(path: Path = AUTHORITY_PATH) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AuthorityError(f"AUTHORITY_RECORD_UNAVAILABLE:{type(exc).__name__}") from exc
    current = record.get("current") if isinstance(record, dict) else None
    if record.get("current_connection_count") != 1 or not isinstance(current, dict):
        raise AuthorityError("AUTHORITY_MUST_HAVE_EXACTLY_ONE_CURRENT_CONNECTION")
    required = ("host", "user", "identity_path", "identity_public_fingerprint", "remote_hostname")
    if any(not str(current.get(key) or "").strip() for key in required):
        raise AuthorityError("CURRENT_CONNECTION_RECORD_INCOMPLETE")
    if current.get("status") != "VERIFIED":
        raise AuthorityError("CURRENT_CONNECTION_NOT_VERIFIED")
    return record


def _identity_path(connection: dict[str, Any]) -> Path:
    return Path(os.path.expanduser(str(connection["identity_path"])))


def public_fingerprint(identity: Path, runner: Callable[..., Any] = subprocess.run) -> str:
    public = Path(str(identity) + ".pub")
    if not public.is_file():
        raise AuthorityError("APPROVED_PUBLIC_IDENTITY_MISSING")
    result = runner(["ssh-keygen", "-lf", str(public)], capture_output=True,
                    text=True, timeout=5, check=False)
    fields = result.stdout.split() if result.returncode == 0 else []
    if len(fields) < 2:
        raise AuthorityError("APPROVED_PUBLIC_IDENTITY_INVALID")
    return fields[1]


def _ssh_base(connection: dict[str, Any]) -> list[str]:
    identity = _identity_path(connection)
    return ["ssh", "-i", str(identity), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=8", f"{connection['user']}@{connection['host']}"]


def verify_connection(connection: dict[str, Any], runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Verify only this connection tuple; never consult HISTORY."""
    identity = _identity_path(connection)
    if not identity.is_file():
        raise AuthorityError("CURRENT_IDENTITY_MISSING")
    fingerprint = public_fingerprint(identity, runner=runner)
    if fingerprint != connection.get("identity_public_fingerprint"):
        raise AuthorityError("CURRENT_IDENTITY_FINGERPRINT_MISMATCH")
    target = _ssh_base(connection)
    remote = ["python3", "-c", EXPECTED_REMOTE_CHECK]
    result = runner([*target, shlex.join(remote)], capture_output=True, text=True,
                    timeout=18, check=False)
    if result.returncode != 0:
        detail = (result.stderr or "").casefold()
        if "permission denied" in detail:
            code = "SSH_AUTHENTICATION_FAILED"
        elif "could not resolve hostname" in detail or "name or service not known" in detail:
            code = "SSH_HOST_UNRESOLVED"
        elif "timed out" in detail:
            code = "SSH_CONNECTION_TIMEOUT"
        else:
            code = "SSH_REMOTE_CHECK_FAILED"
        raise AuthorityError(code)
    try:
        health = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise AuthorityError("REMOTE_HEALTH_RESPONSE_INVALID") from exc
    expected = {
        "hostname": connection["remote_hostname"],
        "user": connection["user"],
        "nova_service": "active",
        "hermes_container": "running",
    }
    mismatches = [key for key, value in expected.items()
                  if str(health.get(key) or "").casefold() != value.casefold()]
    if mismatches:
        raise AuthorityError("REMOTE_IDENTITY_OR_RUNTIME_MISMATCH:" + ",".join(mismatches))
    return {**health, "identity_fingerprint": fingerprint, "connection_used": f"{connection['user']}@{connection['host']}",
            "historical_connectors_attempted": False}


def _safe_exec_args(command: str) -> tuple[str, ...]:
    try:
        tokens = tuple(shlex.split(command))
    except ValueError as exc:
        raise AuthorityError("SAFE_COMMAND_PARSE_FAILED") from exc
    if tokens not in SAFE_COMMANDS:
        raise AuthorityError("COMMAND_NOT_IN_READ_ONLY_ALLOWLIST")
    return tokens


def validate_acceptance_query(update_ids: list[str], start_time: str, end_time: str,
                              max_records: int, session_id: str = "",
                              messages: list[str] | None = None) -> dict[str, Any]:
    """Validate one bounded acceptance evidence selector before remote read."""
    try:
        maximum = int(max_records)
    except (TypeError, ValueError) as exc:
        raise AuthorityError("ACCEPTANCE_QUERY_MAX_RECORDS_INVALID") from exc
    if maximum < 1 or maximum > 100:
        raise AuthorityError("ACCEPTANCE_QUERY_MAX_RECORDS_INVALID")
    has_ids = bool(update_ids)
    has_window = bool(start_time or end_time)
    has_session = bool(session_id)
    has_messages = bool(messages)
    if (sum((has_ids, has_session, has_messages)) > 1
            or (has_window and (has_ids or has_session))):
        raise AuthorityError("ACCEPTANCE_QUERY_SELECTOR_CONFLICT")
    if not has_ids and not has_window and not has_session and not has_messages:
        raise AuthorityError("ACCEPTANCE_QUERY_SELECTOR_REQUIRED")
    if has_session:
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", session_id):
            raise AuthorityError("ACCEPTANCE_QUERY_SESSION_ID_INVALID")
        return {"mode": "session", "session_id": session_id, "max_records": min(maximum, 100)}
    if has_ids:
        if len(update_ids) > 10 or any(not re.fullmatch(r"[0-9]{1,20}", str(value)) for value in update_ids):
            raise AuthorityError("ACCEPTANCE_QUERY_UPDATE_ID_INVALID")
        return {"mode": "update_ids", "update_ids": list(dict.fromkeys(map(str, update_ids))),
                "max_records": min(maximum, 10)}
    if has_messages:
        if len(messages) > 5 or any(not isinstance(value, str) or not value.strip() or len(value) > 500 for value in messages):
            raise AuthorityError("ACCEPTANCE_QUERY_MESSAGE_INVALID")
        if not has_window:
            raise AuthorityError("ACCEPTANCE_QUERY_WINDOW_REQUIRED")
    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        if start.tzinfo is None or end.tzinfo is None or start >= end or (end - start).total_seconds() > 86400:
            raise ValueError("invalid window")
    except (TypeError, ValueError) as exc:
        raise AuthorityError("ACCEPTANCE_QUERY_WINDOW_INVALID") from exc
    return {"mode": "messages" if has_messages else "window", "start_time": start.isoformat(), "end_time": end.isoformat(),
            **({"messages": list(dict.fromkeys(messages))} if has_messages else {}),
            "max_records": min(maximum, 10)}


def read_acceptance_evidence(connection: dict[str, Any], query: dict[str, Any],
                             runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Read only the fixed Nova acceptance state locations using a bounded query."""
    verify_connection(connection, runner=runner)
    remote = ["python3", "-c", NOVA_ACCEPTANCE_EVIDENCE_SCRIPT, json.dumps(query, separators=(",", ":"))]
    result = runner([*_ssh_base(connection), shlex.join(remote)], capture_output=True, text=True,
                    timeout=35, check=False)
    if result.returncode:
        raise AuthorityError("NOVA_ACCEPTANCE_EVIDENCE_READ_FAILED")
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise AuthorityError("NOVA_ACCEPTANCE_EVIDENCE_RESPONSE_INVALID") from exc
    if payload.get("read_only") is not True or payload.get("mutation_count") != 0 \
            or payload.get("arbitrary_path_access") is not False \
            or payload.get("arbitrary_command_execution") is not False \
            or payload.get("secret_exposure") is not False \
            or payload.get("bounded_query") is not True:
        raise AuthorityError("NOVA_ACCEPTANCE_EVIDENCE_GOVERNANCE_CONTRACT_FAILED")
    return payload


def execute_safe(connection: dict[str, Any], command: str,
                 runner: Callable[..., Any] = subprocess.run) -> subprocess.CompletedProcess:
    tokens = _safe_exec_args(command)
    verify_connection(connection, runner=runner)
    return runner([*_ssh_base(connection), shlex.join(tokens)], capture_output=True,
                  text=True, timeout=18, check=False)


def verify_r50_release(connection: dict[str, Any],
                        runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Verify the pinned immutable R50 release without reading unrelated paths."""
    verify_connection(connection, runner=runner)
    result = runner([*_ssh_base(connection), shlex.join(["python3", "-c", R50_VERIFY_SCRIPT])],
                    capture_output=True, text=True, timeout=30, check=False)
    if result.returncode:
        raise AuthorityError("R50_REMOTE_MANIFEST_VERIFICATION_FAILED")
    try:
        report = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise AuthorityError("R50_MANIFEST_REPORT_INVALID") from exc
    if (report.get("release_id") != "nova-operator-v1-20261025-r50-routing-precedence"
            or report.get("source_commit") != "d6077d230987ffec0ce6d7263313f919b5f6d582"
            or report.get("release_source_hash") != "d6077d230987ffec0ce6d7263313f919b5f6d582"):
        raise AuthorityError("R50_RELEASE_IDENTITY_MISMATCH")
    return report


def _verify_local_manifest(root: Path) -> tuple[int, list[str]]:
    manifest = root / "RELEASE_MANIFEST.sha256"
    mismatches: list[str] = []
    entries = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            mismatches.append(relative)
            continue
        entries += 1
        target = root / rel
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            mismatches.append(relative)
    return entries, mismatches


def materialize_r50(connection: dict[str, Any], destination: Path,
                    runner: Callable[..., Any] = subprocess.run) -> tuple[int, list[str]]:
    """Copy only the verified immutable R50 directory to a fresh /private/tmp path."""
    dest = destination.expanduser().resolve()
    if not dest.is_relative_to(Path("/private/tmp")) or dest == Path("/private/tmp"):
        raise AuthorityError("R50_DESTINATION_MUST_BE_UNDER_PRIVATE_TMP")
    if dest.exists():
        raise AuthorityError("R50_DESTINATION_ALREADY_EXISTS")
    remote_report = verify_r50_release(connection, runner=runner)
    if remote_report.get("manifest_mismatches"):
        raise AuthorityError("R50_REMOTE_MANIFEST_HAS_MISMATCHES")
    stage = Path(tempfile.mkdtemp(prefix="nexus-r50-verified-", dir=str(dest.parent)))
    try:
        identity = _identity_path(connection)
        source = f"{connection['user']}@{connection['host']}:{R50_RELEASE}"
        copied = runner(["scp", "-r", "-p", "-i", str(identity), "-o", "IdentitiesOnly=yes",
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", source, str(stage)],
            capture_output=True, text=True, timeout=180, check=False)
        if copied.returncode:
            detail = (copied.stderr or "").casefold()
            if "permission denied" in detail:
                reason = "SSH_AUTHENTICATION_FAILED"
            elif "no such file" in detail or "not found" in detail:
                reason = "REMOTE_RELEASE_PATH_UNAVAILABLE"
            elif "subsystem request failed" in detail or "sftp" in detail:
                reason = "SCP_TRANSFER_PROTOCOL_FAILED"
            elif "timed out" in detail:
                reason = "SCP_TRANSFER_TIMEOUT"
            else:
                reason = "SCP_TRANSFER_FAILED"
            raise AuthorityError("R50_MATERIALIZATION_COPY_FAILED:" + reason)
        staged_release = stage / Path(R50_RELEASE).name
        count, mismatches = _verify_local_manifest(staged_release)
        if count != remote_report["manifest_entries"] or mismatches:
            raise AuthorityError("R50_MATERIALIZED_MANIFEST_MISMATCH")
        shutil.copytree(staged_release, dest, copy_function=shutil.copy2, symlinks=True)
        copied_count, copied_mismatches = _verify_local_manifest(dest)
        if copied_count != count or copied_mismatches:
            shutil.rmtree(dest, onerror=_make_removable)
            raise AuthorityError("R50_FINAL_COPY_MANIFEST_MISMATCH")
        return count, []
    finally:
        if stage.exists():
            shutil.rmtree(stage, onerror=_make_removable)


def _make_removable(function: Callable[..., Any], path: str, _exc_info: Any) -> None:
    os.chmod(path, 0o700)
    function(path)


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def promote_recovery_candidate(record: dict[str, Any], *, host: str, user: str,
                               identity_path: str, remote_hostname: str,
                               runner: Callable[..., Any] = subprocess.run,
                               path: Path = AUTHORITY_PATH) -> dict[str, Any]:
    """Explicit-only candidate promotion; a failure leaves CURRENT byte-identical."""
    candidate = {
        "host": host, "user": user, "identity_path": identity_path,
        "identity_public_fingerprint": public_fingerprint(Path(os.path.expanduser(identity_path)), runner=runner),
        "connection_method": "OpenSSH with explicit IdentityFile; no proxy; explicit recovery mode",
        "identities_only": True, "batch_mode": True, "remote_hostname": remote_hostname,
        "nova_service": f"{NOVA_SERVICE} (user systemd)",
        "hermes_runtime": f"Podman container {HERMES_CONTAINER}",
        "mcp_tunnel_method": record["current"].get("mcp_tunnel_method", ""),
        "last_verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "verification_source": "Explicit --recovery candidate passed full resolver health checks",
        "status": "VERIFIED",
    }
    verify_connection(candidate, runner=runner)
    updated = dict(record)
    history = list(record.get("history") or [])
    previous = dict(record["current"])
    previous["status"] = "SUPERSEDED"
    previous["superseded_at"] = candidate["last_verified_at"]
    history.append(previous)
    updated["current"] = candidate
    updated["history"] = history
    updated["current_connection_count"] = 1
    _atomic_write(path, updated)
    return updated


def _print_health(health: dict[str, Any]) -> None:
    print("ORACLE_SSH_AUTH=PASS")
    print("ORACLE_HOST=" + str(health["hostname"]))
    print("ORACLE_USER=" + str(health["user"]))
    print("NOVA_SERVICE=" + str(health["nova_service"]).upper())
    print("HERMES_RUNTIME=" + str(health["hermes_container"]).upper())
    print("IDENTITY_FINGERPRINT=" + str(health["identity_fingerprint"]))
    print("CONNECTION_USED=" + str(health["connection_used"]))
    print("HISTORICAL_CONNECTORS_AUTO_TRIED=NO")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check", action="store_true")
    actions.add_argument("--status", action="store_true")
    actions.add_argument("--exec", dest="safe_command")
    actions.add_argument("--verify-r50", action="store_true",
                         help="Verify the pinned immutable Oracle R50 release manifest")
    actions.add_argument("--materialize-r50", metavar="DESTINATION",
                         help="Copy the verified R50 release to a fresh path under /private/tmp")
    actions.add_argument("--hermes-inventory", action="store_true",
                         help="Print redacted provider/model metadata from the active Hermes profile")
    actions.add_argument("--nova-runtime-inventory", action="store_true",
                         help="Print allowlisted runtime/model metadata from the active Nova process")
    actions.add_argument("--acceptance-evidence", action="store_true",
                         help="Read a bounded set of existing Nova acceptance updates and their linked evidence")
    actions.add_argument("--acceptance-sequence", action="store_true",
                         help="Find only the fixed ten-turn acceptance sequence among the latest 1000 Nova context records")
    actions.add_argument("--nova-denial-inventory", action="store_true",
                         help="Read recent Nova mission denial codes without returning message content")
    actions.add_argument("--concurrency-inventory", action="store_true",
                         help="Read active Codex governor reservations and scoped limits without mutation")
    actions.add_argument("--release-expired-reservation", metavar="RESERVATION_ID",
                         help="Release one exact OPENAI_CODEX Nova reservation only after proving its TTL expired")
    actions.add_argument("--recovery", action="store_true",
                         help="Explicitly verify and atomically promote a supplied candidate")
    parser.add_argument("--host", help="Candidate host (recovery mode only)")
    parser.add_argument("--user", help="Candidate user (recovery mode only)")
    parser.add_argument("--identity", help="Candidate identity path (recovery mode only)")
    parser.add_argument("--remote-hostname", help="Expected candidate hostname (recovery mode only)")
    parser.add_argument("--acceptance-update-id", action="append", default=[],
                        help="Exact Telegram update ID for the bounded acceptance evidence read; repeat up to 10 times")
    parser.add_argument("--acceptance-start", default="", help="UTC ISO-8601 start time for the bounded acceptance evidence read")
    parser.add_argument("--acceptance-end", default="", help="UTC ISO-8601 end time for the bounded acceptance evidence read")
    parser.add_argument("--acceptance-max-records", type=int, default=10,
                        help="Maximum acceptance records to return (hard-capped at 10)")
    parser.add_argument("--acceptance-session-id", default="",
                        help="Exact bounded Nova acceptance session file to read")
    parser.add_argument("--acceptance-message", action="append", default=[],
                        help="Exact user message for a bounded read-only acceptance evidence query; repeat up to five times")
    args = parser.parse_args(argv)
    try:
        record = load_authority()
        if args.status:
            current = record["current"]
            print("AUTHORITY_RECORD=" + str(AUTHORITY_PATH))
            print("CURRENT_CONNECTION_COUNT=1")
            for key in ("host", "user", "identity_path", "identity_public_fingerprint",
                        "remote_hostname", "nova_service", "hermes_runtime", "status", "last_verified_at"):
                print(f"CURRENT_{key.upper()}={current.get(key, '')}")
            print("HISTORY_ENTRY_COUNT=" + str(len(record.get("history") or [])))
            return 0
        if args.recovery:
            if not all((args.host, args.user, args.identity, args.remote_hostname)):
                raise AuthorityError("RECOVERY_REQUIRES_HOST_USER_IDENTITY_AND_REMOTE_HOSTNAME")
            updated = promote_recovery_candidate(record, host=args.host, user=args.user,
                identity_path=args.identity, remote_hostname=args.remote_hostname)
            print("RECOVERY_CANDIDATE=VERIFIED")
            print("CURRENT_ORACLE_CONNECTION_COUNT=" + str(updated["current_connection_count"]))
            print("CURRENT_PROMOTED=YES")
            return 0
        if args.verify_r50:
            report = verify_r50_release(record["current"])
            print("R50_RELEASE=" + str(report["release_id"]))
            print("R50_SOURCE_COMMIT=" + str(report["source_commit"]))
            print("R50_MANIFEST_ENTRY_COUNT=" + str(report["manifest_entries"]))
            print("R50_MANIFEST_MISMATCH_COUNT=" + str(len(report["manifest_mismatches"])))
            print("R50_MANIFEST_SHA256=" + str(report["manifest_sha256"]))
            print("R50_ARTIFACT_SHA256=" + str(report.get("artifact_sha256") or "NOT_IN_RELEASE_METADATA"))
            print("R50_CLEAN_BASE_VERIFIED=" + ("YES" if not report["manifest_mismatches"] else "NO"))
            if report["manifest_mismatches"]:
                print("R50_MANIFEST_MISMATCH_PATHS=" + ",".join(report["manifest_mismatches"][:20]))
                return 1
            return 0
        if args.materialize_r50:
            count, mismatches = materialize_r50(record["current"], Path(args.materialize_r50))
            print("R50_MATERIALIZED=" + args.materialize_r50)
            print("R50_MANIFEST_ENTRY_COUNT=" + str(count))
            print("R50_MANIFEST_MISMATCH_COUNT=" + str(len(mismatches)))
            print("R50_CLEAN_BASE_RECOVERED=" + ("YES" if not mismatches else "NO"))
            return 0 if not mismatches else 1
        if args.hermes_inventory:
            result = subprocess.run([*_ssh_base(record["current"]),
                shlex.join(["python3", "-c", HERMES_INVENTORY_SCRIPT])],
                capture_output=True, text=True, timeout=30, check=False)
            if result.returncode:
                raise AuthorityError("HERMES_INVENTORY_UNAVAILABLE")
            try:
                inventory = json.loads(result.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError) as exc:
                raise AuthorityError("HERMES_INVENTORY_RESPONSE_INVALID") from exc
            print("HERMES_CONFIG_SOURCE=" + str(inventory.get("config_source")))
            print("HERMES_CONFIG_PRESENT=" + ("YES" if inventory.get("config_present") else "NO"))
            print("HERMES_PROVIDER_FIELDS=" + json.dumps(inventory.get("provider_fields", []), separators=(",", ":")))
            print("HERMES_MODEL_FIELDS=" + json.dumps(inventory.get("model_fields", []), separators=(",", ":")))
            print("HERMES_FALLBACK_FIELDS=" + json.dumps(inventory.get("fallback_fields", []), separators=(",", ":")))
            print("HERMES_AUTH_METHOD=" + str(inventory.get("auth_method")))
            print("HERMES_OAUTH_CREDENTIAL_PRESENT=" + ("YES" if inventory.get("oauth_credential_present") else "NO"))
            print("HERMES_AUTH_KEY_PATHS=" + json.dumps(inventory.get("auth_key_paths", []), separators=(",", ":")))
            print("HERMES_PROFILE_ENV_MODEL_FIELDS=" + json.dumps(inventory.get("profile_env_model_fields", {}), separators=(",", ":")))
            print("HERMES_CREDENTIAL_VARIABLE_NAMES=" + json.dumps(inventory.get("credential_variable_names", []), separators=(",", ":")))
            print("CODEX_AUTH_SOURCE=" + str(inventory.get("codex_auth_source")))
            print("CODEX_AUTH_PRESENT=" + ("YES" if inventory.get("codex_auth_present") else "NO"))
            print("CODEX_AUTH_MODE_HINTS=" + json.dumps(inventory.get("codex_auth_mode_hints", []), separators=(",", ":")))
            print("SECRET_VALUES_PRINTED=NO")
            return 0
        if args.nova_runtime_inventory:
            result = subprocess.run([*_ssh_base(record["current"]),
                shlex.join(["python3", "-c", NOVA_INVENTORY_SCRIPT])],
                capture_output=True, text=True, timeout=30, check=False)
            if result.returncode:
                raise AuthorityError("NOVA_RUNTIME_INVENTORY_UNAVAILABLE")
            try:
                inventory = json.loads(result.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError) as exc:
                raise AuthorityError("NOVA_RUNTIME_INVENTORY_RESPONSE_INVALID") from exc
            for key, output in (("release_root", "NOVA_CODE_ROOT"), ("repo_root", "NOVA_REPO_ROOT"),
                ("model", "NOVA_CONFIGURED_MODEL"), ("profile", "NOVA_HERMES_PROFILE"),
                ("provider", "NOVA_CONFIGURED_PROVIDER"), ("route", "NOVA_CONFIGURED_ROUTE")):
                print(output + "=" + str(inventory.get(key) or "NOT_SET"))
            print("NOVA_ENTRYPOINT=" + str(inventory.get("entrypoint") or "UNKNOWN"))
            print("NOVA_PROCESS_IDENTITY=" + str(inventory.get("pid") or "UNKNOWN"))
            print("SECRET_VALUES_PRINTED=NO")
            return 0
        if args.acceptance_evidence:
            query = validate_acceptance_query(args.acceptance_update_id, args.acceptance_start,
                                              args.acceptance_end, args.acceptance_max_records,
                                              args.acceptance_session_id, args.acceptance_message)
            result = read_acceptance_evidence(record["current"], query)
            print(json.dumps(result, separators=(",", ":")))
            return 0
        if args.acceptance_sequence:
            result = read_acceptance_evidence(record["current"], {"mode": "sequence", "max_records": 10})
            print(json.dumps(result, separators=(",", ":")))
            return 0
        if args.nova_denial_inventory:
            result = subprocess.run([*_ssh_base(record["current"]),
                shlex.join(["python3", "-c", NOVA_DENIAL_INVENTORY_SCRIPT])],
                capture_output=True, text=True, timeout=30, check=False)
            if result.returncode:
                raise AuthorityError("NOVA_DENIAL_INVENTORY_UNAVAILABLE")
            try:
                inventory = json.loads(result.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError) as exc:
                raise AuthorityError("NOVA_DENIAL_INVENTORY_RESPONSE_INVALID") from exc
            print("MISSION_DIR=" + str(inventory.get("mission_dir")))
            print("RECENT_FILES_CHECKED=" + str(inventory.get("files_checked")))
            print("RECENT_DENIALS=" + json.dumps(inventory.get("recent_denials", []), separators=(",", ":")))
            print("MESSAGE_CONTENT_PRINTED=NO")
            return 0
        if args.concurrency_inventory:
            result = subprocess.run([*_ssh_base(record["current"]),
                shlex.join(["python3", "-c", NOVA_CONCURRENCY_INVENTORY_SCRIPT])],
                capture_output=True, text=True, timeout=30, check=False)
            if result.returncode:
                raise AuthorityError("NOVA_CONCURRENCY_INVENTORY_UNAVAILABLE")
            try:
                inventory = json.loads(result.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError) as exc:
                raise AuthorityError("NOVA_CONCURRENCY_INVENTORY_RESPONSE_INVALID") from exc
            if inventory.get("error_class"):
                print("CONCURRENCY_INVENTORY_ERROR_CLASS=" + str(inventory.get("error_class")))
                print("CONCURRENCY_INVENTORY_SAFE_STATUS=" + str(inventory.get("safe_status") or "NOT_AVAILABLE"))
                print("CONCURRENCY_INVENTORY_ERROR_LOCATION=" + json.dumps(inventory.get("error_location"), separators=(",", ":")))
                print("CONCURRENCY_CREDENTIAL_SOURCE=" + str(inventory.get("credential_source") or "UNKNOWN"))
                print("CONCURRENCY_SUPABASE_CONFIG_PRESENT=" + ("YES" if inventory.get("url_present") and inventory.get("credential_present") else "NO"))
                print("REQUEST_CONTENT_PRINTED=NO")
                print("CREDENTIAL_VALUES_PRINTED=NO")
                return 1
            print("CONCURRENCY_BACKEND=" + str(inventory.get("backend") or "UNKNOWN"))
            if inventory.get("backend_path"):
                print("CONCURRENCY_BACKEND_PATH=" + str(inventory.get("backend_path")))
            print("CONCURRENCY_NOW_UTC=" + str(inventory.get("now_utc")))
            print("CONCURRENCY_ACTIVE_RESERVATIONS=" + json.dumps(inventory.get("reservations", []), separators=(",", ":")))
            print("CONCURRENCY_APPLICABLE_POLICIES=" + json.dumps(inventory.get("policies", []), separators=(",", ":")))
            print("REQUEST_CONTENT_PRINTED=NO")
            print("CREDENTIAL_VALUES_PRINTED=NO")
            return 0
        if args.release_expired_reservation:
            if not re.fullmatch(r"reserve_[0-9a-f]{32}", args.release_expired_reservation):
                raise AuthorityError("INVALID_RESERVATION_ID_FORMAT")
            result = subprocess.run([*_ssh_base(record["current"]),
                shlex.join(["python3", "-c", EXPIRED_RESERVATION_RELEASE_SCRIPT,
                            args.release_expired_reservation])],
                capture_output=True, text=True, timeout=30, check=False)
            if result.returncode:
                raise AuthorityError("EXPIRED_RESERVATION_RELEASE_NOT_COMPLETED")
            try:
                report = json.loads(result.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError) as exc:
                raise AuthorityError("EXPIRED_RESERVATION_RELEASE_RESPONSE_INVALID") from exc
            print("STALE_RESERVATION_RELEASED=" + ("YES" if report.get("released") else "NO"))
            print("RESERVATION_STATUS_AFTER=" + str(report.get("reservation_status_after") or "UNCHANGED"))
            print("ACTIVE_CODEX_RESERVATIONS_AFTER=" + str(report.get("active_codex_reservations_after", "UNKNOWN")))
            print("RESERVATION_JOB_ID=" + str(report.get("job_id") or "UNKNOWN"))
            print("REQUEST_CONTENT_PRINTED=NO")
            return 0 if report.get("released") else 1
        health = verify_connection(record["current"])
        _print_health(health)
        if args.check:
            print("RESOLVER_CHECK=PASS")
            return 0
        completed = execute_safe(record["current"], args.safe_command)
        print("SAFE_COMMAND=" + args.safe_command)
        print("RESOLVER_EXEC=" + ("PASS" if completed.returncode == 0 else "FAIL"))
        if completed.stdout:
            print(completed.stdout.rstrip())
        if completed.returncode:
            print("REMOTE_EXIT_CODE=" + str(completed.returncode))
            return completed.returncode or 1
        return 0
    except AuthorityError as exc:
        print("ORACLE_CONNECTION_ERROR=" + str(exc), file=sys.stderr)
        print("HISTORICAL_CONNECTORS_AUTO_TRIED=NO", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
