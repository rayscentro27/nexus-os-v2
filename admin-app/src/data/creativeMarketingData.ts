import { DataTruthClass } from './executiveCommandData';
import { ASSETS } from './assets';

// =============================================================================
// RUNTIME DATA CONTRACT: CREATIVE ASSETS
// =============================================================================

export type CreativeAssetType =
  | 'VIDEO'
  | 'IMAGE'
  | 'SOCIAL_POST'
  | 'LANDING_PAGE'
  | 'AD_CREATIVE'
  | 'PRESENTATION'
  | 'EMAIL_GRAPHIC';

export type CreativeAssetStage =
  | 'DRAFT'
  | 'WAITING_RAY_PROMPT_APPROVAL'
  | 'GENERATING'
  | 'REVIEW'
  | 'REVISION'
  | 'APPROVED'
  | 'READY_FOR_MARKETING'
  | 'REJECTED_WITH_REPAIR';

export type CreativeApprovalState =
  | 'APPROVED'
  | 'WAITING_RAY'
  | 'IN_REVISION'
  | 'DRAFT';

export interface CreativeRevision {
  version: string;
  what_changed: string;
  why_it_changed: string;
  quality_issue: string;
  provider_used: string;
  cost: number;
  result: string;
  timestamp: string;
  whatChanged?: string;
  whyItChanged?: string;
  qualityIssue?: string;
  providerUsed?: string;
}

export interface CreativeAsset {
  id: string;
  title: string;
  campaign_id: string;
  campaign_name: string;
  asset_type: CreativeAssetType;
  platform: 'LinkedIn' | 'Facebook' | 'X' | 'YouTube' | 'TikTok' | 'Web' | 'Email' | 'Cross-Platform';
  current_stage: CreativeAssetStage;
  approval_state: CreativeApprovalState;
  prompt_id: string;
  prompt_version: string;
  exact_approved_creative_prompt: string;
  provider: string;
  created_at: string;
  last_revised: string;
  generation_cost: number;
  thumbnail_url: string;
  truth_class: DataTruthClass;
  preview_data: {
    full_image_url?: string;
    video_duration?: string;
    video_aspect?: string;
    video_fps?: string;
    video_script?: string;
    landing_page_url?: string;
    landing_page_headline?: string;
    landing_page_subhead?: string;
    landing_page_cta?: string;
    social_caption?: string;
    social_hashtags?: string[];
    deck_slide_count?: number;
    deck_slides?: { slideNumber: number; title: string; bullets: string[] }[];
  };
  revisions: CreativeRevision[];
}

export const CREATIVE_OUTPUT_SUMMARY = {
  assetsCreated: 32,
  assetsApproved: 24,
  assetsWaitingRay: 3,
  assetsInRevision: 2,
  videosCreated: 6,
  imagesCreated: 14,
  landingPagesCreated: 3,
  socialPostsCreated: 9,
  costPerUsableAsset: 2.63,
  truthClass: 'PROTOTYPE' as DataTruthClass
};

