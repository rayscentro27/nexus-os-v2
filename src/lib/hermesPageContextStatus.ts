import type { RouteDecision } from './hermesRouteDecision';

export function answerPageContextQuestion({ message, routeDecision, contextPacket }: { message: string; routeDecision: RouteDecision; contextPacket: { pageContext: Record<string, unknown> | null } }): string {
  const lower = message.toLowerCase();
  const page = contextPacket.pageContext;
  const pageId = String(page?.pageId || page?.sectionName || '').trim();
  const route = String(page?.route || page?.path || '').trim();
  const visibleCount = Array.isArray(page?.visibleItems) ? page.visibleItems.length : 0;
  const hasColorQuestion = /\b(?:color|colour)\b/i.test(lower);
  if (routeDecision.routeId === 'page_connection_status') {
    return `I am running inside the Nexus web app chat UI. ${pageId || route ? `The UI passed current-page metadata${pageId ? ` for ${pageId}` : ''}${route ? ` at ${route}` : ''}.` : 'I do not have current page metadata passed into this chat yet.'} Supabase read access is separate and only applies to supported tables when authentication and RLS permit it.`;
  }
  if (!pageId && !route) {
    if (hasColorQuestion) return 'I do not currently have live page-vision or DOM access from this chat. I cannot see the visual appearance or color of the page. If you need a visual answer, the UI would need to pass page metadata or a screenshot. I do not have that capability here.';
    return 'I do not have current page metadata passed into this chat yet. The UI needs to pass page id, section name, route/path, selected record or card id, and visible panel context. I cannot see the page visually or inspect DOM elements from this chat.';
  }
  if (hasColorQuestion) return `You are on ${pageId || route}. I do not have visual page-vision or DOM color inspection capability from this chat. I can tell you the page identity and metadata, but I cannot determine the visual color scheme. The UI would need to pass color/theme metadata for that.`;
  return `You are on ${pageId || route}.${route && pageId ? ` Route: ${route}.` : ''} I received ${visibleCount} visible item${visibleCount === 1 ? '' : 's'} plus any selected record and available-action metadata supplied by the UI. I cannot see anything outside that passed context — I do not have live page-vision or DOM access.`;
}
