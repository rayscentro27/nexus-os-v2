import brainIndex from '../../reports/hermes_second_brain_index_latest.json';
import operations from '../../reports/nexus_operations_status_latest.json';
import liveSeed from '../../reports/live_seed_execution_latest.json';

export function answerMemoryQuestion(message:string):string{
  const text=message.toLowerCase(); const items=brainIndex.items;
  const selected=items.filter(item=>{
    const hay=`${item.title} ${item.summary} ${item.tags.join(' ')}`.toLowerCase();
    if(/codex|commit|pushed|changed|yesterday/.test(text)) return /commit|git|codex|fix|audit/.test(hay);
    if(/seed/.test(text)) return item.source_type==='seed_report';
    if(/fail|block/.test(text)) return /fail|block|incident/.test(hay);
    return item.freshness==='fresh';
  }).slice(0,5);
  const seedSummary=(liveSeed as {summary?:string;status?:string}).summary||(liveSeed as {status?:string}).status||'seed report is present but has no concise status';
  const detail=selected.map(x=>`${x.title}: ${x.summary}`).join('\n- ');
  return `Based on the local second-brain index (${brainIndex.item_count} bounded sources, generated ${brainIndex.generated_at}) and operations audit ${operations.checked_at}:\n- ${detail||'No matching fresh memory item was found.'}${/seed/.test(text)?`\n- Live seed: ${seedSummary}`:''}\n\nThis is report-backed memory, not a complete transcript. Verify stale source timestamps before acting.`;
}