export const CREATIVE_ASSETS_DATA: CreativeAsset[] = [
  {
    id: 'crt-landing-goclear',
    title: 'GoClear Institutional Clearinghouse Hero Landing Page',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    asset_type: 'LANDING_PAGE',
    platform: 'Web',
    current_stage: 'APPROVED',
    approval_state: 'APPROVED',
    prompt_id: 'pmt-gc-lp-884',
    prompt_version: 'v2.4',
    exact_approved_creative_prompt: `System: Direct-response fintech landing page architect.
Generate high-conversion institutional hero section for GoClear Clearinghouse.
Key Value Prop: 'Automate Pre-Trade Clearing & Margin Rebalancing in under 14ms'.
Target Audience: Hedge fund COOs, Prime Broker Risk Officers, FinTech Developers.
Design Directives: Dark slate graphite aesthetic (#0A0F1D), high-contrast cyan glow charts (#06B6D4), SVG latency benchmarks ticker, enterprise-grade typography, frictionless 'Request Protocol Specification' primary CTA with zero fluff.`,
    provider: 'Figma Tokens & SVG Synth',
    created_at: '2026-04-18 10:14 UTC',
    last_revised: '2026-04-20 14:32 UTC',
    generation_cost: 16.00,
    thumbnail_url: ASSETS.landingPagePreview,
    truth_class: 'PROTOTYPE',
    preview_data: {
      full_image_url: ASSETS.landingPagePreview,
      landing_page_url: 'https://goclear.nexus.internal/preview/institutional-v2',
      landing_page_headline: 'Sub-14ms Pre-Trade Clearing & Autonomous Margin Balancing',
      landing_page_subhead: 'Eliminate settlement drag and intra-day liquidity lockups with our certified FIX Protocol clearing gateway.',
      landing_page_cta: 'Request Sandbox Specification'
    },
    revisions: [
      {
        version: 'v2.4',
        what_changed: 'Tightened hero benchmark table from 25ms to verified 14ms latency based on Lab tests.',
        why_it_changed: 'Ray feedback during executive review to highlight exact benchmark verification.',
        quality_issue: 'Previous copy was overly generic; needed hard numbers.',
        provider_used: 'Claude 3.5 Sonnet + Figma SVG',
        cost: 4.50,
        result: 'Approved by Ray for staging.',
        timestamp: 'Apr 20, 2026'
      },
      {
        version: 'v2.0',
        what_changed: 'Replaced light theme with high-contrast institutional dark slate container.',
        why_it_changed: 'Aligned with institutional prime broker terminal expectations.',
        quality_issue: 'Light theme had lower visual authority with hedge fund stakeholders.',
        provider_used: 'Figma Tokens',
        cost: 8.00,
        result: 'Revision accepted, moved to copy polish.',
        timestamp: 'Apr 19, 2026'
      },
      {
        version: 'v1.0',
        what_changed: 'Initial landing page wireframe and headline generation.',
        why_it_changed: 'Initial campaign kick-off from Research queue item #42.',
        quality_issue: 'First draft lacked technical API integration references.',
        provider_used: 'Claude 3.5 Sonnet',
        cost: 3.50,
        result: 'Flagged for redesign.',
        timestamp: 'Apr 18, 2026'
      }
    ]
  },
  {
    id: 'crt-video-liquidity',
    title: 'Order Book Depth & Autonomous Hedging Walkthrough',
    campaign_id: 'cmp-apex-cap',
    campaign_name: 'Apex Capital Quantitative',
    asset_type: 'VIDEO',
    platform: 'YouTube',
    current_stage: 'REVIEW',
    approval_state: 'WAITING_RAY',
    prompt_id: 'pmt-vid-liq-109',
    prompt_version: 'v1.3',
    exact_approved_creative_prompt: `Generate 45-second high-definition product visualizer of an order book depth chart with real-time liquidity rebalancing.
Render 3D isometric dark interface, neon violet bid/ask walls, simulated microsecond fill confirmations, and synthetic audio waveform narration.
Voice tone: Objective, authoritative quantitative engineer.
Closing CTA: 'Inspect the Open-Source Engine on GitHub'.`,
    provider: 'Modal A10G (MuseTalk & Remotion)',
    created_at: '2026-04-21 08:30 UTC',
    last_revised: '2026-04-22 09:15 UTC',
    generation_cost: 4.20,
    thumbnail_url: ASSETS.videoRenderPreview,
    truth_class: 'TEST',
    preview_data: {
      video_duration: '0:45',
      video_aspect: '16:9',
      video_fps: '60 fps',
      video_script: `00:00-00:10: 'When market fragmentation creates 20 basis point spread discrepancies, manual rebalancing is obsolete.'
00:10-00:25: 'Nexus Trading Alpha monitors 50 synthetic asset pairs simultaneously across distributed mempools.'
00:25-00:45: 'Inspect the verifiable execution audit logs in real-time. Sub-second execution, deterministic risk limits.'`
    },
    revisions: [
      {
        version: 'v1.3',
        what_changed: 'Swapped robotic TTS with custom Hermes voice model and synchronized 60fps chart audio.',
        why_it_changed: 'Ray requested natural speech pacing without synthetic stutter.',
        quality_issue: 'Earlier audio stuttered on quantitative terms like "basis points".',
        provider_used: 'Modal A10G + ElevenLabs Turbo',
        cost: 2.40,
        result: 'Staged in Pillar 4 awaiting Ray audio approval.',
        timestamp: 'Apr 22, 2026'
      },
      {
        version: 'v1.0',
        what_changed: 'Initial video render with static candlestick backdrop.',
        why_it_changed: 'First prototype render.',
        quality_issue: 'Background was static; needed animated 3D depth book.',
        provider_used: 'Remotion Render Engine',
        cost: 1.80,
        result: 'Motion updated to 3D.',
        timestamp: 'Apr 21, 2026'
      }
    ]
  },
  {
    id: 'crt-social-risk-ad',
    title: 'LinkedIn Sponsored Ad: 14ms Pre-Trade Risk Verification',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    asset_type: 'AD_CREATIVE',
    platform: 'LinkedIn',
    current_stage: 'READY_FOR_MARKETING',
    approval_state: 'APPROVED',
    prompt_id: 'pmt-ad-li-552',
    prompt_version: 'v3.1',
    exact_approved_creative_prompt: `Generate 1:1 LinkedIn feed ad asset for B2B institutional traders.
Hero text overlay: 'Automate Pre-Trade Risk Verification in 14ms'.
Visual: Dark glassmorphic risk audit badge with verified green checkmark (#10B981) and glowing data lines.
Target audience: Hedge fund managers, trading desk leads.
Footer caption: 'Eliminate trade settlement failure risks before orders route to market.'`,
    provider: 'Figma Vector Synth',
    created_at: '2026-04-19 14:00 UTC',
    last_revised: '2026-04-21 16:45 UTC',
    generation_cost: 8.50,
    thumbnail_url: ASSETS.socialAdCreative,
    truth_class: 'PROTOTYPE',
    preview_data: {
      full_image_url: ASSETS.socialAdCreative,
      social_caption: 'Trading desks lose an average of $42,000/mo to settlement slippage and delayed margin rebalances. GoClear brings pre-trade risk checks down to 14ms deterministically.',
      social_hashtags: ['#FinTech', '#AlgorithmicTrading', '#RiskManagement', '#InstitutionalFinance']
    },
    revisions: [
      {
        version: 'v3.1',
        what_changed: 'Added explicit 1:1 LinkedIn ratio and boosted contrast of typography for mobile readability.',
        why_it_changed: 'Optimized for mobile executive feed display.',
        quality_issue: 'Subtitle was hard to read on smaller screens in v2.',
        provider_used: 'Figma Vector Synth',
        cost: 2.50,
        result: 'Approved and scheduled into Marketing Content Calendar.',
        timestamp: 'Apr 21, 2026'
      }
    ]
  },
  {
    id: 'crt-deck-goclear',
    title: 'GoClear Institutional Customer Discovery Deck (24 Slides)',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    asset_type: 'PRESENTATION',
    platform: 'Cross-Platform',
    current_stage: 'APPROVED',
    approval_state: 'APPROVED',
    prompt_id: 'pmt-pdeck-901',
    prompt_version: 'v4.0',
    exact_approved_creative_prompt: `Generate complete 24-slide customer discovery & partnership deck for GoClear institutional pilots.
Structure: Executive Problem, The Clearing Bottleneck, Architecture Blueprint, Benchmark Comparison, Security & Compliance, Commercial Roadmap.
Color Palette: Nexus Dark Slate (#0F172A), Vivid Emerald (#10B981), Ice Cyan (#06B6D4).
Export format: Vector PDF + Interactive Keynote package.`,
    provider: 'Figma Tokens & Claude 3.5 Sonnet',
    created_at: '2026-04-16 11:20 UTC',
    last_revised: '2026-04-20 18:00 UTC',
    generation_cost: 32.00,
    thumbnail_url: ASSETS.pitchDeckCover,
    truth_class: 'PROTOTYPE',
    preview_data: {
      deck_slide_count: 24,
      deck_slides: [
        { slideNumber: 1, title: 'Title & Vision', bullets: ['GoClear: Autonomous Clearing & Liquidity Balancing', 'Prepared for Institutional Prime Broker Partners'] },
        { slideNumber: 2, title: 'The Problem: Settlement Drag', bullets: ['Traditional clearing cycles lock up to $1.2B in overnight margin', 'Manual exceptions cause 8.4% execution re-quotes'] },
        { slideNumber: 3, title: 'The Solution: Sub-14ms Deterministic Engine', bullets: ['Statutory validation, real-time risk margin recalculation', 'Direct FIX protocol integration without proxy lag'] },
        { slideNumber: 4, title: 'Audited Benchmarks & Security', bullets: ['26 verified readback unit tests passed with zero data loss', 'SOC-2 compliant architecture staged in Postgres'] }
      ]
    },
    revisions: [
      {
        version: 'v4.0',
        what_changed: 'Added Slide 18 detailing Clyde non-dilutive grant backing and state voucher validation.',
        why_it_changed: 'Reinforces financial stability to institutional pilot prospects.',
        quality_issue: 'Deck previously omitted treasury credentials.',
        provider_used: 'Claude 3.5 Sonnet',
        cost: 6.00,
        result: 'Approved by Ray.',
        timestamp: 'Apr 20, 2026'
      }
    ]
  },
  {
    id: 'crt-mockup-app',
    title: 'GoClear Partner Portal UI Design System & Component Library',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    asset_type: 'IMAGE',
    platform: 'Web',
    current_stage: 'APPROVED',
    approval_state: 'APPROVED',
    prompt_id: 'pmt-ui-ds-302',
    prompt_version: 'v2.1',
    exact_approved_creative_prompt: `Comprehensive multi-tenant client portal design system.
Includes dark mode trading terminal, real-time latency indicators, API key provisioners, and audit log inspectors.
Rendered in pristine high-resolution responsive web format.`,
    provider: 'Figma Component Synth',
    created_at: '2026-04-17 09:00 UTC',
    last_revised: '2026-04-19 12:00 UTC',
    generation_cost: 14.50,
    thumbnail_url: ASSETS.creativeAppMockup,
    truth_class: 'PROTOTYPE',
    preview_data: {
      full_image_url: ASSETS.creativeAppMockup
    },
    revisions: [
      {
        version: 'v2.1',
        what_changed: 'Updated typography scale to Inter Tight and added zero-pill compliance styling.',
        why_it_changed: 'Strict Nexus design language alignment.',
        quality_issue: 'Had inconsistent button radius.',
        provider_used: 'Figma Tokens',
        cost: 3.50,
        result: 'Design approved.',
        timestamp: 'Apr 19, 2026'
      }
    ]
  },
  {
    id: 'crt-product-3d',
    title: 'Autonomous Hardware Gateway Product Render (Mac mini Metal)',
    campaign_id: 'cmp-tech-seed',
    campaign_name: 'Autonomous Infrastructure',
    asset_type: 'IMAGE',
    platform: 'Cross-Platform',
    current_stage: 'READY_FOR_MARKETING',
    approval_state: 'APPROVED',
    prompt_id: 'pmt-3d-hw-701',
    prompt_version: 'v1.5',
    exact_approved_creative_prompt: `High-fidelity 3D photorealistic render of an autonomous server appliance.
Sleek matte graphite aluminum casing, soft cyan perimeter LED, rear fiber optic and 10GbE network ports.
Theme: 'Local Apple Silicon Metal Compute for Sovereign Trading'.`,
    provider: 'Blender GPU Synth',
    created_at: '2026-04-18 15:30 UTC',
    last_revised: '2026-04-20 11:15 UTC',
    generation_cost: 12.00,
    thumbnail_url: ASSETS.creativeProductRender,
    truth_class: 'PROTOTYPE',
    preview_data: {
      full_image_url: ASSETS.creativeProductRender
    },
    revisions: [
      {
        version: 'v1.5',
        what_changed: 'Corrected rear port illumination from harsh red to soft cyan.',
        why_it_changed: 'Brand visual harmony with Nexus palette.',
        quality_issue: 'Red implied system fault or hardware alarm.',
        provider_used: 'Blender GPU',
        cost: 4.00,
        result: 'Render finalized.',
        timestamp: 'Apr 20, 2026'
      }
    ]
  }
];

