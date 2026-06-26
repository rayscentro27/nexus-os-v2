export type ContentOpportunityType =
  | 'blog_post'
  | 'seo_landing_page'
  | 'youtube_script'
  | 'short_form_video'
  | 'social_carousel'
  | 'lead_magnet_pdf'
  | 'email_sequence'
  | 'webinar_workshop_outline'
  | 'affiliate_review_article';

export interface ContentOpportunity {
  content_type: ContentOpportunityType;
  target_keyword_topic: string;
  audience: string;
  intent: string;
  offer_tie_in: string;
  affiliate_tie_in: string;
  estimated_difficulty: string;
  expected_revenue_path: string;
  recommended_format: string;
  next_action: string;
  proof_source: string;
  experiment_hypothesis: string;
}
