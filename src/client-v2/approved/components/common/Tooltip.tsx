import React, { useState, useRef, useEffect, useCallback, useId } from 'react';
import { createPortal } from 'react-dom';

export interface TooltipProps {
  content: React.ReactNode;
  title?: string;
  tag?: string;
  tagType?: 'teal' | 'amber' | 'emerald' | 'rose' | 'sky';
  impact?: string;
  underwriterNote?: string;
  metric?: { label: string; value: string };
  position?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
  arrow?: boolean;
  children: React.ReactNode;
  className?: string;
  tooltipClassName?: string;
  disabled?: boolean;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  title,
  tag,
  tagType = 'teal',
  impact,
  underwriterNote,
  metric,
  position = 'top',
  delay = 100,
  arrow = true,
  children,
  className = '',
  tooltipClassName = '',
  disabled = false
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState<{
    top: number;
    left: number;
    actualPosition: 'top' | 'bottom' | 'left' | 'right';
  }>({
    top: 0,
    left: 0,
    actualPosition: position
  });

  const tooltipId = useId();
  const triggerRef = useRef<HTMLDivElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const calculatePosition = useCallback(() => {
    if (!triggerRef.current) return;
    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = 280; // Target width
    const tooltipHeight = 120; // Estimated height
    const gap = 10;
    const padding = 12;

    let targetTop = 0;
    let targetLeft = 0;
    let effectivePos = position;

    // Boundary flip check
    if (position === 'top' && triggerRect.top - tooltipHeight - gap < padding) {
      effectivePos = 'bottom';
    } else if (position === 'bottom' && triggerRect.bottom + tooltipHeight + gap > window.innerHeight - padding) {
      effectivePos = 'top';
    } else if (position === 'left' && triggerRect.left - tooltipWidth - gap < padding) {
      effectivePos = 'right';
    } else if (position === 'right' && triggerRect.right + tooltipWidth + gap > window.innerWidth - padding) {
      effectivePos = 'left';
    }

    if (effectivePos === 'top') {
      targetTop = triggerRect.top - gap;
      targetLeft = triggerRect.left + triggerRect.width / 2;
    } else if (effectivePos === 'bottom') {
      targetTop = triggerRect.bottom + gap;
      targetLeft = triggerRect.left + triggerRect.width / 2;
    } else if (effectivePos === 'left') {
      targetTop = triggerRect.top + triggerRect.height / 2;
      targetLeft = triggerRect.left - gap;
    } else {
      targetTop = triggerRect.top + triggerRect.height / 2;
      targetLeft = triggerRect.right + gap;
    }

    // Horizontal bounds containment
    const halfWidth = tooltipWidth / 2;
    if (effectivePos === 'top' || effectivePos === 'bottom') {
      if (targetLeft - halfWidth < padding) {
        targetLeft = padding + halfWidth;
      } else if (targetLeft + halfWidth > window.innerWidth - padding) {
        targetLeft = window.innerWidth - padding - halfWidth;
      }
    }

    setCoords({
      top: targetTop,
      left: targetLeft,
      actualPosition: effectivePos
    });
  }, [position]);