// =============================================================================
// RUNTIME DATA CONTRACT: MARKETING SCHEDULED & PUBLISHED CONTENT
// =============================================================================

export type MarketingPublishState =
  | 'DRAFT'
  | 'WAITING_CREATIVE'
  | 'WAITING_RAY'
  | 'APPROVED'
  | 'SCHEDULED'
  | 'PUBLISHING'
  | 'PUBLISHED'
  | 'FAILED'
  | 'PAUSED';

export interface MarketingContentItem {
  id: string;
  creative_asset_id: string; // Direct foreign key to Creative Asset!
  campaign_id: string;
  campaign_name: string;
  platform: 'LinkedIn' | 'Facebook' | 'X' | 'YouTube' | 'TikTok' | 'Email' | 'Website / Blog';
  account_name: string;
  post_title: string;
  caption: string;
  thumbnail_url: string;
  scheduled_at: string;
  published_at?: string;
  published_url?: string;
  publish_state: MarketingPublishState;
  approval_state: 'APPROVED' | 'WAITING_RAY' | 'DRAFT';
  owner: string;
  truth_class: DataTruthClass;
  metrics?: {
    reach?: number | null;
    impressions?: number | null;
    views?: number | null;
    reactions?: number | null;
    comments?: number | null;
    shares?: number | null;
    clicks?: number | null;
    leads?: number | null;
    conversions?: number | null;
  };
}

