import React, { useState } from 'react';
import { X, Send, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import { submitJob } from '../../lib/api';
import type { CreateJobInput } from '../../lib/api';
import type { Job } from '../../types/job';

interface JobSubmitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onJobSubmitted: (job: Job) => void;
}

interface TemplatePreset {
  job_type: string;
  name: string;
  description: string;
  category: 'production' | 'chaos';
  defaultPayload: Record<string, unknown>;
  defaultMaxRetries: number;
  defaultTimeout: number;
}

const TEMPLATES: TemplatePreset[] = [
  {
    job_type: 'report_generation',
    name: 'Report Generation',
    description: 'Generates analytical report with simulated database computation and formatting.',
    category: 'production',
    defaultPayload: { report_name: 'Monthly Revenue Summary', rows: 500, format: 'pdf' },
    defaultMaxRetries: 3,
    defaultTimeout: 60,
  },
  {
    job_type: 'dataset_processing',
    name: 'Dataset Processing',
    description: 'Batched ETL aggregation and normalizer for large data streams.',
    category: 'production',
    defaultPayload: { dataset_id: 'ds-fin-2026', chunk_size: 1000, operations: ['clean', 'aggregate'] },
    defaultMaxRetries: 3,
    defaultTimeout: 120,
  },
  {
    job_type: 'notification_dispatch',
    name: 'Notification Dispatch',
    description: 'Dispatches multi-channel webhooks and SMS notifications with retry safety.',
    category: 'production',
    defaultPayload: { channel: 'webhook', recipient_count: 50, template: 'system_alert' },
    defaultMaxRetries: 5,
    defaultTimeout: 45,
  },
  {
    job_type: 'data_pipeline',
    name: 'Data Pipeline',
    description: 'Multi-stage data transformation with dependency synchronization.',
    category: 'production',
    defaultPayload: { pipeline_id: 'pipe-analytics-v2', source: 's3://metrics/inbound' },
    defaultMaxRetries: 3,
    defaultTimeout: 90,
  },
  {
    job_type: 'chaos_flaky_task',
    name: 'Chaos: Flaky Task (Transient Failure)',
    description: 'Simulates network blips to showcase exponential backoff, jitter, and automatic recovery.',
    category: 'chaos',
    defaultPayload: { failure_rate: 0.8, message: 'Upstream gateway timeout' },
    defaultMaxRetries: 4,
    defaultTimeout: 60,
  },
  {
    job_type: 'chaos_poison_pill',
    name: 'Chaos: Poison Pill (Permanent Failure)',
    description: 'Simulates non-recoverable schema corruption to demonstrate immediate DLQ routing.',
    category: 'chaos',
    defaultPayload: { error_message: 'Corrupted payload syntax: unexpected EOF in JSON block' },
    defaultMaxRetries: 2,
    defaultTimeout: 30,
  },
  {
    job_type: 'chaos_slow_worker',
    name: 'Chaos: Slow Worker (Heartbeat Lease)',
    description: 'Simulates heavy computation to demonstrate background lease extension heartbeats.',
    category: 'chaos',
    defaultPayload: { duration_seconds: 15, steps: 5 },
    defaultMaxRetries: 2,
    defaultTimeout: 60,
  },
];

