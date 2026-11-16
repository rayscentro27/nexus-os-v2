export type DataTruthClass = 'LIVE_VERIFIED' | 'TEST_CANARY' | 'PROTOTYPE';

export type WorkOrigin = 'SCHEDULED_DISCOVERY' | 'SOURCE_MONITOR' | 'EXPERT_REQUEST';

export type ResearchSourceType =
  | 'YouTube'
  | 'Web'
  | 'GitHub'
  | 'TradingView'
  | 'SEO'
  | 'Documents';

export type MechanicalIngestionStatus =
  | 'QUEUED'
  | 'PROCESSING'
  | 'INGESTED'
  | 'FAILED_RETRYABLE'
  | 'FAILED_FINAL';

export type MechanicalReceiptStage =
  | 'DISCOVERED'
  | 'CLAIMED'
  | 'METADATA_CAPTURED'
  | 'CONTENT_CAPTURED'
  | 'TRANSCRIPT_CAPTURED'
  | 'CONTENT_NORMALIZED'
  | 'SUPABASE_WRITE_STARTED'
  | 'SUPABASE_WRITE_CONFIRMED';

export type TechnicalDiagnostic =
  | 'Nominal'
  | 'HTTP error'
  | 'rate limited'
  | 'source unavailable'
  | 'ASR required'
  | 'ASR processing'
  | 'Supabase write failed'
  | 'retry pending';

export interface YouTubePipelineDetails {
  captionsAvailable: boolean;
  captionsAcquired: boolean;
  audioRequired: boolean;
  audioAcquired: boolean;
  asrEngine: 'faster-whisper' | 'whisper.cpp' | 'none';
  asrEngineEnvironment?: 'Hermes Cloud / Oracle VM (TESTING)' | 'Mac mini (Local)' | 'none';
  asrProcessing: boolean;
  transcriptCreated: boolean;
  supabaseVerified: boolean;
}

export interface DownstreamAnalysis {
  researchInterpretation: string;
  alphaOpinion: string | null;
  expertRouting: 'Alpha' | 'Mercury (Trading)' | 'Clyde (Funding)' | 'Marketing' | 'Archive';
  expertResult: string | null;
}

export interface MechanicalReceipt {
  stage: MechanicalReceiptStage;
  timestamp: string;
  detail: string;
}

export interface ResearchQueueItem {
  id: string;
  queueSequence: number; // Deterministic FIFO queue sequence (#101, #102...)
  origin: WorkOrigin;
  title: string;
  sourceUrl: string;
  sourceName: string;
  sourceType: ResearchSourceType;
  status: MechanicalIngestionStatus;
  truthClass: DataTruthClass;
  currentStage: MechanicalReceiptStage;
  technicalDiagnostic: TechnicalDiagnostic;
  processor: string;
  workerAvatar: string;
  priority: 'Critical' | 'High' | 'Medium' | 'Low';
  createdAt: string;
  claimedAt: string | null;
  lastAttempt: string;
  retryCount: number;
  failureReason: string | null;

  // Mechanical Ingestion Details (Meaning of INGESTED)
  contentLength: string;
  transcriptStatus: string;
  canonicalPackageId: string;
  supabaseRecordId: string | null;
  readbackResult: 'Verified' | 'Pending' | 'Failed' | 'N/A';

  // YouTube Specific Pipeline Visibility
  youtubePipeline?: YouTubePipelineDetails;

  // Operational Receipts Timeline
  receipts: MechanicalReceipt[];

  // Downstream Analysis (Visually downstream from mechanical ingestion)
  downstreamAnalysis?: DownstreamAnalysis;

  isPrototype?: boolean;
}

export interface DiscoveryHeartbeatStatus {
  status: 'Active' | 'Standby';
  truthClass: DataTruthClass;
  lastDiscoveryCycle: string;
  sourcesDiscoveredCount: number;
  itemsAppendedToFifoCount: number;
  activeDiscoverySource: string;
  secondsUntilNextCycle: number;
  fifoDrainingContinuously: boolean;
  recentHeartbeatLog: Array<{
    cycleNumber: number;
    timestamp: string;
    sourcesFound: number;
    appendedToFifo: number;
    channel: string;
    summary: string;
  }>;
}

