export type DataTruthClass = 'LIVE_VERIFIED' | 'TEST_CANARY' | 'PROTOTYPE';

export type ServiceHealthState = 'HEALTHY' | 'DEGRADED' | 'STALE' | 'STOPPED' | 'UNKNOWN';

export interface ServiceHealthItem {
  id: string;
  name: string;
  host: 'Mac mini' | 'Hermes Cloud / Oracle' | 'Remote / Cloud';
  state: ServiceHealthState;
  lastHeartbeat: string;
  lastSuccess: string;
  currentIncident: string | null;
  recoveryPolicy: string;
  truthClass: DataTruthClass;
  isPrototypeData: boolean;
}

export type FailureClass =
  | 'SERVICE_STOPPED'
  | 'LAUNCHD_JOB_MISSING'
  | 'STALE_LEASE'
  | 'ORPHAN_CLAIM'
  | 'KNOWN_TUNNEL_DOWN'
  | 'TRANSIENT_PROVIDER_TIMEOUT'
  | 'NETWORK_TIMEOUT'
  | 'RATE_LIMIT'
  | 'AUTH_REQUIRED'
  | 'UNKNOWN_FAILURE';

export interface ControlledRecoveryPolicy {
  id: string;
  action: string;
  failureClass: FailureClass;
  mode: 'AUTOMATIC' | 'ESCALATION_ONLY';
  maxAttempts: number;
  cooldown: string;
  verificationMethod: string;
  status: 'CERTIFIED_REAL' | 'TEST_CANARY' | 'ESCALATION_ONLY';
  truthClass: DataTruthClass;
}

export type RecoveryResult =
  | 'RECOVERED'
  | 'ESCALATED'
  | 'RETRYING'
  | 'HUMAN ACTION REQUIRED';

export interface RecoveryActivityItem {
  id: string;
  timestamp: string;
  service: string;
  incident: string;
  recoveryAction: string;
  result: RecoveryResult;
  verification: string;
  receiptId: string;
  truthClass: DataTruthClass;
  isPrototypeData: boolean;
}

export interface ActiveIncidentItem {
  id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  affectedService: string;
  failureClass: FailureClass;
  detectedAt: string;
  recoveryState: 'RECOVERING' | 'RETRYING' | 'ESCALATED_HUMAN' | 'BOUNDED_BACKOFF' | 'MONITORING';
  attempts: number;
  maxAttempts: number;
  currentImpact: string;
  owner: 'Systems Autonomy' | 'Ray Davis (Owner Action)';
  requiresHumanAction: boolean;
  truthClass: DataTruthClass;
  isPrototypeData: boolean;
}

export interface DepartmentOperationHealth {
  id: string;
  deptName: string;
  workerState: 'ONLINE' | 'ACTIVE' | 'IDLE' | 'DEGRADED';
  queueState: 'DRAINING' | 'NOMINAL' | 'BACKLOG' | 'STALLED';
  activeJobs: number;
  retryableJobs: number;
  stalledJobs: number;
  lastSuccess: string;
  systemsIncident: string | null;
  truthClass: DataTruthClass;
  isPrototypeData: boolean;
}

export type HandoffLifecycleStage =
  | 'CREATED'
  | 'DELIVERED'
  | 'ACKNOWLEDGED'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED_RETRYABLE'
  | 'FAILED_FINAL';

export interface DepartmentHandoffItem {
  id: string;
  sourceDept: string;
  targetDept: string;
  topic: string;
  status: HandoffLifecycleStage;
  created: string;
  acknowledged: string | null;
  processed: string | null;
  result: string;
  truthClass: DataTruthClass;
  isPrototypeData: boolean;
}

export type ProviderState = 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE' | 'TIMEOUT' | 'UNKNOWN';

export interface ProviderHealthItem {
  id: string;
  name: string;
  reachable: boolean;
  authenticated: boolean;
  rateLimited: boolean;
  lastCheck: string;
  lastSuccess: string;
  lastFailure: string | null;
  state: ProviderState;
  truthClass: DataTruthClass;
  notes?: string;
}

