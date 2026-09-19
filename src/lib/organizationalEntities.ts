export type NexusEntityType = 'DEPARTMENT' | 'AGENT' | 'ENGINE' | 'EXECUTIVE' | 'CAPABILITY' | 'SERVICE'

export interface NexusOrganizationalEntity { entity_id: string; name: string; entity_type: NexusEntityType; mission: string; owner: string; status: string; current_work: string; handoffs: string[]; capabilities: string[]; parent_department?: string }

const entityRows: Array<[string, string, NexusEntityType, string, string, string, string, string[], string[]]> = [
  ['research', 'Research', 'DEPARTMENT', 'Discover, investigate, cross-check, and preserve evidence.', 'Research AI', 'ACTIVE', 'Current funding-readiness investigation', ['Alpha'], ['Last30Days', 'SEO Engine', 'web acquisition']],
  ['marketing', 'Marketing', 'DEPARTMENT', 'Turn qualified evidence into bounded audience and channel work.', 'Marketing coordinator', 'ACTIVE', 'GoClear funding-readiness draft', ['Creative', 'SEO'], ['campaign planning']],
  ['creative', 'Creative', 'DEPARTMENT', 'Produce governed campaign and communication artifacts.', 'Creative coordinator', 'ACTIVE', 'Social and email drafts', ['Compliance'], ['creative studio']],
  ['systems', 'Systems', 'DEPARTMENT', 'Maintain platform, runtime, and integration reliability.', 'Systems', 'ACTIVE', 'Admin and runtime controls', [], ['runtime operations']],
  ['customer_service', 'Customer Service', 'DEPARTMENT', 'Own customer-facing support and FAQ work.', 'Customer Service', 'READY', 'Funding-readiness FAQ', [], ['support workflows']],
  ['finance', 'Finance', 'DEPARTMENT', 'Own financial controls and measured revenue operations.', 'Finance', 'READY', 'No active cycle assignment', [], ['finance controls']],
  ['funding', 'Funding', 'DEPARTMENT', 'Review funding-readiness evidence and lender boundaries.', 'Clyde/Funding', 'ACTIVE', 'Funding claim guardrails', ['Compliance'], ['funding evidence']],
  ['nova', 'Nova', 'EXECUTIVE', 'Executive interface and decision context for Ray.', 'Hermes/Nova runtime', 'ACTIVE', 'Decision and cycle visibility', ['Ray'], ['executive reporting']],
  ['alpha', 'Alpha', 'AGENT', 'Challenge Research evidence and route qualified intelligence.', 'Alpha model runtime', 'ACTIVE', 'Current package review', ['Research', 'Clyde/Funding'], ['model-backed review']],
  ['hermes', 'Hermes', 'AGENT', 'Route governed conversations and operational context.', 'Hermes runtime', 'ACTIVE', 'Admin and executive routing', ['Nova'], ['governed routing']],
  ['opportunity_engine', 'Opportunity Engine', 'ENGINE', 'Structure opportunities from supported evidence; never replace Research.', 'Research/Alpha handoff', 'ACTIVE', 'Evidence-linked opportunity review', ['Research', 'Alpha'], ['opportunity projection']],
  ['clyde', 'Clyde', 'SERVICE', 'Provide funding-readiness support within its governed client boundary.', 'Funding department', 'READY', 'Available when assigned', ['Funding'], ['client funding guidance']],
  ['last30days', 'Last30Days', 'CAPABILITY', 'Acquire current public demand signals for Research.', 'Research', 'HEALTHY', 'Acquisition tool', ['Research'], ['demand discovery']],
  ['seo_engine', 'SEO Engine', 'CAPABILITY', 'Produce bounded search and technical evidence for Research.', 'Research', 'HEALTHY', 'Acquisition tool', ['Research'], ['SEO analysis']],
  ['youtube_pipeline', 'YouTube Pipeline', 'CAPABILITY', 'Acquire and process eligible video evidence.', 'Research', 'DEGRADED', 'Fallback-aware acquisition', ['Research'], ['video evidence']],
  ['approval_service', 'Governed Approval Service', 'SERVICE', 'Persist and resolve human decisions with receipts.', 'Executive / Admin', 'ACTIVE', 'Campaign approval pending', ['Ray', 'Nova'], ['approval persistence']],
]
export const organizationalEntities: NexusOrganizationalEntity[] = entityRows.map(([entity_id, name, entity_type, mission, owner, status, current_work, handoffs, capabilities]) => ({ entity_id, name, entity_type, mission, owner, status, current_work, handoffs, capabilities }))

export function entitiesByType(type: NexusEntityType) { return organizationalEntities.filter(entity => entity.entity_type === type) }
export function formatEntityList(type: NexusEntityType) { return entitiesByType(type).map(entity => `${entity.name} (${entity.status}) — ${entity.mission}`).join('\n') }
