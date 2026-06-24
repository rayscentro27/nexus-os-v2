import { listTable, listTableDetailed, type Row, type TableQueryResult } from '../services/db';
import { containsSensitive } from './dataScopes';

const LANDING_PAGE_URL = 'https://nexusv20.netlify.app/goclear-apex-readiness.html';
const MAX_COPY = 1800;

export interface ApprovalPreview {
  assetType: string | null;
  platform: string | null;
  targetAccount: string | null;
  caption: string | null;
  body: string | null;
  cta: string | null;
  previewUrl: string | null;
  assetUrl: string | null;
  imageUrl: string | null;
  videoUrl: string | null;
  thumbnailUrl: string | null;
  landingPageUrl: string | null;
  packageType: string | null;
  packagePath: string | null;
  packageCopy: string | null;
  riskNotes: string[];
  score: string | null;
  missingFields: string[];
}

export interface ApprovalReviewItem {
  id: string;
  title: string;
  itemType: string;
  status: string;
  lane: string;
  summary: string;
  createdAt: string | null;
  preview: ApprovalPreview;
  recommendation: string;
}

export interface ApprovalReviewResult {
  query: TableQueryResult;
  items: ApprovalReviewItem[];
}

const SAFE_KEYS = new Set([
  'asset_type', 'preview_url', 'asset_url', 'image_url', 'video_url', 'thumbnail_url',
  'caption', 'copy', 'body', 'text', 'hook', 'platform', 'target_account', 'account_name',
  'account_id', 'cta', 'cta_url', 'landing_page_url', 'package_type', 'package_path',
  'package_id', 'content_blocks', 'sensitivity', 'requires_approval', 'forbidden_actions',
  'risk_flags', 'compliance_status', 'compliance_notes', 'score_summary', 'recommended_use',
]);

function str(v: unknown, max = MAX_COPY): string | null {
  if (v == null) return null;
  const s = String(v).trim();
  if (!s || containsSensitive(s)) return null;
  return s.slice(0, max);
}

function arr(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.map((x) => str(x, 160)).filter((x): x is string => Boolean(x));
}

function payloadOf(row: Row): Row {
  return (row.payload && typeof row.payload === 'object') ? row.payload as Row : {};
}

function sanitizedPayload(row: Row): Row {
  const p = payloadOf(row);
  const out: Row = {};
  for (const [k, v] of Object.entries(p)) {
    if (!SAFE_KEYS.has(k)) continue;
    if (Array.isArray(v)) out[k] = arr(v);
    else if (typeof v === 'object' && v) out[k] = v;
    else out[k] = str(v);
  }
  return out;
}

function approvalBasePreview(a: Row): ApprovalPreview {
  const p = sanitizedPayload(a);
  const score = p.score_summary && typeof p.score_summary === 'object'
    ? `${(p.score_summary as Row).overall ?? 'unknown'} · ${(p.score_summary as Row).decision ?? 'score'}`
    : null;
  const platform = str(p.platform ?? (a.item_type === 'facebook_publish_enablement' ? 'facebook' : null), 80);
  const caption = str(p.caption ?? p.copy ?? p.body ?? p.text);
  const landing = str(p.landing_page_url ?? (a.item_type === 'facebook_publish_enablement' ? LANDING_PAGE_URL : null), 240);
  const missingFields = [];
  if (!caption && !p.preview_url && !landing) missingFields.push('caption/body/preview_url');
  if (!platform && /post|caption|publish|social|facebook|instagram|tiktok|reel/i.test(String(a.item_type))) missingFields.push('platform');
  return {
    assetType: str(p.asset_type ?? a.item_type, 80),
    platform,
    targetAccount: str(p.target_account ?? p.account_name ?? p.account_id, 120),
    caption,
    body: str(p.body ?? p.text),
    cta: str(p.cta ?? p.cta_url, 240),
    previewUrl: str(p.preview_url, 240),
    assetUrl: str(p.asset_url, 240),
    imageUrl: str(p.image_url, 240),
    videoUrl: str(p.video_url, 240),
    thumbnailUrl: str(p.thumbnail_url, 240),
    landingPageUrl: landing,
    packageType: str(p.package_type ?? (a.item_type === 'publish_package' ? 'manual_publish_package' : null), 120),
    packagePath: str(p.package_path, 240),
    packageCopy: null,
    riskNotes: [
      ...arr(p.risk_flags),
      str(p.compliance_status, 80),
      str(p.compliance_notes, 240),
    ].filter((x): x is string => Boolean(x)),
    score,
    missingFields,
  };
}

async function enrichApproval(a: Row, preview: ApprovalPreview): Promise<ApprovalPreview> {
  if (a.item_type === 'publish_package' && a.item_id) {
    const pkg = (await listTable('publish_readiness_packages', { eq: ['id', String(a.item_id)], limit: 1 }))[0];
    if (pkg) {
      preview.packageCopy = str(pkg.final_post_copy);
      preview.cta = preview.cta ?? str(pkg.cta, 240);
      preview.platform = preview.platform ?? str(pkg.platform, 80);
      preview.packageType = preview.packageType ?? 'manual_publish_package';
      preview.riskNotes = [...preview.riskNotes, ...arr(pkg.risk_flags), str(pkg.compliance_status, 80)].filter((x): x is string => Boolean(x));
      preview.missingFields = preview.missingFields.filter((f) => f !== 'caption/body/preview_url');
    }
  }
  const linkedPost = (await listTable('social_posts', { eq: ['approval_id', String(a.id)], limit: 1 }))[0];
  if (linkedPost) {
    preview.caption = preview.caption ?? str(linkedPost.content);
    preview.platform = preview.platform ?? str(linkedPost.platform, 80);
    preview.assetUrl = preview.assetUrl ?? str(linkedPost.media_url, 240);
    preview.targetAccount = preview.targetAccount ?? str((payloadOf(linkedPost)).account_name, 120);
    preview.missingFields = preview.missingFields.filter((f) => f !== 'caption/body/preview_url' && f !== 'platform');
  }
  return preview;
}

