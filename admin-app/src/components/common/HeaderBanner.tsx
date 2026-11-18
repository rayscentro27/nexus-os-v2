import React from 'react';
import { ASSETS } from '../../data/assets';

interface HeaderBannerProps {
  title: string;
  description: string;
  greeting?: string;
  greetingSubtitle?: string;
}

export const HeaderBanner: React.FC<HeaderBannerProps> = ({
  title,
  description,
  greeting = 'Good morning, Ray!',
  greetingSubtitle = "Here's what's happening across Nexus OS today."
}) => {
  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
      {/* Page Title & Subtitle */}
      <div>
        <h1 className="text-2xl lg:text-[28px] font-bold text-slate-900 tracking-tight">
          {title}
        </h1>
        <p className="text-sm text-slate-500 mt-1 max-w-xl">
          {description}
        </p>
      </div>

      {/* Decorative greeting banner with mountain backdrop */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-sky-50 via-teal-50/60 to-blue-100/40 border border-sky-100/80 px-5 py-3 lg:w-[390px] shrink-0 shadow-xs flex items-center justify-between group hover:border-sky-200 transition-colors">
        <div className="relative z-10">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-bold text-slate-800">
              {greeting}
            </span>
            <span className="text-[10px] font-black uppercase tracking-wider px-1.5 py-0.2 rounded-md bg-emerald-100 text-emerald-700 border border-emerald-200/60">
              Active
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-0.5 max-w-[240px] truncate">
            {greetingSubtitle}
          </div>
        </div>

        {/* Mountain illustration graphic */}
        <div className="absolute right-0 top-0 bottom-0 w-36 pointer-events-none opacity-85 group-hover:opacity-95 transition-opacity">
          <img
            src={ASSETS.mountainBanner}
            alt="Mountain Banner"
            className="w-full h-full object-cover object-right"
          />
          <div className="absolute inset-0 bg-gradient-to-l from-transparent via-transparent to-sky-50" />
        </div>
      </div>
    </div>
  );
};
