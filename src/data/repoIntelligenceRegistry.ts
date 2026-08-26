/**
 * Production-safe repo intelligence read model.
 *
 * The operator report under reports/runtime is mutable runtime evidence and
 * is intentionally not a frontend build input.  A governed live source can
 * replace this empty read model later; until then the UI truthfully exposes
 * no production candidates rather than bundling an operator snapshot.
 */
// This is a stable, governed proposal—not runtime evidence and not an
// activation. Keeping the candidate in the build-safe registry preserves the
// operator's review queue without bundling mutable reports or credentials.
export const repoRegistry = {
  candidates: [{
    candidate_id: 'github_mcp_server',
    repository_owner: 'github',
    repository_name: 'github-mcp-server',
    canonical_url: 'https://github.com/github/github-mcp-server',
    source_type: 'OPEN_SOURCE_OR_EXTERNAL_TOOL',
    proposed_disposition: 'INTEGRATE_AS_CONTROLLED_EXTERNAL_TOOL',
    department_owner: 'engineering',
    exact_pattern_under_review: 'Governed GitHub read capability for repository intelligence',
    business_value: 'Read-only repository context for bounded engineering review',
    privacy_risk: 'Repository access must remain scoped and client data prohibited',
    license: 'UNKNOWN',
    ray_decision: 'PENDING',
    evidence_links: ['https://github.com/github/github-mcp-server'],
  }] as Array<Record<string, unknown>>,
};

export default repoRegistry;
