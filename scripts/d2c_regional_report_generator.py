#!/usr/bin/env python3
"""
D2C Intel — Regional Report Generator
=======================================
글로벌 JSONL 데이터를 지역별로 필터링하여
5개 지역(북미/유럽/중남미/아시아/중동아프리카)의
개별 주간 인텔리전스 리포트를 생성합니다.

Usage:
    python scripts/d2c_regional_report_generator.py [YYYY-MM-DD]

Environment:
    ANTHROPIC_API_KEY      — Anthropic API key (required)
    CLAUDE_MODEL_REPORT    — 모델 지정 (default: claude-sonnet-4-20250514)

Output:
    reports/md/regional/YYYY-MM-DD/nam.md
    reports/md/regional/YYYY-MM-DD/eur.md
    reports/md/regional/YYYY-MM-DD/latam.md
    reports/md/regional/YYYY-MM-DD/asia.md
    reports/md/regional/YYYY-MM-DD/mea.md
    reports/json/regional/YYYY-MM-DD/{region}.json  (structured data for dashboard)
"""

import json
import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import anthropic

# ──────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_MD_DIR = ROOT_DIR / "reports" / "md" / "regional"
REPORTS_JSON_DIR = ROOT_DIR / "reports" / "json" / "regional"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("d2c_regional_report")

DEFAULT_MODEL = "claude-sonnet-4-20250514"

# ──────────────────────────────────────────────────────────────
# Region Definitions
# ──────────────────────────────────────────────────────────────

REGIONS = {
    "nam": {
        "id": "nam",
        "name_ko": "북미",
        "name_en": "North America",
        "countries": ["US", "CA"],
        "key_retailers": "Amazon, Best Buy, Costco, Walmart, LG.com, RedFlagDeals",
        "currency_note": "USD/CAD",
    },
    "eur": {
        "id": "eur",
        "name_ko": "유럽",
        "name_en": "Europe",
        "countries": ["UK", "DE", "FR", "IT", "ES"],
        "key_retailers": "MediaMarkt, Currys, Fnac, Darty, Amazon EU, Unieuro, Trovaprezzi",
        "currency_note": "EUR/GBP",
    },
    "latam": {
        "id": "latam",
        "name_ko": "중남미",
        "name_en": "Latin America",
        "countries": ["BR", "MX", "CL"],
        "key_retailers": "Mercado Libre, Magazine Luiza, Liverpool, Pelando, Falabella",
        "currency_note": "BRL/MXN/CLP",
    },
    "asia": {
        "id": "asia",
        "name_ko": "아시아 태평양",
        "name_en": "Asia Pacific",
        "countries": ["AU", "TW", "SG", "TH"],
        "key_retailers": "JB Hi-Fi, Harvey Norman, OzBargain, PChome, Lazada, Shopee",
        "currency_note": "AUD/TWD/SGD/THB",
    },
    "mea": {
        "id": "mea",
        "name_ko": "중동·아프리카",
        "name_en": "Middle East & Africa",
        "countries": ["SA", "EG"],
        "key_retailers": "Noon, Jumia, Carrefour, Sharaf DG, Extra",
        "currency_note": "SAR/EGP",
    },
}

COUNTRY_FLAG = {
    "US": "🇺🇸", "CA": "🇨🇦", "UK": "🇬🇧", "DE": "🇩🇪",
    "FR": "🇫🇷", "ES": "🇪🇸", "IT": "🇮🇹", "BR": "🇧🇷",
    "MX": "🇲🇽", "CL": "🇨🇱", "TH": "🇹🇭", "AU": "🇦🇺",
    "TW": "🇹🇼", "SG": "🇸🇬", "EG": "🇪🇬", "SA": "🇸🇦",
}
COUNTRY_NAME_KO = {
    "US": "미국", "CA": "캐나다", "UK": "영국", "DE": "독일",
    "FR": "프랑스", "ES": "스페인", "IT": "이탈리아", "BR": "브라질",
    "MX": "멕시코", "CL": "칠레", "TH": "태국", "AU": "호주",
    "TW": "대만", "SG": "싱가포르", "EG": "이집트", "SA": "사우디아라비아",
}
CHINESE_BRANDS = {"tcl", "hisense", "haier", "midea"}


# ──────────────────────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> List[dict]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def filter_by_region(records: List[dict], region_countries: List[str]) -> List[dict]:
    return [r for r in records if r.get("country") in region_countries]


