#!/usr/bin/env python3
"""
D2C Intel — Monthly Data Aggregator
=====================================
전월의 모든 Weekly JSONL 데이터와 통계를 집계하여
Monthly Deep Dive 리포트 생성에 필요한 입력 데이터를 준비합니다.

Usage:
    python scripts/d2c_monthly_aggregator.py [YYYY-MM]

Output:
    data/monthly_stats/YYYY-MM.json        (월간 집계 통계)
    data/monthly_raw/openclaw_YYYY-MM_merged.jsonl (통합 JSONL)

Environment:
    (없음 — 로컬 파일만 처리)
"""

import json
import logging
import os
import re
import sys
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
STATS_DIR = DATA_DIR / "weekly_stats"
MONTHLY_STATS_DIR = DATA_DIR / "monthly_stats"
MONTHLY_RAW_DIR = DATA_DIR / "monthly_raw"
REPORTS_DIR = ROOT_DIR / "reports"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("d2c_monthly_aggregator")

COUNTRY_ORDER = [
    "US", "CA", "UK", "DE", "FR", "ES", "IT", "BR",
    "MX", "CL", "TH", "AU", "TW", "SG", "EG", "SA",
]
PRODUCT_ORDER = ["TV", "Refrigerator", "Washing Machine", "Monitor", "LG gram"]
CHINESE_BRANDS = {"tcl", "hisense", "haier", "midea"}


# ──────────────────────────────────────────────────────────────
# Date Utilities
# ──────────────────────────────────────────────────────────────

def get_month_date_range(year_month: str) -> Tuple[date, date]:
    """YYYY-MM → (월 첫날, 월 말일) 반환."""
    year, month = int(year_month[:4]), int(year_month[5:7])
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    return first_day, last_day


def find_weekly_files_for_month(year_month: str) -> Dict[str, List[Path]]:
    """해당 월에 속하는 주간 데이터 파일과 통계 파일을 찾습니다.

    주간 리포트는 일요일에 생성되므로, 해당 월에 속하는 일요일 날짜의 파일을 찾습니다.
    월 경계에 걸치는 주는 리포트 생성일(일요일) 기준으로 판단합니다.
    """
    first_day, last_day = get_month_date_range(year_month)

    # 해당 월의 모든 일요일 찾기 (약간의 여유를 두어 전후 1주 포함)
    search_start = first_day - timedelta(days=7)
    search_end = last_day + timedelta(days=7)

    jsonl_files = []
    stats_files = []

    # JSONL 파일 탐색
    for f in sorted(RAW_DIR.glob("openclaw_????-??-??.jsonl")):
        match = re.match(r"openclaw_(\d{4}-\d{2}-\d{2})\.jsonl", f.name)
        if not match:
            continue
        file_date = date.fromisoformat(match.group(1))
        # 해당 월 범위 내의 파일만 수집
        if first_day <= file_date <= last_day:
            jsonl_files.append(f)
        # 또는 해당 월 직전 일요일 (월 경계 포함)
        elif search_start <= file_date < first_day and file_date.weekday() == 6:
            jsonl_files.append(f)

    # 통계 파일 탐색
    for f in sorted(STATS_DIR.glob("????-??-??.json")):
        match = re.match(r"(\d{4}-\d{2}-\d{2})\.json", f.name)
        if not match:
            continue
        file_date = date.fromisoformat(match.group(1))
        if first_day <= file_date <= last_day:
            stats_files.append(f)
        elif search_start <= file_date < first_day and file_date.weekday() == 6:
            stats_files.append(f)

    return {"jsonl": jsonl_files, "stats": stats_files}


# ──────────────────────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> List[dict]:
    """JSONL 파일을 로드합니다."""
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
        except json.JSONDecodeError:
            continue
    return records


