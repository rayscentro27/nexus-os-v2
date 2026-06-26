export interface ContentTestResult {
  content_title: string;
  channel: string;
  target_keyword: string;
  offer: string;
  affiliate_program: string;
  published_url: string;
  status: 'draft' | 'published' | 'paused' | 'complete' | 'blocked';
  impressions: number;
  clicks: number;
  leads: number;
  conversions: number;
  revenue: number;
  estimated_value: number;
  next_action: string;
}
