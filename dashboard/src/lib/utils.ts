import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number): string {
  return n.toLocaleString();
}

export function formatPct(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`;
}

export function changeIndicator(current: number, previous: number): string {
  if (current > previous) return "up";
  if (current < previous) return "down";
  return "same";
}

export function changePct(current: number, previous: number): number {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
}
