import React, { useState } from 'react';
import { 
  Search, 
  Plus, 
  RotateCw, 
  ExternalLink, 
  Ban, 
  Filter, 
  ChevronLeft, 
  ChevronRight,
  Inbox
} from 'lucide-react';
import type { Job } from '../../types/job';
import { StatusBadge } from './StatusBadge';
import { cancelJob, retryJob } from '../../lib/api';

interface JobExplorerProps {
  jobs: Job[];
  totalJobs: number;
  currentPage: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  jobTypeFilter: string;
  onJobTypeFilterChange: (type: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSelectJob: (job: Job) => void;
  onOpenSubmitModal: () => void;
  loading: boolean;
  onJobUpdated: (job: Job) => void;
  currentUser?: import('../../types/auth').User | null;
}

const STATUS_TABS: { label: string; value: string }[] = [
  { label: 'All Jobs', value: 'all' },
  { label: 'Queued', value: 'queued' },
  { label: 'Running', value: 'running' },
  { label: 'Succeeded', value: 'succeeded' },
  { label: 'Dead-Letter (DLQ)', value: 'dead_letter' },
  { label: 'Failed', value: 'failed' },
  { label: 'Retry-Wait', value: 'retry_wait' },
  { label: 'Cancelled', value: 'cancelled' },
];

export const JobExplorer: React.FC<JobExplorerProps> = ({
  jobs,
  totalJobs,
  currentPage,
  pageSize,
  onPageChange,
  statusFilter,
  onStatusFilterChange,
  jobTypeFilter,
  onJobTypeFilterChange,
  searchQuery,
  onSearchChange,
  onSelectJob,
  onOpenSubmitModal,
  loading,
  onJobUpdated,
  currentUser,
}) => {
  const [actionInProgress, setActionInProgress] = useState<Record<string, boolean>>({});

  const totalPages = Math.max(1, Math.ceil(totalJobs / pageSize));

  const handleQuickRetry = async (e: React.MouseEvent, job: Job) => {
    e.stopPropagation();
    setActionInProgress((prev) => ({ ...prev, [job.id]: true }));
    try {
      const updated = await retryJob(job.id);
      onJobUpdated(updated);
    } catch {
      // Handled in parent
    } finally {
      setActionInProgress((prev) => ({ ...prev, [job.id]: false }));
    }
  };

  const handleQuickCancel = async (e: React.MouseEvent, job: Job) => {
    e.stopPropagation();
    setActionInProgress((prev) => ({ ...prev, [job.id]: true }));
    try {
      const updated = await cancelJob(job.id);
      onJobUpdated(updated);
    } catch {
      // Handled in parent
    } finally {
      setActionInProgress((prev) => ({ ...prev, [job.id]: false }));
    }
  };

  return (
    <div className="card-surface overflow-hidden">
      {/* Header & Main Actions */}
      <div className="p-6 border-b border-purple-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-slate-900">
              {currentUser?.isAdmin ? 'Cluster-Wide Job Explorer' : 'Tenant Workload Explorer'}
            </h2>
            <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${
              currentUser?.isAdmin 
                ? 'bg-purple-100 text-purple-800 border-purple-200' 
                : 'bg-indigo-100 text-indigo-800 border-indigo-200'
            }`}>
              {currentUser?.isAdmin ? 'Cluster Admin' : 'Tenant Scoped'}
            </span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-lavender-100 text-purple-800 border border-lavender-200">
              {totalJobs} Total
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {currentUser?.isAdmin
              ? 'Real-time execution status and lease state across all tenant partitions.'
              : `Workloads submitted by your tenant account (${currentUser?.email || 'operator@taskforge.dev'}).`
            }
          </p>
        </div>

        <button
          onClick={onOpenSubmitModal}
          className="btn-primary text-xs py-2 px-4 shadow-sm flex items-center space-x-1.5 self-start md:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Submit New Job</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 bg-lavender-50/40 border-b border-purple-100 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by Job ID or keyword..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-purple-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-400"
          />
        </div>

        {/* Job Type Dropdown Filter */}
        <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={jobTypeFilter}
            onChange={(e) => onJobTypeFilterChange(e.target.value)}
            className="text-xs bg-white border border-purple-100 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-400 text-slate-700 font-medium"
          >
            <option value="all">All Job Types</option>
            <option value="report_generation">report_generation</option>
            <option value="dataset_processing">dataset_processing</option>
            <option value="notification_dispatch">notification_dispatch</option>
            <option value="data_pipeline">data_pipeline</option>
            <option value="chaos_flaky_task">chaos_flaky_task</option>
            <option value="chaos_poison_pill">chaos_poison_pill</option>
            <option value="chaos_slow_worker">chaos_slow_worker</option>
          </select>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex overflow-x-auto border-b border-purple-100 bg-white px-4 scrollbar-none text-xs font-medium space-x-1 py-1.5">
        {STATUS_TABS.map((tab) => {
          const isActive = statusFilter === tab.value;
          return (
            <button
              key={tab.value}
              onClick={() => onStatusFilterChange(tab.value)}
              className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
                isActive
                  ? 'bg-purple-600 text-white font-semibold shadow-sm'
                  : 'text-slate-600 hover:bg-lavender-100'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-lavender-50/70 border-b border-purple-100 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
            <tr>
              <th className="py-3 px-4">Job ID</th>
              <th className="py-3 px-4">Type</th>
              <th className="py-3 px-4">Status</th>
              {currentUser?.isAdmin && <th className="py-3 px-4">Tenant Partition</th>}
              <th className="py-3 px-4">Attempts</th>
              <th className="py-3 px-4">Submitted At</th>
              <th className="py-3 px-4">Worker Owner</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-purple-50 text-slate-700">
            {loading && jobs.length === 0 ? (
              <tr>
                <td colSpan={currentUser?.isAdmin ? 8 : 7} className="py-12 text-center text-slate-400">
                  <RotateCw className="w-6 h-6 animate-spin mx-auto text-indigo-600 mb-2" />
                  <span>Loading jobs repository...</span>
                </td>
              </tr>
            ) : jobs.length === 0 ? (
              <tr>
                <td colSpan={currentUser?.isAdmin ? 8 : 7} className="py-12 text-center text-slate-400 space-y-3">
                  <Inbox className="w-10 h-10 mx-auto text-slate-300" />
                  <p className="text-xs">No jobs found matching the selected criteria.</p>
                  <button
                    onClick={onOpenSubmitModal}
                    className="btn-secondary text-xs py-1.5 px-3 inline-flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Submit First Job
                  </button>
                </td>
              </tr>
            ) : (
              jobs.map((job) => {
                const isWorking = actionInProgress[job.id];
                const canRetry = ['failed', 'dead_letter', 'cancelled'].includes(job.status);
                const canCancel = ['queued', 'running', 'retry_wait'].includes(job.status);

                return (
                  <tr
                    key={job.id}
                    onClick={() => onSelectJob(job)}
                    className="hover:bg-lavender-50/50 cursor-pointer transition-colors group"
                  >
                    {/* ID */}
                    <td className="py-3 px-4 font-mono font-medium text-indigo-900">
                      <span className="group-hover:text-indigo-600 transition-colors">
                        {job.id.substring(0, 8)}...
                      </span>
                    </td>

                    {/* Job Type */}
                    <td className="py-3 px-4">
                      <span className="font-semibold text-slate-800 bg-lavender-100 text-purple-900 px-2 py-0.5 rounded text-[11px] border border-lavender-200">
                        {job.job_type}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="py-3 px-4">
                      <StatusBadge status={job.status} size="sm" />
                    </td>

                    {/* Tenant Partition (Cluster Admin Only) */}
                    {currentUser?.isAdmin && (
                      <td className="py-3 px-4 font-mono text-[11px]">
                        <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                          {job.owner_id ? `tenant-${job.owner_id.substring(0, 8)}` : 'default-tenant'}
                        </span>
                      </td>
                    )}

                    {/* Attempts */}
                    <td className="py-3 px-4 text-slate-600">
                      <span className="font-semibold text-slate-800">{job.attempt_count}</span>
                      <span className="text-slate-400"> / {job.max_retries}</span>
                    </td>

                    {/* Submitted At */}
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>

                    {/* Worker Owner */}
                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                      {job.lease_owner || <span className="text-slate-300 italic">none</span>}
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right space-x-1 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      {canRetry && (
                        <button
                          onClick={(e) => handleQuickRetry(e, job)}
                          disabled={isWorking}
                          className="p-1.5 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded transition-colors"
                          title="Retry Job"
                        >
                          <RotateCw className={`w-3.5 h-3.5 ${isWorking ? 'animate-spin' : ''}`} />
                        </button>
                      )}

                      {canCancel && (
                        <button
                          onClick={(e) => handleQuickCancel(e, job)}
                          disabled={isWorking}
                          className="p-1.5 text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded transition-colors"
                          title="Cancel Job"
                        >
                          <Ban className={`w-3.5 h-3.5 ${isWorking ? 'animate-spin' : ''}`} />
                        </button>
                      )}

                      <button
                        onClick={() => onSelectJob(job)}
                        className="p-1.5 text-purple-600 hover:text-purple-800 hover:bg-purple-50 rounded transition-colors"
                        title="View Full Details"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-purple-100 flex items-center justify-between text-xs text-slate-500">
        <div>
          Showing page <span className="font-semibold text-slate-800">{currentPage}</span> of{' '}
          <span className="font-semibold text-slate-800">{totalPages}</span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1 || loading}
            className="p-1.5 border border-purple-200 rounded-lg hover:bg-lavender-50 disabled:opacity-40 disabled:hover:bg-transparent transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages || loading}
            className="p-1.5 border border-purple-200 rounded-lg hover:bg-lavender-50 disabled:opacity-40 disabled:hover:bg-transparent transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