def load_weekly_stats(path: Path) -> Optional[dict]:
    """주간 통계 JSON을 로드합니다."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return None


# ──────────────────────────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────────────────────────

def merge_weekly_records(jsonl_files: List[Path]) -> Tuple[List[dict], Dict[str, List[dict]]]:
    """여러 주간 JSONL 파일을 병합하고 주차별로 분류합니다.

    Returns:
        (all_records, weekly_groups) — 전체 레코드와 주차별 그룹
    """
    all_records = []
    weekly_groups: Dict[str, List[dict]] = {}
    seen_urls = set()

    for f in sorted(jsonl_files):
        week_key = f.stem.replace("openclaw_", "")  # YYYY-MM-DD
        records = load_jsonl(f)

        # URL 기반 중복 제거 (주간 간 중복)
        unique_records = []
        for r in records:
            url = r.get("source_url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            unique_records.append(r)

        weekly_groups[week_key] = unique_records
        all_records.extend(unique_records)

        logger.info(f"  Loaded {week_key}: {len(records)} raw → {len(unique_records)} unique")

    return all_records, weekly_groups


def compute_weekly_breakdown(
    weekly_groups: Dict[str, List[dict]]
) -> Dict[str, Dict[str, Any]]:
    """주차별 상세 통계를 계산합니다."""
    breakdown = {}

    for week_idx, (week_key, records) in enumerate(sorted(weekly_groups.items()), 1):
        week_label = f"W{week_idx}"
        countries = Counter(r.get("country", "?") for r in records)
        products = Counter(r.get("product", "?") for r in records)
        pillars = Counter(r.get("pillar", "?") for r in records)
        brands = Counter(r.get("brand", "?") for r in records)

        chinese_records = [r for r in records if r.get("brand", "").lower() in CHINESE_BRANDS]
        negative_kw = {"complaint", "problem", "issue", "broken", "refund", "negative"}
        negative_records = [
            r for r in records
            if any(kw in (r.get("signal_type", "") + r.get("quote_original", "")).lower()
                   for kw in negative_kw)
        ]
        promo_records = [
            r for r in records
            if any(kw in (r.get("signal_type", "") + r.get("pillar", "")).lower()
                   for kw in {"promo", "promotion", "deal", "discount", "retail channel"})
        ]

        breakdown[week_key] = {
            "week_label": week_label,
            "date_key": week_key,
            "total_records": len(records),
            "countries": dict(countries),
            "countries_count": len(countries),
            "products": dict(products),
            "pillars": dict(pillars),
            "brands": dict(brands.most_common(10)),
            "chinese_brand_total": len(chinese_records),
            "chinese_by_country": dict(Counter(r.get("country", "?") for r in chinese_records)),
            "chinese_by_product": dict(Counter(r.get("product", "?") for r in chinese_records)),
            "consumer_negative_count": len(negative_records),
            "lg_promo_count": len(promo_records),
            "tv_ratio_pct": round(
                products.get("TV", 0) / len(records) * 100 if records else 0, 1
            ),
        }

    return breakdown


def compute_monthly_aggregate(
    all_records: List[dict],
    weekly_breakdown: Dict[str, Dict[str, Any]],
    year_month: str,
    prev_monthly_stats: Optional[dict] = None,
) -> dict:
    """전체 월간 집계 통계를 계산합니다."""
    total = len(all_records)
    countries = Counter(r.get("country", "?") for r in all_records)
    products = Counter(r.get("product", "?") for r in all_records)
    pillars = Counter(r.get("pillar", "?") for r in all_records)
    brands = Counter(r.get("brand", "?") for r in all_records)

    chinese_records = [r for r in all_records if r.get("brand", "").lower() in CHINESE_BRANDS]
    negative_kw = {"complaint", "problem", "issue", "broken", "refund", "negative"}
    negative_records = [
        r for r in all_records
        if any(kw in (r.get("signal_type", "") + r.get("quote_original", "")).lower()
               for kw in negative_kw)
    ]
    promo_records = [
        r for r in all_records
        if any(kw in (r.get("signal_type", "") + r.get("pillar", "")).lower()
               for kw in {"promo", "promotion", "deal", "discount", "retail channel"})
    ]

    # 주차별 추이 데이터 (시계열)
    week_labels = []
    week_totals = []
    week_chinese = []
    week_negative = []
    week_promo = []
    week_product_series = {p: [] for p in PRODUCT_ORDER}

    for week_key in sorted(weekly_breakdown.keys()):
        wb = weekly_breakdown[week_key]
        week_labels.append(wb["week_label"])
        week_totals.append(wb["total_records"])
        week_chinese.append(wb["chinese_brand_total"])
        week_negative.append(wb["consumer_negative_count"])
        week_promo.append(wb["lg_promo_count"])
        for p in PRODUCT_ORDER:
            week_product_series[p].append(wb["products"].get(p, 0))

    # MoM 비교 계산
    mom_comparison = {}
    if prev_monthly_stats:
        prev = prev_monthly_stats
        mom_comparison = {
            "total_records": {
                "this": total,
                "prev": prev.get("total_records", 0),
                "change_pct": _pct_change(total, prev.get("total_records", 0)),
            },
            "chinese_brand_total": {
                "this": len(chinese_records),
                "prev": prev.get("chinese_brand_total", 0),
                "change_pct": _pct_change(len(chinese_records), prev.get("chinese_brand_total", 0)),
            },
            "consumer_negative_count": {
                "this": len(negative_records),
                "prev": prev.get("consumer_negative_count", 0),
                "change_pct": _pct_change(len(negative_records), prev.get("consumer_negative_count", 0)),
            },
            "lg_promo_count": {
                "this": len(promo_records),
                "prev": prev.get("lg_promo_count", 0),
                "change_pct": _pct_change(len(promo_records), prev.get("lg_promo_count", 0)),
            },
        }

    # Chart.js 데이터 사전 생성
    chart_data = {
        "monthly_product_trend": {
            "type": "line",
            "title": "제품별 주간 시그널 추이",
            "labels": week_labels,
            "datasets": [
                {
                    "label": p,
                    "data": week_product_series[p],
                    "color": c,
                }
                for p, c in zip(
                    PRODUCT_ORDER,
                    ["#003a66", "#0a7ac4", "#2196F3", "#4CAF50", "#FF9800"],
                )
            ],
        },
        "monthly_china_brand_bar": {
            "type": "bar",
            "title": "중국 브랜드 월간 시그널",
            "labels": [b for b, _ in Counter(
                r.get("brand", "?") for r in chinese_records
            ).most_common(4)],
            "datasets": [{
                "label": "시그널 수",
                "data": [c for _, c in Counter(
                    r.get("brand", "?") for r in chinese_records
                ).most_common(4)],
                "color": "#e63946",
            }],
        },
        "monthly_sentiment_pie": {
            "type": "doughnut",
            "title": "인텔리전스 필라 분포",
            "labels": [p for p, _ in pillars.most_common()],
            "datasets": [{
                "label": "건수",
                "data": [c for _, c in pillars.most_common()],
                "color": "#003a66",
            }],
        },
    }

    return {
        "year_month": year_month,
        "generated_at": datetime.now().isoformat(),
        "weeks_count": len(weekly_breakdown),
        "week_keys": sorted(weekly_breakdown.keys()),
        "total_records": total,
        "countries": {c: countries.get(c, 0) for c in COUNTRY_ORDER},
        "countries_count": len(countries),
        "products": {p: products.get(p, 0) for p in PRODUCT_ORDER},
        "pillars": dict(pillars.most_common()),
        "brands": dict(brands.most_common(15)),
        "chinese_brand_total": len(chinese_records),
        "chinese_by_country": dict(Counter(r.get("country", "?") for r in chinese_records).most_common()),
        "chinese_by_product": dict(Counter(r.get("product", "?") for r in chinese_records)),
        "chinese_by_brand": dict(Counter(r.get("brand", "?") for r in chinese_records).most_common()),
        "consumer_negative_count": len(negative_records),
        "lg_promo_count": len(promo_records),
        "tv_ratio_pct": round(products.get("TV", 0) / total * 100 if total else 0, 1),
        "weekly_breakdown": weekly_breakdown,
        "weekly_trend": {
            "labels": week_labels,
            "totals": week_totals,
            "chinese": week_chinese,
            "negative": week_negative,
            "promo": week_promo,
            "products": week_product_series,
        },
        "mom_comparison": mom_comparison,
        "chart_data": chart_data,
    }


def _pct_change(current: float, previous: float) -> float:
    """퍼센트 변화율을 계산합니다."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / previous * 100, 1)


