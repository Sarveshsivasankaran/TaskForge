# TaskForge: Demonstration Runbook & Operator Guide

> **"Submit once. Process reliably. Recover intelligently."**

Welcome to the TaskForge Demonstration Runbook. This guide provides step-by-step instructions for operators, evaluators, and cloud architects to run, test, and demonstrate the TaskForge Intelligent Asynchronous Job Orchestration Platform.

---

## 1. System Architecture Overview

```
                      +---------------------------------------+
                      |       TaskForge Operations UI         |
                      |   (React 19 + TypeScript + Tailwind)  |
                      +-------------------+-------------------+
                                          | HTTP / JWT / SSE
                                          v
                      +---------------------------------------+
                      |        FastAPI Core Gateway           |
                      | (Idempotency, Auth, SlowAPI Limiting) |
                      +-------------------+-------------------+
                                          |
                      +-------------------+-------------------+
                      | Transactional Outbox (Postgres DB)    |
                      +-------------------+-------------------+
                                          | Outbox Dispatcher
                                          v
                      +---------------------------------------+
                      |  Distributed Queue (Supabase / Table) |
                      +-------------------+-------------------+
                                          |
                   +----------------------+----------------------+
                   |                      |                      |
                   v                      v                      v
        +--------------------+ +--------------------+ +--------------------+
        | Worker Node Alpha  | | Worker Node Beta   | | Recovery Service   |
        |  (Lease Fencing,   | |  (Heartbeats,      | | (Abandoned Leases, |
        |   Jitter Backoff)  | |   Execution Pool)  | |  Backoff Re-queue) |
        +---------+----------+ +---------+----------+ +--------------------+
                  |                      |
                  +-----------+----------+
                              | Structured Streaming
                              v
                  +---------------------------------------+
                  | Elasticsearch / Memory Ring Buffer    |
                  +-------------------+-------------------+
                                      |
                                      v
                  +---------------------------------------+
                  | AI Failure Investigator (CrewAI / LLM)|
                  |   Advisory, Evidence-Grounded, Safe   |
                  +---------------------------------------+
```

---

## 2. Prerequisites & Quickstart

### Prerequisites
- **Python**: 3.11+ (or 3.14)
- **Node.js**: 20+ (with npm)
- **Docker & Docker Compose** (Optional for containerized run)

### Environment Setup
Copy the environment template:
```bash
cp .env.example .env
```
Default configuration uses local SQLite + TableQueue fallback with deterministic AI evaluation out of the box. No external cloud credentials required for local testing!

### Starting the Services

#### Option A: Native Local Development
1. **Backend API Service**:
   ```bash
   cd backend
   pip install -e .
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Asynchronous Worker Engine & Recovery Loop**:
   ```bash
   cd backend
   python -m app.workers.runner
   ```

3. **Frontend Dashboard**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

#### Option B: Docker Compose
```bash
docker-compose up --build
```

---

## 3. Automated Verification & Test Suites

TaskForge includes 40 automated unit, integration, and end-to-end tests covering all platform layers.

### Run Backend Tests (100% Green)
```bash
cd backend
python -m pytest tests -v
```
**Test Coverage Includes:**
- `test_auth.py`: JWT generation, role checks (admin/operator), rate limiting.
- `test_database.py`: SQLAlchemy async models, version counters, optimistic locks.
- `test_jobs_api.py`: Idempotent submission, list/filter/pagination, cancellation, retries.
- `test_queue_dispatch.py`: Outbox pattern, transactional atomicity, table queue operations.
- `test_worker_engine.py`: Lease acquisition, concurrency fencing, jitter backoff, retry exhaustion.
- `test_observability_ai_metrics.py`: Non-blocking log streaming, telemetry aggregation, AI reports.
- `test_e2e_scenarios.py`: Full multi-step crash recovery, poison pills, and prompt-injection defense.

### Run Frontend Typecheck & Build
```bash
cd frontend
npm run build
```

---

## 4. Live Demonstration Walkthrough

You can execute the automated demo script or follow the interactive web console walkthrough.

### Option 1: Automated Terminal Demonstration Script
Run the automated demonstration runner:
```bash
python scripts/demo_runner.py
```
This script automatically executes:
1. Health probe interrogation (`GET /api/health`).
2. Operator session authentication (`POST /api/v1/auth/demo-token`).
3. Happy path job ingestion & completion (`report_generation`).
4. Poison pill submission and immediate Dead-Letter Queue (DLQ) quarantine (`chaos_poison_pill`).
5. Evidence-grounded AI Root-Cause Investigation (`POST /api/jobs/{id}/investigate`).
6. Real-time cluster metrics retrieval.

---

### Option 2: Interactive Web Operations Console Walkthrough

Open `http://localhost:5173` in your web browser.

