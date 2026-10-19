-- ==============================================================================
-- TaskForge Supabase PostgreSQL Row Level Security (RLS) Policies
-- ==============================================================================

-- 1. Enable RLS on all tables
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_outbox ENABLE ROW LEVEL SECURITY;

-- 2. Policies for 'jobs' table
-- Allow users to view only their own jobs
CREATE POLICY "Users can view their own jobs"
ON jobs
FOR SELECT
TO authenticated
USING (auth.uid() = owner_id);

-- Allow users to submit jobs under their own owner_id
CREATE POLICY "Users can insert their own jobs"
ON jobs
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = owner_id);

-- Allow users to cancel their own queued/retry_wait jobs
CREATE POLICY "Users can cancel their own jobs"
ON jobs
FOR UPDATE
TO authenticated
USING (auth.uid() = owner_id)
WITH CHECK (auth.uid() = owner_id AND status = 'cancelled');

-- Service role bypass for backend workers and dispatchers
CREATE POLICY "Service role full access to jobs"
ON jobs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 3. Policies for 'job_attempts' table
-- Allow users to view attempts for jobs they own
CREATE POLICY "Users can view attempts for their jobs"
ON job_attempts
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM jobs
        WHERE jobs.id = job_attempts.job_id
        AND jobs.owner_id = auth.uid()
    )
);

-- Service role has full access to record attempts
CREATE POLICY "Service role full access to job_attempts"
ON job_attempts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4. Policies for 'job_events' table
-- Allow users to view events for their jobs
CREATE POLICY "Users can view events for their jobs"
ON job_events
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM jobs
        WHERE jobs.id = job_events.job_id
        AND jobs.owner_id = auth.uid()
    )
);

-- Service role has full access to append events
CREATE POLICY "Service role full access to job_events"
ON job_events
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 5. Policies for 'job_outbox' table
-- Strictly private to backend dispatchers; authenticated users cannot access
CREATE POLICY "Service role full access to job_outbox"
ON job_outbox
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