def compute_report_period(date_key: str) -> Tuple[str, str]:
    d = date.fromisoformat(date_key)
    days_since_saturday = (d.weekday() + 2) % 7
    end = d - timedelta(days=max(days_since_saturday, 1))
    start = end - timedelta(days=6)
    return start.isoformat(), end.isoformat()


# ──────────────────────────────────────────────────────────────
# Data Summarization for Claude Prompt
# ──────────────────────────────────────────────────────────────

def summarize_regional_data(records: List[dict], region: dict) -> str:
    total = len(records)
    countries = Counter(r.get("country", "?") for r in records)
    products = Counter(r.get("product", "?") for r in records)
    pillars = Counter(r.get("pillar", "?") for r in records)
    brands = Counter(r.get("brand", "?") for r in records)

    chinese_records = [r for r in records if r.get("brand", "").lower() in CHINESE_BRANDS]
    chinese_by_country = Counter(r.get("country", "?") for r in chinese_records)

    negative_kw = {"complaint", "problem", "issue", "broken", "refund", "negative", "불만"}
    negative_records = [
        r for r in records
        if any(kw in (r.get("signal_type", "") + r.get("quote_original", "")).lower() for kw in negative_kw)
    ]

    promo_records = [r for r in records if r.get("brand", "").lower() == "lg"]

    lines = [
        f"지역: {region['name_ko']} ({region['name_en']})",
        f"대상 국가: {', '.join(COUNTRY_FLAG.get(c, c) + ' ' + COUNTRY_NAME_KO.get(c, c) for c in region['countries'])}",
        f"주요 리테일 채널: {region['key_retailers']}",
        f"통화: {region['currency_note']}",
        "",
        f"총 데이터 수집 건수: {total}건",
        f"국가별: {', '.join(f'{COUNTRY_FLAG.get(k,k)} {COUNTRY_NAME_KO.get(k,k)}({v}건)' for k, v in countries.most_common())}",
        f"제품별: {', '.join(f'{k}({v}건)' for k, v in products.most_common())}",
        f"필라별: {', '.join(f'{k}({v}건)' for k, v in pillars.most_common())}",
        f"브랜드별: {', '.join(f'{k}({v}건)' for k, v in brands.most_common(10))}",
        "",
        f"중국 브랜드 위협 건수: {len(chinese_records)}건",
        f"중국 브랜드 국가별: {', '.join(f'{COUNTRY_FLAG.get(k,k)}{k}({v}건)' for k, v in chinese_by_country.most_common())}",
        f"소비자 부정 시그널: {len(negative_records)}건",
        f"LG 프로모션 시그널: {len(promo_records)}건",
        "",
        "=== 주요 시그널 (신뢰도 높은 순) ===",
    ]

    # Add top signals grouped by country
    by_country = defaultdict(list)
    for r in records:
        by_country[r.get("country", "?")].append(r)

    for country_code in region["countries"]:
        c_records = by_country.get(country_code, [])
        if not c_records:
            continue
        lines.append(f"\n--- {COUNTRY_FLAG.get(country_code, '')} {COUNTRY_NAME_KO.get(country_code, country_code)} ({len(c_records)}건) ---")
        # Sort by confidence, take top signals
        sorted_recs = sorted(c_records, key=lambda x: (0 if x.get("confidence") == "high" else 1))
        for r in sorted_recs[:15]:
            brand = r.get("brand", "?")
            product = r.get("product", "?")
            pillar = r.get("pillar", "?")
            value = r.get("value", "")
            quote = r.get("quote_original", "")[:200]
            source = r.get("source", "")
            source_url = r.get("source_url", "")
            conf = r.get("confidence", "medium")
            lines.append(f"  [{brand}/{product}/{pillar}] {value}")
            if quote:
                lines.append(f"    원문: {quote}")
            if source_url:
                lines.append(f"    출처: {source} ({source_url})")

    return "\n".join(lines)


