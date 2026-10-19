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
  job_id: string;
  timestamp: string;
  probable_root_cause: string;
  failure_category: string;
  confidence_score: number;
  summary: string;
  supporting_evidence: string[];
  recommended_next_steps: string[];
}

export interface StoredInvestigation {
  id: string;
  job_id: string;
  provider: string;
  model: string;
  confidence_score: number;
  probable_root_cause: string;
  report: InvestigationReport;
  created_at: string;
}

export interface MetricsSummary {
  total_jobs: number;
  status_counts: Record<JobStatus, number>;
  avg_duration_seconds: number;
  failure_rate_percent: number;
  by_job_type: Record<string, number>;
  timestamp: string;
}