export const MARKETING_CONTENT_SCHEDULE: MarketingContentItem[] = [
  {
    id: 'mkt-post-101',
    creative_asset_id: 'crt-social-risk-ad',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    platform: 'LinkedIn',
    account_name: 'Nexus Systems Engineering',
    post_title: '14ms Pre-Trade Risk Verification Framework Announcement',
    caption: 'How can institutional trading desks eliminate settlement slippage and delayed margin rebalances? We open-sourced the 14ms deterministic benchmark numbers today. Inspect the architectural readback logs below.',
    thumbnail_url: ASSETS.socialAdCreative,
    scheduled_at: 'Tomorrow, 09:00 AM EST',
    publish_state: 'SCHEDULED',
    approval_state: 'APPROVED',
    owner: 'Mira (Marketing Agent)',
    truth_class: 'PROTOTYPE'
  },
  {
    id: 'mkt-post-102',
    creative_asset_id: 'crt-video-liquidity',
    campaign_id: 'cmp-apex-cap',
    campaign_name: 'Apex Capital Quantitative',
    platform: 'YouTube',
    account_name: 'Nexus Tech Labs',
    post_title: 'Order Book Depth & Autonomous Hedging Walkthrough (45s)',
    caption: 'Watch real-time order book liquidity rebalancing across 50 asset pairs running on local Metal Apple Silicon. Zero cloud latency penalty.',
    thumbnail_url: ASSETS.videoRenderPreview,
    scheduled_at: 'Thursday, 02:00 PM EST',
    publish_state: 'WAITING_RAY',
    approval_state: 'WAITING_RAY',
    owner: 'Ray Davis / Mira',
    truth_class: 'TEST'
  },
  {
    id: 'mkt-post-103',
    creative_asset_id: 'crt-landing-goclear',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    platform: 'X',
    account_name: '@NexusSystemsOS',
    post_title: 'GoClear Sandbox Developer Documentation Rollout',
    caption: 'Developers: The GoClear sandbox API protocol is now public for institutional pilot partners. Test your FIX protocol bridges directly.',
    thumbnail_url: ASSETS.landingPagePreview,
    scheduled_at: 'Friday, 11:30 AM EST',
    publish_state: 'SCHEDULED',
    approval_state: 'APPROVED',
    owner: 'Mira (Marketing Agent)',
    truth_class: 'PROTOTYPE'
  },
  {
    id: 'mkt-post-104',
    creative_asset_id: 'crt-social-risk-ad',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    platform: 'Facebook',
    account_name: 'GoClear Official Page',
    post_title: 'Institutional Fintech Clearing Automation Case Study',
    caption: 'Explore how modern hedge fund operations are solving multi-venue trade settlement drag with sub-14ms pre-trade risk verification.',
    thumbnail_url: ASSETS.socialAdCreative,
    scheduled_at: 'Saturday, 10:00 AM EST',
    publish_state: 'PAUSED',
    approval_state: 'APPROVED',
    owner: 'Mira (Marketing Agent)',
    truth_class: 'NOT_CONNECTED' // Explicit Facebook connection state requirement!
  }
];

