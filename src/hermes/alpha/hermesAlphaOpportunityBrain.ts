export function answerAsHermesAlpha(prompt:string) {
  const q=prompt.toLowerCase(); let answer="Alpha recommends scoring one small opportunity from existing local evidence and drafting a controlled experiment for Ray Review.";
  if(q.includes("money")||q.includes("opportun")) answer="Top local-first paths: readiness-review SEO content, fundability checklist lead magnet, compliant affiliate comparisons, and research-backed newsletter drafts. Revenue and traffic are unproven.";
  else if(q.includes("api")||q.includes("affiliate")) answer="Missing analytics, SEO, model-provider, and affiliate inputs limit validation. Use placeholders until Ray supplies approved accounts and keys.";
  else if(q.includes("test next")) answer="Test one SEO candidate and one landing-page draft against a defined evidence and conversion-measurement plan.";
  else if(q.includes("blocked")||q.includes("disabled")) answer="Alpha cannot access Supabase or client data, publish, trade, or mutate production. Those boundaries are intentional.";
  else if(q.includes("report")) answer="Review the Alpha opportunity brief, SEO candidate list, trading research plan, and marketing sample index.";
  return { brain:"Hermes Alpha" as const, role:"opportunity/research brain", answer, tone:"experimental opportunity-focused", noSupabaseUsed:true as const, clientDataUsed:false as const, externalActionPerformed:false as const, rayReviewRequired:true };
}
