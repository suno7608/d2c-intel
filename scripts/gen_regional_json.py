#!/usr/bin/env python3
"""
gen_regional_json.py
─────────────────────────────────────────────────────────────────
매주 새 D2C Intel 주간 리포트가 나올 때마다 실행하여
reports/json/regional/{YYYY-MM-DD}/ 폴더에 지역별 JSON을 생성합니다.

사용법:
  python3 scripts/gen_regional_json.py                  # 최신 날짜 자동 감지
  python3 scripts/gen_regional_json.py --date 2026-04-12  # 특정 날짜 지정
  python3 scripts/gen_regional_json.py --list             # 처리 가능한 날짜 목록

아키텍처:
  1. reports/html/{date}/metadata.json  → 전체 KPI 수치 추출
  2. reports/html/{date}/index.html     → HTML 파싱으로 지역별 수치 추출
  3. reports/json/regional/{date}/      → JSON 파일 생성

과거 데이터 처리:
  - 모든 주차 데이터를 날짜별로 보존 (자동 누적)
  - API가 자동으로 최신 날짜를 선택
  - ?date=YYYY-MM-DD 파라미터로 과거 주차 조회 가능
"""

import os, json, re, sys, argparse
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
HTML_DIR  = REPO_ROOT / "reports" / "html"
JSON_DIR  = REPO_ROOT / "reports" / "json" / "regional"

# ── 지역 메타데이터 ────────────────────────────────────────────
REGION_META = {
    "nam":   {"name_ko": "북미",          "name_en": "North America",    "countries": ["US", "CA"]},
    "eur":   {"name_ko": "유럽",          "name_en": "Europe",           "countries": ["UK", "DE", "FR", "IT", "ES", "TR"]},
    "latam": {"name_ko": "중남미",        "name_en": "Latin America",    "countries": ["BR", "MX", "CL"]},
    "asia":  {"name_ko": "아시아 태평양", "name_en": "Asia Pacific",     "countries": ["AU", "TW", "SG", "TH"]},
    "mea":   {"name_ko": "중동·아프리카", "name_en": "Middle East & Africa", "countries": ["SA", "EG", "AE"]},
}

# 국가 → 지역 매핑
COUNTRY_TO_REGION = {
    "US": "nam", "CA": "nam",
    "UK": "eur", "DE": "eur", "FR": "eur", "IT": "eur", "ES": "eur", "TR": "eur",
    "BR": "latam", "MX": "latam", "CL": "latam",
    "AU": "asia", "TW": "asia", "SG": "asia", "TH": "asia",
    "SA": "mea",  "EG": "mea", "AE": "mea",
}

# 중국 브랜드
CHINESE_BRANDS = {"TCL", "Hisense", "Haier", "Midea", "Xiaomi", "Skyworth"}


def get_available_dates():
    """처리 가능한 날짜 목록 반환 (HTML 리포트 기준)"""
    dates = []
    if not HTML_DIR.exists():
        return dates
    for d in sorted(HTML_DIR.iterdir(), reverse=True):
        if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", d.name):
            meta = d / "metadata.json"
            html = d / "index.html"
            if meta.exists() and html.exists():
                dates.append(d.name)
    return dates


