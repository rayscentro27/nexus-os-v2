import React from 'react';

export type ThreeDIconType =
  | 'command-center'
  | 'nova'
  | 'business-hub'
  | 'clients'
  | 'research'
  | 'trading-engine'
  | 'marketing'
  | 'creative'
  | 'finance'
  | 'operations'
  | 'systems'
  | 'development-labs'
  | 'upgrade-control'
  | 'approvals'
  | 'documents'
  | 'settings'
  | 'kpi-status'
  | 'kpi-clients'
  | 'kpi-queue'
  | 'kpi-approvals'
  | 'kpi-revenue'
  | 'kpi-tenants'
  | 'kpi-onboarding'
  | 'kpi-alert'
  | 'kpi-campaigns'
  | 'kpi-growth'
  | 'kpi-storage'
  | 'kpi-efficiency'
  | 'kpi-trading';

export interface ThreeDIconProps {
  name: ThreeDIconType;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  animate?: boolean;
}

const SIZE_CLASSES = {
  sm: 'w-7 h-7',
  md: 'w-10 h-10',
  lg: 'w-13 h-13',
  xl: 'w-16 h-16'
};

export const ThreeDIcon: React.FC<ThreeDIconProps> = ({
  name,
  size = 'md',
  className = '',
  animate = true
}) => {
  const sizeClass = SIZE_CLASSES[size] || SIZE_CLASSES.md;
  const animClass = animate ? 'transition-all duration-200 group-hover:scale-110 group-hover:-translate-y-0.5' : '';

  switch (name) {
    case 'command-center':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="cc-base-grad" x1="8" y1="12" x2="56" y2="60" gradientUnits="userSpaceOnUse">
                <stop stopColor="#3B82F6" />
                <stop offset="0.6" stopColor="#1D4ED8" />
                <stop offset="1" stopColor="#1E3A8A" />
              </linearGradient>
              <linearGradient id="cc-top-grad" x1="16" y1="10" x2="48" y2="40" gradientUnits="userSpaceOnUse">
                <stop stopColor="#60A5FA" />
                <stop offset="1" stopColor="#2563EB" />
              </linearGradient>
              <linearGradient id="cc-core-grad" x1="24" y1="20" x2="40" y2="36" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38BDF8" />
                <stop offset="1" stopColor="#0284C7" />
              </linearGradient>
              <filter id="cc-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="4" stdDeviation="3" floodColor="#1D4ED8" floodOpacity="0.35" />
              </filter>
            </defs>
            {/* 3D Base Plate with Extrusion */}
            <path d="M32 6L54 18V44L32 58L10 44V18L32 6Z" fill="#1E3A8A" />
            <path d="M32 8L52 19V42L32 54L12 42V19L32 8Z" fill="url(#cc-base-grad)" filter="url(#cc-glow)" />
            
            {/* Top Gloss Refraction Rim */}
            <path d="M32 9L50 19.5L32 30L14 19.5L32 9Z" fill="url(#cc-top-grad)" opacity="0.9" />
            <path d="M32 10L47 18.5L32 27L17 18.5L32 10Z" fill="white" opacity="0.35" />
            
            {/* Left & Right 3D Facets */}
            <path d="M12 21L32 32V53L12 41V21Z" fill="#1D4ED8" opacity="0.85" />
            <path d="M52 21L32 32V53L52 41V21Z" fill="#172554" opacity="0.95" />
            
            {/* Elevated 3D Radar Core / Hologram Cube */}
            <path d="M32 20L42 26V38L32 44L22 38V26L32 20Z" fill="#0284C7" />
            <path d="M32 22L40 27V36L32 41L24 36V27L32 22Z" fill="url(#cc-core-grad)" />
            <path d="M32 23L38 27L32 31L26 27L32 23Z" fill="#E0F2FE" />
            
            {/* Orbital Neon Ring */}
            <ellipse cx="32" cy="32" rx="18" ry="7" stroke="#38BDF8" strokeWidth="2.5" strokeDasharray="3 3" opacity="0.85" />
            <circle cx="48" cy="31" r="3" fill="#67E8F9" />
          </svg>
        </div>
      );

    case 'nova':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="nv-base-grad" x1="12" y1="40" x2="52" y2="58" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0284C7" />
                <stop offset="0.6" stopColor="#1E40AF" />
                <stop offset="1" stopColor="#172554" />
              </linearGradient>
              <linearGradient id="nv-star-core" x1="20" y1="10" x2="44" y2="46" gradientUnits="userSpaceOnUse">
                <stop stopColor="#67E8F9" />
                <stop offset="0.4" stopColor="#38BDF8" />
                <stop offset="0.8" stopColor="#2563EB" />
                <stop offset="1" stopColor="#4F46E5" />
              </linearGradient>
              <linearGradient id="nv-spark-gold" x1="28" y1="24" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                <stop stopColor="#FEF08A" />
                <stop offset="0.5" stopColor="#F59E0B" />
                <stop offset="1" stopColor="#D97706" />
              </linearGradient>
              <filter id="nv-glow" x="-25%" y="-25%" width="150%" height="150%">
                <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#38BDF8" floodOpacity="0.45" />
              </filter>
            </defs>
            {/* 3D Elevated Base Pedestal */}
            <path d="M32 44L52 50V55L32 61L12 55V50L32 44Z" fill="#0F172A" />
            <path d="M32 42L50 48L32 54L14 48L32 42Z" fill="url(#nv-base-grad)" />
            <path d="M32 43L47 47.5L32 52L17 47.5L32 43Z" fill="#38BDF8" opacity="0.4" />

            {/* Glowing Holographic Ring Orbiting Nova */}
            <ellipse cx="32" cy="28" rx="22" ry="9" stroke="#38BDF8" strokeWidth="2" strokeDasharray="3 3" opacity="0.8" />
            <circle cx="53" cy="27" r="2.5" fill="#A5F3FC" />
            <circle cx="11" cy="29" r="2" fill="#67E8F9" />

            {/* 3D Radiant 4-Pointed Star Core */}
            {/* Shadow facet */}
            <path d="M32 6L37 23L54 28L37 33L32 50L27 33L10 28L27 23L32 6Z" fill="#1E3A8A" opacity="0.7" />
            {/* Core Star Body */}
            <path d="M32 5L36.5 22L53 27L36.5 32L32 48L27.5 32L11 27L27.5 22L32 5Z" fill="url(#nv-star-core)" filter="url(#nv-glow)" />

            {/* Dimensional Facets (Light / Dark Split) */}
            <path d="M32 5L36.5 22L32 27V5Z" fill="#BAE6FD" opacity="0.9" />
            <path d="M53 27L36.5 32L32 27L53 27Z" fill="#0284C7" opacity="0.85" />
            <path d="M32 48L27.5 32L32 27V48Z" fill="#1D4ED8" opacity="0.9" />
            <path d="M11 27L27.5 22L32 27L11 27Z" fill="#E0F2FE" opacity="0.95" />

            {/* Center Supernova Gem with Gold Sparkle */}
            <circle cx="32" cy="27" r="5" fill="url(#nv-spark-gold)" />
            <circle cx="32" cy="27" r="2.5" fill="#FFFFFF" />

            {/* Micro Sparkle Accents */}
            <path d="M46 12L47.5 16L51.5 17.5L47.5 19L46 23L44.5 19L40.5 17.5L44.5 16L46 12Z" fill="#FDE047" opacity="0.85" />
            <path d="M18 14L19 17L22 18L19 19L18 22L17 19L14 18L17 17L18 14Z" fill="#67E8F9" opacity="0.75" />
          </svg>
        </div>
      );

    case 'business-hub':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="bh-base-grad" x1="10" y1="20" x2="54" y2="56" gradientUnits="userSpaceOnUse">
                <stop stopColor="#2563EB" />
                <stop offset="0.6" stopColor="#1D4ED8" />
                <stop offset="1" stopColor="#0F172A" />
              </linearGradient>
              <linearGradient id="bh-gold-grad" x1="20" y1="12" x2="44" y2="40" gradientUnits="userSpaceOnUse">
                <stop stopColor="#F59E0B" />
                <stop offset="0.5" stopColor="#D97706" />
                <stop offset="1" stopColor="#B45309" />
              </linearGradient>
              <linearGradient id="bh-top-grad" x1="16" y1="16" x2="48" y2="36" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38BDF8" />
                <stop offset="1" stopColor="#2563EB" />
              </linearGradient>
            </defs>
            {/* 3D Base Platform */}
            <path d="M32 46L54 52V57L32 62L10 57V52L32 46Z" fill="#0F172A" opacity="0.8" />
            {/* 3D Vault / Briefcase Body */}
            <rect x="12" y="24" width="40" height="28" rx="6" fill="url(#bh-base-grad)" />
            {/* Top Lid bevel */}
            <path d="M12 28C12 24.6863 14.6863 22 18 22H46C49.3137 22 52 24.6863 52 28V33H12V28Z" fill="url(#bh-top-grad)" />
            {/* Handle */}
            <path d="M25 22V16C25 14.3431 26.3431 13 28 13H36C37.6569 13 39 14.3431 39 16V22" stroke="url(#bh-gold-grad)" strokeWidth="3.5" strokeLinecap="round" />
            {/* Corporate Buckle / Gold Shield Crest */}
            <rect x="28" y="30" width="8" height="8" rx="2" fill="url(#bh-gold-grad)" />
            <circle cx="32" cy="34" r="1.5" fill="#FEF08A" />
            {/* Dual Enterprise Accent Straps */}
            <line x1="22" y1="22" x2="22" y2="52" stroke="#1E293B" strokeWidth="2.5" opacity="0.6" />
            <line x1="42" y1="22" x2="42" y2="52" stroke="#1E293B" strokeWidth="2.5" opacity="0.6" />
            <line x1="22" y1="22" x2="22" y2="52" stroke="#60A5FA" strokeWidth="1" opacity="0.5" />
            <line x1="42" y1="22" x2="42" y2="52" stroke="#60A5FA" strokeWidth="1" opacity="0.5" />
            {/* Floating Network Node Halo */}
            <circle cx="48" cy="18" r="3" fill="#10B981" />
            <circle cx="48" cy="18" r="5" stroke="#34D399" strokeWidth="1" strokeDasharray="2 2" />
          </svg>
        </div>
      );

    case 'clients':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="cl-avatar-grad" x1="20" y1="12" x2="44" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38BDF8" />
                <stop offset="0.7" stopColor="#0284C7" />
                <stop offset="1" stopColor="#0369A1" />
              </linearGradient>
              <linearGradient id="cl-pedestal" x1="12" y1="40" x2="52" y2="58" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0EA5E9" />
                <stop offset="1" stopColor="#0369A1" />
              </linearGradient>
            </defs>
            {/* 3D Isometric Base Pedestal */}
            <path d="M32 42L54 50V56L32 62L10 56V50L32 42Z" fill="#0C4A6E" />
            <path d="M32 40L52 48L32 54L12 48L32 40Z" fill="url(#cl-pedestal)" />
            <path d="M32 41L49 47.5L32 52.5L15 47.5L32 41Z" fill="#BAE6FD" opacity="0.6" />

            {/* Background Avatar (Secondary) */}
            <circle cx="44" cy="22" r="9" fill="#0284C7" />
            <circle cx="43" cy="21" r="8" fill="#38BDF8" opacity="0.8" />
            <circle cx="41" cy="19" r="3" fill="white" opacity="0.5" />
            <path d="M35 38C35 32 41 30 46 30C51 30 56 33 56 38V42H35V38Z" fill="#0369A1" />

            {/* Foreground Main 3D Avatar (Hero) */}
            <circle cx="26" cy="18" r="12" fill="#075985" />
            <circle cx="26" cy="17" r="11" fill="url(#cl-avatar-grad)" />
            <ellipse cx="23" cy="13" rx="4.5" ry="3" fill="white" opacity="0.6" />

            {/* Hero Shoulders with Extrusion */}
            <path d="M12 46C12 37 18 34 26 34C34 34 40 37 40 46V50H12V46Z" fill="#0369A1" />
            <path d="M14 44C14 36.5 19 34 26 34C33 34 38 36.5 38 44V48H14V44Z" fill="url(#cl-avatar-grad)" />
            <path d="M26 34C20 34 16 37 15 42C18 38 23 36 26 36C29 36 34 38 37 42C36 37 32 34 26 34Z" fill="white" opacity="0.4" />

            {/* Glowing Golden Connection Star */}
            <circle cx="36" cy="30" r="5" fill="#F59E0B" />
            <circle cx="36" cy="30" r="3" fill="#FDE68A" />
          </svg>
        </div>
      );

    case 'research':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="rs-lens-grad" x1="16" y1="16" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                <stop stopColor="#67E8F9" />
                <stop offset="0.5" stopColor="#06B6D4" />
                <stop offset="1" stopColor="#0E7490" />
              </linearGradient>
              <linearGradient id="rs-rim-grad" x1="12" y1="12" x2="44" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#A5F3FC" />
                <stop offset="0.7" stopColor="#0891B2" />
                <stop offset="1" stopColor="#155E75" />
              </linearGradient>
              <linearGradient id="rs-handle-grad" x1="38" y1="38" x2="56" y2="56" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0891B2" />
                <stop offset="0.7" stopColor="#164E63" />
                <stop offset="1" stopColor="#083344" />
              </linearGradient>
            </defs>
            {/* 3D Extruded Lens Shadow */}
            <circle cx="28" cy="28" r="18" fill="#155E75" />
            <circle cx="28" cy="26" r="18" fill="url(#rs-rim-grad)" />
            <circle cx="28" cy="26" r="14" fill="url(#rs-lens-grad)" />

            {/* Convex Glare Arc */}
            <path d="M19 19C24 14 34 14 39 19C37 17 29 16 23 18C19 19 19 19 19 19Z" fill="white" opacity="0.8" />
            <ellipse cx="23" cy="22" rx="4" ry="2.5" transform="rotate(-30 23 22)" fill="white" opacity="0.6" />

            {/* Glowing Refraction Sparkle Inside */}
            <path d="M28 20L30 24L34 26L30 28L28 32L26 28L22 26L26 24L28 20Z" fill="white" opacity="0.9" />

            {/* 3D Metallic Handle */}
            <path d="M40 38L52 50C54 52 54 55 52 57C50 59 47 59 45 57L33 45L40 38Z" fill="#0E7490" />
            <path d="M41 37L53 49C55 51 55 54 53 56C51 58 48 58 46 56L34 44L41 37Z" fill="url(#rs-handle-grad)" />
            <circle cx="50" cy="53" r="2" fill="#67E8F9" />
          </svg>
        </div>
      );

    case 'trading-engine':
    case 'kpi-trading':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="tr-plate-grad" x1="8" y1="12" x2="56" y2="56" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0EA5E9" />
                <stop offset="0.5" stopColor="#2563EB" />
                <stop offset="1" stopColor="#1E1B4B" />
              </linearGradient>
              <linearGradient id="tr-candle-green" x1="18" y1="14" x2="26" y2="38" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34D399" />
                <stop offset="1" stopColor="#059669" />
              </linearGradient>
              <linearGradient id="tr-candle-blue" x1="32" y1="8" x2="40" y2="34" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38BDF8" />
                <stop offset="1" stopColor="#0284C7" />
              </linearGradient>
              <linearGradient id="tr-candle-accent" x1="44" y1="18" x2="52" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#A855F7" />
                <stop offset="1" stopColor="#7C3AED" />
              </linearGradient>
              <linearGradient id="tr-line-glow" x1="12" y1="46" x2="54" y2="18" gradientUnits="userSpaceOnUse">
                <stop stopColor="#F59E0B" />
                <stop offset="0.6" stopColor="#10B981" />
                <stop offset="1" stopColor="#06B6D4" />
              </linearGradient>
              <filter id="tr-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="4" stdDeviation="3" floodColor="#2563EB" floodOpacity="0.4" />
              </filter>
            </defs>
            {/* 3D Isometric Base Pedestal */}
            <path d="M32 46L54 34V46L32 58L10 46V34L32 46Z" fill="#0F172A" />
            <path d="M32 44L54 32L32 20L10 32L32 44Z" fill="url(#tr-plate-grad)" filter="url(#tr-glow)" />

            {/* Glowing Grid Matrix Lines on Pedestal */}
            <path d="M21 26L43 38M21 38L43 26" stroke="#93C5FD" strokeWidth="1" strokeOpacity="0.4" />

            {/* Left 3D Candlestick (Emerald Bullish) */}
            <line x1="20" y1="14" x2="20" y2="38" stroke="#34D399" strokeWidth="2" strokeLinecap="round" />
            <rect x="16" y="20" width="8" height="14" rx="2" fill="url(#tr-candle-green)" stroke="#10B981" strokeWidth="1" />
            <line x1="17.5" y1="21" x2="17.5" y2="33" stroke="white" strokeWidth="1" strokeOpacity="0.6" strokeLinecap="round" />

            {/* Center Tall 3D Candlestick (Cyan Momentum) */}
            <line x1="32" y1="8" x2="32" y2="34" stroke="#67E8F9" strokeWidth="2.5" strokeLinecap="round" />
            <rect x="27.5" y="12" width="9" height="18" rx="2.5" fill="url(#tr-candle-blue)" stroke="#38BDF8" strokeWidth="1" />
            <line x1="29.5" y1="13.5" x2="29.5" y2="28" stroke="white" strokeWidth="1.2" strokeOpacity="0.7" strokeLinecap="round" />

            {/* Right 3D Candlestick (Purple Quant) */}
            <line x1="44" y1="16" x2="44" y2="40" stroke="#C084FC" strokeWidth="2" strokeLinecap="round" />
            <rect x="40" y="22" width="8" height="14" rx="2" fill="url(#tr-candle-accent)" stroke="#9333EA" strokeWidth="1" />
            <line x1="41.5" y1="23" x2="41.5" y2="35" stroke="white" strokeWidth="1" strokeOpacity="0.6" strokeLinecap="round" />

            {/* Dimensional Algo Vector Trend Beam */}
            <path d="M12 40L22 30L34 22L46 14L54 10" stroke="url(#tr-line-glow)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="54" cy="10" r="3.5" fill="#38BDF8" stroke="white" strokeWidth="1.5" />
            <circle cx="54" cy="10" r="1.5" fill="white" />
          </svg>
        </div>
      );

    case 'marketing':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="mk-cone-grad" x1="14" y1="20" x2="42" y2="40" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34D399" />
                <stop offset="0.6" stopColor="#10B981" />
                <stop offset="1" stopColor="#047857" />
              </linearGradient>
              <linearGradient id="mk-rim-grad" x1="38" y1="14" x2="48" y2="44" gradientUnits="userSpaceOnUse">
                <stop stopColor="#A7F3D0" />
                <stop offset="1" stopColor="#059669" />
              </linearGradient>
            </defs>
            {/* 3D Extrusion Shadow of Megaphone */}
            <path d="M16 26L38 18V44L16 36V26Z" fill="#065F46" />
            <path d="M16 24L38 16V42L16 34V24Z" fill="url(#mk-cone-grad)" />
            
            {/* Specular Highlight along top edge */}
            <path d="M16 24L38 16V19L16 26V24Z" fill="white" opacity="0.4" />

            {/* Front Flared 3D Bell Ring */}
            <ellipse cx="38" cy="29" rx="5" ry="13" fill="#047857" />
            <ellipse cx="38" cy="29" rx="4" ry="12" fill="url(#mk-rim-grad)" />
            <ellipse cx="38" cy="29" rx="2" ry="8" fill="#064E3B" />

            {/* Handle & Trigger */}
            <path d="M22 33L20 48H26L28 32H22Z" fill="#047857" />
            <path d="M23 32L21 47H25L27 31H23Z" fill="#10B981" />

            {/* Sonic Wave Rings (Gamified 3D Beams) */}
            <path d="M47 21C51 25 51 33 47 37" stroke="#34D399" strokeWidth="3" strokeLinecap="round" />
            <path d="M53 16C59 22 59 36 53 42" stroke="#6EE7B7" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="1 3" />
            <circle cx="56" cy="29" r="2.5" fill="#A7F3D0" />
          </svg>
        </div>
      );

    case 'creative':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="cr-palette-grad" x1="12" y1="12" x2="52" y2="52" gradientUnits="userSpaceOnUse">
                <stop stopColor="#C084FC" />
                <stop offset="0.5" stopColor="#9333EA" />
                <stop offset="1" stopColor="#6B21A8" />
              </linearGradient>
            </defs>
            {/* 3D Palette Board with Deep Bevel */}
            <path d="M32 10C44 10 52 18 52 28C52 38 46 42 42 42C38 42 36 46 36 50C36 54 32 56 26 56C16 56 10 46 10 32C10 18 20 10 32 10Z" fill="#4C1D95" />
            <path d="M32 8C44 8 52 16 52 26C52 36 46 40 42 40C38 40 36 44 36 48C36 52 32 54 26 54C16 54 10 44 10 30C10 16 20 8 32 8Z" fill="url(#cr-palette-grad)" />
            
            {/* Palette Gloss Rim */}
            <path d="M32 9C43 9 50 16 50 25C47 20 38 12 32 9Z" fill="white" opacity="0.35" />

            {/* Thumbhole with 3D Depth */}
            <ellipse cx="22" cy="42" rx="4" ry="4" fill="#3B0764" />
            <ellipse cx="22" cy="41" rx="3.5" ry="3.5" fill="#1E1B4B" />

            {/* Volumetric Glowing Paint Drops */}
            {/* Cyan drop */}
            <circle cx="22" cy="19" r="4.5" fill="#06B6D4" />
            <circle cx="21" cy="18" r="4" fill="#22D3EE" />
            <circle cx="20" cy="17" r="1.5" fill="white" />

            {/* Rose/Pink drop */}
            <circle cx="34" cy="17" r="5" fill="#E11D48" />
            <circle cx="33" cy="16" r="4.5" fill="#FB7185" />
            <circle cx="32" cy="15" r="1.5" fill="white" />

            {/* Amber drop */}
            <circle cx="44" cy="26" r="4.5" fill="#D97706" />
            <circle cx="43" cy="25" r="4" fill="#FBBF24" />
            <circle cx="42" cy="24" r="1.5" fill="white" />

            {/* Emerald drop */}
            <circle cx="34" cy="32" r="4" fill="#059669" />
            <circle cx="33" cy="31" r="3.5" fill="#34D399" />
          </svg>
        </div>
      );

    case 'finance':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="fn-coin-top" x1="12" y1="12" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                <stop stopColor="#FDE68A" />
                <stop offset="0.6" stopColor="#F59E0B" />
                <stop offset="1" stopColor="#D97706" />
              </linearGradient>
              <linearGradient id="fn-bar-grad" x1="36" y1="16" x2="54" y2="52" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34D399" />
                <stop offset="1" stopColor="#059669" />
              </linearGradient>
            </defs>
            {/* 3D Stack of Gold Coins (Left) */}
            {/* Coin 1 Bottom */}
            <path d="M12 44C12 40 18 38 24 38C30 38 36 40 36 44V50C36 54 30 56 24 56C18 56 12 54 12 50V44Z" fill="#92400E" />
            <ellipse cx="24" cy="44" rx="12" ry="5" fill="#F59E0B" />
            
            {/* Coin 2 Middle */}
            <path d="M12 36C12 32 18 30 24 30C30 30 36 32 36 36V41C36 45 30 47 24 47C18 47 12 45 12 41V36Z" fill="#B45309" />
            <ellipse cx="24" cy="36" rx="12" ry="5" fill="#FBBF24" />

            {/* Coin 3 Top Hero */}
            <path d="M12 28C12 24 18 22 24 22C30 22 36 24 36 28V33C36 37 30 39 24 39C18 39 12 37 12 33V28Z" fill="#D97706" />
            <ellipse cx="24" cy="27" rx="12" ry="5.5" fill="url(#fn-coin-top)" />
            <ellipse cx="24" cy="27" rx="9" ry="3.5" stroke="#FDE68A" strokeWidth="1.5" />
            <text x="24" y="29.5" fontSize="6" fontWeight="900" fill="#78350F" textAnchor="middle">$</text>

            {/* 3D Rising Growth Column (Right) */}
            <path d="M40 32L52 24V50L40 56V32Z" fill="#065F46" />
            <path d="M40 30L52 22L46 18L34 26L40 30Z" fill="#A7F3D0" />
            <path d="M34 26L46 18V44L34 52V26Z" fill="url(#fn-bar-grad)" />

            {/* Upward Diamond Sparkle Flare */}
            <path d="M48 10L50 14L54 16L50 18L48 22L46 18L42 16L46 14L48 10Z" fill="#FDE047" />
          </svg>
        </div>
      );

    case 'systems':
    case 'operations':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="op-cube-top" x1="16" y1="12" x2="48" y2="36" gradientUnits="userSpaceOnUse">
                <stop stopColor="#818CF8" />
                <stop offset="1" stopColor="#4F46E5" />
              </linearGradient>
            </defs>
            {/* Bottom Left Cube */}
            <path d="M12 36L26 28V46L12 54V36Z" fill="#312E81" />
            <path d="M26 28L40 36V54L26 46V28Z" fill="#3730A3" />
            <path d="M26 28L40 20L26 12L12 20L26 28Z" fill="#6366F1" opacity="0.6" />

            {/* Hero Top Floating Isometric Cube */}
            <path d="M32 10L48 19L32 28L16 19L32 10Z" fill="#A5B4FC" />
            <path d="M32 11L46 19L32 27L18 19L32 11Z" fill="white" opacity="0.4" />
            <path d="M16 19L32 28V46L16 37V19Z" fill="url(#op-cube-top)" />
            <path d="M48 19L32 28V46L48 37V19Z" fill="#312E81" />

            {/* Glowing Modular Energy Core Nodes */}
            <circle cx="32" cy="28" r="3" fill="#38BDF8" />
            <circle cx="32" cy="28" r="1.5" fill="white" />
            <circle cx="48" cy="19" r="2.5" fill="#818CF8" />
            <circle cx="16" cy="19" r="2.5" fill="#818CF8" />
          </svg>
        </div>
      );

    case 'development-labs':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="labs-flask-grad" x1="18" y1="12" x2="46" y2="52" gradientUnits="userSpaceOnUse">
                <stop stopColor="#A855F7" />
                <stop offset="0.6" stopColor="#6366F1" />
                <stop offset="1" stopColor="#312E81" />
              </linearGradient>
              <linearGradient id="labs-bubble" x1="24" y1="28" x2="40" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38BDF8" />
                <stop offset="1" stopColor="#06B6D4" />
              </linearGradient>
            </defs>
            {/* Flask base pedestal */}
            <path d="M26 12H38V22L48 42C50 46 47 52 42 52H22C17 52 14 46 16 42L26 22V12Z" fill="url(#labs-flask-grad)" />
            <ellipse cx="32" cy="12" rx="6" ry="2" fill="#C084FC" />
            {/* Glowing fluid fill */}
            <path d="M19 43L24 33C27 34 37 34 40 33L45 43C46 47 43 50 39 50H25C21 50 18 47 19 43Z" fill="url(#labs-bubble)" opacity="0.85" />
            {/* Specular highlight */}
            <path d="M22 26L20 40C19 44 21 47 24 48" stroke="white" strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
            {/* Floating quantum particle sparks */}
            <circle cx="28" cy="40" r="1.5" fill="white" />
            <circle cx="36" cy="42" r="2" fill="#E0F2FE" />
            <circle cx="32" cy="36" r="1" fill="white" />
            <circle cx="32" cy="6" r="2" fill="#F43F5E" />
          </svg>
        </div>
      );

    case 'upgrade-control':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="upg-badge-grad" x1="16" y1="8" x2="48" y2="56" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0284C7" />
                <stop offset="0.5" stopColor="#0D9488" />
                <stop offset="1" stopColor="#064E3B" />
              </linearGradient>
            </defs>
            {/* Hexagonal Certification Seal */}
            <path d="M32 6L50 16V38L32 58L14 38V16L32 6Z" fill="#0F172A" />
            <path d="M32 8L48 17V37L32 55L16 37V17L32 8Z" fill="url(#upg-badge-grad)" />
            {/* Inner Ring */}
            <circle cx="32" cy="30" r="14" stroke="#5EEAD4" strokeWidth="1.5" strokeDasharray="3 2" />
            {/* Upward chevron / certification arrow */}
            <path d="M32 20L40 28H35V38H29V28H24L32 20Z" fill="white" />
            {/* Golden Star Crest */}
            <circle cx="32" cy="44" r="2.5" fill="#FBBF24" />
          </svg>
        </div>
      );

    case 'approvals':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="ap-shield-grad" x1="14" y1="10" x2="50" y2="54" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34D399" />
                <stop offset="0.6" stopColor="#10B981" />
                <stop offset="1" stopColor="#047857" />
              </linearGradient>
            </defs>
            {/* 3D Heraldic Shield Base Plate */}
            <path d="M32 6L50 14V32C50 44 42 53 32 58C22 53 14 44 14 32V14L32 6Z" fill="#064E3B" />
            <path d="M32 8L48 15V32C48 43 41 51 32 56C23 51 16 43 16 32V15L32 8Z" fill="url(#ap-shield-grad)" />

            {/* Specular Highlight along Left Shield Flank */}
            <path d="M32 9L46 16C46 16 34 26 32 46C26 36 20 28 20 20L32 9Z" fill="white" opacity="0.3" />

            {/* Golden Star Crest Atop */}
            <circle cx="32" cy="17" r="3.5" fill="#FBBF24" />
            <circle cx="32" cy="17" r="2" fill="#FEF08A" />

            {/* Embossed Volumetric 3D Checkmark */}
            <path d="M24 32L30 38L42 24" stroke="#064E3B" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M24 30L30 36L42 22" stroke="white" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M24 29L30 35L42 21" stroke="#ECFDF5" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      );

    case 'documents':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="doc-folder-grad" x1="12" y1="16" x2="52" y2="52" gradientUnits="userSpaceOnUse">
                <stop stopColor="#60A5FA" />
                <stop offset="0.6" stopColor="#2563EB" />
                <stop offset="1" stopColor="#1E40AF" />
              </linearGradient>
            </defs>
            {/* Back File Paper with Depth */}
            <path d="M22 10H46L52 16V44H22V10Z" fill="#E2E8F0" />
            <path d="M46 10V16H52L46 10Z" fill="#94A3B8" />

            {/* Middle Data Card */}
            <path d="M18 16H42L48 22V48H18V16Z" fill="#FFFFFF" />
            <path d="M42 16V22H48L42 16Z" fill="#CBD5E1" />
            {/* Text lines */}
            <rect x="23" y="24" width="16" height="2.5" rx="1.2" fill="#93C5FD" />
            <rect x="23" y="29" width="20" height="2.5" rx="1.2" fill="#BFDBFE" />

            {/* Front 3D Folder Shell with Extrusion */}
            <path d="M12 28L22 22H52V52C52 55 49 57 46 57H16C13 57 12 55 12 52V28Z" fill="#1E3A8A" />
            <path d="M12 26L22 20H52V50C52 53 49 55 46 55H16C13 55 12 53 12 50V26Z" fill="url(#doc-folder-grad)" />

            {/* Folder Front Gloss Rim */}
            <path d="M12 26L22 20H52V23L22 23L12 29V26Z" fill="white" opacity="0.4" />

            {/* Holographic Security Emblem */}
            <circle cx="42" cy="42" r="5" fill="#38BDF8" />
            <circle cx="42" cy="42" r="3" fill="#BAE6FD" />
          </svg>
        </div>
      );

    case 'settings':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="st-gear-grad" x1="14" y1="14" x2="50" y2="50" gradientUnits="userSpaceOnUse">
                <stop stopColor="#94A3B8" />
                <stop offset="0.5" stopColor="#64748B" />
                <stop offset="1" stopColor="#334155" />
              </linearGradient>
            </defs>
            {/* 3D Extrusion Shadow of Cogwheel */}
            <path
              d="M32 14L36 8H44L44 14L49 17L56 12L61 17L56 24L59 29L64 31V39L59 41L56 46L61 53L56 58L49 53L44 56V62H36V56L31 53L24 58L19 53L24 46L21 41L16 39V31L21 29L24 24L19 17L24 12L31 17L36 14Z"
              fill="#1E293B"
            />
            {/* Gear Body with Metallic Bevel */}
            <circle cx="32" cy="30" r="18" fill="url(#st-gear-grad)" />
            <circle cx="32" cy="30" r="18" stroke="#CBD5E1" strokeWidth="1.5" opacity="0.6" />

            {/* Central Precision Gem / Core */}
            <circle cx="32" cy="30" r="9" fill="#0F172A" />
            <circle cx="32" cy="30" r="7" fill="#0284C7" />
            <circle cx="32" cy="30" r="4" fill="#38BDF8" />
            <circle cx="30" cy="28" r="1.5" fill="white" />
          </svg>
        </div>
      );

    // KPI HEADERS SPECIFIC ICONS
    case 'kpi-status':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="ks-core" x1="16" y1="16" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34D399" />
                <stop offset="0.6" stopColor="#10B981" />
                <stop offset="1" stopColor="#047857" />
              </linearGradient>
            </defs>
            {/* 3D Pulse Reactor Ring */}
            <circle cx="32" cy="34" r="22" fill="#064E3B" opacity="0.4" />
            <circle cx="32" cy="32" r="20" fill="url(#ks-core)" />
            <circle cx="32" cy="32" r="16" stroke="#A7F3D0" strokeWidth="2.5" opacity="0.8" />
            <ellipse cx="28" cy="24" rx="7" ry="4" transform="rotate(-30 28 24)" fill="white" opacity="0.5" />

            {/* Heartbeat EKG Pulse in 3D White/Emerald */}
            <path
              d="M18 32H25L28 24L33 40L37 28L40 32H46"
              stroke="white"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      );

    case 'kpi-clients':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="kc-sphere" x1="18" y1="12" x2="46" y2="46" gradientUnits="userSpaceOnUse">
                <stop stopColor="#60A5FA" />
                <stop offset="0.7" stopColor="#2563EB" />
                <stop offset="1" stopColor="#1E3A8A" />
              </linearGradient>
            </defs>
            <circle cx="32" cy="22" r="14" fill="#172554" />
            <circle cx="32" cy="20" r="13" fill="url(#kc-sphere)" />
            <ellipse cx="28" cy="15" rx="5" ry="3" fill="white" opacity="0.6" />

            <path d="M14 54C14 42 22 38 32 38C42 38 50 42 50 54V56H14V54Z" fill="#1E3A8A" />
            <path d="M16 52C16 41 23 38 32 38C41 38 48 41 48 52V54H16V52Z" fill="url(#kc-sphere)" />
            <path d="M32 38C26 38 20 42 18 47C22 43 27 40 32 40C37 40 42 43 46 47C44 42 38 38 32 38Z" fill="white" opacity="0.35" />

            {/* Orbiting Satellite Star */}
            <circle cx="46" cy="18" r="4.5" fill="#F59E0B" />
            <circle cx="46" cy="18" r="2.5" fill="#FEF08A" />
          </svg>
        </div>
      );

    case 'kpi-queue':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="kq-grad" x1="16" y1="14" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38BDF8" />
                <stop offset="0.7" stopColor="#0284C7" />
                <stop offset="1" stopColor="#075985" />
              </linearGradient>
            </defs>
            {/* 3D Stack of Research Cards */}
            <path d="M16 38L32 46L48 38L32 30L16 38Z" fill="#0C4A6E" />
            <path d="M16 36L32 44L48 36L32 28L16 36Z" fill="#0284C7" />

            <path d="M16 28L32 36L48 28L32 20L16 28Z" fill="#0369A1" />
            <path d="M16 26L32 34L48 26L32 18L16 26Z" fill="#0EA5E9" />

            <path d="M16 18L32 26L48 18L32 10L16 18Z" fill="url(#kq-grad)" />
            <path d="M32 11L46 18L32 24L18 18L32 11Z" fill="white" opacity="0.5" />

            {/* Priority Beacon Spark */}
            <circle cx="32" cy="18" r="4" fill="#38BDF8" />
            <circle cx="32" cy="18" r="2" fill="white" />
          </svg>
        </div>
      );

    case 'kpi-approvals':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="kap-grad" x1="14" y1="10" x2="50" y2="52" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34D399" />
                <stop offset="0.6" stopColor="#10B981" />
                <stop offset="1" stopColor="#047857" />
              </linearGradient>
            </defs>
            <circle cx="32" cy="34" r="20" fill="#064E3B" opacity="0.5" />
            <circle cx="32" cy="32" r="19" fill="url(#kap-grad)" />
            <ellipse cx="26" cy="22" rx="7" ry="4" transform="rotate(-30 26 22)" fill="white" opacity="0.5" />

            <path d="M22 33L29 40L43 24" stroke="#064E3B" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M22 31L29 38L43 22" stroke="white" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      );

    case 'kpi-revenue':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="kr-gold" x1="16" y1="12" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#FDE68A" />
                <stop offset="0.6" stopColor="#F59E0B" />
                <stop offset="1" stopColor="#D97706" />
              </linearGradient>
            </defs>
            <circle cx="32" cy="34" r="20" fill="#78350F" opacity="0.5" />
            <circle cx="32" cy="32" r="19" fill="url(#kr-gold)" />
            <circle cx="32" cy="32" r="15" stroke="#FEF3C7" strokeWidth="2" opacity="0.7" />
            <text x="32" y="38" fontSize="18" fontWeight="900" fill="#78350F" textAnchor="middle">$</text>
            <circle cx="24" cy="22" r="2" fill="white" opacity="0.8" />
          </svg>
        </div>
      );

    case 'kpi-tenants':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="kt-tower" x1="20" y1="10" x2="44" y2="52" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34D399" />
                <stop offset="0.7" stopColor="#059669" />
                <stop offset="1" stopColor="#064E3B" />
              </linearGradient>
            </defs>
            {/* 3D Isometric Tower Base */}
            <path d="M22 20L36 12L46 18V54L32 60L22 54V20Z" fill="#064E3B" />
            <path d="M22 18L36 10L46 16V52L32 58L22 52V18Z" fill="url(#kt-tower)" />
            <path d="M36 10L46 16L32 22L22 18L36 10Z" fill="#A7F3D0" />
            {/* Glowing Windows Grid */}
            <rect x="25" y="24" width="4" height="4" rx="1" fill="#FEF08A" />
            <rect x="25" y="31" width="4" height="4" rx="1" fill="#FEF08A" />
            <rect x="25" y="38" width="4" height="4" rx="1" fill="#FEF08A" />
            <rect x="36" y="24" width="5" height="4" rx="1" fill="#6EE7B7" />
            <rect x="36" y="31" width="5" height="4" rx="1" fill="#6EE7B7" />
          </svg>
        </div>
      );

    case 'kpi-onboarding':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="ko-grad" x1="14" y1="12" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38BDF8" />
                <stop offset="0.6" stopColor="#0284C7" />
                <stop offset="1" stopColor="#0369A1" />
              </linearGradient>
            </defs>
            <circle cx="28" cy="22" r="10" fill="url(#ko-grad)" />
            <path d="M14 48C14 40 20 36 28 36C36 36 42 40 42 48V50H14V48Z" fill="url(#ko-grad)" />
            {/* 3D Plus Crest */}
            <circle cx="44" cy="28" r="9" fill="#0284C7" />
            <circle cx="44" cy="28" r="8" fill="#38BDF8" />
            <path d="M44 23V33M39 28H49" stroke="white" strokeWidth="2.8" strokeLinecap="round" />
          </svg>
        </div>
      );

    case 'kpi-alert':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="ka-grad" x1="16" y1="12" x2="48" y2="52" gradientUnits="userSpaceOnUse">
                <stop stopColor="#FB7185" />
                <stop offset="0.6" stopColor="#E11D48" />
                <stop offset="1" stopColor="#9F1239" />
              </linearGradient>
            </defs>
            {/* 3D Warning Triangle with Extrusion */}
            <path d="M32 8L54 48H10L32 8Z" fill="#881337" />
            <path d="M32 10L52 46H12L32 10Z" fill="url(#ka-grad)" />
            <path d="M32 11L48 44H16L32 11Z" fill="white" opacity="0.25" />
            <rect x="30" y="22" width="4" height="12" rx="2" fill="white" />
            <circle cx="32" cy="39" r="2.5" fill="white" />
          </svg>
        </div>
      );

    case 'kpi-campaigns':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="kcp-grad" x1="16" y1="12" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#C084FC" />
                <stop offset="0.6" stopColor="#9333EA" />
                <stop offset="1" stopColor="#581C87" />
              </linearGradient>
            </defs>
            {/* 3D Rocket Spacecraft */}
            <path d="M32 8C32 8 44 18 44 34L32 40L20 34C20 18 32 8 32 8Z" fill="url(#kcp-grad)" />
            <ellipse cx="32" cy="24" rx="4" ry="4" fill="#38BDF8" />
            <path d="M20 34L12 42L20 40V34Z" fill="#7E22CE" />
            <path d="M44 34L52 42L44 40V34Z" fill="#7E22CE" />
            <path d="M28 40L32 54L36 40H28Z" fill="#F59E0B" />
            <path d="M29 40L32 48L35 40H29Z" fill="#FEF08A" />
          </svg>
        </div>
      );

    case 'kpi-growth':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="kg-grad" x1="14" y1="14" x2="50" y2="50" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34D399" />
                <stop offset="0.6" stopColor="#10B981" />
                <stop offset="1" stopColor="#047857" />
              </linearGradient>
            </defs>
            <circle cx="32" cy="34" r="20" fill="#064E3B" opacity="0.4" />
            <circle cx="32" cy="32" r="19" fill="url(#kg-grad)" />
            {/* 3D Ascending Arrow */}
            <path d="M20 38L30 28L36 34L46 22" stroke="white" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M38 22H46V30" stroke="white" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      );

    case 'kpi-storage':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="ks-grad" x1="16" y1="12" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#60A5FA" />
                <stop offset="0.7" stopColor="#2563EB" />
                <stop offset="1" stopColor="#1E3A8A" />
              </linearGradient>
            </defs>
            {/* Cylinder 1 Bottom */}
            <path d="M16 42C16 38 23 35 32 35C41 35 48 38 48 42V48C48 52 41 55 32 55C23 55 16 52 16 48V42Z" fill="#172554" />
            <ellipse cx="32" cy="42" rx="16" ry="6" fill="#2563EB" />
            {/* Cylinder 2 Middle */}
            <path d="M16 30C16 26 23 23 32 23C41 23 48 26 48 30V36C48 40 41 43 32 43C23 43 16 40 16 36V30Z" fill="#1E3A8A" />
            <ellipse cx="32" cy="30" rx="16" ry="6" fill="#3B82F6" />
            {/* Cylinder 3 Top */}
            <path d="M16 18C16 14 23 11 32 11C41 11 48 14 48 18V24C48 28 41 31 32 31C23 31 16 28 16 24V18Z" fill="#1D4ED8" />
            <ellipse cx="32" cy="18" rx="16" ry="6" fill="url(#ks-grad)" />
            <ellipse cx="32" cy="18" rx="13" ry="4.5" stroke="#93C5FD" strokeWidth="1.5" />
            {/* LED Status Dots */}
            <circle cx="24" cy="33" r="1.5" fill="#34D399" />
            <circle cx="24" cy="45" r="1.5" fill="#34D399" />
          </svg>
        </div>
      );

    case 'kpi-efficiency':
      return (
        <div className={`relative ${sizeClass} shrink-0 filter drop-shadow-md select-none ${animClass} ${className}`}>
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <defs>
              <linearGradient id="ke-gauge" x1="16" y1="16" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stopColor="#818CF8" />
                <stop offset="0.6" stopColor="#4F46E5" />
                <stop offset="1" stopColor="#312E81" />
              </linearGradient>
            </defs>
            <circle cx="32" cy="34" r="20" fill="#1E1B4B" opacity="0.4" />
            <circle cx="32" cy="32" r="19" fill="url(#ke-gauge)" />
            {/* Tachometer Arc */}
            <path d="M18 36C18 26 24 20 32 20C40 20 46 26 46 36" stroke="#C7D2FE" strokeWidth="3" strokeLinecap="round" />
            {/* Glowing needle */}
            <path d="M32 34L39 25" stroke="#38BDF8" strokeWidth="3.5" strokeLinecap="round" />
            <circle cx="32" cy="34" r="4" fill="#38BDF8" />
            <circle cx="32" cy="34" r="2" fill="white" />
          </svg>
        </div>
      );

    default:
      return null;
  }
};
