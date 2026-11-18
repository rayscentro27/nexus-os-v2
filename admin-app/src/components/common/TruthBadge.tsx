import React from 'react';
import { TruthClass } from '../../types';

export type AnyTruthInput =
  | TruthClass
  | 'LIVE_VERIFIED'
  | 'TEST_CANARY'
  | 'PROTOTYPE'
  | 'TEST'
  | string;

interface TruthBadgeProps {
  truth: AnyTruthInput;
  label?: string;
  size?: 'xs' | 'sm';
  className?: string;
}

const TRUTH_STYLE_MAP: Record<
  string,
  { text: string; bg: string; border: string; fg: string }
> = {
  VERIFIED: {
    text: 'VERIFIED',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    fg: 'text-emerald-700',
  },
  LIVE_VERIFIED: {
    text: 'VERIFIED',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    fg: 'text-emerald-700',
  },
  ESTIMATED: {
    text: 'ESTIMATED',
    bg: 'bg-sky-50',
    border: 'border-sky-200',
    fg: 'text-sky-700',
  },
  PROPOSED: {
    text: 'PROPOSED',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    fg: 'text-amber-800',
  },
  INFERRED: {
    text: 'INFERRED',
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    fg: 'text-indigo-700',
  },
  UNKNOWN: {
    text: 'UNKNOWN',
    bg: 'bg-slate-100',
    border: 'border-slate-300',
    fg: 'text-slate-700',
  },
  NOT_CONNECTED: {
    text: 'NOT CONNECTED',
    bg: 'bg-rose-50',
    border: 'border-rose-200',
    fg: 'text-rose-700',
  },
  PAPER: {
    text: 'PAPER',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    fg: 'text-blue-700',
  },
  DEMO: {
    text: 'DEMO',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    fg: 'text-purple-700',
  },
  PROTOTYPE: {
    text: 'DEMO',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    fg: 'text-purple-700',
  },
  TEST: {
    text: 'TEST',
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    fg: 'text-indigo-700',
  },
  TEST_CANARY: {
    text: 'TEST',
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    fg: 'text-indigo-700',
  },
};

export const TruthBadge: React.FC<TruthBadgeProps> = ({
  truth,
  label,
  size = 'xs',
  className = '',
}) => {
  const normalized = String(truth || 'UNKNOWN').toUpperCase();
  const cfg = TRUTH_STYLE_MAP[normalized] || TRUTH_STYLE_MAP.UNKNOWN;

  return (
    <span
      className={`inline-flex items-center font-semibold tracking-wide rounded border whitespace-nowrap shrink-0 tabular-nums ${
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-1.5 py-0.5 text-[10px]'
      } ${cfg.bg} ${cfg.border} ${cfg.fg} ${className}`}
      title={`Data truth classification: ${cfg.text}`}
    >
      {label || cfg.text}
    </span>
  );
};
