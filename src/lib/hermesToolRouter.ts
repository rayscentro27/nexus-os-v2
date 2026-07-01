import type { RoutedHermesIntent } from './hermesIntentRouter';

export interface HermesToolDecision { tool: 'none'|'page_context'|'supabase'|'operations_reports'|'second_brain'|'web_search'|'approval_gate'; allowed: boolean; requiresApproval: boolean; }
export function selectHermesTool(route: RoutedHermesIntent): HermesToolDecision {
  switch(route.route){
    case 'casual': case 'capability_status': return {tool:'none',allowed:true,requiresApproval:false};
    case 'page_context': return {tool:'page_context',allowed:true,requiresApproval:false};
    case 'nexus_supabase': return {tool:'supabase',allowed:true,requiresApproval:false};
    case 'operations': return {tool:'operations_reports',allowed:true,requiresApproval:false};
    case 'reports_memory': return {tool:'second_brain',allowed:true,requiresApproval:false};
    case 'web_research': return {tool:'web_search',allowed:false,requiresApproval:true};
    case 'execution': return {tool:'approval_gate',allowed:false,requiresApproval:true};
    default:return {tool:'none',allowed:true,requiresApproval:false};
  }
}
