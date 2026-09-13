/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/client-v2/**/*.{ts,tsx}'],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        v2navy: {
          DEFAULT: '#0B2D5B',
          deep: '#082144',
          hover: '#123F75',
          active: '#00B4C6',
        },
        v2canvas: '#F3F6F9',
        v2card: '#FFFFFF',
        v2line: '#DDE6EF',
        v2ink: '#0B2D5B',
        v2muted: '#6B7280',
        v2brand: {
          DEFAULT: '#0B2D5B',
          soft: '#123F75',
          tint: '#E6F7FA',
        },
        v2indigo: {
          DEFAULT: '#00B4C6',
          tint: '#E6F7FA',
        },
        v2emerald: {
          DEFAULT: '#22C55E',
          tint: '#EAF9EF',
        },
        v2amber: {
          DEFAULT: '#D99A24',
          deep: '#9A6B10',
          tint: '#FFF6E2',
        },
        v2red: {
          DEFAULT: '#DC2626',
          deep: '#B91C1C',
          tint: '#FEECEC',
        },
      },
      borderRadius: {
        'v2xl': '18px',
        'v2lg': '14px',
      },
      boxShadow: {
        'v2sm': '0 1px 2px rgba(15,27,61,0.05), 0 1px 4px rgba(15,27,61,0.06)',
        'v2md': '0 10px 30px rgba(15,27,61,0.10)',
      },
      fontSize: {
        'v2xs': ['11px', { lineHeight: '14px' }],
        'v2sm': ['12.5px', { lineHeight: '18px' }],
        'v2base': ['14px', { lineHeight: '20px' }],
        'v2lg': ['16px', { lineHeight: '22px' }],
        'v2xl': ['20px', { lineHeight: '26px' }],
        'v2hero': ['26px', { lineHeight: '32px' }],
      },
    },
  },
  plugins: [],
};
