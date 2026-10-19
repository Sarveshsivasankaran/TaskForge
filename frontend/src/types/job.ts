export type JobStatus = 
  | 'queued' 
  | 'running' 
  | 'succeeded' 
  | 'failed' 
  | 'retry_wait' 
  | 'dead_letter' 
  | 'cancelled';

export interface Job {
  id: string;
  job_type: string;
  status: JobStatus;
  payload: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  max_retries: number;
  attempt_count: number;
  timeout_seconds: number;
  lease_owner?: string | null;
  lease_expires_at?: string | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  version: number;
  user_id?: string | null;
  owner_id?: string | null;
}

export interface JobAttempt {
  id: string;
  job_id: string;
  attempt_number: number;
  worker_id: string;
  status: 'running' | 'succeeded' | 'failed';
  error_message?: string | null;
  error_details?: Record<string, unknown> | null;
  duration_ms?: number | null;
  started_at: string;
  completed_at?: string | null;
}

export interface JobEvent {
  id: string;
  job_id: string;
  event_type: string;
  from_status?: string | null;
  to_status: string;
  details?: Record<string, unknown> | null;
  created_at: string;
}

export interface JobLog {
  timestamp: string;
  job_id: string;
  attempt_number?: number | null;
  worker_id?: string | null;
  level: string;
  event_type: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export interface InvestigationReport {
  job_id?: string;
  timestamp?: string;
  probable_root_cause: string;
  failure_category?: string;
  confidence_score?: number;
  confidence_level?: string;
  summary: string;
  supporting_evidence: string[];
  evidence_references?: string[];
  alternative_explanations?: string[];
  recommended_next_steps: string[];
  uncertainty_or_missing_evidence?: string | null;
}

export interface StoredInvestigation {
  id: string;
  job_id: string;
  provider: string;
  model?: string;
  confidence_score?: number;
  probable_root_cause?: string;
  report: InvestigationReport;
  created_at: string;
}

export interface TimelineItem {
  timestamp: string;
  type: 'lifecycle' | 'event' | 'attempt';
  category: string;
  title: string;
  details?: Record<string, unknown>;
}

export interface FailurePatterns {
  source: 'elasticsearch' | 'in_memory_buffer';
  top_error_patterns: Array<{ error_type: string; count: number }>;
  failures_by_job_type: Array<{ job_type: string; count: number }>;
  total_retries_observed: number;
  total_timeouts_observed: number;
  duration_metrics: {
    count: number;
    avg_ms: number;
    min_ms: number;
    max_ms: number;
  };
}

export interface MetricsSummary {
  total_jobs: number;
  queued_jobs?: number;
  running_jobs?: number;
  succeeded_jobs?: number;
  failed_jobs?: number;
  dead_letter_jobs?: number;
  retry_wait_jobs?: number;
  cancelled_jobs?: number;
  total_attempts?: number;
  status_counts?: Record<JobStatus, number>;
  avg_duration_seconds?: number;
  avg_duration_ms?: number;
  failure_rate_percent: number;
  by_job_type: Record<string, number>;
  timestamp?: string;
}
