import React from 'react';
import type { MetricsSummary } from '../../types/job';
import { 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Zap, 
  RefreshCw,
  BarChart3,
  PieChart as PieIcon
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

  const { total_jobs, status_counts, avg_duration_seconds, failure_rate_percent, by_job_type } = metrics;
  const queuedCount = status_counts.queued || 0;
  const runningCount = status_counts.running || 0;
  const succeededCount = status_counts.succeeded || 0;
  const dlqCount = status_counts.dead_letter || 0;
  const failedCount = status_counts.failed || 0;

  // Prepare Pie Chart Data
  const pieData = Object.entries(status_counts)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({
      name: status.replace('_', ' ').toUpperCase(),
      value: count,
      key: status,
      color: STATUS_COLORS[status] || '#94a3b8'
    }));

  // Prepare Bar Chart Data
  const barData = Object.entries(by_job_type).map(([type, count]) => ({
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
            Cluster Health & Real-time Metrics
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Synchronized telemetry across worker leases, transactional queues, and Elasticsearch streams
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
            onClick={onRefresh}
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
          <div className="text-2xl font-bold text-slate-900">{total_jobs.toLocaleString()}</div>
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
            {total_jobs > 0 ? ((succeededCount / total_jobs) * 100).toFixed(1) : 0}% success rate
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
          <div className="text-2xl font-bold text-rose-700">{failure_rate_percent.toFixed(1)}%</div>
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
            {avg_duration_seconds > 0 ? `${avg_duration_seconds.toFixed(2)}s` : '< 1s'}
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
              Job Status Distribution
            </h3>
            <span className="text-xs text-slate-400">Real-time state partition</span>
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
    </div>
  );
};
