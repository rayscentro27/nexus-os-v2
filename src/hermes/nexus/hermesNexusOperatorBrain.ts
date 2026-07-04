export function answerAsNexusHermes(prompt: string) {
  const q=prompt.toLowerCase(); let answer="Nexus internal operations are available for local tests; external actions remain approval-gated.";
  if(q.includes("ready")) answer="Ready: local command center, research artifacts, GoClear hypothetical readiness, draft generation, reports, and Ray Review preparation.";
  else if(q.includes("blocked")||q.includes("disabled")) answer="Blocked: real client data, external send/publish/charge, automated applications or disputes, production writes without a decision gate, and funded/live trading.";
  else if(q.includes("test next")) answer="Test the local operational cycle first, then inspect the generated Ray Review drafts and connector blockers.";
  else if(q.includes("api")||q.includes("affiliate")) answer="Review the Affiliate/API Setup Center; it reports presence only and never exposes secret values.";
  else if(q.includes("report")) answer="Review the operational cycle, connector audit, readiness scorecard, blockers, Alpha brief, and Ray Review queue.";
  else if(q.includes("automat")) answer="Level 1 local reporting jobs can run safely. External actions require approval; prohibited actions remain blocked.";
  return { brain:"Nexus Hermes" as const, role:"local/operator brain", answer, tone:"concise operational", rayReviewRequired:q.includes("approve")||q.includes("production"), externalActionPerformed:false as const, clientDataUsed:false as const };
}
