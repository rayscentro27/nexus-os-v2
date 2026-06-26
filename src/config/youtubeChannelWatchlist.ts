export interface YouTubeChannelWatchlistItem {
  channel_name: string;
  channel_url: string;
  channel_id: string | null;
  topic_category: string;
  monetization_relevance: number;
  approved_by_ray: boolean;
  enabled: boolean;
  risk_level: 'low' | 'medium' | 'high' | 'low_medium' | 'medium_high';
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

export const RAY_YOUTUBE_WATCHLIST: YouTubeChannelWatchlistItem[] = [
  {
    channel_name: 'Credit Plug',
    channel_url: 'https://www.youtube.com/@creditplug',
    channel_id: null,
    topic_category: 'credit_repair | business_credit | business_funding',
    monetization_relevance: 90,
    approved_by_ray: true,
    enabled: true,
    risk_level: 'medium',
    last_checked_at: null,
    last_seen_video_url: null,
    last_seen_video_published_at: null,
    notes: 'Metadata/transcript-only research for credit repair, business credit, funding, GoClear positioning, SEO opportunities, and content offers.',
  },
  {
    channel_name: 'Michael Ionita',
    channel_url: 'https://www.youtube.com/@michaelionita',
    channel_id: null,
    topic_category: 'online_business | ai_tools | marketing | automation | product_strategy',
    monetization_relevance: 75,
    approved_by_ray: true,
    enabled: true,
    risk_level: 'low_medium',
    last_checked_at: null,
    last_seen_video_url: null,
    last_seen_video_published_at: null,
    notes: 'Metadata/transcript-only research for online business, AI automation, marketing, offer/product strategy, and content testing.',
  },
  {
    channel_name: 'Alec Delpuech',
    channel_url: 'https://www.youtube.com/@alecdelpuech',
    channel_id: null,
    topic_category: 'online_business | ai_tools | marketing | content_strategy',
    monetization_relevance: 72,
    approved_by_ray: true,
    enabled: true,
    risk_level: 'low_medium',
    last_checked_at: null,
    last_seen_video_url: null,
    last_seen_video_published_at: null,
    notes: 'Metadata/transcript-only research for business/product strategy, AI, marketing, content ideas, and experiments.',
  },
  {
    channel_name: 'Stedman Waiters',
    channel_url: 'https://www.youtube.com/@StedmanWaiters',
    channel_id: null,
    topic_category: 'trading_strategy | online_business | market_research',
    monetization_relevance: 60,
    approved_by_ray: true,
    enabled: true,
    risk_level: 'medium_high',
    last_checked_at: null,
    last_seen_video_url: null,
    last_seen_video_published_at: null,
    notes: 'Paper-only Trading Lab research. No live trading, broker execution, scheduler, or auto-executor exposure.',
  },
];