def build_structured_data(records: List[dict], region: dict) -> dict:
    """Build structured JSON data for the dashboard."""
    total = len(records)
    countries = Counter(r.get("country", "?") for r in records)
    products = Counter(r.get("product", "?") for r in records)
    brands = Counter(r.get("brand", "?") for r in records)
    pillars = Counter(r.get("pillar", "?") for r in records)

    chinese_records = [r for r in records if r.get("brand", "").lower() in CHINESE_BRANDS]
    lg_records = [r for r in records if r.get("brand", "").lower() == "lg"]

    # Build per-country breakdown
    country_data = {}
    for c in region["countries"]:
        c_recs = [r for r in records if r.get("country") == c]
        c_chinese = [r for r in c_recs if r.get("brand", "").lower() in CHINESE_BRANDS]
        country_data[c] = {
            "total": len(c_recs),
            "products": dict(Counter(r.get("product", "?") for r in c_recs)),
            "brands": dict(Counter(r.get("brand", "?") for r in c_recs)),
            "chinese_count": len(c_chinese),
            "top_signals": [
                {
                    "brand": r.get("brand"),
                    "product": r.get("product"),
                    "pillar": r.get("pillar"),
                    "value": r.get("value"),
                    "source": r.get("source"),
                    "source_url": r.get("source_url"),
                    "confidence": r.get("confidence"),
                }
                for r in sorted(c_recs, key=lambda x: (0 if x.get("confidence") == "high" else 1))[:10]
            ],
        }

    return {
        "region": region["id"],
        "region_name_ko": region["name_ko"],
        "region_name_en": region["name_en"],
        "countries": region["countries"],
        "total_records": total,
        "country_breakdown": dict(countries),
        "product_breakdown": dict(products),
        "brand_breakdown": dict(brands),
        "pillar_breakdown": dict(pillars),
        "chinese_brand_total": len(chinese_records),
        "lg_total": len(lg_records),
        "country_data": country_data,
    }


# ──────────────────────────────────────────────────────────────
# Claude API Report Generation
# ──────────────────────────────────────────────────────────────

REGIONAL_REPORT_SYSTEM_PROMPT = """당신은 LG전자 D2C 글로벌 인텔리전스 애널리스트입니다.
주어진 지역 데이터를 기반으로 해당 지역의 주간 인텔리전스 리포트를 작성합니다.

리포트는 반드시 아래 구조를 따르세요:

# {지역명} D2C 주간 인텔리전스 리포트

## 1. 경영진 요약
### 핵심 인사이트
- 3~4개의 핵심 인사이트 (이 지역의 가장 중요한 변화와 위험요소)
### 실행 필요
1. 구체적인 액션 아이템 (Owner, Deadline 포함)
2. ...
3. ...

### 1.1 핵심 발견
| # | Category | Finding | Country-Product | Severity |
테이블 형식으로 주요 발견사항 정리 (최소 5개)

### 1.2 이번 주 주요 지표
| Metric | This Week | Trend |
지역 내 주요 메트릭 정리

### 1.3 권장 실행 과제
| Priority | Action | Target Country | Target Product | Owner | Deadline |
P1/P2/P3 우선순위별 실행 과제 (최소 4개)

## 2. 핵심 경보
### 핵심 인사이트
### 실행 필요
### 2.1 국가별 알림 맵
| Country | Alert | Severity | 근거 |
해당 지역 국가별 핵심 알림
### 2.2 소비자 부정 알림
| # | Country | Product | Issue | Severity |
### 2.3 경쟁사 공격 행보
| # | Country | Competitor | Action | LG Impact |
### 2.4 중국 브랜드 모멘텀
| Country | Brand | Signal | Threat |

## 3. 커버리지 대시보드
### 3.1 소비자 반응 모니터링
| Country | Consumer Pulse | Severity |
### 3.2 유통 채널 프로모션
| Country | Retail Channel Pulse | LG/Comp Signal |
### 3.3 경쟁 가격 및 포지셔닝
가격 비교 테이블 (TV, 냉장고, 세탁기, 모니터 등)
### 3.4 중국 브랜드 위협 추적
| Country | Brand | Product | Threat Level | Key Action |
브랜드별 분석 (TCL, Hisense, Haier, Midea)

## 4. 전략 요약
### TV 부문 대응 전략
### 가전 부문 대응 전략
### 모니터/gram 부문 전략

규칙:
- 모든 내용은 한국어로 작성
- 국가명 앞에 국기 이모지 사용 (예: 🇺🇸 US)
- Severity는 🔴 Critical, 🟡 Warning, 🟢 Normal 사용
- 실행 필요 항목에는 반드시 Owner와 Deadline을 명시
- source_url이 있는 데이터는 [🔗 Source](URL) 형태로 출처 링크 첨부
- 해당 지역에 속한 국가의 데이터만 분석 (다른 지역 국가 언급 불가)
- 구체적인 가격, 제품명, 리테일러명을 데이터에서 인용
- 인사이트는 추상적 분석이 아닌 실행 가능한 제안 중심으로 작성
"""