export interface OracleHealthTelemetry {
  hermes: 'ONLINE' | 'TESTING' | 'DEGRADED';
  ollama: 'ACTIVE' | 'BENCHMARKING' | 'IDLE';
  containers: string;
  disk: string;
  ram: string;
  tunnel: 'CONNECTED' | 'RECONNECTING' | 'TESTING';
  nexusMcp: 'HEALTHY' | 'DEGRADED';
  lastVerified: string;
  truthClass: DataTruthClass;
  isPrototypeData: boolean;
}

export interface HumanActionRequiredItem {
  id: string;
  issue: string;
  affectedCapability: string;
  whySystemsStopped: string;
  requiredAction: string;
  timeWaiting: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  truthClass: DataTruthClass;
}

export interface SafetyGuardrail {
  name: string;
  status: 'ENABLED' | 'DISABLED';
  behavior: 'POSITIVE_SAFETY' | 'RESTRICTIVE';
  description: string;
  truthClass: DataTruthClass;
}

// =========================================================================
// INITIAL VERIFIED SYSTEMS DATASETS
// =========================================================================

export const SYSTEMS_EXECUTIVE_SUMMARY = {
  status: 'OPERATIONAL',
  subStatus: 'Controlled Recovery Certified',
  p0Status: 'PASS',
  p1Status: 'PASS_REAL',
  certifiedPhases: [
    'DETECTION_AND_DURABLE_HANDOFF=PASS',
    'CONTROLLED_RECOVERY=PASS_REAL'
  ],
  truthClass: 'LIVE_VERIFIED' as DataTruthClass,
  supportingCopy:
    'Monitors Nexus services, workers, dependencies, incidents, recovery actions, and cross-department operational health.',
  metrics: {
    servicesMonitored: 13,
    activeIncidents: 2,
    recoveriesToday: 7,
    humanActionRequired: 1,
    isPrototypeData: true
  }
};

export const SYSTEMS_SAFETY_GUARDRAILS: SafetyGuardrail[] = [
  {
    name: 'Arbitrary Shell Execution',
    status: 'DISABLED',
    behavior: 'RESTRICTIVE',
    description: 'Autonomous workers cannot run unsanctioned bash or shell scripts.',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    name: 'Destructive Auto Recovery',
    status: 'DISABLED',
    behavior: 'RESTRICTIVE',
    description: 'No database drop, volume wipe, or branch force-push permitted in auto recovery.',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    name: 'Unknown Failure Auto Recovery',
    status: 'DISABLED',
    behavior: 'RESTRICTIVE',
    description: 'Unclassified error codes immediately halt and escalate to owner judgment.',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    name: 'Authentication Bypass',
    status: 'DISABLED',
    behavior: 'RESTRICTIVE',
    description: 'Expired sessions or 401/403 states always require explicit human credentials.',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    name: 'Recovery Receipts',
    status: 'ENABLED',
    behavior: 'POSITIVE_SAFETY',
    description: 'Immutable JSON receipts persisted to audit log prior to service restart acknowledgment.',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    name: 'Recovery Loop Protection',
    status: 'ENABLED',
    behavior: 'POSITIVE_SAFETY',
    description: 'Circuit breaker trips on 3 failed attempts within a 15-minute sliding window.',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    name: 'Human Escalation',
    status: 'ENABLED',
    behavior: 'POSITIVE_SAFETY',
    description: 'Direct alert dispatch to Nova feed and Command Center owner judgment queue.',
    truthClass: 'LIVE_VERIFIED'
  }
];

