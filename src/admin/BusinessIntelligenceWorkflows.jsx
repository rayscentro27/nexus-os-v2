import React, { useEffect, useState } from 'react'
import { supabase } from '../lib/supabaseClient'
import { BI_BANK_TYPES, BI_NOTEBOOK_TYPES, BUSINESS_INTELLIGENCE_PROMPTS } from '../lib/businessIntelligenceWorkflows'
import FeederOpportunityIntakePanel from '../components/FeederOpportunityIntakePanel'
import '../components/feederIntake.css'
import './businessIntelligenceWorkflows.css'

const TITLES = { BUSINESS_OPPORTUNITY_FEEDER:'Business Opportunity Notebook', BUSINESS_FUNDING_FEEDER:'Business Funding Notebook', BUSINESS_CREATION_BANKABILITY:'Business Creation Notebook' }
const OWNERS = { BUSINESS_OPPORTUNITY_FEEDER:'RESEARCH', BUSINESS_FUNDING_FEEDER:'RESEARCH', BUSINESS_CREATION_BANKABILITY:'RESEARCH' }
const BANK_TITLES = { BUSINESS_HUB:'Business Hub', OPPORTUNITY_BANK:'Opportunity Bank', OPPORTUNITY_COMPONENT_BANK:'Opportunity Component Bank', FUNDING_PRODUCT_BANK:'Funding Product Bank', BUSINESS_CREDIT_PRODUCT_BANK:'Business Credit Product Bank' }
const LABEL = value => String(value || '').replaceAll('_',' ')

