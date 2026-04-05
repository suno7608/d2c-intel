import fs from "fs";
import path from "path";

const ROOT = path.resolve(process.cwd(), "..");

export interface RawRecord {
  country: string;
  product: string;
  pillar: string;
  brand: string;
  signal_type: string;
  value: string;
  currency: string;
  price_value: string;
  discount: string;
  rating: string;
  quote_original: string;
  source_url: string;
  source: string;
  collected_at: string;
  confidence: string;
  search_engine?: string;
}

export interface WeeklyStats {
  date: string;
  total_records: number;
  countries_count: number;
  countries: Record<string, number>;
  products: Record<string, number>;
  brands: Record<string, number>;
  pillars: Record<string, number>;
  confidence: Record<string, number>;
  tv_ratio_pct: number;
  chinese_brand_total: number;
  chinese_by_country: Record<string, number>;
  chinese_by_product: Record<string, number>;
  consumer_negative_count: number;
  lg_promo_count: number;
}

export interface PriceAlert {
  price_key: string;
  brand: string;
  product: string;
  model: string;
  country: string;
  currency: string;
  prev_price: number;
  new_price: number;
  change_pct: number;
  direction: "drop" | "increase";
  prev_date: string;
  new_date: string;
  source_url: string;
}

export interface ReportMetadata {
  week: string;
  report_period: { start: string; end: string };
  version: string;
  generated_at: string;
  metrics: Record<string, number>;
  critical_countries: string[];
  executive_key_insights: string[];
  links: Record<string, string>;
}

export const REGIONS: Record<string, { name: string; nameKo: string; countries: string[] }> = {
  na: { name: "North America", nameKo: "북미", countries: ["US", "CA", "MX"] },
  eu: { name: "Europe", nameKo: "유럽", countries: ["UK", "DE", "FR", "ES", "IT"] },
  latam: { name: "Latin America", nameKo: "중남미", countries: ["BR", "CL"] },
  apac: { name: "Asia Pacific", nameKo: "아시아", countries: ["AU", "TH", "TW", "SG"] },
  mea: { name: "MEA", nameKo: "중동/아프리카", countries: ["SA", "EG", "TR"] },
};

export const COUNTRY_FLAGS: Record<string, string> = {
  US: "🇺🇸", CA: "🇨🇦", MX: "🇲🇽", UK: "🇬🇧", DE: "🇩🇪",
  FR: "🇫🇷", ES: "🇪🇸", IT: "🇮🇹", BR: "🇧🇷", CL: "🇨🇱",
  AU: "🇦🇺", TH: "🇹🇭", TW: "🇹🇼", SG: "🇸🇬", SA: "🇸🇦",
  EG: "🇪🇬", TR: "🇹🇷",
};

export const COUNTRY_NAMES: Record<string, string> = {
  US: "United States", CA: "Canada", MX: "Mexico", UK: "United Kingdom",
  DE: "Germany", FR: "France", ES: "Spain", IT: "Italy", BR: "Brazil",
  CL: "Chile", AU: "Australia", TH: "Thailand", TW: "Taiwan", SG: "Singapore",
  SA: "Saudi Arabia", EG: "Egypt", TR: "Turkey",
};

export function getCountryRegion(country: string): string {
  for (const [region, cfg] of Object.entries(REGIONS)) {
    if (cfg.countries.includes(country)) return region;
  }
  return "unknown";
}

function readJSON<T>(filePath: string): T | null {
  const full = path.join(ROOT, filePath);
  if (!fs.existsSync(full)) return null;
  return JSON.parse(fs.readFileSync(full, "utf-8"));
}

function readJSONL<T>(filePath: string): T[] {
  const full = path.join(ROOT, filePath);
  if (!fs.existsSync(full)) return [];
  return fs
    .readFileSync(full, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));
}

export function getWeeklyStatsList(): WeeklyStats[] {
  const dir = path.join(ROOT, "data/weekly_stats");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json") && /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
    .sort()
    .map((f) => readJSON<WeeklyStats>(`data/weekly_stats/${f}`)!)
    .filter(Boolean);
}

export function getWeeklyStats(date: string): WeeklyStats | null {
  return readJSON(`data/weekly_stats/${date}.json`);
}

export function getRawRecords(date: string): RawRecord[] {
  return readJSONL(`data/raw/openclaw_${date}.jsonl`);
}

export function getAllRawRecords(): RawRecord[] {
  const dir = path.join(ROOT, "data/raw");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.startsWith("openclaw_") && f.endsWith(".jsonl"))
    .sort()
    .flatMap((f) => readJSONL<RawRecord>(`data/raw/${f}`));
}

export function getPriceAlerts(date: string): { alerts: PriceAlert[] } | null {
  return readJSON(`data/price_history/price_alerts_${date}.json`);
}

export function getLatestPriceAlerts(): PriceAlert[] {
  const dir = path.join(ROOT, "data/price_history");
  if (!fs.existsSync(dir)) return [];
  const files = fs
    .readdirSync(dir)
    .filter((f) => f.startsWith("price_alerts_") && f.endsWith(".json"))
    .sort();
  if (!files.length) return [];
  const data = readJSON<{ alerts: PriceAlert[] }>(`data/price_history/${files[files.length - 1]}`);
  return data?.alerts ?? [];
}

export function getReportMetadata(date: string): ReportMetadata | null {
  return readJSON(`reports/html/${date}/metadata.json`);
}

export function getManifest(): { weeks: ReportMetadata[] } | null {
  return readJSON("reports/html/latest/manifest.json");
}

export function getReportDates(): string[] {
  const dir = path.join(ROOT, "reports/html");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => /^\d{4}-\d{2}-\d{2}$/.test(f))
    .sort()
    .reverse();
}

export function getReportHTML(date: string, lang: "ko" | "en" = "ko"): string | null {
  const fileName = lang === "en" ? "index_en.html" : "index.html";
  const full = path.join(ROOT, `reports/html/${date}/${fileName}`);
  if (!fs.existsSync(full)) return null;
  return fs.readFileSync(full, "utf-8");
}
