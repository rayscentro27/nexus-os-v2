/**
 * Nexus OS v2 — Hermes Work Router / Department Dispatcher
 * Prompt 2: Phase I
 *
 * Classifies natural-language prompts and routes them to the correct
 * department, process, and activation mode.
 */

import { ActivationMode } from './nexusActivationModes';
import { NEXUS_PROCESS_REGISTRY } from './nexusProcessRegistry';

export type DepartmentId =
  | 'command_center' | 'alpha_strategy' | 'nexus_hermes' | 'app'
  | 'landing_pages' | 'client_portal' | 'credit_readiness' | 'business_setup'
  | 'funding_grants' | 'research' | 'youtube_research' | 'notebooklm'
  | 'marketing' | 'creative_studio' | 'affiliate' | 'email'
  | 'social_video' | 'trading' | 'billing_referral' | 'system_health'
  | 'ray_review' | 'recovery' | 'telegram';

export interface WorkOrder {
  work_order_id: string;
  created_at: string;
  created_by: 'ray' | 'system' | 'alpha' | 'hermes';
  source_prompt: string;
  department: DepartmentId;
  process_id: string;
  activation_mode: ActivationMode;
  assigned_tool: 'codex' | 'kilo' | 'opencode' | 'manual' | 'script' | 'nexus' | 'alpha' | 'hermes';
  responsibilities: string[];
  dependencies: string[];
  expected_outputs: string[];
  status: string;
  current_phase: string;
  last_successful_step: string;
  changed_files: string[];
  test_status: string;
  interruption_reason: string;
  recovery_prompt: string;
  ray_review_required: boolean;
  receipt_id: string;
}

export interface RoutingDecision {
  department: DepartmentId;
  process_id: string;
  activation_mode: ActivationMode;
  confidence: number;
  reasoning: string;
  responsibilities: string[];
  expected_outputs: string[];
  ray_review_required: boolean;
  recovery_prompt: string;
}

// Intent classification patterns
const INTENT_PATTERNS: Array<{
  pattern: RegExp;
  department: DepartmentId;
  process_id: string;
  mode: ActivationMode;
  confidence: number;
}> = [
  // Research
  { pattern: /research|find|discover|explore|investigate/i, department: 'research', process_id: 'alpha_research_intake', mode: 'DRY_RUN', confidence: 0.7 },
  { pattern: /youtube|video|channel|transcript/i, department: 'youtube_research', process_id: 'youtube_researcher', mode: 'DRY_RUN', confidence: 0.8 },
  { pattern: /notebook|notebooklm|export|import.*research/i, department: 'notebooklm', process_id: 'notebooklm_importer', mode: 'OBSERVE', confidence: 0.8 },

  // Client
  { pattern: /client|portal|onboard|credit.*profile|business.*setup/i, department: 'client_portal', process_id: 'client_portal', mode: 'OBSERVE', confidence: 0.7 },
  { pattern: /credit.*repair|dispute|credit.*score/i, department: 'credit_readiness', process_id: 'client_portal', mode: 'OBSERVE', confidence: 0.7 },
  { pattern: /funding|grant|apply.*fund/i, department: 'funding_grants', process_id: 'client_portal', mode: 'OBSERVE', confidence: 0.7 },

  // Marketing
  { pattern: /marketing|campaign|content|post|social|tiktok|instagram/i, department: 'marketing', process_id: 'creative_engine', mode: 'DRY_RUN', confidence: 0.7 },
  { pattern: /creative|video.*package|script|storyboard|hook/i, department: 'creative_studio', process_id: 'creative_engine', mode: 'DRY_RUN', confidence: 0.8 },
  { pattern: /email|newsletter|resend/i, department: 'email', process_id: 'email_sandbox', mode: 'DRY_RUN', confidence: 0.7 },
  { pattern: /seo|keyword|landing.*page|funnel/i, department: 'marketing', process_id: 'creative_engine', mode: 'DRY_RUN', confidence: 0.7 },

  // System
  { pattern: /health|status|system|monitor/i, department: 'system_health', process_id: 'system_health_check', mode: 'OBSERVE', confidence: 0.8 },
  { pattern: /review|approve|reject|ray/i, department: 'ray_review', process_id: 'ray_review_queue', mode: 'OBSERVE', confidence: 0.8 },
  { pattern: /report|audit|summary/i, department: 'system_health', process_id: 'report_generation', mode: 'DRY_RUN', confidence: 0.7 },

  // Trading
  { pattern: /trade|trading|backtest|strategy|oanda/i, department: 'trading', process_id: 'trading_lab', mode: 'SANDBOX_TEST', confidence: 0.8 },

  // App
  { pattern: /app|build.*app|create.*app|feature/i, department: 'app', process_id: 'app_department', mode: 'DRY_RUN', confidence: 0.6 },

  // Billing
  { pattern: /stripe|billing|subscription|payment|paywall/i, department: 'billing_referral', process_id: 'client_portal', mode: 'SANDBOX_TEST', confidence: 0.7 },

  // Alpha
  { pattern: /alpha|strategy|opportunity|score|evaluate/i, department: 'alpha_strategy', process_id: 'alpha_strategy_brain', mode: 'SANDBOX_TEST', confidence: 0.7 },

  // Recovery
  { pattern: /recover|interrupt|crash|fail|stuck/i, department: 'recovery', process_id: 'self_audit_monitor', mode: 'OBSERVE', confidence: 0.8 },

  // Telegram
  { pattern: /telegram|tg|bot.*message/i, department: 'telegram', process_id: 'telegram_readiness', mode: 'OBSERVE', confidence: 0.8 },
];

