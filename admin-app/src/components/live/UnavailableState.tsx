import React from 'react';
import { TruthBadge } from '../common/TruthBadge';

export const UnavailableState: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs flex items-center gap-2 text-xs text-slate-600">
    <TruthBadge truth="NOT_CONNECTED" />
    <span>{children}</span>
  </div>
);
