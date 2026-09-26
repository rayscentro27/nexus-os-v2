import React from 'react';

export type GiantIconType =
  | 'shield'
  | 'gauge'
  | 'vault'
  | 'building'
  | 'bank-column'
  | 'rocket'
  | 'compass'
  | 'library'
  | 'clyde'
  | 'profile'
  | 'target';

interface GiantIconProps {
  type: GiantIconType;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'hero';
  className?: string;
  glow?: boolean;
}

export const GiantIcon: React.FC<GiantIconProps> = ({
  type,
  size = 'lg',
  className = '',
  glow = true
}) => {
  const sizeMap = {
    sm: 'w-10 h-10',
    md: 'w-14 h-14',
    lg: 'w-20 h-20',
    xl: 'w-28 h-28',
    hero: 'w-36 h-36'
  };

  const glowColors: Record<GiantIconType, string> = {
    shield: 'from-emerald-500/20 via-teal-500/10 to-transparent',
    gauge: 'from-amber-500/20 via-orange-500/10 to-transparent',
    vault: 'from-cyan-500/20 via-blue-500/10 to-transparent',
    building: 'from-sky-500/20 via-indigo-500/10 to-transparent',
    'bank-column': 'from-teal-500/20 via-emerald-500/10 to-transparent',
    rocket: 'from-teal-400/25 via-sky-500/15 to-transparent',
    compass: 'from-indigo-500/20 via-cyan-500/10 to-transparent',
    library: 'from-amber-400/20 via-yellow-500/10 to-transparent',
    clyde: 'from-[#00D2B4]/25 via-sky-500/20 to-transparent',
    profile: 'from-sky-400/20 via-blue-500/10 to-transparent',
    target: 'from-teal-400/20 via-cyan-500/10 to-transparent'
  };

  const renderSvg = () => {
    switch (type) {
      case 'shield':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <path
              d="M40 10L64 22V42C64 56.4 53.8 69.8 40 74C26.2 69.8 16 56.4 16 42V22L40 10Z"
              stroke="#00D2B4"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="url(#shield-grad)"
            />
            <path
              d="M40 22L54 29V42C54 51.5 48 59.8 40 62.5C32 59.8 26 51.5 26 42V29L40 22Z"
              stroke="#0EA5E9"
              strokeWidth="1.5"
              strokeDasharray="2 3"
              fill="rgba(14, 165, 233, 0.05)"
            />
            <path
              d="M32 41L37 46L48 35"
              stroke="#F1F5F9"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <defs>
              <linearGradient id="shield-grad" x1="40" y1="10" x2="40" y2="74" gradientUnits="userSpaceOnUse">
                <stop stopColor="#00D2B4" stopOpacity="0.25" />
                <stop stopColor="#101A2C" stopOpacity="0.85" />
              </linearGradient>
            </defs>
          </svg>
        );

      case 'gauge':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <path
              d="M16 54A32 32 0 1 1 64 54"
              stroke="#25344D"
              strokeWidth="6"
              strokeLinecap="round"
            />
            <path
              d="M16 54A32 32 0 0 1 54 20"
              stroke="#00D2B4"
              strokeWidth="6"
              strokeLinecap="round"
            />
            <circle cx="40" cy="50" r="5" fill="#00D2B4" />
            <line
              x1="40"
              y1="50"
              x2="52"
              y2="24"
              stroke="#F1F5F9"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <circle cx="64" cy="54" r="3" fill="#F59E0B" />
            <circle cx="16" cy="54" r="3" fill="#10B981" />
          </svg>
        );

      case 'vault':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <rect
              x="12"
              y="16"
              width="56"
              height="48"
              rx="8"
              stroke="#00D2B4"
              strokeWidth="2.5"
              fill="url(#vault-fill)"
            />
            <circle cx="40" cy="40" r="14" stroke="#0EA5E9" strokeWidth="2.5" strokeDasharray="3 3" />
            <circle cx="40" cy="40" r="7" fill="#00D2B4" />
            <line x1="40" y1="20" x2="40" y2="26" stroke="#00D2B4" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="40" y1="54" x2="40" y2="60" stroke="#00D2B4" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="20" y1="40" x2="26" y2="40" stroke="#00D2B4" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="54" y1="40" x2="60" y2="40" stroke="#00D2B4" strokeWidth="2.5" strokeLinecap="round" />
            <defs>
              <linearGradient id="vault-fill" x1="12" y1="16" x2="68" y2="64" gradientUnits="userSpaceOnUse">
                <stop stopColor="#F0FDFA" stopOpacity="0.9" />
                <stop stopColor="#E0F2FE" stopOpacity="0.95" />
              </linearGradient>
            </defs>
          </svg>
        );

      case 'building':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <path
              d="M16 66V26L36 12V66H16Z"
              stroke="#00D2B4"
              strokeWidth="2.5"
              fill="rgba(0, 210, 180, 0.08)"
            />
            <path
              d="M36 66V22L64 34V66H36Z"
              stroke="#0EA5E9"
              strokeWidth="2.5"
              fill="rgba(14, 165, 233, 0.1)"
            />
            {/* Windows */}
            <rect x="23" y="32" width="5" height="5" rx="1" fill="#00D2B4" fillOpacity="0.8" />
            <rect x="23" y="44" width="5" height="5" rx="1" fill="#00D2B4" fillOpacity="0.8" />
            <rect x="23" y="54" width="5" height="5" rx="1" fill="#00D2B4" fillOpacity="0.8" />
            <rect x="44" y="38" width="5" height="5" rx="1" fill="#0EA5E9" fillOpacity="0.8" />
            <rect x="52" y="38" width="5" height="5" rx="1" fill="#0EA5E9" fillOpacity="0.8" />
            <rect x="44" y="50" width="5" height="5" rx="1" fill="#0EA5E9" fillOpacity="0.8" />
            <rect x="52" y="50" width="5" height="5" rx="1" fill="#0EA5E9" fillOpacity="0.8" />
            <line x1="10" y1="66" x2="70" y2="66" stroke="#64748B" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        );

      case 'bank-column':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            {/* Pediment / Roof */}
            <path d="M40 14L16 28H64L40 14Z" stroke="#00D2B4" strokeWidth="2.5" fill="rgba(0, 210, 180, 0.1)" />
            {/* Architrave */}
            <rect x="14" y="28" width="52" height="4" rx="1" fill="#0EA5E9" />
            {/* Columns */}
            <rect x="20" y="36" width="6" height="24" rx="1.5" stroke="#00D2B4" strokeWidth="2" fill="rgba(0, 210, 180, 0.2)" />
            <rect x="31" y="36" width="6" height="24" rx="1.5" stroke="#00D2B4" strokeWidth="2" fill="rgba(0, 210, 180, 0.2)" />
            <rect x="43" y="36" width="6" height="24" rx="1.5" stroke="#00D2B4" strokeWidth="2" fill="rgba(0, 210, 180, 0.2)" />
            <rect x="54" y="36" width="6" height="24" rx="1.5" stroke="#00D2B4" strokeWidth="2" fill="rgba(0, 210, 180, 0.2)" />
            {/* Base */}
            <rect x="12" y="60" width="56" height="6" rx="2" fill="#0EA5E9" />
          </svg>
        );

      case 'rocket':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <path
              d="M40 12C40 12 56 22 56 46H24C24 22 40 12 40 12Z"
              stroke="#00D2B4"
              strokeWidth="2.5"
              fill="rgba(0, 210, 180, 0.15)"
            />
            <circle cx="40" cy="32" r="5" stroke="#0EA5E9" strokeWidth="2" fill="#0B132B" />
            <path d="M24 40L14 50V56L24 52" stroke="#00D2B4" strokeWidth="2" fill="rgba(0, 210, 180, 0.2)" />
            <path d="M56 40L66 50V56L56 52" stroke="#00D2B4" strokeWidth="2" fill="rgba(0, 210, 180, 0.2)" />
            {/* Thrust Flame */}
            <path
              d="M34 52L40 68L46 52H34Z"
              fill="#F59E0B"
              stroke="#F59E0B"
              strokeWidth="1.5"
            />
          </svg>
        );

      case 'compass':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <circle cx="40" cy="40" r="28" stroke="#0EA5E9" strokeWidth="2.5" strokeDasharray="4 3" />
            <circle cx="40" cy="40" r="32" stroke="#1E293B" strokeWidth="1.5" />
            {/* Needle */}
            <polygon points="40,16 45,36 40,40 35,36" fill="#00D2B4" stroke="#00D2B4" strokeWidth="1" />
            <polygon points="40,64 45,44 40,40 35,44" fill="#64748B" stroke="#64748B" strokeWidth="1" />
            <circle cx="40" cy="40" r="3.5" fill="#FFFFFF" />
          </svg>
        );

      case 'library':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <path
              d="M16 22C24 18 36 18 40 22C44 18 56 18 64 22V62C56 58 44 58 40 62C36 58 24 58 16 62V22Z"
              stroke="#00D2B4"
              strokeWidth="2.5"
              fill="rgba(0, 210, 180, 0.1)"
            />
            <line x1="40" y1="22" x2="40" y2="62" stroke="#0EA5E9" strokeWidth="2.5" />
            <line x1="22" y1="32" x2="34" y2="30" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
            <line x1="22" y1="42" x2="34" y2="40" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
            <line x1="46" y1="30" x2="58" y2="32" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
            <line x1="46" y1="40" x2="58" y2="42" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
          </svg>
        );

      case 'clyde':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <circle cx="40" cy="40" r="30" stroke="#00D2B4" strokeWidth="2.5" fill="url(#clyde-core)" />
            {/* Orbital Rings */}
            <ellipse cx="40" cy="40" rx="34" ry="12" stroke="#0EA5E9" strokeWidth="1.5" strokeDasharray="3 3" transform="rotate(-25 40 40)" />
            {/* Copilot Eyes / Neural Node */}
            <circle cx="32" cy="38" r="3.5" fill="#06090F" />
            <circle cx="48" cy="38" r="3.5" fill="#06090F" />
            <path d="M34 46C37 49 43 49 46 46" stroke="#06090F" strokeWidth="2" strokeLinecap="round" />
            <circle cx="40" cy="18" r="3" fill="#00D2B4" />
            <defs>
              <linearGradient id="clyde-core" x1="16" y1="16" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                <stop stopColor="#00D2B4" />
                <stop stopColor="#0EA5E9" />
              </linearGradient>
            </defs>
          </svg>
        );

      case 'profile':
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <circle cx="40" cy="30" r="14" stroke="#0EA5E9" strokeWidth="2.5" fill="rgba(14, 165, 233, 0.15)" />
            <path
              d="M18 64C18 52 28 46 40 46C52 46 62 52 62 64"
              stroke="#00D2B4"
              strokeWidth="2.5"
              strokeLinecap="round"
              fill="rgba(0, 210, 180, 0.1)"
            />
            <circle cx="56" cy="22" r="5" fill="#F59E0B" />
          </svg>
        );

      case 'target':
      default:
        return (
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full">
            <circle cx="40" cy="40" r="30" stroke="#1E293B" strokeWidth="3" />
            <circle cx="40" cy="40" r="20" stroke="#0EA5E9" strokeWidth="2.5" strokeDasharray="3 3" />
            <circle cx="40" cy="40" r="10" stroke="#00D2B4" strokeWidth="3" fill="rgba(0, 210, 180, 0.2)" />
            <circle cx="40" cy="40" r="3" fill="#FFFFFF" />
          </svg>
        );
    }
  };

  return (
    <div className={`relative flex items-center justify-center ${sizeMap[size]} ${className}`}>
      {glow && (
        <div
          className={`absolute inset-0 rounded-full bg-gradient-to-br ${glowColors[type]} blur-xl opacity-75`}
        />
      )}
      <div className="relative z-10 w-full h-full drop-shadow-md">
        {renderSvg()}
      </div>
    </div>
  );
};