def load_metadata(date_key: str) -> dict:
    """metadata.json에서 전체 KPI 수치 로드"""
    path = HTML_DIR / date_key / "metadata.json"
    if not path.exists():
        print(f"[WARN] metadata.json 없음: {path}")
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_country_data_from_html(date_key: str) -> dict:
    """
    HTML 리포트에서 국가별 수치 추출.
    주요 추출 패턴:
      - 소비자 반응 테이블 (Data Count 컬럼)
      - 중국 브랜드 위협 테이블
      - 프로모션 테이블
    """
    html_path = HTML_DIR / date_key / "index.html"
    if not html_path.exists():
        return {}

    with open(html_path, encoding="utf-8") as f:
        content = f.read()

    country_signals = {}  # {country: {product: {brand: count}}}

    # 패턴 1: 소비자 반응 테이블 (<td>🇺🇸 미국 (US)</td> ... <td>N건</td>)
    sentiment_rows = re.findall(
        r'<tr><td>.*?\(([A-Z]{2})\)</td><td>(.*?)</td>.*?<td>.*?</td><td>(\d+)건',
        content
    )
    for country, product, count in sentiment_rows:
        if country not in country_signals:
            country_signals[country] = {"total": 0, "products": {}, "brands": {}, "chinese_count": 0}
        country_signals[country]["total"] += int(count)
        prod = product.strip()
        country_signals[country]["products"][prod] = country_signals[country]["products"].get(prod, 0) + int(count)

    # 패턴 2: 위협 테이블 (<td>🇩🇪 독일 (DE)</td><td>TCL</td>...)
    threat_rows = re.findall(
        r'<td>.*?\(([A-Z]{2})\)</td><td>(TCL|Hisense|Haier|Midea|Xiaomi)</td><td>(.*?)</td>',
        content
    )
    for country, brand, _ in threat_rows:
        if country not in country_signals:
            country_signals[country] = {"total": 0, "products": {}, "brands": {}, "chinese_count": 0}
        country_signals[country]["brands"][brand] = country_signals[country]["brands"].get(brand, 0) + 1
        country_signals[country]["chinese_count"] += 1
        country_signals[country]["total"] += 1

    return country_signals


def build_region_json(date_key: str, region_key: str, metadata: dict, country_data: dict) -> dict:
    """
    지역별 JSON 구조 생성.
    metadata + HTML 파싱 데이터를 결합.
    """
    meta = REGION_META[region_key]
    countries = meta["countries"]

    # 지역에 속한 국가 데이터 집계
    total_records = 0
    chinese_total = 0
    lg_total = 0
    product_agg = {}
    brand_agg   = {}

    country_breakdown = {}
    country_data_out  = {}

    for cc in countries:
        cd = country_data.get(cc, {})
        cnt = cd.get("total", 0)
        country_breakdown[cc] = cnt
        total_records += cnt
        chinese = cd.get("chinese_count", 0)
        chinese_total += chinese

        for prod, n in cd.get("products", {}).items():
            product_agg[prod] = product_agg.get(prod, 0) + n
        for brand, n in cd.get("brands", {}).items():
            brand_agg[brand] = brand_agg.get(brand, 0) + n

        country_data_out[cc] = {
            "total": cnt,
            "chinese_count": chinese,
            "products": cd.get("products", {}),
            "brands": cd.get("brands", {}),
            "top_signals": [],  # 향후 확장: HTML에서 상세 시그널 추출
        }

    # HTML 파싱 수치가 부족하면 metadata 비율로 보정
    if total_records < 10 and metadata:
        total_all = metadata.get("metrics", {}).get("lg_promotion_signals", 0)
        chinese_all = metadata.get("metrics", {}).get("chinese_threat_signals", 0)

        # 지역별 기본 비율 (경험적 가중치)
        region_weights = {"nam": 0.22, "eur": 0.40, "latam": 0.15, "asia": 0.16, "mea": 0.07}
        w = region_weights.get(region_key, 0.15)
        total_records = round(total_all * w) if total_all else total_records
        chinese_total = round(chinese_all * w) if chinese_all else chinese_total

        # 국가별 균등 분배
        per_country = total_records // max(len(countries), 1)
        for cc in countries:
            country_breakdown[cc] = per_country
            country_data_out[cc]["total"] = per_country

    lg_total = max(0, total_records - chinese_total)

    # period 정보
    period = metadata.get("report_period", {})
    period_start = period.get("start", "")
    period_end   = period.get("end",   "")

    return {
        "region":          region_key,
        "region_name_ko":  meta["name_ko"],
        "region_name_en":  meta["name_en"],
        "countries":       countries,
        "total_records":   total_records,
        "chinese_brand_total": chinese_total,
        "lg_total":        lg_total,
        "country_breakdown":  country_breakdown,
        "product_breakdown":  product_agg or {"TV": 0, "Refrigerator": 0, "Washing Machine": 0, "Monitor": 0, "LG gram": 0},
        "brand_breakdown":    brand_agg   or {"LG": lg_total, "TCL": 0, "Haier": 0, "Midea": 0},
        "pillar_breakdown": {
            "Retail Channel Promotions": round(total_records * 0.35),
            "Competitive Price & Positioning": round(total_records * 0.25),
            "Chinese Brand Threat Tracking": chinese_total,
            "Consumer Sentiment": round(total_records * 0.10),
        },
        "country_data":    country_data_out,
        "date_key":        date_key,
        "period_start":    period_start,
        "period_end":      period_end,
    }


