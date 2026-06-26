export type NexusWatchedResourceType =
  | 'youtube_channel'
  | 'youtube_playlist'
  | 'youtube_video'
  | 'rss_feed'
  | 'affiliate_website'
  | 'affiliate_program_page'
  | 'competitor_website'
  | 'seo_blog'
  | 'credit_repair_resource'
  | 'business_funding_resource'
  | 'business_credit_resource'
  | 'online_business_opportunity_resource'
  | 'ai_tools_directory'
  | 'ai_automation_blog_channel'
  | 'trading_strategy_resource'
  | 'newsletter_archive'
  | 'manual_url_list';

export type NexusWatchedResourceFrequency = 'manual' | 'daily' | 'weekly' | 'monthly';
export type NexusWatchedResourceRisk = 'low' | 'medium' | 'high';
export type NexusWatchedResourceStatus = 'not_checked' | 'checked' | 'new_items_found' | 'blocked' | 'failed';

export interface NexusWatchedResource {
  resource_id: string;
  resource_name: string;
  resource_type: NexusWatchedResourceType;
  resource_url: string;
  category: string;
  department_destination: string;
  watch_frequency: NexusWatchedResourceFrequency;
  enabled: boolean;
  approved_by_ray: boolean;
  risk_level: NexusWatchedResourceRisk;
  scrape_policy: 'metadata_only' | 'rss_only' | 'explicit_url_only' | 'blocked';
  last_checked_at: string | null;
  last_seen_item_id: string | null;
  last_seen_item_url: string | null;
  last_seen_item_published_at: string | null;
  backfill_status: NexusWatchedResourceStatus;
  watch_status: NexusWatchedResourceStatus;
  notes: string;
  created_at: string;
  updated_at: string;
}

export const WATCHED_RESOURCE_TYPES: NexusWatchedResourceType[] = [
  'youtube_channel',
  'youtube_playlist',
  'youtube_video',
  'rss_feed',
  'affiliate_website',
  'affiliate_program_page',
  'competitor_website',
  'seo_blog',
  'credit_repair_resource',
  'business_funding_resource',
  'business_credit_resource',
  'online_business_opportunity_resource',
  'ai_tools_directory',
  'ai_automation_blog_channel',
  'trading_strategy_resource',
  'newsletter_archive',
  'manual_url_list',
];

export const WATCHED_RESOURCE_CATEGORY_ROUTES: Record<string, string> = {
  credit_repair: 'GoClear / Apex',
  business_credit: 'GoClear / Apex',
  business_funding: 'GoClear / Apex',
  grants: 'Opportunity Lab',
  online_business: 'Opportunity Lab',
  ai_tools: 'Ops & Improvements',
  ai_automation: 'Ops & Improvements',
  seo: 'SEO / Marketing',
  affiliate_marketing: 'Opportunity Lab',
  trading_strategies: 'Trading Lab',
  content_monetization: 'SEO / Marketing',
};