export const INITIAL_DISCOVERY_HEARTBEAT: DiscoveryHeartbeatStatus = {
  status: 'Active',
  truthClass: 'TEST_CANARY',
  lastDiscoveryCycle: 'Cycle #143 (Test Canary · Completed at 09:42 AM)',
  sourcesDiscoveredCount: 8,
  itemsAppendedToFifoCount: 5,
  activeDiscoverySource: 'YouTube (faster-whisper evaluation) & TradingView Ingestion',
  secondsUntilNextCycle: 45,
  fifoDrainingContinuously: true,
  recentHeartbeatLog: [
    {
      cycleNumber: 143,
      timestamp: '09:42 AM Today',
      sourcesFound: 8,
      appendedToFifo: 5,
      channel: 'YouTube & TradingView Web Ingestion',
      summary: 'Discovered 5 candidate items; appended deterministically to universal FIFO queue (Test Canary).'
    },
    {
      cycleNumber: 142,
      timestamp: '09:22 AM Today',
      sourcesFound: 6,
      appendedToFifo: 3,
      channel: 'GitHub Architecture Feeds',
      summary: 'SearXNG Docker spec and API docs appended to FIFO (Test Canary).'
    },
    {
      cycleNumber: 141,
      timestamp: '09:02 AM Today',
      sourcesFound: 12,
      appendedToFifo: 4,
      channel: 'SEO & Developer Demand Queries',
      summary: 'Extracted search trend signals; 4 clusters queued for mechanical parsing (Prototype).'
    }
  ]
};

