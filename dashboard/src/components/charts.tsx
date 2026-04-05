"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend,
} from "recharts";

const COLORS = ["#a50034", "#2563eb", "#16a34a", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];

interface ChartProps {
  data: { name: string; value: number }[];
  height?: number;
}

export function ProductDonut({ data, height = 240 }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" label={({ name, percent }: any) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false} fontSize={11}>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function BrandBar({ data, height = 240 }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 60, right: 16, top: 8, bottom: 8 }}>
        <XAxis type="number" fontSize={11} />
        <YAxis type="category" dataKey="name" fontSize={11} width={55} />
        <Tooltip />
        <Bar dataKey="value" fill="#a50034" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

interface TrendProps {
  data: { week: string; total: number; chinese: number; negative: number }[];
  height?: number;
}

export function WeeklyTrend({ data, height = 280 }: TrendProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ left: 0, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
        <XAxis dataKey="week" fontSize={11} />
        <YAxis fontSize={11} />
        <Tooltip />
        <Legend fontSize={11} />
        <Line type="monotone" dataKey="total" name="Total Records" stroke="#a50034" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="chinese" name="Chinese Threat" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="negative" name="Consumer Negative" stroke="#dc2626" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

interface RegionChartProps {
  data: { name: string; records: number; countries: number }[];
  height?: number;
}

export function RegionBar({ data, height = 200 }: RegionChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ left: 16, right: 16, top: 8, bottom: 8 }}>
        <XAxis dataKey="name" fontSize={11} />
        <YAxis fontSize={11} />
        <Tooltip />
        <Bar dataKey="records" name="Records" fill="#a50034" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

interface PillarChartProps {
  data: { name: string; value: number }[];
  height?: number;
}

export function PillarChart({ data, height = 200 }: PillarChartProps) {
  const shortNames: Record<string, string> = {
    "Chinese Brand Threat Tracking": "Chinese Threat",
    "Retail Channel Promotions": "Retail Promo",
    "Competitive Price & Positioning": "Price Intel",
    "Consumer Sentiment": "Consumer",
    "Market Signal": "Market Signal",
  };
  const mapped = data.map((d) => ({ ...d, name: shortNames[d.name] || d.name }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={mapped} margin={{ left: 16, right: 16, top: 8, bottom: 8 }}>
        <XAxis dataKey="name" fontSize={10} angle={-15} textAnchor="end" height={50} />
        <YAxis fontSize={11} />
        <Tooltip />
        <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
