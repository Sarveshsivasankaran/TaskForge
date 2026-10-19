import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Layers, 
  CheckCircle2, 
  RefreshCw, 
  User, 
  LogOut, 
  Shield, 
  Sparkles, 
  ArrowRightLeft,
  Lock,
  ExternalLink
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { MetricsOverview } from '../components/dashboard/MetricsOverview';
import { JobExplorer } from '../components/dashboard/JobExplorer';
import { JobSubmitModal } from '../components/dashboard/JobSubmitModal';
import { JobDetailModal } from '../components/dashboard/JobDetailModal';
import { AdminControlCenter } from '../components/dashboard/AdminControlCenter';
import { fetchMetricsSummary, fetchJobs, fetchJobById } from '../lib/api';
import type { Job, MetricsSummary } from '../types/job';

interface HealthStatus {
  status: string;
  app_name: string;
  environment: string;
  version?: string;
  timestamp: string;
}

export const DashboardPage: React.FC = () => {
  const { user, signOut, loading: authLoading } = useAuth();
  const navigate = useNavigate();

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

  // Redirect to login if unauthenticated once auth is settled
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login');
    }
  }, [user, authLoading, navigate]);

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

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
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
              className="btn-primary text-xs py-1.5 px-3 flex items-center space-x-1.5 shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Enqueue Job</span>
            </button>

            {/* Role & Profile Badge */}
            {user ? (
              <div className="flex items-center space-x-2">
                <div className={`flex items-center space-x-2.5 border rounded-xl px-3 py-1.5 text-xs shadow-sm ${
                  user.isAdmin 
                    ? 'bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200' 
                    : 'bg-gradient-to-r from-indigo-50 to-cyan-50 border-indigo-200'
                }`}>
                  <div className={`h-6 w-6 rounded-lg flex items-center justify-center font-bold text-white shadow-sm ${
                    user.isAdmin ? 'bg-gradient-to-tr from-purple-700 to-indigo-600' : 'bg-gradient-to-tr from-indigo-600 to-cyan-600'
                  }`}>
                    {user.isAdmin ? <Shield className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
                  </div>
                  <div className="text-left hidden md:block">
                    <p className="font-bold text-slate-800 leading-tight text-[11px]">{user.email}</p>
                    <p className={`text-[10px] font-extrabold uppercase tracking-wider ${
                      user.isAdmin ? 'text-purple-700' : 'text-indigo-700'
                    }`}>
                      {user.isAdmin ? 'Cluster Administrator' : 'Tenant Operator'}
                    </p>
                  </div>
                </div>

                {/* Switch Role Button */}
                <button
                  onClick={() => navigate('/login')}
                  className="p-1.5 text-purple-700 hover:text-purple-900 hover:bg-lavender-100 rounded-lg transition-colors border border-purple-100 text-xs flex items-center space-x-1"
                  title="Switch Role or Persona"
                >
                  <ArrowRightLeft className="w-3.5 h-3.5" />
                  <span className="hidden xl:inline text-[11px] font-semibold">Switch</span>
                </button>

                {/* Sign Out Button */}
                <button
                  onClick={handleSignOut}
                  className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  title="Sign Out to Login Page"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => navigate('/login')}
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
        {/* Role Scoping & Permissions Banner */}
        {user?.isAdmin ? (
          <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-purple-900 via-indigo-950 to-slate-900 text-white shadow-elevated relative overflow-hidden">
            <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="inline-flex items-center space-x-1.5 text-[11px] font-bold text-amber-300 uppercase tracking-widest bg-white/10 px-2.5 py-0.5 rounded-full border border-white/20 mb-1">
                  <Shield className="w-3.5 h-3.5 text-amber-300" />
                  <span>Cluster Administrator</span>
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  Cluster Operations & Infrastructure
                </h2>
                <p className="text-xs text-purple-200/90 max-w-3xl leading-relaxed">
                  Cluster-wide visibility across all tenant partitions with manual lease recovery and outbox sweep controls.
                </p>
              </div>

              <div className="flex sm:flex-col items-end gap-2 flex-shrink-0">
                <span className="px-3 py-1 rounded-lg text-xs font-bold bg-amber-400 text-purple-950 shadow-sm">
                  Admin Privileges
                </span>
                <span className="text-[11px] text-purple-200/80">
                  {totalJobs} Total Jobs
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-indigo-900 via-slate-900 to-purple-950 text-white shadow-elevated relative overflow-hidden">
            <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="inline-flex items-center space-x-1.5 text-[11px] font-bold text-cyan-300 uppercase tracking-widest bg-white/10 px-2.5 py-0.5 rounded-full border border-white/20 mb-1">
                  <Lock className="w-3.5 h-3.5 text-cyan-300" />
                  <span>Tenant Workspace</span>
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  Workload Operations ({user?.email || 'operator@taskforge.dev'})
                </h2>
                <p className="text-xs text-indigo-200/90 max-w-3xl leading-relaxed">
                  Jobs and execution telemetry are scoped to your tenant account.
                </p>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => navigate('/login')}
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-all flex items-center space-x-1"
                >
                  <span>Switch Role</span>
                  <ExternalLink className="w-3 h-3 ml-1" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Phase 8 & 11: Real-Time Cluster Metrics & Analytics */}
        <MetricsOverview
          metrics={metrics}
          loading={metricsLoading}
          onRefresh={loadMetrics}
          autoRefresh={autoRefresh}
          onToggleAutoRefresh={() => setAutoRefresh(!autoRefresh)}
        />

        {/* Admin Exclusive: Cluster Control Plane & Recovery Scanner */}
        {user?.isAdmin && (
          <AdminControlCenter
            onActionComplete={() => {
              loadMetrics();
              loadJobs();
            }}
          />
        )}

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
          currentUser={user}
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
            FastAPI · Supabase Queues · Async Workers · Elasticsearch · CrewAI
          </div>
        </div>
      </footer>

      {/* Modals */}
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
};
