const OBJECT_KEYS = [
  'research',
  'opportunities',
  'handoffs',
  'departments',
  'ray_decisions',
  'youtube',
  'seo',
]

/**
 * The authenticated live projection may legitimately be partial while the
 * runtime snapshot is loading or unavailable. Keep that boundary explicit so
 * Admin surfaces render unavailable values instead of throwing.
 */
export function normalizeAdminState(baseState, candidate) {
  const base = baseState && typeof baseState === 'object' ? baseState : {}
  const incoming = candidate && typeof candidate === 'object' ? candidate : {}
  const normalized = { ...base, ...incoming }
  OBJECT_KEYS.forEach((key) => {
    normalized[key] = {
      ...(base[key] && typeof base[key] === 'object' ? base[key] : {}),
      ...(incoming[key] && typeof incoming[key] === 'object' ? incoming[key] : {}),
    }
  })
  normalized.ray_decisions.items = Array.isArray(normalized.ray_decisions.items) ? normalized.ray_decisions.items : []
  normalized.recent_findings = Array.isArray(normalized.recent_findings) ? normalized.recent_findings : []
  normalized.campaign_list = Array.isArray(normalized.campaign_list) ? normalized.campaign_list : []
  normalized.pipeline = Array.isArray(normalized.pipeline) ? normalized.pipeline : []
  return normalized
}