export const MARKETING_PUBLISHED_CONTENT: MarketingContentItem[] = [
  {
    id: 'mkt-pub-201',
    creative_asset_id: 'crt-deck-goclear',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    platform: 'LinkedIn',
    account_name: 'Ray Davis [Founder]',
    post_title: 'Why Traditional Trade Settlement Architecture Locks Up $1.2B',
    caption: 'We compiled a 24-slide breakdown of the modern prime broker clearing bottleneck. The core culprit: legacy batch processing instead of deterministic event-driven risk checks.',
    thumbnail_url: ASSETS.pitchDeckCover,
    scheduled_at: 'Apr 20, 2026',
    published_at: 'Apr 20, 2026 14:15 UTC',
    published_url: 'https://linkedin.com/feed/update/urn:li:activity:7188421094',
    publish_state: 'PUBLISHED',
    approval_state: 'APPROVED',
    owner: 'Ray Davis',
    truth_class: 'PROTOTYPE',
    metrics: {
      reach: 4820,
      impressions: 7240,
      views: 3150,
      reactions: 142,
      comments: 28,
      shares: 19,
      clicks: 340,
      leads: 14,
      conversions: 2
    }
  },
  {
    id: 'mkt-pub-202',
    creative_asset_id: 'crt-landing-goclear',
    campaign_id: 'cmp-goclear-inst',
    campaign_name: 'GoClear Institutional Pilot',
    platform: 'X',
    account_name: '@NexusSystemsOS',
    post_title: 'Sub-14ms Pre-Trade Clearing Benchmark Verified',
    caption: '26/26 audit checks passed on our local Metal quantified order book engine. Zero settlement failure exceptions observed in testing.',
    thumbnail_url: ASSETS.landingPagePreview,
    scheduled_at: 'Apr 19, 2026',
    published_at: 'Apr 19, 2026 16:30 UTC',
    published_url: 'https://x.com/NexusSystemsOS/status/1781349021',
    publish_state: 'PUBLISHED',
    approval_state: 'APPROVED',
    owner: 'Mira',
    truth_class: 'PROTOTYPE',
    metrics: {
      reach: 8900,
      impressions: 14200,
      views: 6100,
      reactions: 230,
      comments: 42,
      shares: 58,
      clicks: 512,
      leads: 9,
      conversions: 1
    }
  },
  {
    id: 'mkt-pub-203',
    creative_asset_id: 'crt-product-3d',
    campaign_id: 'cmp-tech-seed',
    campaign_name: 'Autonomous Infrastructure',
    platform: 'Facebook',
    account_name: 'Nexus Systems Lab',
    post_title: 'Sovereign On-Premise AI Compute for Capital Desks',
    caption: 'How autonomous trading desks are running Ollama quants on bare-metal Apple Silicon to save ~$3,200/mo over cloud token fees.',
    thumbnail_url: ASSETS.creativeProductRender,
    scheduled_at: 'Apr 18, 2026',
    published_at: 'Apr 18, 2026 12:00 UTC',
    published_url: 'https://facebook.com/NexusSystems/posts/894021',
    publish_state: 'PUBLISHED',
    approval_state: 'APPROVED',
    owner: 'Mira',
    truth_class: 'NOT_CONNECTED', // Explicit Facebook API not connected
    metrics: {
      reach: null,
      impressions: null,
      views: null,
      reactions: null,
      comments: null,
      shares: null,
      clicks: null,
      leads: null
    }
  }
];

