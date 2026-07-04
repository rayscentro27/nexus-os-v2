import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

function nexusLocalBridges() {
  return {
    name: 'nexus-local-static-and-alpha-bridge',
    configureServer(server: any) {
      server.middlewares.use(async (req: any, res: any, next: any) => {
        const path = String(req.url || '').split('?')[0];
        if (path === '/got-funding' || path === '/got-funding/') {
          try { res.statusCode=200; res.setHeader('Content-Type','text/html; charset=utf-8'); res.end(await readFile(resolve(process.cwd(),'public/got-funding/index.html'))); } catch { next(); }
          return;
        }
        if (path !== '/api/alpha/status' && path !== '/api/alpha/chat' && path !== '/api/alpha/search') return next();
        res.setHeader('Content-Type','application/json');
        if(path==='/api/alpha/search'){
          let raw='';for await(const chunk of req)raw+=chunk;let body:any={};try{body=JSON.parse(raw)}catch{}const query=String(body.query||'').trim().slice(0,500);if(!query){res.statusCode=400;res.end(JSON.stringify({error:'query_required',status:'failed',provider:'duckduckgo_keyless'}));return}
          const base=process.env.ALPHA_SEARXNG_URL;if(!base){res.statusCode=503;res.end(JSON.stringify({error:'search_connector_missing',status:'connector_missing',provider:'none',results:[]}));return}try{const reply=await fetch(`${base.replace(/\/$/,'')}/search?q=${encodeURIComponent(query)}&format=json`,{signal:AbortSignal.timeout(5000),headers:{accept:'application/json'}});const data:any=await reply.json();const results=(data.results||[]).slice(0,5).map((item:any)=>{let domain='';try{domain=new URL(item.url).hostname}catch{}return {title:String(item.title||'Untitled').slice(0,160),url:String(item.url||''),domain,snippet:String(item.content||'').slice(0,500),provider:'searxng',timestamp:new Date().toISOString()}});res.statusCode=reply.ok?200:502;res.end(JSON.stringify({results,provider:'searxng',status:reply.ok?'searched':'failed',count:results.length}));}catch{res.statusCode=502;res.end(JSON.stringify({error:'searxng_unavailable',status:'failed',provider:'searxng',results:[]}))}return;
        }
        const ollamaUrl=process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';
        let ollama=false, models:string[]=[];
        try { const reply=await fetch(`${ollamaUrl}/api/tags`,{signal:AbortSignal.timeout(1500)}); const data:any=await reply.json(); ollama=reply.ok; models=(data.models||[]).filter((x:any)=>!x.remote_host).map((x:any)=>String(x.name)).sort((a:string,b:string)=>Number(b.startsWith('gemma3:1b'))-Number(a.startsWith('gemma3:1b'))); } catch {}
        const status={activeProvider:'deterministic_local',providers:{deterministic_local:{available:true,reason:'Always-available local fallback'},ollama_local:{available:ollama,reason:ollama?'Local Ollama is reachable':'Local Ollama is not reachable',models},groq:{available:false,reason:'Hosted provider requires the deployed Netlify bridge'},openrouter:{available:false,reason:'Hosted provider requires the deployed Netlify bridge'}},liveWeb:Boolean(process.env.ALPHA_SEARXNG_URL),webSearch:{available:Boolean(process.env.ALPHA_SEARXNG_URL),provider:process.env.ALPHA_SEARXNG_URL?'searxng':'none',reason:process.env.ALPHA_SEARXNG_URL?'SearXNG backend configured':'No verified backend search connector'},supabase:false,clientData:false};
        if(path==='/api/alpha/status'){res.end(JSON.stringify(status));return;}
        let raw=''; for await(const chunk of req) raw+=chunk; let body:any={}; try{body=JSON.parse(raw)}catch{}
        if(body.provider!=='ollama_local'||!ollama){res.statusCode=503;res.end(JSON.stringify({error:'selected_provider_unavailable',status}));return;}
        const model=String(body.model||models[0]||'qwen2.5:0.5b');
        const system='You are Hermes Alpha, Ray strategy and opportunity partner. Use plain language. Never claim current web facts, use client data, access Supabase, or execute actions. State uncertainty. Never guarantee funding, credit, approvals, or trading results.';
        try{const reply=await fetch(`${ollamaUrl}/api/chat`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({model,stream:false,messages:[{role:'system',content:system},{role:'user',content:String(body.prompt||'')}]}),signal:AbortSignal.timeout(60000)});const data:any=await reply.json();res.statusCode=reply.ok?200:502;res.end(JSON.stringify({provider:'ollama_local',model,text:data.message?.content||'',externalCallPerformed:false,noSupabaseUsed:true,clientDataUsed:false}));}catch{res.statusCode=502;res.end(JSON.stringify({error:'ollama_request_failed'}));}
      });
    }
  };
}

export default defineConfig({
  plugins: [nexusLocalBridges(), react()],
  build: { outDir: 'dist' },
});