  const showTooltip = () => {
    if (disabled) return;
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      calculatePosition();
      setIsVisible(true);
    }, delay);
  };

  const hideTooltip = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  useEffect(() => {
    if (!isVisible) return;
    const handleScrollOrResize = () => {
      calculatePosition();
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') hideTooltip();
    };

    window.addEventListener('scroll', handleScrollOrResize, true);
    window.addEventListener('resize', handleScrollOrResize);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('scroll', handleScrollOrResize, true);
      window.removeEventListener('resize', handleScrollOrResize);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isVisible, calculatePosition]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const getTagClasses = () => {
    switch (tagType) {
      case 'amber':
        return 'text-amber-800 border-amber-300 bg-amber-50';
      case 'emerald':
        return 'text-emerald-800 border-emerald-300 bg-emerald-50';
      case 'rose':
        return 'text-rose-800 border-rose-300 bg-rose-50';
      case 'sky':
        return 'text-sky-800 border-sky-300 bg-sky-50';
      case 'teal':
      default:
        return 'text-teal-800 border-teal-300 bg-teal-50';
    }
  };

  const getTransformOrigin = () => {
    switch (coords.actualPosition) {
      case 'bottom':
        return 'translate(-50%, 0)';
      case 'left':
        return 'translate(-100%, -50%)';
      case 'right':
        return 'translate(0, -50%)';
      case 'top':
      default:
        return 'translate(-50%, -100%)';
    }
  };

  return (
    <>
      <div
        ref={triggerRef}
        aria-describedby={isVisible ? tooltipId : undefined}
        className={`relative ${className}`}
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={showTooltip}
        onBlur={hideTooltip}
      >
        {children}
      </div>

      {isVisible &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            id={tooltipId}
            ref={tooltipRef}
            role="tooltip"
            aria-live="polite"
            style={{
              position: 'fixed',
              top: `${coords.top}px`,
              left: `${coords.left}px`,
              transform: getTransformOrigin(),
              zIndex: 9999
            }}
            className={`pointer-events-none w-72 max-w-[calc(100vw-24px)] animate-fade-in ${tooltipClassName}`}
          >
            {/* Tooltip Card Body with Clean Light Design & High-Contrast Precision */}
            <div className="relative rounded-xl border border-slate-200/90 bg-white/98 p-3 text-slate-800 shadow-xl text-left backdrop-blur-md ring-1 ring-slate-900/5">
              {/* Header with Title and Metadata Tag */}
              {(title || tag) && (
                <div className="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-slate-100">
                  {title && (
                    <span className="text-[11px] font-bold text-slate-900 truncate flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-500 shrink-0 shadow-xs shadow-teal-500/50" />
                      {title}
                    </span>
                  )}
                  {tag && (
                    <span
                      className={`px-1.5 py-0.2 rounded font-mono font-bold text-[9px] uppercase border shrink-0 ${getTagClasses()}`}
                    >
                      {tag}
                    </span>
                  )}
                </div>
              )}

              {/* Optional Key Metric Row */}
              {metric && (
                <div className="mb-2 p-1.5 rounded-md bg-slate-50 border border-slate-200/70 flex items-center justify-between text-[10px]">
                  <span className="text-slate-500 font-medium">{metric.label}:</span>
                  <span className="font-mono font-bold text-slate-900 tabular-nums">{metric.value}</span>
                </div>
              )}

              {/* Context-Aware Financial Explanation Body */}
              <div className="text-[11px] text-slate-600 leading-relaxed font-normal">
                {content}
              </div>

              {/* Optional Financial Impact Indicator */}
              {impact && (
                <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center gap-1.5 text-[10px] text-teal-800 font-semibold font-mono bg-teal-50/60 px-2 py-1 rounded">
                  <span className="text-teal-600">⚡</span>
                  <span>{impact}</span>
                </div>
              )}

              {/* Institutional Underwriter Badge */}
              <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center justify-between text-[9px] text-slate-500 font-mono">
                <span className="text-teal-700 font-semibold flex items-center gap-1">
                  <span>🏛️</span> {underwriterNote || 'GoClear Underwriter Context'}
                </span>
                <span className="text-slate-400">Tier 1 Benchmark</span>
              </div>

              {/* Pointer Notch Arrow */}
              {arrow && (
                <div
                  className={`absolute w-2 h-2 bg-white rotate-45 pointer-events-none ${
                    coords.actualPosition === 'top'
                      ? '-bottom-1 left-1/2 -translate-x-1/2 border-r border-b border-slate-200/90'
                      : coords.actualPosition === 'bottom'
                      ? '-top-1 left-1/2 -translate-x-1/2 border-l border-t border-slate-200/90'
                      : coords.actualPosition === 'left'
                      ? '-right-1 top-1/2 -translate-y-1/2 border-r border-t border-slate-200/90'
                      : '-left-1 top-1/2 -translate-y-1/2 border-l border-b border-slate-200/90'
                  }`}
                />
              )}
            </div>
          </div>,
          document.body
        )}
    </>
  );
};
