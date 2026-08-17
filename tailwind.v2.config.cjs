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
          DEFAULT: '#0F1B3D',
          deep: '#0A1329',
          hover: '#1E2F5E',
          active: '#1768F2',
        },
        v2canvas: '#F7F9FC',
        v2card: '#FFFFFF',
        v2line: '#E5EAF3',
        v2ink: '#0F1B3D',
        v2muted: '#5B6B84',
        v2brand: {
          DEFAULT: '#1768F2',
          soft: '#4F8BFF',
          tint: '#E9F1FF',
        },
        v2indigo: {
          DEFAULT: '#6366F1',
          tint: '#EEEFFE',
        },
        v2emerald: {
          DEFAULT: '#12B886',
          tint: '#E8F8F0',
        },
        v2amber: {
          DEFAULT: '#F6B33D',
          deep: '#D98A14',
          tint: '#FDF3E3',
        },
        v2red: {
          DEFAULT: '#E5534C',
          deep: '#C8433C',
          tint: '#FDECEB',
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