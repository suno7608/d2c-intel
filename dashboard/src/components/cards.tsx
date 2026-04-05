"use client";

import { formatNumber, formatPct, changePct } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  prev?: number;
  current?: number;
  icon?: string;
  color?: "default" | "danger" | "success" | "warning" | "info";
}

const COLOR_MAP = {
  default: "border-l-[var(--card-border)]",
  danger: "border-l-[var(--danger)]",
  success: "border-l-[var(--success)]",
  warning: "border-l-[var(--warning)]",
  info: "border-l-[var(--info)]",
};

export function StatCard({ title, value, subtitle, prev, current, icon, color = "default" }: StatCardProps) {
  const showChange = prev !== undefined && current !== undefined && prev > 0;
  const pct = showChange ? changePct(current!, prev!) : 0;
  const isUp = pct > 0;

  return (
    <div className={`rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4 border-l-4 ${COLOR_MAP[color]}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider">{title}</p>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <p className="mt-2 text-2xl font-bold">{typeof value === "number" ? formatNumber(value) : value}</p>
      {showChange && (
        <p className={`mt-1 text-xs ${isUp ? "text-[var(--success)]" : "text-[var(--danger)]"}`}>
          {isUp ? "↑" : "↓"} {formatPct(Math.abs(pct))} vs prev week
        </p>
      )}
      {subtitle && <p className="mt-1 text-xs text-[var(--muted)]">{subtitle}</p>}
    </div>
  );
}

interface AlertCardProps {
  brand: string;
  model: string;
  country: string;
  changePct: number;
  direction: string;
  currency: string;
  prevPrice: number;
  newPrice: number;
}

export function PriceAlertCard({ brand, model, country, changePct: pct, direction, currency, prevPrice, newPrice }: AlertCardProps) {
  const isDrop = direction === "drop";
  return (
    <div className="flex items-center justify-between py-2 border-b border-[var(--card-border)] last:border-0">
      <div>
        <p className="text-sm font-medium">
          {brand} {model}
        </p>
        <p className="text-xs text-[var(--muted)]">{country}</p>
      </div>
      <div className="text-right">
        <p className={`text-sm font-bold ${isDrop ? "text-[var(--success)]" : "text-[var(--danger)]"}`}>
          {isDrop ? "↓" : "↑"} {Math.abs(pct).toFixed(1)}%
        </p>
        <p className="text-xs text-[var(--muted)]">
          {currency} {prevPrice.toLocaleString()} → {newPrice.toLocaleString()}
        </p>
      </div>
    </div>
  );
}

interface InsightCardProps {
  insight: string;
  index: number;
}

export function InsightCard({ insight, index }: InsightCardProps) {
  return (
    <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
      <div className="flex gap-3">
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--accent)] text-white text-xs flex items-center justify-center font-bold">
          {index + 1}
        </span>
        <p className="text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: insight }} />
      </div>
    </div>
  );
}