// =============================================================================
// AUDIENCE RESPONSE & INTELLIGENCE DATA (Requirement 12 & 13)
// =============================================================================

export type CommentClassification =
  | 'POSITIVE'
  | 'QUESTION'
  | 'OBJECTION'
  | 'COMPLAINT'
  | 'BUYING_INTENT'
  | 'FEATURE_REQUEST'
  | 'SPAM_LOW_VALUE';

export interface AudienceComment {
  id: string;
  post_id: string;
  post_title: string;
  platform: 'LinkedIn' | 'Facebook' | 'X' | 'YouTube';
  author: string;
  author_title: string;
  author_avatar: string;
  comment_text: string;
  timestamp: string;
  classification: CommentClassification;
  engagement: number;
  reply_status: 'PENDING_APPROVAL' | 'REPLIED' | 'ARCHIVED' | 'ESCALATED_TO_SALES';
  truth_class: DataTruthClass;
}

export const AUDIENCE_COMMENTS_DATA: AudienceComment[] = [
  {
    id: 'cmt-101',
    post_id: 'mkt-pub-201',
    post_title: 'Why Traditional Trade Settlement Architecture Locks Up $1.2B',
    platform: 'LinkedIn',
    author: 'David Vance',
    author_title: 'Head of Prime Broker Risk at Apex Capital',
    author_avatar: ASSETS.alexRiveraAvatar,
    comment_text: 'Are you running FIX 4.4 or 5.0 SP2? We need direct memory access if you are claiming 14ms latency on order reconciliation.',
    timestamp: '2 hours ago',
    classification: 'BUYING_INTENT',
    engagement: 14,
    reply_status: 'ESCALATED_TO_SALES',
    truth_class: 'PROTOTYPE'
  },
  {
    id: 'cmt-102',
    post_id: 'mkt-pub-201',
    post_title: 'Why Traditional Trade Settlement Architecture Locks Up $1.2B',
    platform: 'LinkedIn',
    author: 'Elena Rostova',
    author_title: 'Managing Director, Horizon Clearinghouse',
    author_avatar: ASSETS.sarahAvatar,
    comment_text: 'Does this integrate with legacy DTCC settlement feeds, or is this strictly for bilateral OTC swaps?',
    timestamp: '5 hours ago',
    classification: 'QUESTION',
    engagement: 8,
    reply_status: 'PENDING_APPROVAL',
    truth_class: 'PROTOTYPE'
  },
  {
    id: 'cmt-103',
    post_id: 'mkt-pub-202',
    post_title: 'Sub-14ms Pre-Trade Clearing Benchmark Verified',
    platform: 'X',
    author: '@quant_marcus',
    author_title: 'Proprietary Trader, Chicago',
    author_avatar: ASSETS.marcusAvatar,
    comment_text: '14ms is impressive for software, but what happens during 3-sigma volatility spikes when mempools congest?',
    timestamp: '1 day ago',
    classification: 'OBJECTION',
    engagement: 22,
    reply_status: 'PENDING_APPROVAL',
    truth_class: 'PROTOTYPE'
  },
  {
    id: 'cmt-104',
    post_id: 'mkt-pub-201',
    post_title: 'Why Traditional Trade Settlement Architecture Locks Up $1.2B',
    platform: 'LinkedIn',
    author: 'Michael Sterling',
    author_title: 'CTO, Global Clearing Partners',
    author_avatar: ASSETS.michaelAvatar,
    comment_text: 'Slide 14 on memory footprint is brilliant. Would love to pilot this on our sandbox testnet next week.',
    timestamp: '1 day ago',
    classification: 'BUYING_INTENT',
    engagement: 31,
    reply_status: 'ESCALATED_TO_SALES',
    truth_class: 'PROTOTYPE'
  },
  {
    id: 'cmt-105',
    post_id: 'mkt-pub-202',
    post_title: 'Sub-14ms Pre-Trade Clearing Benchmark Verified',
    platform: 'X',
    author: '@defi_dev_sam',
    author_title: 'Core Protocol Engineer',
    author_avatar: ASSETS.taylorAvatar,
    comment_text: 'Can we self-host the vector state on our own Mac mini fleet or does it require your cloud cluster?',
    timestamp: '2 days ago',
    classification: 'FEATURE_REQUEST',
    engagement: 6,
    reply_status: 'REPLIED',
    truth_class: 'PROTOTYPE'
  }
];

