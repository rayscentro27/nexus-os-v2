/**
 * Production-safe repo intelligence read model.
 *
 * The operator report under reports/runtime is mutable runtime evidence and
 * is intentionally not a frontend build input.  A governed live source can
 * replace this empty read model later; until then the UI truthfully exposes
 * no production candidates rather than bundling an operator snapshot.
 */
export const repoRegistry = { candidates: [] as Array<Record<string, unknown>> };

export default repoRegistry;
