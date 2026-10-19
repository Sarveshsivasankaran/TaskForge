import React, { useState, useEffect } from 'react';
import { 
  X, 
  Copy, 
  Check, 
  RotateCw, 
  Ban, 
  Sparkles, 
  Clock, 
  Server, 
  FileText, 
  Code, 
  ListTree, 
  AlertCircle,
  HelpCircle,
  Brain,
  ShieldAlert,
  Terminal
} from 'lucide-react';
import type { 
  Job, 
  JobAttempt, 
  JobEvent, 
  JobLog, 
  StoredInvestigation 
} from '../../types/job';
import { 
  fetchJobAttempts, 
  fetchJobEvents, 
  fetchJobLogs, 
  fetchJobInvestigations, 
  investigateJob, 
  retryJob, 
  cancelJob 
} from '../../lib/api';
import { StatusBadge } from './StatusBadge';

interface JobDetailModalProps {
  job: Job | null;
  isOpen: boolean;
  onClose: () => void;
  onJobUpdated: (updatedJob: Job) => void;
}

type TabType = 'timeline' | 'payload' | 'logs' | 'ai';

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  job,
  isOpen,
  onClose,
  onJobUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('timeline');
  const [copied, setCopied] = useState<boolean>(false);
  
  // Data states
  const [attempts, setAttempts] = useState<JobAttempt[]>([]);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [logs, setLogs] = useState<JobLog[]>([]);
  const [investigations, setInvestigations] = useState<StoredInvestigation[]>([]);
  
  // Loading & action states
  const [_loading, setLoading] = useState<boolean>(false);
  const [isRetrying, setIsRetrying] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [isInvestigating, setIsInvestigating] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [logFilter, setLogFilter] = useState<string>('ALL');

  useEffect(() => {
    if (job && isOpen) {
      loadDetails(job.id);
    }
  }, [job?.id, isOpen]);

  const loadDetails = async (jobId: string) => {
    setLoading(true);
    setActionError(null);
    try {
      const [attemptsData, eventsData, logsData, invData] = await Promise.all([
        fetchJobAttempts(jobId).catch(() => []),
        fetchJobEvents(jobId).catch(() => []),
        fetchJobLogs(jobId).catch(() => []),
        fetchJobInvestigations(jobId).catch(() => []),
      ]);
      setAttempts(attemptsData);
      setEvents(eventsData);
      setLogs(logsData);
      setInvestigations(invData);
    } catch {
      // Graceful fallback
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !job) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(job.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    setActionError(null);
    try {
      const updated = await retryJob(job.id);
      onJobUpdated(updated);
      await loadDetails(job.id);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Retry failed');
    } finally {
      setIsRetrying(false);
    }
  };

  const handleCancel = async () => {
    setIsCancelling(true);
    setActionError(null);
    try {
      const updated = await cancelJob(job.id);
      onJobUpdated(updated);
      await loadDetails(job.id);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Cancel failed');
    } finally {
      setIsCancelling(false);
    }
  };

  const handleTriggerInvestigation = async () => {
    setIsInvestigating(true);
    setActionError(null);
    try {
      const newInv = await investigateJob(job.id);
      setInvestigations((prev) => [newInv, ...prev]);
      setActiveTab('ai');
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'AI investigation failed');
    } finally {
      setIsInvestigating(false);
    }
  };

  const canRetry = ['failed', 'dead_letter', 'cancelled'].includes(job.status);
  const canCancel = ['queued', 'running', 'retry_wait'].includes(job.status);
  const isFailed = ['failed', 'dead_letter'].includes(job.status);

  const filteredLogs = logs.filter((l) => {
    if (logFilter === 'ALL') return true;
    return l.level.toUpperCase() === logFilter;
  });

  const latestInvestigation = investigations.length > 0 ? investigations[0] : null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6">
      <div className="bg-white rounded-2xl shadow-elevated border border-purple-100 max-w-4xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="p-5 border-b border-purple-100 bg-gradient-to-r from-purple-50/60 via-lavender-50/40 to-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2.5">
              <span className="font-mono text-xs text-slate-500 bg-white px-2 py-0.5 rounded border border-purple-100 flex items-center gap-1 shadow-sm">
                {job.id}
                <button 
                  onClick={handleCopyId} 
                  className="text-slate-400 hover:text-indigo-600 transition-colors p-0.5"
                  title="Copy Job ID"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                </button>
              </span>
              <StatusBadge status={job.status} size="md" />
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-800 border border-indigo-200">
                {job.job_type}
              </span>
            </div>
            <div className="text-xs text-slate-500">
              Created {new Date(job.created_at).toLocaleString()} · Attempt {job.attempt_count} of {job.max_retries} · Schema v{job.version}
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center space-x-2">
            {isFailed && (
              <button
                onClick={handleTriggerInvestigation}
                disabled={isInvestigating}
                className="btn-primary text-xs py-1.5 px-3 flex items-center space-x-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 shadow-sm"
              >
                <Brain className={`w-3.5 h-3.5 ${isInvestigating ? 'animate-spin' : ''}`} />
                <span>{isInvestigating ? 'Analyzing...' : 'AI Investigate'}</span>
              </button>
            )}

            {canRetry && (
              <button
                onClick={handleRetry}
                disabled={isRetrying}
                className="btn-secondary text-xs py-1.5 px-3 flex items-center space-x-1 border border-lavender-300"
              >
                <RotateCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
                <span>Retry</span>
              </button>
            )}

            {canCancel && (
              <button
                onClick={handleCancel}
                disabled={isCancelling}
                className="px-3 py-1.5 text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-lg transition-colors flex items-center space-x-1"
              >
                <Ban className={`w-3.5 h-3.5 ${isCancelling ? 'animate-spin' : ''}`} />
                <span>Cancel</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Global Action Error Banner */}
        {actionError && (
          <div className="px-5 py-2.5 bg-rose-50 border-b border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{actionError}</span>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-purple-100 px-6 bg-white space-x-6 text-xs font-medium">
          <button
            onClick={() => setActiveTab('timeline')}
            className={`py-3 border-b-2 flex items-center space-x-1.5 transition-colors ${
              activeTab === 'timeline'
                ? 'border-indigo-600 text-indigo-700 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <ListTree className="w-3.5 h-3.5" />
            <span>Execution Timeline</span>
            <span className="text-[10px] px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded-full font-bold">
              {attempts.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('payload')}
            className={`py-3 border-b-2 flex items-center space-x-1.5 transition-colors ${
              activeTab === 'payload'
                ? 'border-indigo-600 text-indigo-700 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            <span>Payload & Result</span>
          </button>

          <button
            onClick={() => setActiveTab('logs')}
            className={`py-3 border-b-2 flex items-center space-x-1.5 transition-colors ${
              activeTab === 'logs'
                ? 'border-indigo-600 text-indigo-700 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Observability Logs</span>
            <span className="text-[10px] px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded-full font-bold">
              {logs.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('ai')}
            className={`py-3 border-b-2 flex items-center space-x-1.5 transition-colors ${
              activeTab === 'ai'
                ? 'border-purple-600 text-purple-700 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-600" />
            <span>AI Failure Investigation</span>
            {investigations.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.2 bg-purple-100 text-purple-700 rounded-full font-bold">
                {investigations.length}
              </span>
            )}
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* TAB 1: TIMELINE */}
          {activeTab === 'timeline' && (
            <div className="space-y-6">
              {/* Job Metadata Summary Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-lavender-50/60 rounded-xl border border-purple-100 text-xs">
                <div>
                  <span className="text-slate-400 block text-[11px]">Lease Owner</span>
                  <span className="font-mono text-slate-800 font-medium">{job.lease_owner || 'None (Idle)'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Lease Expiration</span>
                  <span className="text-slate-800">
                    {job.lease_expires_at ? new Date(job.lease_expires_at).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Started At</span>
                  <span className="text-slate-800">
                    {job.started_at ? new Date(job.started_at).toLocaleTimeString() : 'Pending'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Timeout Failsafe</span>
                  <span className="text-slate-800">{job.timeout_seconds}s</span>
                </div>
              </div>

              {/* Error Message Callout if failed */}
              {job.error_message && (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-1">
                  <div className="flex items-center space-x-2 text-rose-800 font-bold text-xs">
                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                    <span>Terminal Error Cause:</span>
                  </div>
                  <pre className="text-xs text-rose-900 font-mono whitespace-pre-wrap bg-white/70 p-2.5 rounded border border-rose-100">
                    {job.error_message}
                  </pre>
                </div>
              )}

              {/* Attempts Timeline */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Server className="w-3.5 h-3.5 text-indigo-600" />
                  Worker Execution Attempts
                </h4>

                {attempts.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No execution attempts recorded yet.</p>
                ) : (
                  <div className="space-y-3">
                    {attempts.map((att) => (
                      <div
                        key={att.id}
                        className="p-4 rounded-xl border border-purple-100 bg-white shadow-sm space-y-2 hover:border-purple-200 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="h-6 w-6 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 font-bold text-xs flex items-center justify-center">
                              #{att.attempt_number}
                            </span>
                            <span className="text-xs font-mono font-medium text-slate-700">
                              Worker: {att.worker_id}
                            </span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs text-slate-400">
                              {att.duration_ms ? `${att.duration_ms.toFixed(1)} ms` : 'Running...'}
                            </span>
                            <span
                              className={`text-[11px] font-semibold px-2 py-0.5 rounded-full capitalize ${
                                att.status === 'succeeded'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : att.status === 'failed'
                                  ? 'bg-rose-100 text-rose-800'
                                  : 'bg-indigo-100 text-indigo-800 animate-pulse'
                              }`}
                            >
                              {att.status}
                            </span>
                          </div>
                        </div>

                        {att.error_message && (
                          <div className="text-xs text-rose-700 bg-rose-50/70 p-2 rounded border border-rose-100 font-mono">
                            {att.error_message}
                          </div>
                        )}

                        <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
                          <span>Started: {new Date(att.started_at).toLocaleTimeString()}</span>
                          {att.completed_at && (
                            <span>Completed: {new Date(att.completed_at).toLocaleTimeString()}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* State Transition Audit Events */}
              <div className="space-y-2 pt-2">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-purple-600" />
                  State Transition Audit Trail
                </h4>
                <div className="border border-purple-100 rounded-xl divide-y divide-purple-50 text-xs bg-white">
                  {events.map((evt) => (
                    <div key={evt.id} className="p-2.5 flex items-center justify-between hover:bg-lavender-50/40">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-purple-700 font-semibold">{evt.event_type}</span>
                        {evt.from_status && (
                          <span className="text-slate-400">
                            {evt.from_status} → <strong className="text-slate-700">{evt.to_status}</strong>
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-400">
                        {new Date(evt.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: PAYLOAD & RESULT */}
          {activeTab === 'payload' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-indigo-600" />
                    Input Parameters (Payload)
                  </h4>
                  <button
                    onClick={() => navigator.clipboard.writeText(JSON.stringify(job.payload, null, 2))}
                    className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
                  >
                    <Copy className="w-3 h-3" /> Copy
                  </button>
                </div>
                <pre className="text-xs font-mono p-3 bg-slate-900 text-emerald-400 rounded-xl overflow-x-auto border border-slate-800 max-h-96">
                  {JSON.stringify(job.payload, null, 2)}
                </pre>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    Execution Output (Result)
                  </h4>
                  {job.result && (
                    <button
                      onClick={() => navigator.clipboard.writeText(JSON.stringify(job.result, null, 2))}
                      className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3" /> Copy
                    </button>
                  )}
                </div>
                {job.result ? (
                  <pre className="text-xs font-mono p-3 bg-slate-900 text-sky-400 rounded-xl overflow-x-auto border border-slate-800 max-h-96">
                    {JSON.stringify(job.result, null, 2)}
                  </pre>
                ) : (
                  <div className="p-8 border border-dashed border-purple-200 rounded-xl text-center text-xs text-slate-400 flex flex-col items-center justify-center space-y-2">
                    <HelpCircle className="w-6 h-6 text-slate-300" />
                    <span>No result output produced yet.</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: OBSERVABILITY LOGS */}
          {activeTab === 'logs' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-slate-700">Filter Level:</span>
                  {['ALL', 'INFO', 'WARN', 'ERROR'].map((lvl) => (
                    <button
                      key={lvl}
                      onClick={() => setLogFilter(lvl)}
                      className={`text-[11px] px-2 py-0.5 rounded font-semibold transition-colors ${
                        logFilter === lvl
                          ? 'bg-purple-600 text-white'
                          : 'bg-lavender-100 text-purple-700 hover:bg-lavender-200'
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
                <span className="text-xs text-slate-400">
                  {filteredLogs.length} events logged to Elasticsearch index
                </span>
              </div>

              {filteredLogs.length === 0 ? (
                <div className="p-8 border border-dashed border-purple-200 rounded-xl text-center text-xs text-slate-400">
                  No log records found for this filter.
                </div>
              ) : (
                <div className="font-mono text-xs bg-slate-950 text-slate-200 p-4 rounded-xl border border-slate-800 space-y-2 max-h-[420px] overflow-y-auto">
                  {filteredLogs.map((l, idx) => {
                    const isErr = l.level.toUpperCase() === 'ERROR';
                    const isWarn = l.level.toUpperCase() === 'WARN';
                    return (
                      <div key={idx} className="border-b border-slate-900 pb-2 last:border-0 last:pb-0">
                        <div className="flex items-center space-x-2 text-[11px]">
                          <span className="text-slate-500">[{new Date(l.timestamp).toLocaleTimeString()}]</span>
                          <span
                            className={`font-bold px-1.5 py-0.2 rounded text-[10px] ${
                              isErr
                                ? 'bg-rose-950 text-rose-400 border border-rose-800'
                                : isWarn
                                ? 'bg-amber-950 text-amber-400 border border-amber-800'
                                : 'bg-indigo-950 text-indigo-400 border border-indigo-800'
                            }`}
                          >
                            {l.level}
                          </span>
                          <span className="text-purple-400 font-semibold">{l.event_type}</span>
                          {l.worker_id && <span className="text-slate-500">({l.worker_id})</span>}
                        </div>
                        <div className="mt-1 text-slate-300 pl-1">{l.message}</div>
                        {l.details && Object.keys(l.details).length > 0 && (
                          <pre className="text-[10px] text-slate-400 mt-1 pl-2 border-l border-slate-800">
                            {JSON.stringify(l.details)}
                          </pre>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: AI FAILURE INVESTIGATION */}
          {activeTab === 'ai' && (
            <div className="space-y-6">
              {!latestInvestigation ? (
                <div className="p-8 border border-dashed border-purple-200 rounded-2xl bg-gradient-to-br from-lavender-50/50 to-white text-center space-y-4">
                  <div className="h-12 w-12 rounded-2xl bg-purple-100 text-purple-700 flex items-center justify-center mx-auto">
                    <Brain className="w-6 h-6" />
                  </div>
                  <div className="max-w-md mx-auto space-y-1">
                    <h4 className="text-sm font-bold text-slate-900">No AI Investigation Report Generated</h4>
                    <p className="text-xs text-slate-500">
                      TaskForge AI autonomously inspects correlated log records, database state changes, and worker stack traces to pinpoint the exact failure cause.
                    </p>
                  </div>
                  <button
                    onClick={handleTriggerInvestigation}
                    disabled={isInvestigating}
                    className="btn-primary text-xs py-2 px-4 shadow-md inline-flex items-center space-x-1.5"
                  >
                    <Sparkles className={`w-4 h-4 ${isInvestigating ? 'animate-spin' : ''}`} />
                    <span>{isInvestigating ? 'Analyzing Failure Evidence...' : 'Initiate AI Investigation'}</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-5">
                  {/* Executive Summary Card */}
                  <div className="p-5 rounded-2xl border border-purple-200 bg-gradient-to-br from-purple-50/80 via-white to-lavender-50/40 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Brain className="w-5 h-5 text-purple-700" />
                        <h4 className="text-sm font-bold text-purple-950">AI Root-Cause Diagnosis</h4>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200">
                          {latestInvestigation.report.failure_category}
                        </span>
                        <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                          {(latestInvestigation.confidence_score * 100).toFixed(0)}% Confidence
                        </span>
                      </div>
                    </div>

                    <div className="p-3 bg-white rounded-xl border border-purple-100">
                      <span className="text-xs font-bold text-slate-500 block uppercase tracking-wider mb-1">
                        Probable Root Cause
                      </span>
                      <p className="text-sm font-semibold text-slate-900">
                        {latestInvestigation.report.probable_root_cause}
                      </p>
                      <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                        {latestInvestigation.report.summary}
                      </p>
                    </div>
                  </div>

                  {/* Supporting Evidence */}
                  <div className="space-y-2">
                    <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-indigo-600" />
                      Supporting Log & Execution Evidence
                    </h5>
                    <ul className="space-y-2">
                      {latestInvestigation.report.supporting_evidence.map((ev, i) => (
                        <li
                          key={i}
                          className="p-2.5 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-800 font-mono flex items-start space-x-2"
                        >
                          <span className="text-purple-600 font-bold">•</span>
                          <span>{ev}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Actionable Next Steps */}
                  <div className="space-y-2">
                    <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      Recommended Operator Remediation Steps
                    </h5>
                    <div className="space-y-2">
                      {latestInvestigation.report.recommended_next_steps.map((step, i) => (
                        <div
                          key={i}
                          className="p-3 bg-emerald-50/70 rounded-xl border border-emerald-200 text-xs text-emerald-950 flex items-start space-x-2.5"
                        >
                          <div className="h-5 w-5 rounded-full bg-emerald-200 text-emerald-800 font-bold text-[11px] flex items-center justify-center flex-shrink-0 mt-0.5">
                            {i + 1}
                          </div>
                          <span className="leading-relaxed font-medium">{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Re-run button */}
                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={handleTriggerInvestigation}
                      disabled={isInvestigating}
                      className="text-xs text-purple-700 hover:text-purple-900 font-semibold flex items-center space-x-1"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${isInvestigating ? 'animate-spin' : ''}`} />
                      <span>Re-analyze with Latest Logs</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
