import type { GlobalThemeOverrides } from 'naive-ui'

/**
 * Alert Management Design System Theme
 *
 * Color Palette (Dark Mode OLED optimized):
 * - Primary: Amber (#F59E0B) - Main buttons, emphasis
 * - Secondary: Amber-400 (#FBBF24) - Secondary emphasis
 * - Background: Slate-900 (#0F172A) - Main background
 * - Surface: Slate-800 (#1E293B) - Card backgrounds
 * - Success: Emerald-500 (#10B981) - Long/buy signals
 * - Danger: Red-500 (#EF4444) - Short/sell signals
 * - Warning: Amber-500 (#F59E0B) - Warning states
 */

export const alertThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#F59E0B',
    primaryColorHover: '#FBBF24',
    primaryColorPressed: '#D97706',
    primaryColorSuppl: '#FBBF24',
    bodyColor: '#0F172A',
    cardColor: '#1E293B',
    modalColor: '#1E293B',
    popoverColor: '#1E293B',
    tableColor: '#1E293B',
    inputColor: '#1E293B',
    actionColor: '#1E293B',
    borderColor: 'rgba(148, 163, 184, 0.1)',
    dividerColor: 'rgba(148, 163, 184, 0.1)',
    hoverColor: 'rgba(245, 158, 11, 0.1)',
    textColorBase: '#F8FAFC',
    textColor1: '#F8FAFC',
    textColor2: '#CBD5E1',
    textColor3: '#94A3B8',
    placeholderColor: '#64748B',
    borderRadius: '8px',
    borderRadiusSmall: '6px',
    fontFamily: "'Fira Sans', 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontFamilyMono: "'Fira Code', 'SF Mono', 'Monaco', 'Consolas', monospace",
  },
  Button: {
    textColorPrimary: '#0F172A',
    textColorHoverPrimary: '#0F172A',
    textColorPressedPrimary: '#0F172A',
    textColorFocusPrimary: '#0F172A',
    colorSecondary: 'rgba(245, 158, 11, 0.15)',
    colorSecondaryHover: 'rgba(245, 158, 11, 0.25)',
    colorSecondaryPressed: 'rgba(245, 158, 11, 0.35)',
    borderSecondary: '1px solid rgba(245, 158, 11, 0.3)',
    textColorSecondary: '#F59E0B',
    textColorSecondaryHover: '#FBBF24',
  },
  Card: {
    borderRadius: '12px',
    paddingMedium: '16px',
    paddingSmall: '12px',
    borderColor: 'rgba(148, 163, 184, 0.1)',
    titleTextColor: '#F8FAFC',
    colorEmbedded: '#1E293B',
  },
  Tag: {
    borderRadius: '6px',
    padding: '0 8px',
    fontSize: '11px',
    fontWeight: '500',
  },
  Tabs: {
    tabTextColorLine: '#94A3B8',
    tabTextColorActiveLine: '#F59E0B',
    tabTextColorHoverLine: '#F8FAFC',
    barColor: '#F59E0B',
    textColor: '#94A3B8',
    textColorActive: '#F59E0B',
  },
  Input: {
    borderRadius: '8px',
    color: '#1E293B',
    colorFocus: '#1E293B',
    border: '1px solid rgba(148, 163, 184, 0.1)',
    borderHover: '1px solid rgba(245, 158, 11, 0.4)',
    borderFocus: '1px solid rgba(245, 158, 11, 0.6)',
    boxShadowFocus: '0 0 0 2px rgba(245, 158, 11, 0.2)',
  },
  Select: {
    peers: {
      InternalSelection: {
        borderRadius: '8px',
        color: '#1E293B',
        border: '1px solid rgba(148, 163, 184, 0.1)',
        borderHover: '1px solid rgba(245, 158, 11, 0.4)',
        borderFocus: '1px solid rgba(245, 158, 11, 0.6)',
        boxShadowFocus: '0 0 0 2px rgba(245, 158, 11, 0.2)',
      },
    },
  },
  Modal: {
    borderRadius: '16px',
    color: '#1E293B',
  },
  Alert: {
    borderRadius: '10px',
    padding: '12px 16px',
  },
  Spin: {
    textColor: '#94A3B8',
  },
  Empty: {
    textColor: '#64748B',
    extraTextColor: '#64748B',
  },
}

/**
 * CSS Custom Properties for Alert Dashboard
 * Used for component-specific styling
 */
export const alertCssVars = {
  // Primary colors
  '--alert-primary': '#F59E0B',
  '--alert-primary-hover': '#FBBF24',
  '--alert-primary-pressed': '#D97706',

  // Background colors
  '--alert-bg': '#0F172A',
  '--alert-surface': '#1E293B',
  '--alert-surface-hover': '#334155',

  // Text colors
  '--alert-text-primary': '#F8FAFC',
  '--alert-text-secondary': '#94A3B8',
  '--alert-text-tertiary': '#64748B',

  // Signal colors
  '--alert-success': '#10B981',
  '--alert-success-bg': 'rgba(16, 185, 129, 0.15)',
  '--alert-danger': '#EF4444',
  '--alert-danger-bg': 'rgba(239, 68, 68, 0.15)',
  '--alert-warning': '#F59E0B',
  '--alert-warning-bg': 'rgba(245, 158, 11, 0.15)',

  // Border colors
  '--alert-border': 'rgba(148, 163, 184, 0.1)',
  '--alert-border-hover': 'rgba(245, 158, 11, 0.3)',

  // Spacing
  '--alert-spacing-xs': '4px',
  '--alert-spacing-sm': '8px',
  '--alert-spacing-md': '12px',
  '--alert-spacing-lg': '16px',
  '--alert-spacing-xl': '24px',

  // Border radius
  '--alert-radius-sm': '6px',
  '--alert-radius-md': '8px',
  '--alert-radius-lg': '12px',

  // Transitions
  '--alert-transition': '200ms ease-out',
  '--alert-transition-slow': '300ms cubic-bezier(0.4, 0, 0.2, 1)',

  // Shadows
  '--alert-shadow-sm': '0 2px 8px rgba(0, 0, 0, 0.2)',
  '--alert-shadow-md': '0 4px 16px rgba(0, 0, 0, 0.3)',
  '--alert-shadow-lg': '0 8px 24px rgba(0, 0, 0, 0.4)',
  '--alert-shadow-glow': '0 0 20px rgba(245, 158, 11, 0.15)',
} as const

export type AlertCssVars = typeof alertCssVars