export default function BusinessIntelligenceWorkflows() {
  const [notebooks,setNotebooks] = useState([]), [banks,setBanks] = useState([]), [handoffs,setHandoffs] = useState([]), [records,setRecords] = useState([])
  const [selected,setSelected] = useState('BUSINESS_OPPORTUNITY_FEEDER'), [prompt,setPrompt] = useState(''), [message,setMessage] = useState(''), [busy,setBusy] = useState(false)
  const ready = Boolean(supabase)
  async function load() {
    if (!supabase) return
    const [n,b,h,r,p] = await Promise.all([
      supabase.from('business_intelligence_notebooks').select('notebook_type,owner_department,manager_department,master_prompt_version,master_prompt,notebook_reference,notebook_id,status,source_count,last_sync,last_research_run').order('notebook_type').limit(10),
      supabase.from('business_intelligence_banks').select('bank_type,item_count,stale_items,last_sync,last_research_run,status').order('bank_type').limit(10),
      supabase.from('business_intelligence_handoffs').select('id,handoff_type,case_id,from_department,next_owner,status,created_at').order('created_at',{ascending:false}).limit(12),
      supabase.from('business_intelligence_records').select('record_type,status,updated_at').order('updated_at',{ascending:false}).limit(100),
      supabase.from('business_intelligence_project_notebooks').select('notebook_type,status'),
    ])
    if (n.error || b.error || h.error || r.error || p.error) { setMessage('Business Intelligence Supabase read failed. Confirm migration and administrator access.'); return }
    const projectType={BUSINESS_OPPORTUNITY_FEEDER:'BUSINESS_OPPORTUNITY',BUSINESS_FUNDING_FEEDER:'BUSINESS_FUNDING',BUSINESS_CREATION_BANKABILITY:'BUSINESS_CREATION'}
    setNotebooks((n.data || []).map(row=>({...row,active_projects:(p.data||[]).filter(project=>project.notebook_type===projectType[row.notebook_type]&&project.status==='ACTIVE').length}))); setBanks(b.data || []); setHandoffs(h.data || []); setRecords(r.data || [])
  }
  useEffect(() => { void load() }, [])
  useEffect(() => { const row = notebooks.find(item => item.notebook_type === selected); setPrompt(row?.master_prompt || BUSINESS_INTELLIGENCE_PROMPTS[selected]) },[selected,notebooks])
  async function ensureNotebooks() {
    if (!supabase) return
    setBusy(true)
    const rows = BI_NOTEBOOK_TYPES.map(type => ({ notebook_type:type, owner_department:OWNERS[type], manager_department:'RESEARCH', master_prompt_version:'v1', master_prompt:BUSINESS_INTELLIGENCE_PROMPTS[type], status:'ACTIVE' }))
    const {error} = await supabase.from('business_intelligence_notebooks').upsert(rows,{onConflict:'notebook_type',ignoreDuplicates:true})
    setBusy(false); setMessage(error ? 'Notebook templates could not be initialized. Confirm Admin access and migration.' : 'Three reusable workflow templates are initialized in Supabase. NotebookLM references can be connected per template.'); await load()
  }
  async function savePrompt() {
    const row = notebooks.find(item => item.notebook_type === selected)
    if (!row || !supabase) return
    const {error} = await supabase.from('business_intelligence_notebooks').update({master_prompt:prompt,master_prompt_version:`v${Number(String(row.master_prompt_version).replace(/^v/i,'')) + 1}`,last_updated:new Date().toISOString()}).eq('notebook_type',selected)
    setMessage(error ? 'Prompt update failed; no state was changed.' : 'Master prompt saved with a new version.'); await load()
  }
  async function setReference() {
    const row=notebooks.find(item=>item.notebook_type===selected); if(!row||!supabase)return
    const value=window.prompt('NotebookLM notebook URL or ID',row.notebook_reference||''); if(value===null)return
    const {error}=await supabase.from('business_intelligence_notebooks').update({notebook_reference:value.trim()||null,notebook_id:value.trim()||null,last_updated:new Date().toISOString()}).eq('notebook_type',selected)
    setMessage(error?'Notebook reference update failed.':'Notebook reference saved.'); await load()
  }
  async function action(kind) {
    if(kind==='EDIT MASTER PROMPT'){document.getElementById('bi-master-prompt')?.focus();return}
    if(kind==='CHANGE NOTEBOOK REFERENCE'){setReference();return}
    if(kind==='VIEW BANK'){document.getElementById('bi-banks')?.scrollIntoView({behavior:'smooth'});return}
    if(kind==='VIEW RECENT HANDOFFS'){document.getElementById('bi-handoffs')?.scrollIntoView({behavior:'smooth'});return}
    if(kind==='VIEW STALE RECORDS'){setMessage(`${records.filter(item=>item.status==='STALE').length} stale workflow records.`);return}
    if(kind==='REQUEST REFRESH'){setMessage('Refresh request recorded locally. Research owner: RESEARCH; next action: source refresh.');return}
    if(kind==='RUN TEST'){
      if(!supabase)return
      const testId=`BI-TEST-${selected}-${new Date().toISOString().slice(0,10)}`
      const {error}=await supabase.from('business_intelligence_records').upsert({record_type:'WORKFLOW_TEMPLATE_TEST',record_key:testId,status:'TEST_READY',evidence_level:'RESEARCH_REQUIRED',payload:{notebook_type:selected,master_prompt_version:notebooks.find(x=>x.notebook_type===selected)?.master_prompt_version,automated_decision:false},source_references:[],next_action:'Attach a real source or safe profile fixture and execute this template',next_owner:'RESEARCH'},{onConflict:'record_type,record_key'})
      setMessage(error?'Could not persist test case.':`Test case ${testId} persisted; source execution remains the next action.`); await load()
    }
  }
  const active=notebooks.find(row=>row.notebook_type===selected)
  return <section className="bi-workflows" aria-label="Business intelligence workflows">
    <header><div><span>BUSINESS INTELLIGENCE WORKFLOWS</span><h2>Opportunity · Creation · Funding</h2><p>Workflow controls the process. AI recommends; Supabase stores state; Ray or the client decides.</p></div><button disabled={!ready||busy} onClick={()=>void ensureNotebooks()}>{busy?'Working…':'Initialize three templates'}</button></header>
    {!ready && <p role="status">Supabase is not configured in this session.</p>}{message&&<p role="status">{message}</p>}
    <div className="bi-template-grid">{BI_NOTEBOOK_TYPES.map(type=>{const row=notebooks.find(n=>n.notebook_type===type);return <button key={type} className={selected===type?'selected':''} onClick={()=>setSelected(type)}><strong>{TITLES[type]}</strong><small>Owner {row?.owner_department||OWNERS[type]} · Manager {row?.manager_department||'RESEARCH'}</small><small>{row?.notebook_id||'NotebookLM reference not connected'} · prompt {row?.master_prompt_version||'v1'}</small><small>Sources {row?.source_count||0} · active projects {row?.active_projects||0}</small></button>})}</div>
    <div className="bi-section"><div className="bi-section-title"><div><small>MASTER PROMPT · {active?.master_prompt_version||'v1'}</small><h3>{TITLES[selected]}</h3></div><span>{active?.status||'TEMPLATE'}</span></div><textarea id="bi-master-prompt" value={prompt} onChange={e=>setPrompt(e.target.value)} rows={14} aria-label="Master prompt"/><div className="bi-actions">{['VIEW','EDIT MASTER PROMPT','CHANGE NOTEBOOK REFERENCE','RUN TEST','VIEW BANK','VIEW RECENT HANDOFFS','VIEW STALE RECORDS','REQUEST REFRESH'].map(label=><button key={label} onClick={()=>void action(label)}>{label}</button>)}<button className="primary" disabled={!active} onClick={()=>void savePrompt()}>Save master prompt</button></div></div>
    <div className="bi-section" id="bi-banks"><div className="bi-section-title"><div><small>SUPABASE AUTHORITATIVE REGISTRIES</small><h3>Banks and institutional memory</h3></div></div><div className="bi-bank-grid">{BI_BANK_TYPES.map(type=>{const bank=banks.find(b=>b.bank_type===type);const count=records.filter(r=>r.record_type===type).length;return <article key={type}><strong>{BANK_TITLES[type]}</strong><small>{bank?.item_count??count} items · {bank?.stale_items??0} stale</small><small>Last sync {bank?.last_sync?new Date(bank.last_sync).toLocaleString():'not synced'}</small><small>Last research {bank?.last_research_run?new Date(bank.last_research_run).toLocaleString():'not run'}</small></article>})}</div></div>
    <div className="bi-section" id="bi-handoffs"><div className="bi-section-title"><div><small>FORMAL DEPARTMENT TRANSFERS</small><h3>Recent handoffs</h3></div></div>{handoffs.length?handoffs.map(h=><article className="bi-row" key={h.id}><b>{LABEL(h.handoff_type)}</b><span>{h.case_id} · {h.from_department} → {h.next_owner}</span><small>{h.status} · {new Date(h.created_at).toLocaleString()}</small></article>):<p>No handoffs are stored yet.</p>}</div>
    <div className="bi-section"><div className="bi-section-title"><div><small>DECISION BOUNDARIES</small><h3>Recommendations require a human decision</h3></div></div><p>Atlas recommends business opportunities and Nexus funding to Ray. Clyde recommends client funding to the client. Business setup actions requiring approval remain gated. AI cannot terminate, shelve, approve financing, apply, form an entity, or choose a false NAICS code.</p></div>
    <div className="bi-section" id="feeder-notebooks"><FeederOpportunityIntakePanel mode="settings"/></div>
  </section>
}
