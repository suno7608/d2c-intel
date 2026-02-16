#!/usr/bin/env bash
# 매주 수집 후 실행 — W-o-W 트렌드 비교용 통계 저장
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
DATA_FILE="$ROOT_DIR/data/raw/openclaw_${DATE_KEY}.jsonl"
STATS_DIR="$ROOT_DIR/data/weekly_stats"
STATS_FILE="$STATS_DIR/${DATE_KEY}.json"

mkdir -p "$STATS_DIR"

if [[ ! -f "$DATA_FILE" ]]; then
  echo "data file not found: $DATA_FILE" >&2
  exit 1
fi

python3 -c "
import sys, json
from collections import Counter

records = []
for line in open('$DATA_FILE'):
    line = line.strip()
    if not line.startswith('{'): continue
    try:
        records.append(json.loads(line))
    except: pass

countries = Counter(r.get('country','?') for r in records)
products = Counter(r.get('product','?') for r in records)
brands = Counter(r.get('brand','?') for r in records)
pillars = Counter(r.get('pillar','?') for r in records)
confidence = Counter(r.get('confidence','?') for r in records)

# 중국 브랜드 국가별
chinese_brands = {'TCL','Hisense','Haier','Midea'}
chinese_by_country = Counter()
chinese_by_product = Counter()
for r in records:
    if r.get('brand','') in chinese_brands:
        chinese_by_country[r.get('country','?')] += 1
        chinese_by_product[r.get('product','?')] += 1

# Consumer negative
negatives = [r for r in records if 'negative' in r.get('signal_type','').lower() or 'complaint' in r.get('signal_type','').lower()]

# LG 프로모션
lg_promos = [
    r for r in records
    if r.get('brand','') == 'LG'
    and (
        'promo' in r.get('signal_type','').lower()
        or 'discount' in r.get('signal_type','').lower()
    )
]

def is_low_confidence(v):
    if isinstance(v, str):
        return v.lower() == 'low'
    if isinstance(v, (int, float)):
        return v < 0.5
    return False

low_conf_count = sum(1 for r in records if is_low_confidence(r.get('confidence')))

stats = {
    'date': '$DATE_KEY',
    'total_records': len(records),
    'countries_count': len(countries),
    'countries': dict(countries.most_common()),
    'products': dict(products.most_common()),
    'brands': dict(brands.most_common()),
    'pillars': dict(pillars.most_common()),
    'confidence': dict(confidence.most_common()),
    'tv_ratio_pct': round(products.get('TV',0)/max(len(records),1)*100, 1),
    'chinese_brand_total': sum(chinese_by_country.values()),
    'chinese_by_country': dict(chinese_by_country.most_common()),
    'chinese_by_product': dict(chinese_by_product.most_common()),
    'chinese_countries_count': len(chinese_by_country),
    'consumer_negative_count': len(negatives),
    'lg_promo_count': len(lg_promos),
    'low_confidence_pct': round(low_conf_count/max(len(records),1)*100, 1)
}

with open('$STATS_FILE', 'w') as f:
    json.dump(stats, f, indent=2, ensure_ascii=False)

print(f'Stats saved: {len(records)} records, {len(countries)} countries, TV {stats[\"tv_ratio_pct\"]}%')
print(f'Low confidence: {stats[\"low_confidence_pct\"]}%')
" 

echo "saved: $STATS_FILE"
