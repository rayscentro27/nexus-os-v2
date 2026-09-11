export type V2RouteContract = {
  purpose: string
  realData: string[]
  actions: string[]
  backend: string[]
  access: string
  mobile: string
  visualDesignPending: boolean
}

export const V2_ROUTE_CONTRACTS: Record<string, V2RouteContract> = {
  '/client-v2/dashboard': { purpose: 'Summary and navigation', realData: ['client identity', 'readiness summary', 'next actions', 'recent activity'], actions: ['navigate', 'open Clyde'], backend: ['client data adapter', 'RLS client context'], access: 'authenticated client or FREE_GUEST', mobile: 'single-column summary; no workflow duplication', visualDesignPending: true },
  '/client-v2/credit': { purpose: 'Credit profile and status', realData: ['credit profile', 'review state'], actions: ['view', 'request review'], backend: ['Supabase credit/readiness contracts'], access: 'authenticated client', mobile: 'stacked status sections', visualDesignPending: false },
  '/client-v2/utilization': { purpose: 'Credit utilization details', realData: ['utilization data'], actions: ['view', 'open guidance'], backend: ['Supabase client-scoped data'], access: 'authenticated client', mobile: 'no wide tables', visualDesignPending: false },
  '/client-v2/documents': { purpose: 'Document requirements and uploads', realData: ['required', 'missing', 'received', 'review state'], actions: ['upload', 'view status'], backend: ['Supabase storage/RLS', 'document records'], access: 'authenticated client or FREE_GUEST', mobile: 'thumb-friendly upload control', visualDesignPending: true },
  '/client-v2/business': { purpose: 'Business setup foundation', realData: ['business profile', 'setup tasks'], actions: ['update permitted fields'], backend: ['Supabase client profile/RLS'], access: 'authenticated client or FREE_GUEST', mobile: 'one form section at a time', visualDesignPending: false },
  '/client-v2/bankability': { purpose: 'Business bankability requirements', realData: ['bankability tasks', 'document state'], actions: ['view', 'upload supporting document'], backend: ['readiness and document contracts'], access: 'authenticated client or FREE_GUEST', mobile: 'stacked requirements', visualDesignPending: false },
  '/client-v2/funding-readiness': { purpose: 'Readiness blockers and next steps', realData: ['readiness result', 'blockers', 'recommendations'], actions: ['request review', 'open funding gate'], backend: ['readiness adapter', 'funding gate'], access: 'authenticated client or FREE_GUEST; execution gated', mobile: 'single primary next action', visualDesignPending: true },
  '/client-v2/recommendations': { purpose: 'Approved client recommendations', realData: ['approved recommendations'], actions: ['view', 'acknowledge'], backend: ['Supabase recommendations/RLS'], access: 'authenticated client', mobile: 'readable list; no dense grid', visualDesignPending: false },
  '/client-v2/resources': { purpose: 'Approved educational resources', realData: ['approved resources'], actions: ['view'], backend: ['approved knowledge source'], access: 'authenticated client or FREE_GUEST', mobile: 'single-column reading', visualDesignPending: false },
  '/client-v2/review': { purpose: 'Review request and status', realData: ['review status', 'case status'], actions: ['request review', 'view status'], backend: ['review intake/RLS'], access: 'authenticated client', mobile: 'short form sections', visualDesignPending: false },
  '/client-v2/support': { purpose: 'Customer Service help and cases', realData: ['case status', 'communication history'], actions: ['request help', 'request escalation'], backend: ['Customer Service gateway', 'Supabase cases'], access: 'authenticated client', mobile: 'conversation-first', visualDesignPending: false },
  '/client-v2/account': { purpose: 'Account and access state', realData: ['profile', 'access tier', 'security state'], actions: ['update permitted profile fields', 'sign out'], backend: ['Supabase Auth/profile/RLS'], access: 'authenticated client', mobile: 'stacked account sections', visualDesignPending: false },
}
