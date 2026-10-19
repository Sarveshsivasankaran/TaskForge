import type { 
  Job, 
  JobAttempt, 
  JobEvent, 
  JobLog, 
  MetricsSummary, 
  StoredInvestigation 
} from '../types/job';

const getAuthToken = (): string | null => {
  return localStorage.getItem('taskforge_token') || localStorage.getItem('taskforge_auth_token');
};

const getHeaders = (customHeaders: Record<string, string> = {}): HeadersInit => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...customHeaders,
  };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

export async function fetchMetricsSummary(): Promise<MetricsSummary> {
  const res = await fetch('/api/metrics/summary', {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to load metrics: HTTP ${res.status}`);
  }
  return res.json();
}

export interface GetJobsParams {
  status?: string;
  job_type?: string;
  page?: number;
  limit?: number;
  search?: string;
}

export interface JobsResponse {
  items: Job[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export async function fetchJobs(params: GetJobsParams = {}): Promise<JobsResponse> {
  const searchParams = new URLSearchParams();
  if (params.status && params.status !== 'all') {
    searchParams.set('status', params.status);
  }
  if (params.job_type && params.job_type !== 'all') {
    searchParams.set('job_type', params.job_type);
  }
  if (params.page) {
    searchParams.set('page', params.page.toString());
  }
  if (params.limit) {
    searchParams.set('limit', params.limit.toString());
  }

  const url = `/api/jobs?${searchParams.toString()}`;
  const res = await fetch(url, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch jobs: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchJobById(id: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${id}`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch job ${id}: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchJobAttempts(jobId: string): Promise<JobAttempt[]> {
  const res = await fetch(`/api/jobs/${jobId}/attempts`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch attempts: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchJobEvents(jobId: string): Promise<JobEvent[]> {
  const res = await fetch(`/api/jobs/${jobId}/events`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch events: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchJobLogs(jobId: string): Promise<JobLog[]> {
  const res = await fetch(`/api/jobs/${jobId}/logs`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch logs: HTTP ${res.status}`);
  }
  return res.json();
}

export interface CreateJobInput {
  job_type: string;
  payload: Record<string, unknown>;
  max_retries?: number;
  timeout_seconds?: number;
  idempotency_key?: string;
}

export async function submitJob(input: CreateJobInput): Promise<Job> {
  const res = await fetch('/api/jobs', {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to submit job: HTTP ${res.status}`);
  }
  return res.json();
}

export async function cancelJob(jobId: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to cancel job: HTTP ${res.status}`);
  }
  return res.json();
}

export async function retryJob(jobId: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}/retry`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to retry job: HTTP ${res.status}`);
  }
  return res.json();
}

export async function investigateJob(jobId: string): Promise<StoredInvestigation> {
  const res = await fetch(`/api/jobs/${jobId}/investigate`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to run investigation: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchJobInvestigations(jobId: string): Promise<StoredInvestigation[]> {
  const res = await fetch(`/api/jobs/${jobId}/investigations`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch investigations: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchJobTimeline(jobId: string): Promise<import('../types/job').TimelineItem[]> {
  const res = await fetch(`/api/jobs/${jobId}/timeline`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch timeline: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchFailurePatterns(): Promise<import('../types/job').FailurePatterns> {
  const res = await fetch('/api/metrics/failure-patterns', {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch failure patterns: HTTP ${res.status}`);
  }
  return res.json();
}

export interface ClusterStatus {
  status: string;
  cluster_mode: string;
  authorized_admin: string;
  caller_id: string;
  total_jobs: number;
  distinct_tenants: number;
  pending_outbox: number;
  dead_letter_jobs: number;
  running_jobs: number;
  queued_jobs: number;
  succeeded_jobs: number;
  status_distribution: Record<string, number>;
}

export async function fetchClusterStatus(): Promise<ClusterStatus> {
  const res = await fetch('/api/v1/admin/cluster-status', {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch cluster status: HTTP ${res.status}`);
  }
  return res.json();
}

export async function triggerLeaseRecovery(): Promise<{ status: string; recovered_count: number; message: string }> {
  const res = await fetch('/api/v1/admin/recover-leases', {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Lease recovery failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function triggerOutboxSweep(): Promise<{ status: string; dispatched_count: number; message: string }> {
  const res = await fetch('/api/v1/admin/sweep-outbox', {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Outbox sweep failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function verifyAdminAccess(): Promise<{ status: string; message: string; caller_id: string }> {
  const res = await fetch('/api/v1/auth/admin-only', {
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Admin verification failed: HTTP ${res.status}`);
  }
  return res.json();
}