export const INITIAL_RESEARCH_QUEUE: ResearchQueueItem[] = [
  {
    id: 'res-yt-01',
    queueSequence: 101,
    origin: 'SOURCE_MONITOR',
    title: 'YouTube Ingestion: Quant Trading Order Execution & Slippage Microstructure',
    sourceUrl: 'https://youtube.com/watch?v=qnt_slip_9821',
    sourceName: 'Quantitative Trading Systems Engineering Channel (Synthetic Example)',
    sourceType: 'YouTube',
    status: 'INGESTED',
    truthClass: 'TEST_CANARY',
    currentStage: 'SUPABASE_WRITE_CONFIRMED',
    technicalDiagnostic: 'Nominal',
    processor: 'Worker-Research-01 (Oracle / Hermes Cloud · TESTING)',
    workerAvatar: 'WR',
    priority: 'Critical',
    createdAt: '08:15 AM Today',
    claimedAt: '08:16 AM Today',
    lastAttempt: '08:24 AM Today',
    retryCount: 0,
    failureReason: null,

    contentLength: '24.8 KB (6,420 words normalized text)',
    transcriptStatus: 'Evaluation canary: Audio demuxed → faster-whisper ASR benchmark under test on Hermes Cloud (TEST CANARY - Not certified production worker)',
    canonicalPackageId: 'pkg-yt-slippage-101.json',
    supabaseRecordId: 'rec_sp_2026_0929_101 (Test Schema)',
    readbackResult: 'Verified',

    youtubePipeline: {
      captionsAvailable: false,
      captionsAcquired: false,
      audioRequired: true,
      audioAcquired: true,
      asrEngine: 'faster-whisper',
      asrEngineEnvironment: 'Hermes Cloud / Oracle VM (TESTING)',
      asrProcessing: false,
      transcriptCreated: true,
      supabaseVerified: true
    },

    receipts: [
      { stage: 'DISCOVERED', timestamp: '08:15 AM', detail: 'Source monitor identified test video candidate.' },
      { stage: 'CLAIMED', timestamp: '08:16 AM', detail: 'Claimed by Worker-Research-01 in FIFO order.' },
      { stage: 'METADATA_CAPTURED', timestamp: '08:17 AM', detail: 'Title, duration (48m 12s), channel ID indexed in test harness.' },
      { stage: 'CONTENT_CAPTURED', timestamp: '08:18 AM', detail: 'yt-dlp checked timedtext API: zero public captions available.' },
      { stage: 'TRANSCRIPT_CAPTURED', timestamp: '08:21 AM', detail: 'Extracted 16kHz audio stream. faster-whisper CPU benchmark evaluated in 3m 15s on Hermes Cloud container (TEST CANARY).' },
      { stage: 'CONTENT_NORMALIZED', timestamp: '08:22 AM', detail: 'Clean punctuation, timestamps, and speaker diarization segments normalized.' },
      { stage: 'SUPABASE_WRITE_STARTED', timestamp: '08:23 AM', detail: 'Writing canonical package to test schema public.research_canonical_packages.' },
      { stage: 'SUPABASE_WRITE_CONFIRMED', timestamp: '08:24 AM', detail: 'Supabase write succeeded. SHA256 checksum readback verified in test store.' }
    ],

    downstreamAnalysis: {
      researchInterpretation: 'Author documents empirical adverse selection of 4.2 bps during pre-market auction crosses. Detailed TWAP avoidance techniques outlined.',
      alphaOpinion: 'Quantitative validity high. Backtest candidate identified for Mercury trading engine.',
      expertRouting: 'Mercury (Trading)',
      expertResult: 'Queued in trading research engine for slippage mitigation stress testing.'
    },
    isPrototype: false
  },
  {
    id: 'res-yt-02',
    queueSequence: 102,
    origin: 'SCHEDULED_DISCOVERY',
    title: 'YouTube Ingestion: faster-whisper vs whisper.cpp Latency and Memory Benchmarks',
    sourceUrl: 'https://youtube.com/watch?v=asr_bench_4412',
    sourceName: 'Systems Engineering & ASR Performance Tech Talks (Synthetic Example)',
    sourceType: 'YouTube',
    status: 'PROCESSING',
    truthClass: 'TEST_CANARY',
    currentStage: 'TRANSCRIPT_CAPTURED',
    technicalDiagnostic: 'ASR processing',
    processor: 'Worker-Research-01 (Oracle / Hermes Cloud · TESTING)',
    workerAvatar: 'WR',
    priority: 'High',
    createdAt: '08:30 AM Today',
    claimedAt: '08:32 AM Today',
    lastAttempt: '08:44 AM Today',
    retryCount: 0,
    failureReason: null,

    contentLength: '18.4 KB (audio stream in progress)',
    transcriptStatus: 'ASR evaluation in progress via whisper.cpp with NEON/AVX optimizations on Hermes Cloud (TEST CANARY)',
    canonicalPackageId: 'pkg-yt-asrbench-102.json',
    supabaseRecordId: null,
    readbackResult: 'Pending',

    youtubePipeline: {
      captionsAvailable: false,
      captionsAcquired: false,
      audioRequired: true,
      audioAcquired: true,
      asrEngine: 'whisper.cpp',
      asrEngineEnvironment: 'Hermes Cloud / Oracle VM (TESTING)',
      asrProcessing: true,
      transcriptCreated: false,
      supabaseVerified: false
    },

    receipts: [
      { stage: 'DISCOVERED', timestamp: '08:30 AM', detail: 'Scheduled discovery appended video URL to FIFO.' },
      { stage: 'CLAIMED', timestamp: '08:32 AM', detail: 'Worker-Research-01 assigned next executable FIFO item.' },
      { stage: 'METADATA_CAPTURED', timestamp: '08:33 AM', detail: 'Duration: 32m 04s. Format: 1080p.' },
      { stage: 'CONTENT_CAPTURED', timestamp: '08:35 AM', detail: 'No captions found. Demuxing audio track.' },
      { stage: 'TRANSCRIPT_CAPTURED', timestamp: '08:44 AM', detail: 'whisper.cpp processing batch #3 of 4 on CPU (Evaluation in progress).' }
    ],

    downstreamAnalysis: {
      researchInterpretation: 'Comparing CPU RAM footprint and latency across containerized Oracle VM workers.',
      alphaOpinion: 'Pending raw transcription persistence in Supabase.',
      expertRouting: 'Alpha',
      expertResult: 'Downstream queue waiting for Supabase verified readback.'
    },
    isPrototype: false
  },
  {
    id: 'res-tv-01',
    queueSequence: 103,
    origin: 'SOURCE_MONITOR',
    title: 'TradingView Strategy: London-NY Open Breakout Volatility Channel PineScript v5',
    sourceUrl: 'https://tradingview.com/script/lny_open_breakout_v5/',
    sourceName: 'TradingView Public Community Scripts (Synthetic Example)',
    sourceType: 'TradingView',
    status: 'INGESTED',
    truthClass: 'TEST_CANARY',
    currentStage: 'SUPABASE_WRITE_CONFIRMED',
    technicalDiagnostic: 'Nominal',
    processor: 'Worker-Research-02 (Mac mini)',
    workerAvatar: 'W2',
    priority: 'High',
    createdAt: '08:45 AM Today',
    claimedAt: '08:46 AM Today',
    lastAttempt: '08:49 AM Today',
    retryCount: 0,
    failureReason: null,

    contentLength: '12.1 KB (PineScript source, parameters, description)',
    transcriptStatus: 'N/A (Generic web/document ingestion path - Test Canary)',
    canonicalPackageId: 'pkg-tv-lny-breakout-103.json',
    supabaseRecordId: 'rec_sp_2026_0929_103',
    readbackResult: 'Verified',

    receipts: [
      { stage: 'DISCOVERED', timestamp: '08:45 AM', detail: 'TradingView webhook trigger indexed public script.' },
      { stage: 'CLAIMED', timestamp: '08:46 AM', detail: 'Claimed by Worker-Research-02 in deterministic FIFO order.' },
      { stage: 'METADATA_CAPTURED', timestamp: '08:47 AM', detail: 'Author, script version (v5), and open-source license captured.' },
      { stage: 'CONTENT_CAPTURED', timestamp: '08:47 AM', detail: 'Public description, mathematical formula, and PineScript code acquired.' },
      { stage: 'CONTENT_NORMALIZED', timestamp: '08:48 AM', detail: 'Rules, indicators, and parameter blocks extracted.' },
      { stage: 'SUPABASE_WRITE_STARTED', timestamp: '08:48 AM', detail: 'Inserting canonical record into public.research_canonical_packages.' },
      { stage: 'SUPABASE_WRITE_CONFIRMED', timestamp: '08:49 AM', detail: 'Persisted to Supabase. Verified readback confirmed in test store.' }
    ],

    downstreamAnalysis: {
      researchInterpretation: 'Mechanical rules define a 15-minute volatility breakout filter around 08:00 GMT and 13:30 GMT. Ingested without requiring Mercury pre-approval.',
      alphaOpinion: 'Quantitative feasibility score: 8.7/10. Passed to Mercury for execution backtest.',
      expertRouting: 'Mercury (Trading)',
      expertResult: 'Mercury backtesting regime pass rate: 84% across simulated tick logs.'
    },
    isPrototype: false
  },
  {
    id: 'res-gh-01',
    queueSequence: 104,
    origin: 'EXPERT_REQUEST',
    title: 'GitHub Architecture: SearXNG Meta-Search Engine Docker Compose & JSON API Spec',
    sourceUrl: 'https://github.com/searxng/searxng-docker',
    sourceName: 'GitHub Repositories / Architecture Specs (Synthetic Example)',
    sourceType: 'GitHub',
    status: 'INGESTED',
    truthClass: 'TEST_CANARY',
    currentStage: 'SUPABASE_WRITE_CONFIRMED',
    technicalDiagnostic: 'Nominal',
    processor: 'Worker-Research-02 (Mac mini)',
    workerAvatar: 'W2',
    priority: 'Medium',
    createdAt: '08:50 AM Today',
    claimedAt: '08:51 AM Today',
    lastAttempt: '08:55 AM Today',
    retryCount: 0,
    failureReason: null,

    contentLength: '42.6 KB (README, docker-compose.yml, settings.yml, API schemas)',
    transcriptStatus: 'N/A (Document / Code ingestion path - Test Canary)',
    canonicalPackageId: 'pkg-gh-searxng-104.json',
    supabaseRecordId: 'rec_sp_2026_0929_104',
    readbackResult: 'Verified',

    receipts: [
      { stage: 'DISCOVERED', timestamp: '08:50 AM', detail: 'Systems engineer queued expert request for SearXNG tool specs.' },
      { stage: 'CLAIMED', timestamp: '08:51 AM', detail: 'Assigned in deterministic FIFO queue sequence.' },
      { stage: 'METADATA_CAPTURED', timestamp: '08:52 AM', detail: 'Git commit hash, branch, tags, and repo license captured.' },
      { stage: 'CONTENT_CAPTURED', timestamp: '08:53 AM', detail: 'Repository files, JSON API format specs, and rate-limiting params parsed.' },
      { stage: 'CONTENT_NORMALIZED', timestamp: '08:54 AM', detail: 'Generated clean canonical package.' },
      { stage: 'SUPABASE_WRITE_STARTED', timestamp: '08:54 AM', detail: 'Executing Supabase write.' },
      { stage: 'SUPABASE_WRITE_CONFIRMED', timestamp: '08:55 AM', detail: 'Write acknowledged. Verified readback completed in test store.' }
    ],

    downstreamAnalysis: {
      researchInterpretation: 'Provides self-hosted meta-search JSON endpoint without API key quotas. Directly applicable to Hermes Cloud worker evaluation.',
      alphaOpinion: 'Relevant to infrastructure capability, not quant trading.',
      expertRouting: 'Archive',
      expertResult: 'Spec filed in Systems / Hermes Cloud worker evaluation documentation.'
    },
    isPrototype: false
  },
  {
    id: 'res-seo-01',
    queueSequence: 105,
    origin: 'SCHEDULED_DISCOVERY',
    title: 'SEO Demand Signals: Autonomous AI Operating System Search Demand & Query Clusters',
    sourceUrl: 'https://trends.google.com/search_signals/nexus_os_clusters',
    sourceName: 'Search Engine Demand Ingestion Feed (Synthetic Prototype)',
    sourceType: 'SEO',
    status: 'FAILED_RETRYABLE',
    truthClass: 'PROTOTYPE',
    currentStage: 'CONTENT_CAPTURED',
    technicalDiagnostic: 'rate limited',
    processor: 'Worker-Research-01 (Oracle Cloud)',
    workerAvatar: 'WR',
    priority: 'Medium',
    createdAt: '08:55 AM Today',
    claimedAt: '08:56 AM Today',
    lastAttempt: '08:58 AM Today',
    retryCount: 2,
    failureReason: 'Upstream query provider returned HTTP 429: rate limit exceeded (exponential backoff pending for 3m 45s).',

    contentLength: '8.2 KB (partial JSON buffer - Prototype)',
    transcriptStatus: 'N/A',
    canonicalPackageId: 'pkg-seo-demand-105.json',
    supabaseRecordId: null,
    readbackResult: 'Pending',

    receipts: [
      { stage: 'DISCOVERED', timestamp: '08:55 AM', detail: 'Scheduled discovery scraped developer search query feed (Prototype).' },
      { stage: 'CLAIMED', timestamp: '08:56 AM', detail: 'Worker-Research-01 assigned from FIFO.' },
      { stage: 'METADATA_CAPTURED', timestamp: '08:57 AM', detail: 'Query cluster parameters and time range (Last-30-Days) captured.' },
      { stage: 'CONTENT_CAPTURED', timestamp: '08:58 AM', detail: 'HTTP 429 rate limit encountered on page 3 of query results.' }
    ],

    downstreamAnalysis: {
      researchInterpretation: 'Awaiting remaining query clusters before downstream synthesis.',
      alphaOpinion: 'Downstream gate pending full raw ingestion.',
      expertRouting: 'Marketing',
      expertResult: 'Pending exponential backoff retry.'
    },
    isPrototype: true
  },
  {
    id: 'res-doc-01',
    queueSequence: 106,
    origin: 'EXPERT_REQUEST',
    title: 'Documents: Supabase Row-Level Security Verification Guidelines & Multi-Tenant Isolation',
    sourceUrl: 'https://supabase.com/docs/guides/database/postgres/row-level-security',
    sourceName: 'Supabase Official Engineering Documentation (Synthetic Example)',
    sourceType: 'Documents',
    status: 'INGESTED',
    truthClass: 'TEST_CANARY',
    currentStage: 'SUPABASE_WRITE_CONFIRMED',
    technicalDiagnostic: 'Nominal',
    processor: 'Worker-Research-02 (Mac mini)',
    workerAvatar: 'W2',
    priority: 'High',
    createdAt: '09:00 AM Today',
    claimedAt: '09:01 AM Today',
    lastAttempt: '09:04 AM Today',
    retryCount: 0,
    failureReason: null,

    contentLength: '31.4 KB (normalized markdown & SQL examples)',
    transcriptStatus: 'N/A (Document ingestion path - Test Canary)',
    canonicalPackageId: 'pkg-doc-supabase-rls-106.json',
    supabaseRecordId: 'rec_sp_2026_0929_106',
    readbackResult: 'Verified',

    receipts: [
      { stage: 'DISCOVERED', timestamp: '09:00 AM', detail: 'Dispatched from Client Portal build dependency.' },
      { stage: 'CLAIMED', timestamp: '09:01 AM', detail: 'Claimed by Worker-Research-02 in FIFO sequence.' },
      { stage: 'METADATA_CAPTURED', timestamp: '09:02 AM', detail: 'Doc version, URL, author timestamp indexed.' },
      { stage: 'CONTENT_CAPTURED', timestamp: '09:02 AM', detail: 'Parsed full markdown text and 14 SQL policy snippets.' },
      { stage: 'CONTENT_NORMALIZED', timestamp: '09:03 AM', detail: 'Canonical package assembled with verified source hash.' },
      { stage: 'SUPABASE_WRITE_STARTED', timestamp: '09:03 AM', detail: 'Writing canonical package to Supabase.' },
      { stage: 'SUPABASE_WRITE_CONFIRMED', timestamp: '09:04 AM', detail: 'Supabase write confirmed and verified in test store.' }
    ],

    downstreamAnalysis: {
      researchInterpretation: 'RLS policies establish tenant isolation using auth.jwt() claims. Directly used to verify Client Portal authorization suite.',
      alphaOpinion: 'Security isolation verified for GoClear Client Portal release candidate.',
      expertRouting: 'Marketing',
      expertResult: 'Artifact referenced in Client Portal production deployment dossier.'
    },
    isPrototype: false
  },
  {
    id: 'res-web-01',
    queueSequence: 107,
    origin: 'SCHEDULED_DISCOVERY',
    title: 'Web Ingestion: Fedwire Funds Service ISO 20022 Migration Technical Specifications',
    sourceUrl: 'https://frbservices.org/resources/financial-services/wires/iso-20022-implementation',
    sourceName: 'Federal Reserve Financial Services Gateway (Synthetic Prototype)',
    sourceType: 'Web',
    status: 'QUEUED',
    truthClass: 'PROTOTYPE',
    currentStage: 'DISCOVERED',
    technicalDiagnostic: 'Nominal',
    processor: 'Unassigned (Awaiting FIFO dispatch)',
    workerAvatar: 'UN',
    priority: 'Medium',
    createdAt: '09:15 AM Today',
    claimedAt: null,
    lastAttempt: 'Not yet attempted',
    retryCount: 0,
    failureReason: null,

    contentLength: 'Pending fetch (Prototype)',
    transcriptStatus: 'N/A',
    canonicalPackageId: 'pkg-web-iso20022-107.json',
    supabaseRecordId: null,
    readbackResult: 'Pending',

    receipts: [
      { stage: 'DISCOVERED', timestamp: '09:15 AM', detail: 'Autonomous discovery appended Fedwire ISO 20022 URL to Universal FIFO (Prototype).' }
    ],

    downstreamAnalysis: {
      researchInterpretation: 'Pending mechanical ingestion.',
      alphaOpinion: 'Not yet analyzed.',
      expertRouting: 'Clyde (Funding)',
      expertResult: 'Pending.'
    },
    isPrototype: true
  },
  {
    id: 'res-web-02',
    queueSequence: 108,
    origin: 'SOURCE_MONITOR',
    title: 'Web Ingestion: Defunct Legacy Sandboxed Endpoint Reference',
    sourceUrl: 'https://testnet.legacy-clearing.invalid/v1/spec',
    sourceName: 'Archived Sandbox Provider (Synthetic Prototype)',
    sourceType: 'Web',
    status: 'FAILED_FINAL',
    truthClass: 'PROTOTYPE',
    currentStage: 'DISCOVERED',
    technicalDiagnostic: 'HTTP error',
    processor: 'Worker-Research-02 (Mac mini)',
    workerAvatar: 'W2',
    priority: 'Low',
    createdAt: '07:30 AM Today',
    claimedAt: '07:31 AM Today',
    lastAttempt: '07:35 AM Today',
    retryCount: 3,
    failureReason: 'HTTP 404 Not Found: Remote host permanently decommissioned. Final failure state confirmed (Prototype example).',

    contentLength: '0 KB',
    transcriptStatus: 'N/A',
    canonicalPackageId: 'pkg-web-defunct-108.json',
    supabaseRecordId: null,
    readbackResult: 'Failed',

    receipts: [
      { stage: 'DISCOVERED', timestamp: '07:30 AM', detail: 'Source monitor queued legacy endpoint (Prototype).' },
      { stage: 'CLAIMED', timestamp: '07:31 AM', detail: 'Worker-Research-02 attempted fetch.' },
      { stage: 'DISCOVERED', timestamp: '07:35 AM', detail: 'HTTP 404 permanent failure confirmed after 3 attempts.' }
    ],

    downstreamAnalysis: {
      researchInterpretation: 'Decommissioned endpoint. Excluded from downstream analysis.',
      alphaOpinion: 'Dropped.',
      expertRouting: 'Archive',
      expertResult: 'Marked dead in canonical registry.'
    },
    isPrototype: true
  }
];