export const JobSubmitModal: React.FC<JobSubmitModalProps> = ({
  isOpen,
  onClose,
  onJobSubmitted,
}) => {
  const [selectedTemplate, setSelectedTemplate] = useState<TemplatePreset>(TEMPLATES[0]);
  const [jobType, setJobType] = useState<string>(TEMPLATES[0].job_type);
  const [payloadText, setPayloadText] = useState<string>(
    JSON.stringify(TEMPLATES[0].defaultPayload, null, 2)
  );
  const [maxRetries, setMaxRetries] = useState<number>(TEMPLATES[0].defaultMaxRetries);
  const [timeoutSeconds, setTimeoutSeconds] = useState<number>(TEMPLATES[0].defaultTimeout);
  const [idempotencyKey, setIdempotencyKey] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSelectTemplate = (template: TemplatePreset) => {
    setSelectedTemplate(template);
    setJobType(template.job_type);
    setPayloadText(JSON.stringify(template.defaultPayload, null, 2));
    setMaxRetries(template.defaultMaxRetries);
    setTimeoutSeconds(template.defaultTimeout);
    setError(null);
  };

  const handleGenerateIdempotencyKey = () => {
    setIdempotencyKey(`idem-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    let parsedPayload: Record<string, unknown> = {};
    try {
      parsedPayload = JSON.parse(payloadText);
    } catch {
      setError('Invalid JSON payload syntax. Please verify commas and quotes.');
      return;
    }

    setIsSubmitting(true);
    try {
      const input: CreateJobInput = {
        job_type: jobType,
        payload: parsedPayload,
        max_retries: maxRetries,
        timeout_seconds: timeoutSeconds,
        idempotency_key: idempotencyKey.trim() || undefined,
      };

      const job = await submitJob(input);
      onJobSubmitted(job);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit job');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-elevated border border-purple-100 max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-5 border-b border-purple-100 flex items-center justify-between bg-gradient-to-r from-purple-50/50 via-lavender-50/30 to-white">
          <div className="flex items-center space-x-2.5">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-sm">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 leading-tight">Submit Asynchronous Job</h3>
              <p className="text-xs text-slate-500">Dispatches via Transactional Outbox to Supabase Queue</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3 text-rose-700 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Quick Preset Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Select Preset Workload
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {TEMPLATES.map((tmpl) => {
                const isSelected = selectedTemplate.job_type === tmpl.job_type;
                const isChaos = tmpl.category === 'chaos';
                return (
                  <button
                    key={tmpl.job_type}
                    type="button"
                    onClick={() => handleSelectTemplate(tmpl)}
                    className={`text-left p-3 rounded-xl border text-xs transition-all flex flex-col justify-between ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20'
                        : 'border-purple-100 bg-white hover:bg-lavender-50/50 hover:border-purple-200'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full mb-1">
                      <span className="font-bold text-slate-800">{tmpl.name}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          isChaos
                            ? 'bg-amber-100 text-amber-800 border border-amber-200'
                            : 'bg-indigo-100 text-indigo-800 border border-indigo-200'
                        }`}
                      >
                        {isChaos ? 'Chaos test' : 'Standard'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 line-clamp-2">{tmpl.description}</p>
                  </button>
                );
              })}
            </div>
          </div>

          <form id="job-submit-form" onSubmit={handleSubmit} className="space-y-4">
            {/* Job Type Input */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Handler Name / Job Type
              </label>
              <input
                type="text"
                value={jobType}
                onChange={(e) => setJobType(e.target.value)}
                required
                className="w-full text-xs font-mono px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-purple-400 focus:outline-none"
              />
            </div>

            {/* Payload JSON */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-slate-700">Payload (JSON)</label>
                <button
                  type="button"
                  onClick={() => setPayloadText(JSON.stringify(selectedTemplate.defaultPayload, null, 2))}
                  className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" /> Reset to default
                </button>
              </div>
              <textarea
                rows={5}
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
                className="w-full text-xs font-mono p-3 bg-slate-900 text-slate-100 rounded-lg border border-slate-800 focus:ring-2 focus:ring-purple-400 focus:outline-none resize-none"
              />
            </div>

            {/* Parameters Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Max Retries ({maxRetries})
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(parseInt(e.target.value))}
                  className="w-full accent-indigo-600"
                />
                <span className="text-[11px] text-slate-500">
                  After {maxRetries} attempts, routes to Dead-Letter Queue
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Execution Timeout ({timeoutSeconds}s)
                </label>
                <input
                  type="range"
                  min={10}
                  max={300}
                  step={5}
                  value={timeoutSeconds}
                  onChange={(e) => setTimeoutSeconds(parseInt(e.target.value))}
                  className="w-full accent-indigo-600"
                />
                <span className="text-[11px] text-slate-500">Lease heartbeat failsafe threshold</span>
              </div>
            </div>

            {/* Idempotency Key */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-slate-700">
                  Idempotency Key (Optional)
                </label>
                <button
                  type="button"
                  onClick={handleGenerateIdempotencyKey}
                  className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  Generate Unique Key
                </button>
              </div>
              <input
                type="text"
                placeholder="e.g. order-99823-batch-1"
                value={idempotencyKey}
                onChange={(e) => setIdempotencyKey(e.target.value)}
                className="w-full text-xs font-mono px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-purple-400 focus:outline-none"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">
                Prevents duplicate job insertion under retries or network reconnects.
              </span>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 border-t border-purple-100 flex items-center justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            form="job-submit-form"
            type="submit"
            disabled={isSubmitting}
            className="btn-primary text-xs py-2 px-4 flex items-center space-x-1.5 shadow-sm"
          >
            {isSubmitting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            <span>{isSubmitting ? 'Enqueuing...' : 'Enqueue Job'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
