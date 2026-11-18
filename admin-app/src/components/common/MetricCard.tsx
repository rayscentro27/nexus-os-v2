import React from 'react';
import { ChevronRight } from 'lucide-react';
import { ThreeDIcon, ThreeDIconType } from './ThreeDIcon';

interface MetricCardProps {
  label: string;
  value: string;
  change?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  threeDIcon?: ThreeDIconType;
  iconBgColor?: string;
  badge?: string;
  onClick?: () => void;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  change,
  subtitle,
  icon,
  threeDIcon,
  iconBgColor = 'bg-blue-50 text-blue-600',
  badge,
  onClick,
  className = ''
}) => {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl p-4 sm:p-5 border border-slate-100 shadow-[0_2px_10px_rgba(15,23,42,0.03)] hover:shadow-[0_8px_24px_rgba(37,99,235,0.09)] hover:border-blue-200 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer flex items-center justify-between group relative overflow-hidden ${className}`}
    >
      <div className="flex items-center gap-4">
        {/* Larger, high-visibility 3D-styled icon container */}
        {threeDIcon ? (
          <div className="shrink-0 group-hover:scale-105 transition-transform duration-200">
            <ThreeDIcon name={threeDIcon} size="lg" />
          </div>
        ) : (
          <div
            className={`w-13 h-13 rounded-2xl flex items-center justify-center shrink-0 shadow-2xs group-hover:scale-108 group-hover:shadow-sm transition-all duration-200 relative ${iconBgColor}`}
          >
            {/* 3D Specular highlight rim */}
            <div className="absolute inset-0 rounded-2xl border-t border-white/60 pointer-events-none" />
            <div className="transform transition-transform group-hover:rotate-3 [&>svg]:w-6.5 [&>svg]:h-6.5 [&>svg]:stroke-[2.2]">
              {icon}
            </div>
          </div>
        )}

        <div>
          <div className="flex items-center gap-1.5">
            <span className="text-[13px] font-semibold text-slate-500">{label}</span>
            {badge && (
              <span className="px-1.5 py-0.5 rounded-md text-[9px] font-extrabold uppercase tracking-wider bg-blue-100 text-blue-700">
                {badge}
              </span>
            )}
          </div>
          <div className="text-2xl sm:text-[26px] font-black text-slate-900 tracking-tight mt-0.5 tabular-nums">
            {value}
          </div>
          {(change || subtitle) && (
            <div className="text-[12px] font-semibold text-slate-500 mt-1 flex items-center gap-1.5">
              {change && (
                <span className={change.includes('↑') ? 'text-emerald-600 font-bold' : change.includes('↓') ? 'text-rose-500 font-bold' : 'text-slate-600'}>
                  {change}
                </span>
              )}
              {subtitle && (
                <span className="flex items-center gap-1 text-slate-400 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  {subtitle}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-slate-50 group-hover:bg-blue-50 text-slate-300 group-hover:text-blue-600 transition-colors shrink-0 ml-2">
        <ChevronRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
      </div>
    </div>
  );
};