export const INITIAL_SERVICES: ServiceHealthItem[] = [
  {
    id: 'srv-cok',
    name: 'Continuous Operating Kernel',
    host: 'Mac mini',
    state: 'HEALTHY',
    lastHeartbeat: '8s ago',
    lastSuccess: '8s ago',
    currentIncident: null,
    recoveryPolicy: 'Launchd Restart (Max 3, 30s cd)',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-res-cons',
    name: 'Research Consumer',
    host: 'Mac mini',
    state: 'HEALTHY',
    lastHeartbeat: '14s ago',
    lastSuccess: '45s ago',
    currentIncident: null,
    recoveryPolicy: 'Queue lease release & worker restart',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-res-disc',
    name: 'Research Discovery',
    host: 'Mac mini',
    state: 'HEALTHY',
    lastHeartbeat: '32s ago',
    lastSuccess: '2m ago',
    currentIncident: null,
    recoveryPolicy: 'Cron reschedule & backoff probe',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-hermes-gw',
    name: 'Hermes Gateway',
    host: 'Mac mini',
    state: 'HEALTHY',
    lastHeartbeat: '5s ago',
    lastSuccess: '5s ago',
    currentIncident: null,
    recoveryPolicy: 'Launchd Reload (Max 3, 60s cd)',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-mcp-bridge',
    name: 'Nexus MCP Bridge',
    host: 'Mac mini',
    state: 'HEALTHY',
    lastHeartbeat: '12s ago',
    lastSuccess: '12s ago',
    currentIncident: null,
    recoveryPolicy: 'Socket reopen & handshake verify',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-notebook-mcp',
    name: 'Notebook MCP',
    host: 'Mac mini',
    state: 'DEGRADED',
    lastHeartbeat: '18s ago',
    lastSuccess: '4m ago',
    currentIncident: 'Transient socket timeout on python kernel runner',
    recoveryPolicy: 'Re-bind local port & ping RPC',
    truthClass: 'TEST_CANARY',
    isPrototypeData: true
  },
  {
    id: 'srv-oracle-hermes',
    name: 'Oracle · Nova / Hermes Coordination',
    host: 'Hermes Cloud / Oracle',
    state: 'HEALTHY',
    lastHeartbeat: '9s ago',
    lastSuccess: '9s ago',
    currentIncident: null,
    recoveryPolicy: 'Reserved strictly for Nova/Hermes & essential coordination',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-contabo-n8n',
    name: 'Contabo · n8n & Postiz Workers',
    host: 'Remote / Cloud',
    state: 'HEALTHY',
    lastHeartbeat: '14s ago',
    lastSuccess: '2m ago',
    currentIncident: null,
    recoveryPolicy: 'Container health probe & webhook replay',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-ollama',
    name: 'Ollama Local Metal (Mac mini)',
    host: 'Mac mini',
    state: 'HEALTHY',
    lastHeartbeat: '22s ago',
    lastSuccess: '22s ago',
    currentIncident: null,
    recoveryPolicy: 'Launchd local inference restart',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-trad-wrk',
    name: 'Trading R1 Core (Paper)',
    host: 'Mac mini',
    state: 'HEALTHY',
    lastHeartbeat: '11s ago',
    lastSuccess: '9m ago',
    currentIncident: null,
    recoveryPolicy: 'Circuit breaker & OANDA Practice reconciler',
    truthClass: 'TEST_CANARY',
    isPrototypeData: false
  },
  {
    id: 'srv-commerce-stripe',
    name: 'Commerce · Printify & Stripe Gate',
    host: 'Remote / Cloud',
    state: 'STOPPED',
    lastHeartbeat: '38m ago',
    lastSuccess: '38m ago',
    currentIncident: 'Live checkout BLOCKED: missing real Stripe test credential/certification',
    recoveryPolicy: 'Awaiting Stripe test credential & Stage B approval',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  },
  {
    id: 'srv-mkt-wrk',
    name: 'Marketing & Facebook Integration',
    host: 'Remote / Cloud',
    state: 'UNKNOWN',
    lastHeartbeat: '12m ago',
    lastSuccess: 'Unlinked',
    currentIncident: 'Facebook direct API NOT_CONNECTED; routing Stage A via Postiz',
    recoveryPolicy: 'Awaiting Meta OAuth or Postiz Stage A release',
    truthClass: 'PROTOTYPE',
    isPrototypeData: false
  },
  {
    id: 'srv-cre-wrk',
    name: 'Creative Services',
    host: 'Remote / Cloud',
    state: 'HEALTHY',
    lastHeartbeat: '45s ago',
    lastSuccess: '2h ago',
    currentIncident: null,
    recoveryPolicy: 'Retry registered provider API',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  }
];