def generate_regional_report(
    client: anthropic.Anthropic,
    data_summary: str,
    region: dict,
    date_key: str,
    period_start: str,
    period_end: str,
    model: str,
) -> str:
    """Generate a regional report using Claude API."""

    user_prompt = f"""아래는 {region['name_ko']}({region['name_en']}) 지역의 주간 D2C 인텔리전스 수집 데이터입니다.

보고 기간: {period_start} — {period_end}
생성일: {date_key}
대상 국가: {', '.join(region['countries'])}

이 데이터를 기반으로 {region['name_ko']} 지역 전용 주간 인텔리전스 리포트를 작성해주세요.
글로벌 리포트와 동일한 깊이와 구체성으로, 이 지역에 해당하는 국가의 데이터만 분석합니다.

=== 수집 데이터 ===
{data_summary}
"""

    logger.info(f"Generating {region['name_ko']} report with {model}...")

    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=REGIONAL_REPORT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    model = os.environ.get("CLAUDE_MODEL_REPORT", DEFAULT_MODEL)

    # Date key
    if len(sys.argv) > 1:
        date_key = sys.argv[1]
    else:
        date_key = datetime.now().strftime("%Y-%m-%d")

    # Optional: generate only specific region
    target_region = sys.argv[2] if len(sys.argv) > 2 else None

    logger.info(f"Regional report generation for {date_key}")
    if target_region:
        logger.info(f"Target region: {target_region}")

    # Load data
    jsonl_path = DATA_DIR / "raw" / f"openclaw_{date_key}.jsonl"
    if not jsonl_path.exists():
        logger.error(f"JSONL file not found: {jsonl_path}")
        sys.exit(1)

    all_records = load_jsonl(jsonl_path)
    logger.info(f"Loaded {len(all_records)} records from {jsonl_path}")

    period_start, period_end = compute_report_period(date_key)

    # Create output directories
    md_dir = REPORTS_MD_DIR / date_key
    json_dir = REPORTS_JSON_DIR / date_key
    md_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic(api_key=api_key)

    regions_to_process = (
        {target_region: REGIONS[target_region]} if target_region and target_region in REGIONS
        else REGIONS
    )

    for region_id, region in regions_to_process.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {region['name_ko']} ({region_id})")
        logger.info(f"Countries: {region['countries']}")

        # Filter data by region
        regional_records = filter_by_region(all_records, region["countries"])
        logger.info(f"Filtered records: {len(regional_records)}")

        if len(regional_records) == 0:
            logger.warning(f"No data for region {region_id}, skipping")
            continue

        # Build structured JSON for dashboard
        structured = build_structured_data(regional_records, region)
        structured["date_key"] = date_key
        structured["period_start"] = period_start
        structured["period_end"] = period_end

        json_path = json_dir / f"{region_id}.json"
        json_path.write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Structured data saved: {json_path}")

        # Generate Claude report
        data_summary = summarize_regional_data(regional_records, region)
        report_md = generate_regional_report(
            client, data_summary, region, date_key, period_start, period_end, model
        )

        # Add metadata header
        header = f"""---
region: {region_id}
region_name: {region['name_ko']}
date: {date_key}
period: {period_start} — {period_end}
countries: {', '.join(region['countries'])}
total_records: {len(regional_records)}
generated_at: {datetime.now().isoformat()}
---

"""
        full_report = header + report_md

        md_path = md_dir / f"{region_id}.md"
        md_path.write_text(full_report, encoding="utf-8")
        logger.info(f"Report saved: {md_path} ({len(full_report)} chars)")

    # Create index file
    index = {
        "date_key": date_key,
        "period_start": period_start,
        "period_end": period_end,
        "regions": {},
    }
    for region_id in regions_to_process:
        json_path = json_dir / f"{region_id}.json"
        if json_path.exists():
            data = json.loads(json_path.read_text(encoding="utf-8"))
            index["regions"][region_id] = {
                "name_ko": data["region_name_ko"],
                "total_records": data["total_records"],
                "chinese_brand_total": data["chinese_brand_total"],
                "countries": data["countries"],
            }

    index_path = json_dir / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"\nIndex saved: {index_path}")
    logger.info("Regional report generation complete!")


if __name__ == "__main__":
    main()