#### Step 1: Sign in with Demo Operator Profile
- Click **"Sign In"** in the top navigation bar.
- Choose **"Operator / Admin Demo"** or enter any custom test credentials.
- Notice the user role badge and authenticated JWT session state.

#### Step 2: Explore Real-Time Cluster Telemetry
- Inspect the top KPI summary cards:
  - **Total Ingested**
  - **Active Pool** (Queued & Running)
  - **Succeeded Rate**
  - **Dead-Letter (DLQ)**
  - **Failure Rate %**
  - **Average Latency (seconds)**
- Observe the **Job Status Distribution Donut Chart** and **Workload Volume by Job Type Bar Chart** powered by Recharts.
- Toggle **Live Sync (4s)** for real-time polling updates.

#### Step 3: Enqueue a Happy-Path Job
1. Click **"Enqueue Job"** in the top header.
2. Select **"Report Generation"** preset.
3. Review default parameters (`report_name: "Monthly Revenue Summary"`, `rows: 500`).
4. Click **"Enqueue Job"**.
5. Watch the job appear in the explorer table, transition from `Queued` -> `Running` -> `Succeeded`.
6. Click the job to view:
   - **Execution Timeline**: Execution latency in milliseconds, worker hostname, lease details.
   - **Payload & Result**: Exact JSON output returned by the background handler.
   - **Observability Logs**: Structured log entries indexed into Elasticsearch.

#### Step 4: Demonstrate Poison Pill DLQ Quarantine
1. Click **"Enqueue Job"**.
2. Select **"Chaos: Poison Pill (Permanent Failure)"**.
3. Submit the job.
4. Notice that because this is a non-transient, permanent data error (`PermanentExecutionError`), TaskForge **immediately routes the job to `dead_letter` status** rather than wasting compute retrying a toxic payload.

#### Step 5: Trigger Evidence-Grounded AI Failure Diagnosis
1. Open the drawer for the poisoned job.
2. Click the **"AI Investigate"** button.
3. The platform invokes the CrewAI/LLM investigation service (with deterministic fallback).
4. Review the generated diagnosis:
   - **Root Cause Hypothesis**: Pinpoints corrupted payload and unparseable input.
   - **Confidence Score**: e.g. 95% High Confidence.
   - **Supporting Log Evidence**: Correlated timestamps, worker error traces.
   - **Actionable Remediation Steps**: Operator instructions to sanitize source schema.

#### Step 6: Test Operator Lifecycle Controls
1. Enqueue a **Chaos: Flaky Task** or **Notification Dispatch**.
2. Cancel it mid-stream via the **"Cancel"** action button.
3. Manually retry any cancelled or dead-letter job via the **"Retry"** button to restore it to the queue.

---

## 5. Security & Reliability Highlights

| Feature | Architectural Implementation |
|---|---|
| **Atomicity** | Dual-write problem eliminated using **Transactional Outbox Pattern**. |
| **Concurrency Fencing** | Optimistic locking via `version` column and cryptographic `lease_token`. |
| **Backoff & Jitter** | Exponential backoff with **Full Jitter** to prevent thundering herd spikes. |
| **Poison Pill Defense** | Fatal errors trigger immediate DLQ quarantine, stopping worker death spirals. |
| **Crash Recovery** | `AbandonedJobRecoveryService` reclaims jobs from dead workers after lease timeouts. |
| **Data Protection** | Regex credential scrubbing redacts API keys, DB passwords, and JWTs prior to AI inspection. |
| **Prompt Injection Guard** | Filters untrusted delimiters (`Ignore all prior instructions`, etc.) before LLM prompt assembly. |
