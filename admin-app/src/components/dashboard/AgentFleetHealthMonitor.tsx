import React from 'react';
import { UnavailableState } from '../live/UnavailableState';

export const AgentFleetHealthMonitor: React.FC = () => (
  <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs">
    <UnavailableState>Agent health metrics are not connected to a live source.</UnavailableState>
  </div>
);
