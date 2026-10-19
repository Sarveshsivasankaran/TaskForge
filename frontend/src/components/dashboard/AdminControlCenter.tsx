import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  RefreshCw, 
  Send, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle,
  Layers,
  Server,
  Activity,
  Zap,
  Info
} from 'lucide-react';
import { 
  fetchClusterStatus, 
  triggerLeaseRecovery, 
  triggerOutboxSweep, 
  verifyAdminAccess,
  type ClusterStatus 
} from '../../lib/api';

interface AdminControlCenterProps {
  onActionComplete?: () => void;
}

export const AdminControlCenter: React.FC<AdminControlCenterProps> = ({ onActionComplete }) => {
  const [clusterStatus, setClusterStatus] = useState<ClusterStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const loadClusterStatus = async () => {
    setLoadingStatus(true);
    try {
      const data = await fetchClusterStatus();
      setClusterStatus(data);
    } catch {
      // Graceful fallback
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    loadClusterStatus();
  }, []);

  const handleLeaseRecovery = async () => {
    setActiveAction('recovery');
    setActionFeedback(null);
    try {
      const res = await triggerLeaseRecovery();
      setActionFeedback({
        type: 'success',
        message: res.message || `Successfully scanned cluster: ${res.recovered_count} expired worker leases recovered.`
      });
      loadClusterStatus();
      if (onActionComplete) onActionComplete();
    } catch (err: unknown) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Lease recovery failed'
      });
    } finally {
      setActiveAction(null);
    }
  };

  const handleOutboxSweep = async () => {
    setActiveAction('outbox');
    setActionFeedback(null);
    try {
      const res = await triggerOutboxSweep();
      setActionFeedback({
        type: 'success',
        message: res.message || `Successfully swept outbox: ${res.dispatched_count} messages published to broker.`
      });
      loadClusterStatus();
      if (onActionComplete) onActionComplete();
    } catch (err: unknown) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Outbox sweep failed'
      });
    } finally {
      setActiveAction(null);
    }
  };

  const handleSecurityAudit = async () => {
    setActiveAction('audit');
    setActionFeedback(null);
    try {
      const res = await verifyAdminAccess();
      setActionFeedback({
        type: 'success',
        message: `Cryptographic audit verified! Caller authorized with service_role claims (ID: ${res.caller_id})`
      });
    } catch (err: unknown) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Admin verification failed'
      });
    } finally {
      setActiveAction(null);
    }
  };

  return (
    <div className="card-surface p-6 sm:p-7 border-2 border-purple-200/80 bg-gradient-to-br from-white via-purple-50/20 to-lavender-50/40 shadow-md space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-purple-100 pb-4">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-purple-700 to-indigo-600 text-white flex items-center justify-center shadow-md">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-slate-900">Cluster Recovery Controls</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-purple-100 text-purple-800 border border-purple-200">
                Admin
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Manual triggers for expired worker leases, transactional outbox sweeps, and security audits.
            </p>
          </div>
        </div>

        <button
          onClick={loadClusterStatus}
          disabled={loadingStatus}
          className="btn-secondary text-xs py-1.5 px-3 self-start sm:self-auto flex items-center space-x-1.5"
          title="Refresh cluster diagnostics"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-purple-600 ${loadingStatus ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Cluster Telemetry Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-white p-3.5 rounded-xl border border-purple-100 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Total Workloads</span>
            <Layers className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-xl font-extrabold text-slate-900">
            {clusterStatus ? clusterStatus.total_jobs : '—'}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Across all partitions</p>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-purple-100 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Tenants</span>
            <Server className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-xl font-extrabold text-indigo-900">
            {clusterStatus ? clusterStatus.distinct_tenants : '—'}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Active namespaces</p>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-purple-100 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Pending Outbox</span>
            <Zap className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-xl font-extrabold text-amber-800">
            {clusterStatus ? clusterStatus.pending_outbox : '—'}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Awaiting dispatch</p>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-purple-100 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Dead Letter Pool</span>
            <Activity className="w-4 h-4 text-rose-500" />
          </div>
          <p className="text-xl font-extrabold text-rose-800">
            {clusterStatus ? clusterStatus.dead_letter_jobs : '—'}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Terminal failures</p>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionFeedback && (
        <div className={`p-3.5 rounded-xl text-xs flex items-start space-x-2.5 animate-in fade-in duration-150 border ${
          actionFeedback.type === 'success' 
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
            : 'bg-rose-50 border-rose-200 text-rose-800'
        }`}>
          {actionFeedback.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
          )}
          <span className="font-medium leading-relaxed">{actionFeedback.message}</span>
        </div>
      )}

      {/* Control Actions Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Action 1: Reclaim Leases */}
        <button
          onClick={handleLeaseRecovery}
          disabled={activeAction !== null}
          className="p-3.5 rounded-xl border border-purple-200 hover:border-purple-400 bg-white hover:bg-purple-50/50 text-left transition-all shadow-sm hover:shadow group disabled:opacity-60"
        >
          <div className="flex items-center space-x-2 text-purple-900 font-bold text-xs mb-1">
            <RefreshCw className={`w-3.5 h-3.5 text-purple-600 ${activeAction === 'recovery' ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
            <span>Reclaim Expired Leases</span>
          </div>
          <p className="text-[11px] text-slate-500 leading-snug">
            Scans workers whose heartbeat timed out, fences crashed nodes, and re-queues tasks.
          </p>
        </button>

        {/* Action 2: Sweep Outbox */}
        <button
          onClick={handleOutboxSweep}
          disabled={activeAction !== null}
          className="p-3.5 rounded-xl border border-indigo-200 hover:border-indigo-400 bg-white hover:bg-indigo-50/50 text-left transition-all shadow-sm hover:shadow group disabled:opacity-60"
        >
          <div className="flex items-center space-x-2 text-indigo-900 font-bold text-xs mb-1">
            <Send className={`w-3.5 h-3.5 text-indigo-600 ${activeAction === 'outbox' ? 'animate-bounce' : ''}`} />
            <span>Sweep Outbox Dispatch</span>
          </div>
          <p className="text-[11px] text-slate-500 leading-snug">
            Publishes pending transactional outbox records to queue broker.
          </p>
        </button>

        {/* Action 3: Security Audit */}
        <button
          onClick={handleSecurityAudit}
          disabled={activeAction !== null}
          className="p-3.5 rounded-xl border border-slate-200 hover:border-purple-300 bg-white hover:bg-slate-50 text-left transition-all shadow-sm hover:shadow group disabled:opacity-60"
        >
          <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs mb-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Verify Security Claims</span>
          </div>
          <p className="text-[11px] text-slate-500 leading-snug">
            Verifies cryptographic JWT claims against the admin security endpoint.
          </p>
        </button>
      </div>

      <div className="flex items-center space-x-2 text-[11px] text-purple-700 bg-purple-50/60 border border-purple-100 rounded-lg px-3 py-2">
        <Info className="w-3.5 h-3.5 flex-shrink-0" />
        <span>
          <strong>Notice:</strong> Administrative operations require service_role privileges. Standard tenant callers receive 403 Forbidden.
        </span>
      </div>
    </div>
  );
};
