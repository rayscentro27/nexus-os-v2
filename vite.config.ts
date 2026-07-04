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
        if (path !== '/api/alpha/status' && path !== '/api/alpha/chat') return next();
        res.setHeader('Content-Type','application/json');
        const ollamaUrl=process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';
        let ollama=false, models:string[]=[];
        try { const reply=await fetch(`${ollamaUrl}/api/tags`,{signal:AbortSignal.timeout(1500)}); const data:any=await reply.json(); ollama=reply.ok; models=(data.models||[]).filter((x:any)=>!x.remote_host).map((x:any)=>String(x.name)).sort((a:string,b:string)=>Number(b.startsWith('gemma3:1b'))-Number(a.startsWith('gemma3:1b'))); } catch {}
        const status={activeProvider:'deterministic_local',providers:{deterministic_local:{available:true,reason:'Always-available local fallback'},ollama_local:{available:ollama,reason:ollama?'Local Ollama is reachable':'Local Ollama is not reachable',models},groq:{available:false,reason:'Hosted provider requires a server-side Netlify bridge and GROQ_API_KEY'},openrouter:{available:false,reason:'Hosted provider requires a server-side Netlify bridge and OPENROUTER_API_KEY'}},liveWeb:false,supabase:false,clientData:false};
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
