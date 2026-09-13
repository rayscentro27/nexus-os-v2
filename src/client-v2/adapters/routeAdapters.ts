import type { V2ViewData } from '../types/v2-models'

export type RouteAdapterState = {
  adapter: string
  backend: string
  hasData: boolean
  permittedActions: string[]
}

/** One read-contract registry for V2 routes; selectors use the existing live view model. */
export function resolveRouteAdapter(path: string, data: V2ViewData): RouteAdapterState {
  const states: Record<string, RouteAdapterState> = {
    '/client-v2/dashboard': { adapter: 'useV2ClientData.dashboard', backend: 'Supabase client context/readiness adapter', hasData: Boolean(data.profile), permittedActions: ['navigate', 'open Clyde'] },
    '/client-v2/credit': { adapter: 'creditRepair + scores', backend: 'Supabase client-scoped credit/readiness data', hasData: data.creditRepair.negativeItems.length > 0 || data.scores.credit > 0, permittedActions: ['view', 'request review'] },
    '/client-v2/utilization': { adapter: 'profile + credit data', backend: 'Supabase client profile/readiness data', hasData: Boolean(data.profile), permittedActions: ['view', 'open guidance'] },
    '/client-v2/documents': { adapter: 'useV2ClientData.documents', backend: 'Supabase document/storage/RLS adapter', hasData: data.documents.requiredCount > 0 || data.documents.uploadedCount > 0, permittedActions: ['upload', 'view status'] },
    '/client-v2/business': { adapter: 'flow + readiness', backend: 'Supabase business/readiness data', hasData: Boolean(data.profile) || data.scores.business > 0, permittedActions: ['view', 'update permitted fields'] },
    '/client-v2/bankability': { adapter: 'readiness + documents', backend: 'Supabase bankability/document data', hasData: Boolean(data.readiness.stages.business_bankability?.requirements?.length || (data.readiness.stages as any).tier1?.requirements?.length), permittedActions: ['view', 'upload supporting document'] },
    '/client-v2/funding-readiness': { adapter: 'useV2ClientData.readiness + funding gate', backend: 'Supabase readiness adapter and governed funding gate', hasData: data.readiness.outstandingRequirements.length > 0 || data.readiness.overallScore > 0, permittedActions: ['request review', 'open funding gate'] },
    '/client-v2/recommendations': { adapter: 'Hermes approved recommendations', backend: 'Supabase-approved client guidance', hasData: data.hermes.recommendations.length > 0, permittedActions: ['view', 'acknowledge'] },
    '/client-v2/review': { adapter: 'flow.reviewStatus', backend: 'Supabase review/case state', hasData: Boolean(data.flow.reviewStatus), permittedActions: ['view', 'request review'] },
    '/client-v2/support': { adapter: 'client AI customer_service gateway', backend: 'Supabase-backed Customer Service path', hasData: true, permittedActions: ['request help', 'request escalation'] },
    '/client-v2/account': { adapter: 'profile + auth context', backend: 'Supabase Auth/client profile', hasData: Boolean(data.profile), permittedActions: ['view', 'update permitted profile fields', 'sign out'] },
    '/client-v2/goals': { adapter: 'customerGoalsAdapter', backend: 'Supabase client readiness context + evidence contract', hasData: Boolean(data.profile), permittedActions: ['view', 'acknowledge next action'] },
    '/client-v2/resources': { adapter: 'approved resource boundary', backend: 'Approved GoClear knowledge source', hasData: data.mode === 'live', permittedActions: ['view'] },
  }
  return states[path] || { adapter: 'client portal live data', backend: 'Existing V2 data adapter', hasData: data.mode === 'live', permittedActions: [] }
}
