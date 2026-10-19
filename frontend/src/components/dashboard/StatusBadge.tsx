import React from 'react';
import type { JobStatus } from '../../types/job';
import { 
  Clock, 
  Loader2, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  RotateCw, 
  Ban 
} from 'lucide-react';

interface StatusBadgeProps {
  status: JobStatus | string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normStatus = (status || '').toLowerCase() as JobStatus;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[11px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3 py-1.5 text-sm gap-2',
  }[size];

  switch (normStatus) {
    case 'queued':
      return (
        <span className={`inline-flex items-center font-medium rounded-full bg-sky-50 text-sky-700 border border-sky-200 ${sizeClasses}`}>
          <Clock className="w-3.5 h-3.5 text-sky-500" />
          <span>Queued</span>
        </span>
      );

    case 'running':
      return (
        <span className={`inline-flex items-center font-medium rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 animate-pulse ${sizeClasses}`}>
          <Loader2 className="w-3.5 h-3.5 text-indigo-600 animate-spin" />
          <span>Running</span>
        </span>
      );

    case 'succeeded':
      return (
        <span className={`inline-flex items-center font-medium rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 ${sizeClasses}`}>
          <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
          <span>Succeeded</span>
        </span>
      );

    case 'failed':
      return (
        <span className={`inline-flex items-center font-medium rounded-full bg-rose-50 text-rose-700 border border-rose-200 ${sizeClasses}`}>
          <XCircle className="w-3.5 h-3.5 text-rose-500" />
          <span>Failed</span>
        </span>
      );

    case 'retry_wait':
      return (
        <span className={`inline-flex items-center font-medium rounded-full bg-amber-50 text-amber-700 border border-amber-200 ${sizeClasses}`}>
          <RotateCw className="w-3.5 h-3.5 text-amber-500" />
          <span>Retry Wait</span>
        </span>
      );

    case 'dead_letter':
      return (
        <span className={`inline-flex items-center font-medium rounded-full bg-purple-100 text-purple-900 border border-purple-300 ${sizeClasses}`}>
          <AlertTriangle className="w-3.5 h-3.5 text-purple-600" />
          <span>Dead Letter (DLQ)</span>
        </span>
      );

    case 'cancelled':
      return (
        <span className={`inline-flex items-center font-medium rounded-full bg-slate-100 text-slate-700 border border-slate-200 ${sizeClasses}`}>
          <Ban className="w-3.5 h-3.5 text-slate-500" />
          <span>Cancelled</span>
        </span>
      );

    default:
      return (
        <span className={`inline-flex items-center font-medium rounded-full bg-slate-100 text-slate-600 border border-slate-200 ${sizeClasses}`}>
          <span>{status}</span>
        </span>
      );
  }
};
