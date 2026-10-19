import React, { useState, useEffect } from 'react';
import type { MetricsSummary, FailurePatterns } from '../../types/job';
import { fetchFailurePatterns } from '../../lib/api';
import { 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Zap, 
  RefreshCw,
  BarChart3,
  PieChart as PieIcon,
  ShieldAlert,
  Server,
  Layers
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  Tooltip, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid 
} from 'recharts';

interface MetricsOverviewProps {
  metrics: MetricsSummary | null;
  loading: boolean;
  onRefresh: () => void;
  autoRefresh: boolean;
  onToggleAutoRefresh: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  succeeded: '#10b981', // Emerald
  running: '#6366f1',   // Indigo
  queued: '#0ea5e9',    // Sky
  retry_wait: '#f59e0b',// Amber
  dead_letter: '#7c3aed',// Violet
  failed: '#ef4444',    // Rose
  cancelled: '#64748b'  // Slate
};

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({
  metrics,
  loading,
  onRefresh,
  autoRefresh,
  onToggleAutoRefresh,
}) => {
  const [failurePatterns, setFailurePatterns] = useState<FailurePatterns | null>(null);

  useEffect(() => {
    loadFailurePatterns();
  }, []);

  const loadFailurePatterns = async () => {
    try {
      const data = await fetchFailurePatterns();
      setFailurePatterns(data);
    } catch {
      // Graceful fallback
    }
  };

  const handleRefreshAll = () => {
    onRefresh();
    loadFailurePatterns();
  };

  if (!metrics) {
    return (
      <div className="card-surface p-6 animate-pulse">
        <div className="h-6 bg-lavender-100 rounded w-1/4 mb-4"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-lavender-50 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  const statusCounts = metrics.status_counts || {
    queued: metrics.queued_jobs || 0,
    running: metrics.running_jobs || 0,
    succeeded: metrics.succeeded_jobs || 0,
    failed: metrics.failed_jobs || 0,
    dead_letter: metrics.dead_letter_jobs || 0,
    retry_wait: metrics.retry_wait_jobs || 0,
    cancelled: metrics.cancelled_jobs || 0,
  };
  const totalJobs = metrics.total_jobs || 0;
  const queuedCount = statusCounts.queued || 0;
  const runningCount = statusCounts.running || 0;
  const succeededCount = statusCounts.succeeded || 0;
  const dlqCount = statusCounts.dead_letter || 0;
  const failedCount = statusCounts.failed || 0;
  const avgDuration = metrics.avg_duration_seconds ?? (metrics.avg_duration_ms ? metrics.avg_duration_ms / 1000 : 0);
  const failureRate = metrics.failure_rate_percent || 0;
  const byJobType = metrics.by_job_type || {};

  // Prepare Pie Chart Data
  const pieData = Object.entries(statusCounts)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({
      name: status.replace('_', ' ').toUpperCase(),
      value: count,
      key: status,
      color: STATUS_COLORS[status] || '#94a3b8'
    }));

  // Prepare Bar Chart Data
  const barData = Object.entries(byJobType).map(([type, count]) => ({
    name: type.replace('_', ' '),
    count
  }));

  return (
    <div className="space-y-6">
      {/* Top Header with live toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-600" />
            Cluster Metrics
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time throughput, status breakdown, and execution latencies.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-xs font-medium text-slate-600 cursor-pointer bg-white px-3 py-1.5 rounded-lg border border-purple-100 shadow-sm hover:bg-lavender-50">
            <input 
              type="checkbox" 
              checked={autoRefresh} 
              onChange={onToggleAutoRefresh} 
              className="rounded text-indigo-600 focus:ring-purple-400"
            />
            <span>Live Sync (4s)</span>
          </label>

          <button
            onClick={handleRefreshAll}
            disabled={loading}
            className="p-2 text-purple-700 hover:bg-lavender-100 rounded-lg transition-colors border border-lavender-200 shadow-sm"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        {/* Total Jobs */}
        <div className="card-surface p-4 border-l-4 border-l-indigo-600">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Ingested</span>
            <Activity className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{totalJobs.toLocaleString()}</div>
          <div className="text-[11px] text-slate-400 mt-1">Across all tenants</div>
        </div>

        {/* Queued & Running */}
        <div className="card-surface p-4 border-l-4 border-l-sky-500">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Pool</span>
            <Clock className="w-4 h-4 text-sky-500" />
          </div>
          <div className="text-2xl font-bold text-sky-700">
            {queuedCount + runningCount}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            <span className="text-sky-600 font-medium">{queuedCount} queued</span> · <span className="text-indigo-600 font-medium">{runningCount} active</span>
          </div>
        </div>

        {/* Succeeded */}
        <div className="card-surface p-4 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Succeeded</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-700">{succeededCount.toLocaleString()}</div>
          <div className="text-[11px] text-emerald-600 mt-1 font-medium">
            {totalJobs > 0 ? ((succeededCount / totalJobs) * 100).toFixed(1) : 0}% success rate
          </div>
        </div>

        {/* Dead Letter (DLQ) */}
        <div className="card-surface p-4 border-l-4 border-l-purple-600">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Dead Letter (DLQ)</span>
            <AlertTriangle className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-purple-900">{dlqCount}</div>
          <div className="text-[11px] text-purple-600 mt-1">
            Exhausted max retries
          </div>
        </div>

        {/* Failure Rate */}
        <div className="card-surface p-4 border-l-4 border-l-rose-500">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Failure Rate</span>
            <Zap className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-700">{failureRate.toFixed(1)}%</div>
          <div className="text-[11px] text-slate-500 mt-1">
            {failedCount + dlqCount} terminal failures
          </div>
        </div>

        {/* Avg Duration */}
        <div className="card-surface p-4 border-l-4 border-l-amber-500">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Avg Latency</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {avgDuration > 0 ? `${avgDuration.toFixed(2)}s` : '< 1s'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Lease to completion</div>
        </div>
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Breakdown Donut */}
        <div className="card-surface p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-purple-600" />
              Status Breakdown
            </h3>
            <span className="text-xs text-slate-400">Current partition</span>
          </div>

          <div className="h-56 w-full flex items-center justify-center">
            {pieData.length === 0 ? (
              <p className="text-xs text-slate-400">No job executions recorded yet</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#ffffff', 
                      borderRadius: '8px', 
                      border: '1px solid #e9e0ff',
                      boxShadow: '0 4px 6px -1px rgba(76, 29, 149, 0.1)',
                      fontSize: '12px'
                    }} 
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="flex flex-wrap gap-3 justify-center mt-2 pt-2 border-t border-purple-50">
            {pieData.map((d) => (
              <div key={d.key} className="flex items-center space-x-1.5 text-xs">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }}></span>
                <span className="text-slate-600 capitalize">{d.key.replace('_', ' ')}:</span>
                <span className="font-semibold text-slate-800">{d.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Job Volume by Type Bar Chart */}
        <div className="card-surface p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-indigo-600" />
              Workload Volume by Job Type
            </h3>
            <span className="text-xs text-slate-400">Distribution of registered handlers</span>
          </div>

          <div className="h-56 w-full">
            {barData.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <p className="text-xs text-slate-400">No jobs submitted yet</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3eeff" />
                  <XAxis 
                    dataKey="name" 
                    tick={{ fontSize: 10, fill: '#64748b' }} 
                    angle={-15} 
                    textAnchor="end"
                  />
                  <YAxis tick={{ fontSize: 10, fill: '#64748b' }} allowDecimals={false} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#ffffff', 
                      borderRadius: '8px', 
                      border: '1px solid #e9e0ff',
                      fontSize: '12px'
                    }} 
                  />
                  <Bar dataKey="count" fill="#8a48f7" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Elasticsearch Observability & Failure Pattern Analytics */}
      {failurePatterns && (
        <div className="card-surface p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-5 h-5 text-purple-700" />
              <h3 className="text-sm font-bold text-slate-900">
                Observability & Failure Pattern Analysis
              </h3>
            </div>
            <span className="text-[11px] px-2.5 py-0.5 rounded-full font-mono font-medium bg-lavender-100 text-purple-700 border border-purple-200">
              Telemetry Source: {failurePatterns.source}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Top Error Patterns */}
            <div className="p-4 bg-purple-50/50 rounded-xl border border-purple-100 space-y-2">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-purple-600" />
                Top Error Categories
              </span>
              {failurePatterns.top_error_patterns.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No errors captured in telemetry window</p>
              ) : (
                <div className="space-y-1.5">
                  {failurePatterns.top_error_patterns.map((ep, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs bg-white p-2 rounded border border-purple-100">
                      <span className="font-mono text-purple-900 font-semibold">{ep.error_type}</span>
                      <span className="font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded text-[11px]">{ep.count}x</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Retries & Timeouts */}
            <div className="p-4 bg-lavender-50/50 rounded-xl border border-purple-100 space-y-2">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5 text-indigo-600" />
                Resilience & Recovery Events
              </span>
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between p-2.5 bg-white rounded-lg border border-purple-100 text-xs">
                  <span className="text-slate-600">Retries Scheduled:</span>
                  <span className="font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
                    {failurePatterns.total_retries_observed}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2.5 bg-white rounded-lg border border-purple-100 text-xs">
                  <span className="text-slate-600">Timeout Interventions:</span>
                  <span className="font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded">
                    {failurePatterns.total_timeouts_observed}
                  </span>
                </div>
              </div>
            </div>

            {/* Execution Duration Statistics */}
            <div className="p-4 bg-indigo-50/40 rounded-xl border border-indigo-100 space-y-2">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-indigo-600" />
                Aggregated Execution Durations
              </span>
              <div className="grid grid-cols-3 gap-2 pt-1 text-center">
                <div className="bg-white p-2.5 rounded-lg border border-indigo-100">
                  <span className="text-[10px] text-slate-400 block uppercase">Min</span>
                  <span className="text-xs font-bold text-slate-800">{failurePatterns.duration_metrics.min_ms}ms</span>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-indigo-100">
                  <span className="text-[10px] text-slate-400 block uppercase">Avg</span>
                  <span className="text-xs font-bold text-indigo-700">{failurePatterns.duration_metrics.avg_ms}ms</span>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-indigo-100">
                  <span className="text-[10px] text-slate-400 block uppercase">Max</span>
                  <span className="text-xs font-bold text-slate-800">{failurePatterns.duration_metrics.max_ms}ms</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