export const AUDIENCE_INTELLIGENCE_SUMMARY = {
  topRecurringQuestions: [
    'Does GoClear support FIX 4.4 and FIX 5.0 SP2 protocols directly?',
    'Can the verification engine be self-hosted on bare-metal hardware?',
    'How does margin rebalancing handle multi-currency cross-collateralization?'
  ],
  topObjections: [
    'Latency during 3-sigma black-swan volatility spikes',
    'Integration friction with legacy DTCC settlement batch files',
    'Regulatory classification of autonomous pre-trade risk checks'
  ],
  commonCustomerLanguage: [
    '"Settlement drag"',
    '"Sub-14ms execution"',
    '"Intra-day liquidity lockup"',
    '"Deterministic risk limits"'
  ],
  sentimentBreakdown: {
    positive: 62,
    question: 24,
    objection: 9,
    high_intent: 5
  },
  feedbackLoops: [
    {
      trigger: 'Repeated question regarding FIX 5.0 protocol support',
      destination: 'Research / Opportunities' as const,
      action: 'Clyde created Research Item #44: FIX Protocol Bridge Specification',
      status: 'ACTIVE_ROUTED' as const
    },
    {
      trigger: 'Objection on 3-sigma volatility spike latency',
      destination: 'Marketing optimization' as const,
      action: 'Mira staged new Stress-Test FAQ section for next week deck iteration',
      status: 'ACTIVE_ROUTED' as const
    },
    {
      trigger: 'Strong buying intent from David Vance & Michael Sterling',
      destination: 'Sales / lead workflow' as const,
      action: '2 Enterprise Leads routed into Pillar 4 for Ray NDA execution',
      status: 'ACTIVE_ROUTED' as const
    },
    {
      trigger: 'Ad creative 1:1 format outperforming wide banner by 3.2x',
      destination: 'Creative reference signal' as const,
      action: 'Creative default template set to 1:1 square for sponsored feed units',
      status: 'ACTIVE_ROUTED' as const
    }
  ]
};

