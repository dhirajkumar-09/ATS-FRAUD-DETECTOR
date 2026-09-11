import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { TrustLabel } from './types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getTrustColor(label: TrustLabel | string): string {
  switch (label?.toUpperCase()) {
    case 'TRUSTED':
      return '#3CB697';
    case 'SUSPICIOUS':
      return '#E09C52';
    case 'HIGH RISK':
    case 'FRAUD':
      return '#E05252';
    default:
      return '#6B7280';
  }
}

export function getSeverityColor(severity: string): string {
  switch (severity?.toUpperCase()) {
    case 'HIGH':
      return '#E05252';
    case 'MEDIUM':
      return '#E09C52';
    case 'LOW':
      return '#3CB697';
    default:
      return '#6B7280';
  }
}

export function getSeverityBadgeClass(severity: string): string {
  switch (severity?.toUpperCase()) {
    case 'HIGH':
      return 'bg-red-500/15 text-red-400 border border-red-500/30';
    case 'MEDIUM':
      return 'bg-amber-500/15 text-amber-400 border border-amber-500/30';
    case 'LOW':
      return 'bg-teal-500/15 text-teal-400 border border-teal-500/30';
    default:
      return 'bg-gray-500/15 text-gray-400 border border-gray-500/30';
  }
}

export function getTrustBadgeClass(label: TrustLabel | string): string {
  switch (label?.toUpperCase()) {
    case 'TRUSTED':
      return 'bg-teal-500/15 text-teal-400 border border-teal-500/30';
    case 'SUSPICIOUS':
      return 'bg-amber-500/15 text-amber-400 border border-amber-500/30';
    case 'HIGH RISK':
    case 'FRAUD':
      return 'bg-red-500/15 text-red-400 border border-red-500/30';
    default:
      return 'bg-gray-500/15 text-gray-400 border border-gray-500/30';
  }
}

export function formatScore(score: number): string {
  if (score == null || isNaN(score)) return '0.0';
  return (score * 100).toFixed(1);
}

export function formatPercent(value: number): string {
  if (value == null || isNaN(value)) return '0%';
  return `${Math.round(value * 100)}%`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const SIGNAL_COLORS: Record<string, string> = {
  near_white_text: '#E05252',
  hidden_text: '#E05252',
  keyword_stuffing: '#E09C52',
  font_size_manipulation: '#A855F7',
  whitespace_padding: '#3B82F6',
  invisible_characters: '#EC4899',
  default: '#6B7280',
};

export function getSignalColor(signalType: string): string {
  return SIGNAL_COLORS[signalType] ?? SIGNAL_COLORS.default;
}
