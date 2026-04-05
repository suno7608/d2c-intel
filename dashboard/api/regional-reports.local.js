/**
 * GET /api/regional-reports  — LOCAL DEV VERSION
 * 로컬 파일시스템에서 직접 읽음 (GitHub 불필요)
 * local-dev-server.mjs 에서 이 파일을 우선 사용
 */

import fs from 'fs';
import path from 'path';

// process.cwd()는 서버 실행 디렉터리 (d2c-intel 루트)
const REPO_ROOT = process.cwd();

const REGIONS = ['nam', 'eur', 'latam', 'asia', 'mea'];
const REGION_NAMES = {
  nam: { ko: '북미', en: 'North America' },
  eur: { ko: '유럽', en: 'Europe' },
  latam: { ko: '중남미', en: 'Latin America' },
  asia: { ko: '아시아 태평양', en: 'Asia Pacific' },
  mea: { ko: '중동·아프리카', en: 'Middle East & Africa' },
};

function getAvailableDates() {
  const dir = path.join(REPO_ROOT, 'reports', 'json', 'regional');
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter(f => fs.statSync(path.join(dir, f)).isDirectory())
    .sort().reverse();
}

function readLocalJSON(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); }
  catch { return null; }
}

function readLocalFile(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try { return fs.readFileSync(filePath, 'utf8'); }
  catch { return null; }
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'no-store');

  try {
    const { list, date, region, format = 'full' } = req.query;

    if (list === 'true') {
      const dates = getAvailableDates();
      const result = [];
      for (const d of dates.slice(0, 12)) {
        const indexPath = path.join(REPO_ROOT, 'reports', 'json', 'regional', d, 'index.json');
        const index = readLocalJSON(indexPath);
        result.push({
          date: d,
          period_start: index?.period_start,
          period_end: index?.period_end,
          regions: Object.keys(index?.regions || {}).map(rid => ({
            id: rid,
            ...REGION_NAMES[rid],
            total_records: index.regions[rid]?.total_records || 0,
            chinese_brand_total: index.regions[rid]?.chinese_brand_total || 0,
            countries: index.regions[rid]?.countries || [],
          })),
        });
      }
      return res.status(200).json({ success: true, data: { dates: result } });
    }

    const dates = getAvailableDates();
    const dateKey = date || dates[0];
    if (!dateKey) {
      return res.status(404).json({ error: 'No regional reports found', hint: 'Run d2c_regional_report_generator.py first' });
    }

    const regionsToFetch = region && REGIONS.includes(region) ? [region] : REGIONS;

    // 기간 정보
    const indexPath = path.join(REPO_ROOT, 'reports', 'json', 'regional', dateKey, 'index.json');
    const index = readLocalJSON(indexPath) || {};

    const result = {
      date: dateKey,
      period_start: index.period_start,
      period_end: index.period_end,
      regions: {},
    };

    for (const rid of regionsToFetch) {
      const entry = { id: rid, ...REGION_NAMES[rid] };

      if (format === 'json' || format === 'full') {
        const jsonPath = path.join(REPO_ROOT, 'reports', 'json', 'regional', dateKey, `${rid}.json`);
        entry.data = readLocalJSON(jsonPath);
      }

      if (format === 'md' || format === 'full') {
        const mdPath = path.join(REPO_ROOT, 'reports', 'md', 'regional', dateKey, `${rid}.md`);
        const raw = readLocalFile(mdPath);
        // 프론트매터 제거
        entry.markdown = raw ? raw.replace(/^---[\s\S]*?---\s*/, '') : null;
      }

      result.regions[rid] = entry;
    }

    return res.status(200).json({ success: true, data: result });

  } catch (error) {
    console.error('Regional Reports (local) API error:', error);
    return res.status(500).json({ error: error.message });
  }
}
