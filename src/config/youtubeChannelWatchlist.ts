export interface YouTubeChannelWatchlistItem {
  channel_name: string;
  channel_url: string;
  channel_id: string | null;
  topic_category: string;
  monetization_relevance: number;
  approved_by_ray: boolean;
  enabled: boolean;
  risk_level: 'low' | 'medium' | 'high';
  last_checked_at: string | null;
  last_seen_video_url: string | null;
  last_seen_video_published_at: string | null;
  notes: string;
}

export const YOUTUBE_TOPIC_CATEGORIES = [
  'credit_repair',
  'business_funding',
  'business_credit',
  'online_business',
  'ai_automation',
  'affiliate_marketing',
  'trading_strategies',
  'seo_content_growth',
] as const;

export const SAMPLE_YOUTUBE_WATCHLIST: YouTubeChannelWatchlistItem[] = [
  {
    channel_name: 'Sample Credit Repair Education Channel',
    channel_url: 'https://www.youtube.com/@sample-credit-education',
    channel_id: null,
    topic_category: 'credit_repair',
    monetization_relevance: 80,
    approved_by_ray: false,
    enabled: false,
    risk_level: 'medium',
    last_checked_at: null,
    last_seen_video_url: null,
    last_seen_video_published_at: null,
    notes: 'Fixture only. Add real channels through the manual registry after review.',
  },
];