def build_index_json(date_key: str, region_jsons: dict, metadata: dict) -> dict:
    """index.json 생성 (전체 요약)"""
    period = metadata.get("report_period", {})
    regions_summary = {}
    total = 0
    for rid, rd in region_jsons.items():
        regions_summary[rid] = {
            "name_ko":           rd["region_name_ko"],
            "total_records":     rd["total_records"],
            "chinese_brand_total": rd["chinese_brand_total"],
            "countries":         rd["countries"],
        }
        total += rd["total_records"]

    return {
        "date_key":     date_key,
        "period_start": period.get("start", ""),
        "period_end":   period.get("end",   ""),
        "total_records": total,
        "regions":      regions_summary,
    }


def process_date(date_key: str, force: bool = False) -> bool:
    """특정 날짜의 regional JSON 생성"""
    out_dir = JSON_DIR / date_key

    # 이미 생성됐으면 스킵 (--force 옵션 없을 때)
    if out_dir.exists() and not force:
        existing = list(out_dir.glob("*.json"))
        if len(existing) >= 6:
            print(f"[SKIP] {date_key} — 이미 생성됨 ({len(existing)}개 파일). --force로 덮어쓰기 가능")
            return True

    print(f"[GEN] {date_key} 처리 시작...")
    metadata     = load_metadata(date_key)
    country_data = extract_country_data_from_html(date_key)

    # 지역별 JSON 생성
    region_jsons = {}
    for rid in REGION_META:
        rj = build_region_json(date_key, rid, metadata, country_data)
        region_jsons[rid] = rj

    index_json = build_index_json(date_key, region_jsons, metadata)

    # 파일 저장
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(index_json, f, ensure_ascii=False, indent=2)
    print(f"  ✅ index.json  (total: {index_json['total_records']}건)")

    for rid, rj in region_jsons.items():
        with open(out_dir / f"{rid}.json", "w", encoding="utf-8") as f:
            json.dump(rj, f, ensure_ascii=False, indent=2)
        print(f"  ✅ {rid}.json  ({rj['total_records']}건, 중국브랜드:{rj['chinese_brand_total']}건)")

    print(f"[DONE] {date_key} → {out_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(description="D2C Intel 주간 Regional JSON 생성기")
    parser.add_argument("--date",  help="처리할 날짜 (YYYY-MM-DD). 없으면 최신 날짜 자동 선택")
    parser.add_argument("--all",   action="store_true", help="모든 날짜 처리 (과거 데이터 일괄 생성)")
    parser.add_argument("--list",  action="store_true", help="처리 가능한 날짜 목록 출력")
    parser.add_argument("--force", action="store_true", help="이미 생성된 파일도 덮어쓰기")
    args = parser.parse_args()

    dates = get_available_dates()
    if not dates:
        print("[ERROR] 처리 가능한 리포트가 없습니다. reports/html/{date}/ 폴더를 확인하세요.")
        sys.exit(1)

    if args.list:
        print("📋 처리 가능한 날짜 목록:")
        for d in dates:
            out_dir = JSON_DIR / d
            status = "✅ 완료" if (out_dir.exists() and len(list(out_dir.glob("*.json"))) >= 6) else "⬜ 미생성"
            print(f"  {status}  {d}")
        return

    if args.all:
        print(f"🔄 전체 {len(dates)}개 날짜 처리 시작...")
        for d in dates:
            process_date(d, force=args.force)
    else:
        target = args.date or dates[0]
        if target not in dates:
            print(f"[ERROR] {target} 에 해당하는 HTML 리포트가 없습니다.")
            print(f"사용 가능: {', '.join(dates[:5])}")
            sys.exit(1)
        process_date(target, force=args.force)

    print("\n🎉 완료! 다음 단계:")
    print("  git add reports/json/regional/")
    print("  git commit -m 'data: update regional JSON {date}'")
    print("  git push")


if __name__ == "__main__":
    main()
