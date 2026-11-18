import React from 'react';

interface BrandLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ className = '', size = 'md' }) => {
  const isLg = size === 'lg';
  const logoDimensions = isLg ? 'w-11 h-11' : 'w-10 h-10';

  return (
    <div className={`flex items-center gap-3.5 ${className}`}>
      {/* Nexus geometric dual-triangle mark */}
      <div className={`relative ${logoDimensions} shrink-0 flex items-center justify-center p-1 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100 shadow-2xs`}>
        <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full drop-shadow-xs">
          <defs>
            <linearGradient id="nexusGrad1" x1="4" y1="36" x2="20" y2="4" gradientUnits="userSpaceOnUse">
              <stop stopColor="#1E40AF" />
              <stop offset="1" stopColor="#3B82F6" />
            </linearGradient>
            <linearGradient id="nexusGrad2" x1="20" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse">
              <stop stopColor="#0284C7" />
              <stop offset="1" stopColor="#06B6D4" />
            </linearGradient>
          </defs>
          {/* Left triangle pillar */}
          <path d="M6 34L20 6L14 34H6Z" fill="url(#nexusGrad1)" />
          {/* Right triangle pillar */}
          <path d="M34 34L20 6L26 34H34Z" fill="url(#nexusGrad2)" />
          {/* Central angled connector */}
          <path d="M14 34L20 18L26 34H14Z" fill="#2563EB" fillOpacity="0.85" />
        </svg>
      </div>

      <div className="flex flex-col leading-tight select-none">
        <div className="flex items-baseline gap-1.5">
          <span className="font-black text-[18px] tracking-tight text-[#0F172A]">Nexus OS</span>
          <span className="px-1.5 py-0.2 rounded-md bg-blue-100/80 text-blue-700 text-[9px] font-black uppercase tracking-wider">
            v2.4
          </span>
        </div>
        <span className="text-[13px] font-bold text-[#334155]">Admin Center</span>
        <span className="text-[10px] text-[#64748B] font-semibold tracking-wide">AI Enterprise OS</span>
      </div>
    </div>
  );
};
