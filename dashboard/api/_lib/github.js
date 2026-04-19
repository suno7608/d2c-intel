/**
 * GitHub Data Access Layer
 * Fetches raw data files from the d2c-intel repository.
 * Uses GitHub API with token for private repos or unauthenticated for public.
 */

const REPO_OWNER = 'suno7608';
const REPO_NAME = 'd2c-intel';
const BRANCH = 'master';

const GITHUB_API = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}`;
const RAW_BASE = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${BRANCH}`;

function getHeaders() {
  const headers = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'd2c-intel-dashboard',
  };
  if (process.env.GITHUB_TOKEN) {
    headers['Authorization'] = `Bearer ${process.env.GITHUB_TOKEN}`;
  }
  return headers;
}

/**
 * Fetch a raw file from the repository
 */
export async function fetchRawFile(path) {
  const url = `${RAW_BASE}/${path}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}: ${res.status} ${res.statusText}`);
  }
  return res.text();
}

/**
 * Fetch and parse a JSON file from the repository
 */
export async function fetchJSON(path) {
  const text = await fetchRawFile(path);
  return JSON.parse(text);
}

/**
 * Fetch and parse a JSONL file (returns array of objects)
 */
export async function fetchJSONL(path) {
  const text = await fetchRawFile(path);
  return text
    .trim()
    .split('\n')
    .filter(line => line.trim())
    .map(line => JSON.parse(line));
}

/**
 * List files in a directory using GitHub API
 */
export async function listFiles(dirPath) {
  const url = `${GITHUB_API}/contents/${dirPath}?ref=${BRANCH}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to list ${dirPath}: ${res.status}`);
  }
  return res.json();
}

/**
 * Get the latest weekly stats date key
 */
export async function getLatestWeeklyDate() {
  const files = await listFiles('data/weekly_stats');
  const dates = files
    .filter(f => f.name.endsWith('.json'))
    .map(f => f.name.replace('.json', ''))
    .sort()
    .reverse();
  return dates[0] || null;
}

/**
 * Get the latest daily news date key
 */
export async function getLatestNewsDate() {
  const files = await listFiles('data/daily_news');
  const dates = files
    .filter(f => f.name.endsWith('.jsonl'))
    .map(f => f.name.replace('.jsonl', ''))
    .sort()
    .reverse();
  return dates[0] || null;
}

/**
 * Get available report dates
 */
export async function getReportDates() {
  const files = await listFiles('data/weekly_stats');
  return files
    .filter(f => f.name.endsWith('.json'))
    .map(f => f.name.replace('.json', ''))
    .sort()
    .reverse();
}

/**
 * Compute regional aggregation from raw JSONL data
 */
export function aggregateByRegion(records) {
  const regionMap = {
    US: 'nam', CA: 'nam',
    UK: 'eur', DE: 'eur', FR: 'eur', IT: 'eur', ES: 'eur',
    BR: 'latam', MX: 'latam', CL: 'latam',
    AU: 'asia', TW: 'asia', SG: 'asia', TH: 'asia',
    SA: 'mea', EG: 'mea',
  };

  const regionNames = {
    nam: 'North America',
    eur: 'Europe',
    latam: 'Latin America',
    asia: 'Asia Pacific',
    mea: 'Middle East & Africa',
  };

  const regions = {};

  for (const r of records) {
    const regionId = regionMap[r.country] || 'other';
    if (!regions[regionId]) {
      regions[regionId] = {
        id: regionId,
        name: regionNames[regionId] || 'Other',
        totalRecords: 0,
        countries: {},
        products: {},
        brands: {},
        pillars: {},
        signals: [],
      };
    }
    const reg = regions[regionId];
    reg.totalRecords++;
    reg.countries[r.country] = (reg.countries[r.country] || 0) + 1;
    reg.products[r.product] = (reg.products[r.product] || 0) + 1;
    if (r.brand) reg.brands[r.brand] = (reg.brands[r.brand] || 0) + 1;
    if (r.pillar) reg.pillars[r.pillar] = (reg.pillars[r.pillar] || 0) + 1;
    reg.signals.push({
      country: r.country,
      product: r.product,
      brand: r.brand,
      pillar: r.pillar,
      value: r.value,
      source: r.source,
      source_url: r.source_url,
      confidence: r.confidence,
    });
  }

  // Limit signals to top 50 per region (most recent / highest confidence)
  for (const reg of Object.values(regions)) {
    reg.signals = reg.signals
      .sort((a, b) => (b.confidence === 'high' ? 1 : 0) - (a.confidence === 'high' ? 1 : 0))
      .slice(0, 50);
  }

  return regions;
}

/**
 * Compute KPI metrics from weekly stats
 */
export function computeKPIs(currentStats, previousStats) {
  const current = currentStats;
  const prev = previousStats;

  const chineseTotal = current.chinese_brand_total || 0;
  const totalRecords = current.total_records || 1;
  const chinesePct = ((chineseTotal / totalRecords) * 100).toFixed(1);

  // Sentiment score (derived from consumer sentiment signals)
  const consumerSentiment = current.pillars?.['Consumer Sentiment'] || 0;
  const sentimentScore = consumerSentiment > 0
    ? Math.min(100, Math.round(50 + (consumerSentiment / totalRecords) * 500))
    : 72; // default baseline

  const kpis = {
    totalSignals: totalRecords,
    totalSignalsDelta: prev ? totalRecords - (prev.total_records || 0) : 0,
    countriesCovered: current.countries_count || 0,
    chineseBrandThreats: chineseTotal,
    chineseBrandPct: parseFloat(chinesePct),
    chineseDelta: prev ? chineseTotal - (prev.chinese_brand_total || 0) : 0,
    sentimentScore,
    lgPromoCount: current.lg_promo_count || 0,
    products: current.products || {},
    brands: current.brands || {},
    pillars: current.pillars || {},
    topCountries: current.countries || {},
    tvRatio: current.tv_ratio_pct || 0,
    dateKey: current.date,
  };

  return kpis;
}