# ──────────────────────────────────────────────────────────────
# Previous Monthly Stats
# ──────────────────────────────────────────────────────────────

def load_previous_monthly_stats(year_month: str) -> Optional[dict]:
    """전월 Monthly 통계를 로드합니다."""
    year, month = int(year_month[:4]), int(year_month[5:7])
    if month == 1:
        prev_month = f"{year - 1}-12"
    else:
        prev_month = f"{year}-{month - 1:02d}"

    prev_path = MONTHLY_STATS_DIR / f"{prev_month}.json"
    if prev_path.exists():
        try:
            return json.loads(prev_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    # 대상 월 결정
    if len(sys.argv) > 1 and re.match(r"\d{4}-\d{2}", sys.argv[1]):
        year_month = sys.argv[1][:7]
    else:
        # 기본값: 전월
        today = date.today()
        if today.month == 1:
            year_month = f"{today.year - 1}-12"
        else:
            year_month = f"{today.year}-{today.month - 1:02d}"

    logger.info(f"D2C Monthly Aggregation — target month: {year_month}")

    # 디렉토리 준비
    MONTHLY_STATS_DIR.mkdir(parents=True, exist_ok=True)
    MONTHLY_RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 주간 파일 탐색
    files = find_weekly_files_for_month(year_month)
    jsonl_files = files["jsonl"]
    stats_files = files["stats"]

    if not jsonl_files:
        logger.error(f"No weekly JSONL files found for {year_month}")
        logger.error(f"Searched in: {RAW_DIR}")
        sys.exit(1)

    logger.info(f"Found {len(jsonl_files)} JSONL files, {len(stats_files)} stats files")

    # 데이터 병합
    all_records, weekly_groups = merge_weekly_records(jsonl_files)
    logger.info(f"Merged: {len(all_records)} total records from {len(weekly_groups)} weeks")

    if len(weekly_groups) < 2:
        logger.warning(f"Only {len(weekly_groups)} week(s) of data — monthly report may be sparse")

    # 주차별 통계
    weekly_breakdown = compute_weekly_breakdown(weekly_groups)

    # 전월 통계 로드
    prev_stats = load_previous_monthly_stats(year_month)
    if prev_stats:
        logger.info(f"Loaded previous month stats: {prev_stats.get('year_month')}")
    else:
        logger.info("No previous month stats found (first monthly report)")

    # 월간 집계
    monthly_stats = compute_monthly_aggregate(
        all_records, weekly_breakdown, year_month, prev_stats
    )

    # 통합 JSONL 저장
    merged_path = MONTHLY_RAW_DIR / f"openclaw_{year_month}_merged.jsonl"
    with open(merged_path, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info(f"Merged JSONL: {merged_path} ({len(all_records)} records)")

    # 월간 통계 저장
    stats_path = MONTHLY_STATS_DIR / f"{year_month}.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(monthly_stats, f, ensure_ascii=False, indent=2)
    logger.info(f"Monthly stats: {stats_path}")

    # 요약 출력
    logger.info("=== Monthly Aggregation Summary ===")
    logger.info(f"Month: {year_month}")
    logger.info(f"Weeks: {len(weekly_groups)}")
    logger.info(f"Total records: {len(all_records)}")
    logger.info(f"Countries: {monthly_stats['countries_count']}")
    logger.info(f"Products: {monthly_stats['products']}")
    logger.info(f"Chinese brand signals: {monthly_stats['chinese_brand_total']}")
    logger.info(f"TV ratio: {monthly_stats['tv_ratio_pct']}%")

    if monthly_stats["mom_comparison"]:
        logger.info("MoM comparison:")
        for k, v in monthly_stats["mom_comparison"].items():
            logger.info(f"  {k}: {v['prev']} → {v['this']} ({v['change_pct']:+.1f}%)")

    print(f"[d2c_monthly_aggregator] {year_month}: {len(all_records)} records, "
          f"{len(weekly_groups)} weeks → {stats_path}")


if __name__ == "__main__":
    main()
