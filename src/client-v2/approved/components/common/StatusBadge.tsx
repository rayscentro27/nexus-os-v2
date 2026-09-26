import React from 'react';

export type BadgeStatus = 'In Progress' | 'Completed' | 'Blocked' | 'Pending';

interface StatusBadgeProps {
  status: BadgeStatus;
  label?: string;
  size?: 'sm' | 'md';
  variant?: 'light' | 'dark';
  pulse?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'sm',
  variant = 'light',
  pulse = true,
  className = ''
}) => {
  const displayLabel = label || status;

  // Configuration for each status
  const config = {
    Completed: {
      light: {
        container: 'bg-emerald-50 text-emerald-800 border-emerald-300/80 shadow-2xs',
        dot: 'bg-emerald-500',
        icon: (
          <svg className="w-3 h-3 text-emerald-700 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )
      },
      dark: {
        container: 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40 shadow-xs',
        dot: 'bg-emerald-400',
        icon: (
          <svg className="w-3 h-3 text-emerald-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )
      }
    },
    'In Progress': {
      light: {
        container: 'bg-sky-50 text-sky-800 border-sky-300/80 shadow-2xs',
        dot: 'bg-sky-500',
        icon: (
          <span className="relative flex h-2 w-2 shrink-0">
            {pulse && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
            )}
            <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-600" />
          </span>
        )
      },
      dark: {
        container: 'bg-sky-950/80 text-sky-300 border-sky-500/40 shadow-xs',
        dot: 'bg-sky-400',
        icon: (
          <span className="relative flex h-2 w-2 shrink-0">
            {pulse && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
            )}
            <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-400" />
          </span>
        )
      }
    },
    Blocked: {
      light: {
        container: 'bg-rose-50 text-rose-800 border-rose-300/80 shadow-2xs',
        dot: 'bg-rose-500',
        icon: (
          <svg className="w-3 h-3 text-rose-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        )
      },
      dark: {
        container: 'bg-rose-950/80 text-rose-300 border-rose-500/40 shadow-xs',
        dot: 'bg-rose-400',
        icon: (
          <svg className="w-3 h-3 text-rose-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        )
      }
    },
    Pending: {
      light: {
        container: 'bg-slate-100 text-slate-700 border-slate-300/80 shadow-2xs',
        dot: 'bg-slate-400',
        icon: <span className="inline-block w-2 h-2 rounded-full bg-slate-400 shrink-0" />
      },
      dark: {
        container: 'bg-slate-800 text-slate-300 border-slate-600/60 shadow-xs',
        dot: 'bg-slate-400',
        icon: <span className="inline-block w-2 h-2 rounded-full bg-slate-400 shrink-0" />
      }
    }
  };

  const currentConfig = config[status] || config['Pending'];
  const theme = variant === 'dark' ? currentConfig.dark : currentConfig.light;

  const sizeClasses =
    size === 'sm'
      ? 'px-1.5 py-0.5 text-[9px] gap-1 rounded'
      : 'px-2 py-0.5 text-[10px] gap-1.5 rounded-md';

  return (
    <span
      className={`inline-flex items-center font-mono font-bold uppercase tracking-wider border select-none transition-colors ${sizeClasses} ${theme.container} ${className}`}
    >
      {theme.icon}
      <span>{displayLabel}</span>
    </span>
  );
};