export function classifyIntent(prompt: string): RoutingDecision {
  const normalized = prompt.toLowerCase().trim();

  for (const entry of INTENT_PATTERNS) {
    if (entry.pattern.test(normalized)) {
      const process = NEXUS_PROCESS_REGISTRY.find(p => p.process_id === entry.process_id);
      return {
        department: entry.department,
        process_id: entry.process_id,
        activation_mode: entry.mode,
        confidence: entry.confidence,
        reasoning: `Matched pattern: ${entry.pattern.source}`,
        responsibilities: process ? [process.name] : [],
        expected_outputs: process ? process.output_files : [],
        ray_review_required: process?.ray_review_required ?? false,
        recovery_prompt: process?.recovery_prompt ?? '',
      };
    }
  }

  // Default: route to Hermes for general processing
  return {
    department: 'nexus_hermes',
    process_id: 'hermes_work_router',
    activation_mode: 'SANDBOX_TEST',
    confidence: 0.3,
    reasoning: 'No specific pattern matched; defaulting to Hermes operations brain',
    responsibilities: ['General processing'],
    expected_outputs: [],
    ray_review_required: false,
    recovery_prompt: 'Reclassify prompt with more specific intent',
  };
}

let workOrderCounter = 0;

export function createWorkOrder(
  prompt: string,
  decision: RoutingDecision,
  createdBy: 'ray' | 'system' | 'alpha' | 'hermes' = 'ray'
): WorkOrder {
  workOrderCounter++;
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 6);
  return {
    work_order_id: `wo_${ts}_${rand}_${workOrderCounter}`,
    created_at: new Date().toISOString(),
    created_by: createdBy,
    source_prompt: prompt,
    department: decision.department,
    process_id: decision.process_id,
    activation_mode: decision.activation_mode,
    assigned_tool: 'opencode',
    responsibilities: decision.responsibilities,
    dependencies: [],
    expected_outputs: decision.expected_outputs,
    status: 'ready',
    current_phase: 'initiated',
    last_successful_step: '',
    changed_files: [],
    test_status: '',
    interruption_reason: '',
    recovery_prompt: decision.recovery_prompt,
    ray_review_required: decision.ray_review_required,
    receipt_id: '',
  };
}

export function getHermesResponse(prompt: string): {
  department: string;
  process: string;
  mode: string;
  confidence: number;
  reasoning: string;
  ray_review: boolean;
  recovery: string;
} {
  const decision = classifyIntent(prompt);
  return {
    department: decision.department,
    process: decision.process_id,
    mode: decision.activation_mode,
    confidence: decision.confidence,
    reasoning: decision.reasoning,
    ray_review: decision.ray_review_required,
    recovery: decision.recovery_prompt,
  };
}