export const CONTROLLED_RECOVERY_POLICIES: ControlledRecoveryPolicy[] = [
  // AUTOMATIC / VERIFIED
  {
    id: 'pol-auto-1',
    action: 'Restart Approved Launchd Service',
    failureClass: 'SERVICE_STOPPED',
    mode: 'AUTOMATIC',
    maxAttempts: 3,
    cooldown: '30s',
    verificationMethod: 'Process PID check + socket handshake readback',
    status: 'CERTIFIED_REAL',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    id: 'pol-auto-2',
    action: 'Reload Approved Launchd Job',
    failureClass: 'LAUNCHD_JOB_MISSING',
    mode: 'AUTOMATIC',
    maxAttempts: 2,
    cooldown: '45s',
    verificationMethod: 'launchctl list grep verification',
    status: 'CERTIFIED_REAL',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    id: 'pol-auto-3',
    action: 'Recover Stale Lease',
    failureClass: 'STALE_LEASE',
    mode: 'AUTOMATIC',
    maxAttempts: 2,
    cooldown: '60s',
    verificationMethod: 'Atomic TTL lease reclaim in Supabase queue table',
    status: 'CERTIFIED_REAL',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    id: 'pol-auto-4',
    action: 'Retry Registered Dependency',
    failureClass: 'TRANSIENT_PROVIDER_TIMEOUT',
    mode: 'AUTOMATIC',
    maxAttempts: 4,
    cooldown: 'Exponential (10s, 30s, 90s)',
    verificationMethod: 'HTTP HEAD 200/204 response confirmation',
    status: 'CERTIFIED_REAL',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    id: 'pol-auto-5',
    action: 'Requeue Retryable Work',
    failureClass: 'ORPHAN_CLAIM',
    mode: 'AUTOMATIC',
    maxAttempts: 3,
    cooldown: '15s',
    verificationMethod: 'Queue consumer heartbeat confirmed',
    status: 'CERTIFIED_REAL',
    truthClass: 'LIVE_VERIFIED'
  },

  // BOUNDARY / ESCALATION
  {
    id: 'pol-esc-1',
    action: 'Restore Known Tunnel',
    failureClass: 'KNOWN_TUNNEL_DOWN',
    mode: 'ESCALATION_ONLY',
    maxAttempts: 1,
    cooldown: '120s',
    verificationMethod: 'Ping Oracle private subnet endpoint (Uncertified in prod)',
    status: 'TEST_CANARY',
    truthClass: 'TEST_CANARY'
  },
  {
    id: 'pol-esc-2',
    action: 'Restart Approved Container',
    failureClass: 'SERVICE_STOPPED',
    mode: 'ESCALATION_ONLY',
    maxAttempts: 1,
    cooldown: '60s',
    verificationMethod: 'Stateless container hash validation (Escalation-only)',
    status: 'TEST_CANARY',
    truthClass: 'TEST_CANARY'
  },
  {
    id: 'pol-esc-3',
    action: 'Relaunch Approved Browser Profile',
    failureClass: 'AUTH_REQUIRED',
    mode: 'ESCALATION_ONLY',
    maxAttempts: 1,
    cooldown: 'Manual',
    verificationMethod: 'CDP endpoint inspection + Human cookie session verify',
    status: 'ESCALATION_ONLY',
    truthClass: 'TEST_CANARY'
  },
  {
    id: 'pol-esc-4',
    action: 'Clear Transient Lock',
    failureClass: 'UNKNOWN_FAILURE',
    mode: 'ESCALATION_ONLY',
    maxAttempts: 1,
    cooldown: 'Manual',
    verificationMethod: 'Safety boundary check prevents arbitrary file unlock',
    status: 'ESCALATION_ONLY',
    truthClass: 'LIVE_VERIFIED'
  }
];

