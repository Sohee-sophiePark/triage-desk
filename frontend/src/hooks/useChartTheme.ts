import { useThemeStore } from '@/stores/themeStore';

export interface ChartTheme {
  text: string;
  muted: string;
  grid: string;
  tooltip: { bg: string; border: string; text: string };
  colors: string[];
}

const DARK: ChartTheme = {
  text: '#e5e5e5',
  muted: '#737373',
  grid: '#262626',
  tooltip: { bg: '#111111', border: '#262626', text: '#e5e5e5' },
  colors: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#f97316'],
};

const LIGHT: ChartTheme = {
  text: '#111827',
  muted: '#6b7280',
  grid: '#e5e7eb',
  tooltip: { bg: '#ffffff', border: '#e5e7eb', text: '#111827' },
  colors: ['#2563eb', '#059669', '#d97706', '#7c3aed', '#dc2626', '#0891b2', '#ea580c'],
};

export function useChartTheme(): ChartTheme {
  const { theme } = useThemeStore();
  return theme === 'dark' ? DARK : LIGHT;
}
