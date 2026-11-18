import React from 'react';

export type StatusVariant =
  | 'Live'
  | 'In Review'
  | 'On Track'
  | 'At Risk'
  | 'Needs Attention'
  | 'Needs Signature'
  | 'Needs Review'
  | 'Verified'
  | 'Paid'
  | 'Sent'
  | 'Overdue'
  | 'Pending'
  | 'Approved'
  | 'Changes Requested'
  | 'Draft'
  | 'Healthy'
  | 'Stable'
  | 'Queued'
  | 'Active';

interface StatusBadgeProps {
  status: StatusVariant | string;
  className?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className = '',
  size = 'md'
}) => {
  let bg = 'bg-slate-50 text-slate-700 border-slate-200/80';
  let dotColor = 'bg-slate-400';

  const s = status.toLowerCase();

  if (s === 'live' || s === 'on track' || s === 'verified' || s === 'paid' || s === 'approved' || s === 'healthy' || s === 'active') {
    bg = 'bg-emerald-50/90 text-emerald-700 border-emerald-200/60';
    dotColor = 'bg-emerald-500';
  } else if (s === 'in review' || s === 'sent') {
    bg = 'bg-blue-50/90 text-blue-700 border-blue-200/60';
    dotColor = 'bg-blue-500';
  } else if (s === 'at risk' || s === 'changes requested') {
    bg = 'bg-rose-50/90 text-rose-700 border-rose-200/60';
    dotColor = 'bg-rose-500';
  } else if (s === 'needs attention' || s === 'needs signature' || s === 'needs review' || s === 'overdue' || s === 'pending') {
    bg = 'bg-amber-50/90 text-amber-700 border-amber-200/60';
    dotColor = 'bg-amber-500';
  } else if (s === 'stable') {
    bg = 'bg-sky-50 text-sky-700 border-sky-200/60';
    dotColor = 'bg-sky-500';
  } else if (s === 'draft' || s === 'queued') {
    bg = 'bg-slate-100 text-slate-600 border-slate-200';
    dotColor = 'bg-slate-400';
  }

  const paddingClass = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  const isLiveOrActive = s === 'live' || s === 'active' || s === 'on track';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-bold rounded-full border whitespace-nowrap select-none transition-colors ${paddingClass} ${bg} ${className}`}
    >
      <span className="relative flex h-2 w-2 shrink-0">
        {isLiveOrActive && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${dotColor} opacity-60`} />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColor}`} />
      </span>
      <span>{status}</span>
    </span>
  );
};