export const INITIAL_RECOVERY_ACTIVITY: RecoveryActivityItem[] = [
  {
    id: 'rec-01',
    timestamp: '19:42:15',
    service: 'Research Consumer',
    incident: 'Worker heartbeat missed (stale lease on item #105)',
    recoveryAction: 'Recover Stale Lease & Requeue in FIFO',
    result: 'RECOVERED',
    verification: 'Supabase TTL atomic lock cleared; claimed by Worker-01',
    receiptId: 'rcpt_7f3b89a_001',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: true
  },
  {
    id: 'rec-02',
    timestamp: '19:15:02',
    service: 'Hermes Gateway',
    incident: 'Daemon unresponsive to SIGUSR1 probe',
    recoveryAction: 'Restart Approved Launchd Service (launchctl kickstart)',
    result: 'RECOVERED',
    verification: 'PID 84102 established; socket /tmp/hermes.sock responding',
    receiptId: 'rcpt_7f3b89a_002',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: true
  },
  {
    id: 'rec-03',
    timestamp: '18:48:33',
    service: 'Notebook MCP',
    incident: 'Transient Python kernel timeout (HTTP 504)',
    recoveryAction: 'Retry Registered Dependency (attempt 2 of 4)',
    result: 'RETRYING',
    verification: 'Kernel socket backoff active; awaiting port bind',
    receiptId: 'rcpt_7f3b89a_003',
    truthClass: 'TEST_CANARY',
    isPrototypeData: true
  },
  {
    id: 'rec-04',
    timestamp: '18:02:11',
    service: 'Oracle Tunnel',
    incident: 'WireGuard tunnel keepalive packet loss > 40%',
    recoveryAction: 'Restore Known Tunnel (Boundary Escalation)',
    result: 'ESCALATED',
    verification: 'Live interruption certification pending; notified Nova',
    receiptId: 'rcpt_7f3b89a_004',
    truthClass: 'TEST_CANARY',
    isPrototypeData: true
  },
  {
    id: 'rec-05',
    timestamp: '17:20:45',
    service: 'Clyde Grants Worker',
    incident: 'State grant portal endpoint requires 2FA authentication',
    recoveryAction: 'Halt automated execution (Auth Bypass Disabled)',
    result: 'HUMAN ACTION REQUIRED',
    verification: 'Safety guardrail enforced; awaiting Ray credential input',
    receiptId: 'rcpt_7f3b89a_005',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: true
  }
];

export const INITIAL_ACTIVE_INCIDENTS: ActiveIncidentItem[] = [
  {
    id: 'inc-01',
    severity: 'MEDIUM',
    affectedService: 'Oracle Tunnel',
    failureClass: 'KNOWN_TUNNEL_DOWN',
    detectedAt: '3m ago',
    recoveryState: 'BOUNDED_BACKOFF',
    attempts: 1,
    maxAttempts: 2,
    currentImpact: 'Remote Oracle ASR evaluation latency increased by 180ms',
    owner: 'Systems Autonomy',
    requiresHumanAction: false,
    truthClass: 'TEST_CANARY',
    isPrototypeData: true
  },
  {
    id: 'inc-02',
    severity: 'HIGH',
    affectedService: 'Funding / Clyde Workers',
    failureClass: 'AUTH_REQUIRED',
    detectedAt: '28m ago',
    recoveryState: 'ESCALATED_HUMAN',
    attempts: 0,
    maxAttempts: 0,
    currentImpact: 'Grant filing package submission paused at state credential gate',
    owner: 'Ray Davis (Owner Action)',
    requiresHumanAction: true,
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: true
  }
];

