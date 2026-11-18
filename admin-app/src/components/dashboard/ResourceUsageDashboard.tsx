import React from 'react';
import { UnavailableState } from '../live/UnavailableState';

export const ResourceUsageDashboard: React.FC<{ compact?: boolean }> = ({ compact = false }) => (
  <div className={compact ? 'bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-2xs' : 'bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs'}>
    <UnavailableState>Resource telemetry is not connected to a live source.</UnavailableState>
  </div>
);
