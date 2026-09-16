export type UserRole = 'ADMIN' | 'MAINTAINER' | 'DEVELOPER';

export interface DecodedToken {
  sub: string;
  role: UserRole;
  id: number;
  exp?: number;
  iat?: number;
}

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  auth_provider?: string;
  is_active?: boolean;
  picture_url?: string | null;
  created_at?: string;
}

export interface KnownAccount {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  picture_url?: string | null;
  auth_provider?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  email: string;
  full_name: string;
  picture_url?: string | null;
}

export interface CodeIssue {
  file_path: string;
  line_number: number;
  issue_type: 'SYNTAX' | 'IMPORT' | 'LINT' | 'LOGIC' | 'RUNTIME' | string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
}

export interface PatchAction {
  file_path: string;
  original_snippet: string;
  replacement_snippet: string;
  explanation: string;
}

export interface PRRecordSummary {
  id: number;
  repo: string;
  pr_number: number;
  title: string;
  status: 'RECEIVED' | 'ANALYZING' | 'HEALED' | 'FAILED' | string;
  timestamp: string;
  confidence: number | null;
  summary?: string | null;
  commit_sha?: string | null;
}

export interface PRRecordDetail extends PRRecordSummary {
  issues: CodeIssue[];
  patches: PatchAction[];
  ast_valid?: boolean;
  ast_logs?: string;
}

export interface PRStats {
  total: number;
  healed: number;
  analyzing: number;
  failed?: number;
  success_rate: number;
  avg_confidence: number;
}

export interface SandboxSimulateResult {
  success: boolean;
  ast_valid: boolean;
  ast_logs: string;
  confidence: number;
  summary: string;
  issues: CodeIssue[];
  patches: PatchAction[];
  diff?: {
    before: string;
    after: string;
  };
}

export interface AdminRepository {
  id: number;
  full_name: string;
  webhook_secret: string;
  is_active: boolean;
  auto_commit_enabled: boolean;
  created_by_id?: number | null;
  pr_count: number;
  webhook_status: string;
}

export interface TokenUsagePoint {
  timestamp: string;
  tokens: number;
  cost: number;
}

export interface AdminTelemetry {
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    history: TokenUsagePoint[];
  };
  llm_health: {
    success_count: number;
    failure_count: number;
    active_runs: number;
    error_rate_pct: number;
    avg_latency_sec: number;
    current_model: string;
  };
  runtime_config: LLMConfig;
  audit_logs: {
    id: number;
    timestamp: string;
    actor: string;
    action: string;
    status: string;
    details: string;
  }[];
}

export interface LLMConfig {
  model_target: string;
  confidence_threshold: number;
  rate_limit_rpm: number;
  ast_sandboxing: boolean;
  auto_commit_global: boolean;
}

// ---------------------------------------------------------------------------
// 3-Agent Event-Driven Pipeline Types
// ---------------------------------------------------------------------------

export interface AgentStepTrace {
  step_number: number;
  agent_name: string;
  action: string;
  status: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface PatchDetail {
  file_path: string;
  line_number: number;
  error_type: string;
  original_code: string;
  repaired_code: string;
  explanation: string;
}

export interface DiagnosticRepairResult {
  success: boolean;
  target_file: string;
  identified_line_numbers: number[];
  intercepted_errors: string[];
  root_cause_reasoning: string;
  surgical_diff: string;
  patches_applied: PatchDetail[];
  file_updated_on_disk: boolean;
}

export interface TestRunResult {
  passed: boolean;
  exit_code: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_type?: string | null;
  stack_trace: string;
  raw_output: string;
  failing_tests: string[];
  duration_seconds: number;
  summary: string;
}

export interface VerificationResult {
  is_verified: boolean;
  pass_rate_percent: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  execution_time_seconds: number;
  verification_output: string;
  summary: string;
}

export interface VisualDiagnosticTrace {
  pipeline_status: 'HEALED' | 'PASS' | 'FAILED' | string;
  target_file: string;
  test_target: string;
  total_iterations: number;
  total_duration_seconds: number;
  initial_failure?: TestRunResult | null;
  repairs: DiagnosticRepairResult[];
  final_verification: VerificationResult | null;
  trace_steps: AgentStepTrace[];
  diagnostic_summary: string;
}