function recommendationFor(a: Row, p: ApprovalPreview): string {
  if (a.item_type === 'facebook_publish_enablement') {
    return 'Approve only after Ray confirms the exact post copy and live landing page. Approval alone must not publish or set publish_enabled automatically.';
  }
  if (p.riskNotes.some((r) => /blocked|failed|risk/i.test(r))) return 'Request changes before approval.';
  if (p.caption || p.packageCopy || p.landingPageUrl) return 'Review the preview copy/link, then approve only if it matches the GoClear readiness positioning.';
  return 'Preview data is thin. Request changes or add preview metadata before approving.';
}

export async function loadPendingApprovalReviews(limit = 20): Promise<ApprovalReviewResult> {
  const query = await listTableDetailed('approvals', { limit, eq: ['status', 'pending'] });
  const items: ApprovalReviewItem[] = [];
  for (const a of query.data) {
    const preview = await enrichApproval(a, approvalBasePreview(a));
    items.push({
      id: String(a.id),
      title: str(a.title ?? a.item_type, 180) ?? 'Untitled approval',
      itemType: String(a.item_type ?? 'approval'),
      status: String(a.status ?? 'unknown'),
      lane: String(a.lane ?? 'system'),
      summary: str(a.summary, 500) ?? '',
      createdAt: str(a.created_at, 80),
      preview,
      recommendation: recommendationFor(a, preview),
    });
  }
  return { query, items };
}

export function findApprovalReview(items: ApprovalReviewItem[], ref: string): ApprovalReviewItem | null {
  const s = ref.trim().toLowerCase();
  const num = /^#?(\d+)$/.exec(s)?.[1];
  if (num) return items[Number(num) - 1] ?? null;
  return items.find((item) => item.id.toLowerCase().startsWith(s.replace(/^approval\s+/, ''))) ?? null;
}

export function isApprovalReviewPrompt(text: string): boolean {
  const t = (text || '').toLowerCase();
  return /\b(approvals? waiting|pending approvals?|review (my |all )?approvals?|walk me through approvals?|show me approval|what needs my approval|what should i approve|approval queue|approve queue)\b/.test(t);
}

export function isApprovalDirectAction(text: string): boolean {
  return /\b(approve|reject|decline|request changes?)\s+(#?\d+|approval\s+[a-f0-9-]{6,})\b/i.test(text || '');
}

export function approvalRefFromPrompt(text: string): string | null {
  const t = text || '';
  return /(?:show|review|open)\s+(?:approval\s+)?(#?\d+|[a-f0-9-]{6,})/i.exec(t)?.[1] ?? null;
}

export function formatApprovalReviewList(items: ApprovalReviewItem[]): string {
  if (!items.length) return 'No pending approvals are visible for this session.';
  const lines = [`You have ${items.length} pending approval${items.length === 1 ? '' : 's'} visible. I can review them, but I cannot approve, reject, publish, send, trade, or set publish_enabled.`];
  items.forEach((item, i) => {
    const p = item.preview;
    const preview = p.caption || p.packageCopy || p.landingPageUrl || 'Preview not available';
    lines.push(`\n${i + 1}. ${item.title}\nType: ${item.itemType}\nStatus: ${item.status}\nTarget: ${p.platform ?? 'unknown'}${p.targetAccount ? ` · ${p.targetAccount}` : ''}\nSummary: ${item.summary || 'No summary provided.'}\nPreview: ${preview.slice(0, 420)}\nRisk: ${p.riskNotes.join('; ') || 'No extra risk flags shown.'}\nRecommendation: ${item.recommendation}\nNext action: Review it in the Approvals tab. Say "review #${i + 1}" for more detail.`);
  });
  return lines.join('\n');
}

export function formatApprovalReviewDetail(item: ApprovalReviewItem, index?: number): string {
  const p = item.preview;
  const copy = p.caption || p.packageCopy || p.body || 'Preview not available.';
  const media = [p.imageUrl && `Image: ${p.imageUrl}`, p.videoUrl && `Video: ${p.videoUrl}`, p.thumbnailUrl && `Thumbnail: ${p.thumbnailUrl}`, p.assetUrl && `Asset: ${p.assetUrl}`, p.previewUrl && `Preview: ${p.previewUrl}`, p.landingPageUrl && `Landing page: ${p.landingPageUrl}`].filter(Boolean).join('\n');
  const missing = p.missingFields.length ? `\nMissing preview fields: ${p.missingFields.join(', ')}` : '';
  return `${index ? `Approval #${index}: ` : ''}${item.title}
Type: ${item.itemType}
Status: ${item.status}
Created: ${item.createdAt ?? 'unknown'}
Target: ${p.platform ?? 'unknown'}${p.targetAccount ? ` · ${p.targetAccount}` : ''}
Summary: ${item.summary || 'No summary provided.'}
Copy/preview:
${copy}
${p.cta ? `\nCTA: ${p.cta}` : ''}
${media ? `\n${media}` : ''}
Risk notes: ${p.riskNotes.join('; ') || 'No extra risk flags shown.'}
Recommendation: ${item.recommendation}
Next action: Use the Approvals tab buttons. I cannot approve, reject, publish, send, trade, deploy, or set publish_enabled for you.${missing}`;
}