// =============================================================================
// CONTENT PERFORMANCE TOTALS & ATTRIBUTION (Requirements 14, 15, 16)
// =============================================================================

export const CONTENT_PERFORMANCE_METRICS = {
  totalReach: '13,720 (PROTOTYPE)',
  totalImpressions: '21,440',
  totalViews: '9,250',
  totalEngagement: '488',
  totalComments: '70',
  totalShares: '77',
  totalClicks: '852',
  totalLeads: '23 MQLs',
  totalCustomers: '3 Pilots',
  verifiedRevenue: '$0.00 / NOT CONNECTED',
  topPost: 'Why Traditional Settlement Locks $1.2B (LinkedIn)',
  topVideo: 'Order Book Depth Walkthrough (YouTube - Staged)',
  topPlatform: 'LinkedIn (68% of Inbound MQLs)',
  topCampaign: 'GoClear Institutional Pilot',
  bestCTA: '"Request Sandbox Specification" (4.8% CTR)',
  bestFormat: '1:1 Sponsored Risk Badge Graphic'
};

export const ATTRIBUTION_PIPELINE = [
  {
    step: '1. Content Asset',
    label: 'LinkedIn Deck & 14ms Ad',
    metric: '21,440 Impressions',
    status: 'PROTOTYPE'
  },
  {
    step: '2. Direct Clicks',
    label: 'Inbound Inquiries',
    metric: '852 Qualified Clicks (3.97% CTR)',
    status: 'PROTOTYPE'
  },
  {
    step: '3. Generated Leads',
    label: 'Institutional Form Submissions',
    metric: '23 Pilot Inquiries ($0 Ad Spend)',
    status: 'PROTOTYPE'
  },
  {
    step: '4. Qualified Leads',
    label: 'Verified Institutional COOs',
    metric: '7 MQLs Handed to Ray',
    status: 'PROTOTYPE'
  },
  {
    step: '5. Signed Customers',
    label: 'Pilot Agreement Stage',
    metric: '3 Pilot Agreements Staged',
    status: 'PROTOTYPE'
  },
  {
    step: '6. Verified Revenue',
    label: 'Settled Merchant Invoices',
    metric: '$0.00 (NOT CONNECTED / NOT PROVEN)',
    status: 'NOT_CONNECTED'
  }
];
