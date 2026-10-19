import { useState, useEffect, useCallback } from 'react';
import { 
  Layers, 
  CheckCircle2, 
  RefreshCw,
  User,
  LogOut,
  Shield,
  Sparkles,
  Sliders
} from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AuthModal } from './components/auth/AuthModal';
import { MetricsOverview } from './components/dashboard/MetricsOverview';
import { JobExplorer } from './components/dashboard/JobExplorer';
import { JobSubmitModal } from './components/dashboard/JobSubmitModal';
import { JobDetailModal } from './components/dashboard/JobDetailModal';
import { fetchMetricsSummary, fetchJobs, fetchJobById } from './lib/api';
import type { Job, MetricsSummary } from './types/job';

interface HealthStatus {
  status: string;
  app_name: string;
  environment: string;
  version?: string;
  timestamp: string;
}

function DashboardContent() {
  const { user, signOut } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Metrics state
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [metricsLoading, setMetricsLoading] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  // Jobs state
  const [jobs, setJobs] = useState<Job[]>([]);
  const [totalJobs, setTotalJobs] = useState<number>(0);
  const [jobsLoading, setJobsLoading] = useState<boolean>(false);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [jobTypeFilter, setJobTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modals
  const [submitModalOpen, setSubmitModalOpen] = useState<boolean>(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState<boolean>(false);

  // Load API Health
  const loadHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setHealth(data);
    } catch (err: unknown) {
      setHealthError(err instanceof Error ? err.message : 'API offline');
    } finally {
      setHealthLoading(false);
    }
  };

  // Load Metrics
  const loadMetrics = useCallback(async () => {
    setMetricsLoading(true);
    try {
      const data = await fetchMetricsSummary();
      setMetrics(data);
    } catch {
      // Graceful fallback
    } finally {
      setMetricsLoading(false);
    }
  }, []);

  // Load Jobs
  const loadJobs = useCallback(async () => {
    setJobsLoading(true);
    try {
      const data = await fetchJobs({
        page: currentPage,
        limit: pageSize,
        status: statusFilter,
        job_type: jobTypeFilter,
        search: searchQuery,
      });
      setJobs(data.items);
      setTotalJobs(data.total);
    } catch {
      // Graceful fallback
    } finally {
      setJobsLoading(false);
    }
  }, [currentPage, pageSize, statusFilter, jobTypeFilter, searchQuery]);

  // Initial load
  useEffect(() => {
    loadHealth();
    loadMetrics();
    loadJobs();
  }, [loadMetrics, loadJobs]);

  // Auto-refresh interval (every 4 seconds for live telemetry & job state updates)
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadMetrics();
      loadJobs();
      if (selectedJob) {
        fetchJobById(selectedJob.id)
          .then((updated) => setSelectedJob(updated))
          .catch(() => {});
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [autoRefresh, loadMetrics, loadJobs, selectedJob]);

  // Handlers
  const handleJobSubmitted = (newJob: Job) => {
    loadMetrics();
    loadJobs();
    setSelectedJob(newJob);
    setDetailModalOpen(true);
  };

  const handleJobUpdated = (updatedJob: Job) => {
    setJobs((prev) => prev.map((j) => (j.id === updatedJob.id ? updatedJob : j)));
    if (selectedJob && selectedJob.id === updatedJob.id) {
      setSelectedJob(updatedJob);
    }
    loadMetrics();
  };

  const handleSelectJob = (job: Job) => {
    setSelectedJob(job);
    setDetailModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-lavender-50 text-slate-800 flex flex-col font-sans">
      {/* Top Navigation */}
      <header className="bg-white border-b border-purple-100 shadow-sm sticky top-0 z-40 backdrop-blur-md bg-white/95">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <span className="text-xl font-bold bg-gradient-to-r from-indigo-900 via-purple-900 to-slate-900 bg-clip-text text-transparent">
                TaskForge
              </span>
              <span className="hidden sm:inline-block ml-3 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-lavender-100 text-purple-800 border border-lavender-200">
                Operations Console
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3 sm:space-x-4">
            {/* API Status Badge */}
            <div className="hidden sm:flex items-center space-x-2 text-xs">
              <span className="text-slate-500 font-medium">Cluster:</span>
              {healthLoading ? (
                <span className="badge bg-amber-100 text-amber-800 animate-pulse">Checking...</span>
              ) : healthError ? (
                <span className="badge bg-rose-100 text-rose-800">Offline</span>
              ) : (
                <span className="badge bg-emerald-100 text-emerald-800 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Online v{health?.version || '1.0.0'}
                </span>
              )}
            </div>

            {/* Quick Action: New Job */}
            <button
              onClick={() => setSubmitModalOpen(true)}
              className="btn-primary text-xs py-1.5 px-3 flex items-center space-x-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Enqueue Job</span>
            </button>

            {/* User Profile or Sign-In Trigger */}
            {user ? (
              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-2 bg-lavender-50 border border-lavender-200 rounded-lg px-2.5 py-1 text-xs">
                  <div className="h-5 w-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
                    {user.isAdmin ? <Shield className="w-3 h-3" /> : <User className="w-3 h-3" />}
                  </div>
                  <div className="text-left hidden md:block">
                    <p className="font-semibold text-slate-800 leading-tight text-[11px]">{user.email}</p>
                    <p className="text-[9px] text-purple-600 font-bold uppercase">{user.role}</p>
                  </div>
                </div>
                <button
                  onClick={signOut}
                  className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setAuthModalOpen(true)}
                className="btn-secondary text-xs py-1.5 px-3 flex items-center space-x-1"
              >
                <User className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
            )}

            <button
              onClick={() => {
                loadHealth();
                loadMetrics();
                loadJobs();
              }}
              className="p-2 text-purple-700 hover:bg-lavender-100 rounded-lg transition-colors border border-lavender-200 shadow-sm"
              title="Manual Cluster Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Banner Tagline */}
        <div className="card-surface p-6 sm:p-8 bg-gradient-to-br from-white via-lavender-50/60 to-purple-50/40 relative overflow-hidden">
          <div className="relative z-10 max-w-3xl space-y-2">
            <div className="inline-flex items-center space-x-2 text-xs font-bold text-indigo-700 uppercase tracking-widest bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-100 mb-1">
              <Sliders className="w-3.5 h-3.5 text-indigo-600" />
              <span>Enterprise Asynchronous Engine</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Submit once. Process reliably. Recover intelligently.
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              TaskForge provides distributed transactional queue orchestration, optimistic lease concurrency, full jitter backoff retry policies, poison pill quarantine, and evidence-grounded AI failure investigations.
            </p>
          </div>
        </div>

        {/* Phase 8 & 11: Real-Time Cluster Metrics & Analytics */}
        <MetricsOverview
          metrics={metrics}
          loading={metricsLoading}
          onRefresh={loadMetrics}
          autoRefresh={autoRefresh}
          onToggleAutoRefresh={() => setAutoRefresh(!autoRefresh)}
        />

        {/* Phase 8: Jobs Explorer Table with Search & Status Tabs */}
        <JobExplorer
          jobs={jobs}
          totalJobs={totalJobs}
          currentPage={currentPage}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          jobTypeFilter={jobTypeFilter}
          onJobTypeFilterChange={setJobTypeFilter}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onSelectJob={handleSelectJob}
          onOpenSubmitModal={() => setSubmitModalOpen(true)}
          loading={jobsLoading}
          onJobUpdated={handleJobUpdated}
        />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-purple-100 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-3">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-700">TaskForge Cloud Computing</span>
            <span>·</span>
            <span>Fault-Tolerant Distributed Background Runner</span>
          </div>
          <div>
            Built with FastAPI · Supabase Queues · Async Workers · Elasticsearch · CrewAI
          </div>
        </div>
      </footer>

      {/* Modals */}
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />

      <JobSubmitModal
        isOpen={submitModalOpen}
        onClose={() => setSubmitModalOpen(false)}
        onJobSubmitted={handleJobSubmitted}
      />

      <JobDetailModal
        job={selectedJob}
        isOpen={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        onJobUpdated={handleJobUpdated}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <DashboardContent />
    </AuthProvider>
  );
}
