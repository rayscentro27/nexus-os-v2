import type { RouteDecision } from './hermesRouteDecision';

export function answerPageContextQuestion({ message, routeDecision, contextPacket }: { message: string; routeDecision: RouteDecision; contextPacket: { pageContext: Record<string, unknown> | null } }): string {
  void message;
  const page = contextPacket.pageContext;
  const pageId = String(page?.pageId || page?.sectionName || '').trim();
  const route = String(page?.route || page?.path || '').trim();
  const visibleCount = Array.isArray(page?.visibleItems) ? page.visibleItems.length : 0;
  if (routeDecision.routeId === 'page_connection_status') {
    return `I am running inside the Nexus web app chat UI. ${pageId || route ? `The UI passed current-page metadata${pageId ? ` for ${pageId}` : ''}${route ? ` at ${route}` : ''}.` : 'I do not have current page metadata passed into this chat yet.'} Supabase read access is separate and only applies to supported tables when authentication and RLS permit it.`;
  }
  if (!pageId && !route) return 'I do not have current page metadata passed into this chat yet. The UI needs to pass page id, section name, route/path, selected record or card id, and visible panel context.';
  return `You are on ${pageId || route}.${route && pageId ? ` Route: ${route}.` : ''} I received ${visibleCount} visible item${visibleCount === 1 ? '' : 's'} plus any selected record and available-action metadata supplied by the UI. I cannot see anything outside that passed context.`;
}