export const INITIAL_DEPARTMENT_OPERATIONS: DepartmentOperationHealth[] = [
  {
    id: 'dept-res',
    deptName: 'Research',
    workerState: 'ACTIVE',
    queueState: 'DRAINING',
    activeJobs: 2,
    retryableJobs: 1,
    stalledJobs: 0,
    lastSuccess: '45s ago (Ingested #104)',
    systemsIncident: null,
    truthClass: 'TEST_CANARY',
    isPrototypeData: true
  },
  {
    id: 'dept-trad',
    deptName: 'Trading',
    workerState: 'ACTIVE',
    queueState: 'NOMINAL',
    activeJobs: 1,
    retryableJobs: 0,
    stalledJobs: 0,
    lastSuccess: '1m ago (Paper tick fill #982)',
    systemsIncident: null,
    truthClass: 'TEST_CANARY',
    isPrototypeData: true
  },
  {
    id: 'dept-clyde',
    deptName: 'Funding / Clyde',
    workerState: 'DEGRADED',
    queueState: 'STALLED',
    activeJobs: 0,
    retryableJobs: 0,
    stalledJobs: 1,
    lastSuccess: '1h 14m ago',
    systemsIncident: 'Auth Required (Grant portal credential)',
    truthClass: 'PROTOTYPE',
    isPrototypeData: true
  },
  {
    id: 'dept-mkt',
    deptName: 'Marketing',
    workerState: 'IDLE',
    queueState: 'NOMINAL',
    activeJobs: 0,
    retryableJobs: 0,
    stalledJobs: 0,
    lastSuccess: '18m ago (SEO trend batch)',
    systemsIncident: null,
    truthClass: 'PROTOTYPE',
    isPrototypeData: true
  },
  {
    id: 'dept-cre',
    deptName: 'Creative',
    workerState: 'ACTIVE',
    queueState: 'DRAINING',
    activeJobs: 1,
    retryableJobs: 0,
    stalledJobs: 0,
    lastSuccess: '3m ago (Token pack export)',
    systemsIncident: null,
    truthClass: 'PROTOTYPE',
    isPrototypeData: true
  },
  {
    id: 'dept-nova',
    deptName: 'Nova',
    workerState: 'ONLINE',
    queueState: 'NOMINAL',
    activeJobs: 1,
    retryableJobs: 0,
    stalledJobs: 0,
    lastSuccess: 'Just now (Incident alert dispatch)',
    systemsIncident: null,
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: false
  }
];

export const INITIAL_DEPARTMENT_HANDOFFS: DepartmentHandoffItem[] = [
  {
    id: 'hnd-01',
    sourceDept: 'Research',
    targetDept: 'Systems',
    topic: 'ASR Benchmark Engine Latency Manifest',
    status: 'COMPLETED',
    created: '19:20',
    acknowledged: '19:21',
    processed: '19:22',
    result: 'Logged telemetry to Oracle benchmark evaluation suite',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: true
  },
  {
    id: 'hnd-02',
    sourceDept: 'Systems',
    targetDept: 'Research',
    topic: 'Stale Lease #105 Recovery Notification',
    status: 'COMPLETED',
    created: '19:42',
    acknowledged: '19:42',
    processed: '19:43',
    result: 'Item #105 unlocked and returned to FIFO queue head',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: true
  },
  {
    id: 'hnd-03',
    sourceDept: 'Systems',
    targetDept: 'Nova',
    topic: 'Incident Alert: Clyde 2FA Auth Required',
    status: 'DELIVERED',
    created: '19:35',
    acknowledged: '19:35',
    processed: null,
    result: 'Rendered in executive action feed for Ray',
    truthClass: 'LIVE_VERIFIED',
    isPrototypeData: true
  },
  {
    id: 'hnd-04',
    sourceDept: 'Trading',
    targetDept: 'Systems',
    topic: 'Paper Engine Heartbeat Slip Telemetry',
    status: 'ACKNOWLEDGED',
    created: '19:50',
    acknowledged: '19:51',
    processed: null,
    result: 'Awaiting log rotation window',
    truthClass: 'TEST_CANARY',
    isPrototypeData: true
  },
  {
    id: 'hnd-05',
    sourceDept: 'Creative',
    targetDept: 'Systems',
    topic: 'Provider Latency Exceeded Notice (Replicate/HF)',
    status: 'PROCESSING',
    created: '19:45',
    acknowledged: '19:46',
    processed: null,
    result: 'Probing Hugging Face endpoint health',
    truthClass: 'PROTOTYPE',
    isPrototypeData: true
  }
];

