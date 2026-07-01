import { routeHermesIntent, type RoutedHermesIntent } from './hermesIntentRouter';
import { selectHermesTool } from './hermesToolRouter';

export interface HermesOrchestration { routing:RoutedHermesIntent; tool:ReturnType<typeof selectHermesTool>; shouldQuerySupabase:boolean; shouldQueryWeb:boolean; }
export function orchestrateHermes(message:string, hasPageContext=false):HermesOrchestration{
  const routing=routeHermesIntent(message,hasPageContext); const tool=selectHermesTool(routing);
  return {routing,tool,shouldQuerySupabase:tool.tool==='supabase'||routing.intent==='run_nexus_audit',shouldQueryWeb:tool.tool==='web_search'&&tool.allowed};
}