export const INITIAL_PROVIDERS_HEALTH: ProviderHealthItem[] = [
  {
    id: 'prov-supabase',
    name: 'Supabase',
    reachable: true,
    authenticated: true,
    rateLimited: false,
    lastCheck: '10s ago',
    lastSuccess: '10s ago',
    lastFailure: null,
    state: 'HEALTHY',
    notes: 'PostgreSQL connection pool healthy; RLS readback active',
    truthClass: 'LIVE_VERIFIED'
  },
  {
    id: 'prov-oracle-hermes',
    name: 'Oracle Hermes',
    reachable: true,
    authenticated: true,
    rateLimited: false,
    lastCheck: '15s ago',
    lastSuccess: '15s ago',
    lastFailure: null,
    state: 'HEALTHY',
    notes: 'Compute worker environment responding on internal port',
    truthClass: 'TEST_CANARY'
  },
  {
    id: 'prov-oracle-tunnel',
    name: 'Oracle Tunnel',
    reachable: true,
    authenticated: true,
    rateLimited: false,
    lastCheck: '30s ago',
    lastSuccess: '3m ago',
    lastFailure: 'Jitter latency > 180ms',
    state: 'DEGRADED',
    notes: 'Keepalive packets delayed; auto-reconnect backoff monitoring',
    truthClass: 'TEST_CANARY'
  },
  {
    id: 'prov-notebook-mcp',
    name: 'Notebook MCP',
    reachable: true,
    authenticated: true,
    rateLimited: false,
    lastCheck: '18s ago',
    lastSuccess: '4m ago',
    lastFailure: '504 Gateway Timeout',
    state: 'DEGRADED',
    notes: 'Kernel reconnect in progress on Mac mini host',
    truthClass: 'TEST_CANARY'
  },
  {
    id: 'prov-modal',
    name: 'Modal',
    reachable: true,
    authenticated: true,
    rateLimited: false,
    lastCheck: '2m ago',
    lastSuccess: '2m ago',
    lastFailure: null,
    state: 'HEALTHY',
    notes: 'GPU container probe configured (Standby)',
    truthClass: 'TEST_CANARY'
  },
  {
    id: 'prov-ollama',
    name: 'Ollama',
    reachable: true,
    authenticated: true,
    rateLimited: false,
    lastCheck: '45s ago',
    lastSuccess: '45s ago',
    lastFailure: null,
    state: 'HEALTHY',
    notes: 'Local LLM inference socket nominal on Oracle instance',
    truthClass: 'TEST_CANARY'
  },
  {
    id: 'prov-hf',
    name: 'Hugging Face',
    reachable: true,
    authenticated: true,
    rateLimited: true,
    lastCheck: '1m ago',
    lastSuccess: '5m ago',
    lastFailure: 'HTTP 429 Rate Limited',
    state: 'DEGRADED',
    notes: 'Backoff timer 120s remaining before next poll',
    truthClass: 'PROTOTYPE'
  },
  {
    id: 'prov-kaggle',
    name: 'Kaggle',
    reachable: false,
    authenticated: false,
    rateLimited: false,
    lastCheck: '10m ago',
    lastSuccess: 'Never',
    lastFailure: 'Credentials unconfigured',
    state: 'UNKNOWN',
    notes: 'API key not configured in environment (Unprobed)',
    truthClass: 'PROTOTYPE'
  },
  {
    id: 'prov-openrouter',
    name: 'OpenRouter',
    reachable: true,
    authenticated: true,
    rateLimited: false,
    lastCheck: '1m ago',
    lastSuccess: '1m ago',
    lastFailure: null,
    state: 'HEALTHY',
    notes: 'Model fallback proxy operational',
    truthClass: 'PROTOTYPE'
  }
];

export const INITIAL_ORACLE_HEALTH: OracleHealthTelemetry = {
  hermes: 'ONLINE',
  ollama: 'ACTIVE',
  containers: '4 active (stateless evaluation)',
  disk: '32% (48 GB / 150 GB)',
  ram: '41% (6.5 GB / 16 GB)',
  tunnel: 'CONNECTED',
  nexusMcp: 'HEALTHY',
  lastVerified: '12s ago (Isolated heartbeat probe)',
  truthClass: 'TEST_CANARY',
  isPrototypeData: true
};

export const INITIAL_HUMAN_ACTIONS: HumanActionRequiredItem[] = [
  {
    id: 'act-01',
    issue: 'State Innovation Grant Portal 2FA Required',
    affectedCapability: 'Funding / Clyde Worker Automated Submission',
    whySystemsStopped:
      'Authentication Bypass is strictly DISABLED by safety guardrails. Systems cannot generate SMS or authenticator tokens.',
    requiredAction:
      'Provide owner 2FA verification code in Clyde Department or complete manual portal login.',
    timeWaiting: '28m',
    severity: 'HIGH',
    truthClass: 'LIVE_VERIFIED'
  }
];
