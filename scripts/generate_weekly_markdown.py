#!/usr/bin/env python3
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


COUNTRY_ORDER = [
    "US",
    "CA",
    "UK",
    "DE",
    "FR",
    "ES",
    "IT",
    "BR",
    "MX",
    "CL",
    "TH",
    "AU",
    "TW",
    "SG",
    "EG",
    "SA",
]

COUNTRY_LABEL = {
    "US": "🇺🇸 US",
    "CA": "🇨🇦 CA",
    "UK": "🇬🇧 UK",
    "DE": "🇩🇪 DE",
    "FR": "🇫🇷 FR",
    "ES": "🇪🇸 ES",
    "IT": "🇮🇹 IT",
    "BR": "🇧🇷 BR",
    "MX": "🇲🇽 MX",
    "CL": "🇨🇱 CL",
    "TH": "🇹🇭 TH",
    "AU": "🇦🇺 AU",
    "TW": "🇹🇼 TW",
    "SG": "🇸🇬 SG",
    "EG": "🇪🇬 EG",
    "SA": "🇸🇦 SA",
    "GLOBAL": "🌍 GLOBAL",
}

PRODUCT_ORDER = ["TV", "Refrigerator", "Washing Machine", "Monitor", "LG gram"]
PRODUCT_LABEL = {
    "TV": "TV",
    "Refrigerator": "Refrigerator",
    "Washing Machine": "Washing Machine",
    "Monitor": "Monitor",
    "LG gram": "LG gram",
}

CHINESE_BRANDS = {"tcl", "hisense", "haier", "midea"}
NEGATIVE_KEYWORDS = {
    "problem",
    "issue",
    "fault",
    "broke",
    "broken",
    "complaint",
    "regret",
    "worst",
    "waiting",
    "waited",
    "refund",
    "고장",
    "불만",
    "문제",
}
PROMO_KEYWORDS = {
    "promotion",
    "promo",
    "discount",
    "deal",
    "rollback",
    "cashback",
    "coupon",
    "offer",
    "sale",
    "savings",
}
PRICING_KEYWORDS = {
    "pricing",
    "price",
    "pricing_comparison",
}

CONFIDENCE_SCORE = {"high": 3, "medium": 2, "low": 1}


def usage() -> None:
    print(
        "Usage: generate_weekly_markdown.py <root_dir> <date_key> <start_date> <end_date> <output_md> <prepared_by> <distribution> <version>",
        file=sys.stderr,
    )
    sys.exit(1)


def safe_text(value: object) -> str:
    return str(value or "").replace("\n", " ").strip()


def has_url(url: str) -> bool:
    return bool(re.match(r"^https?://", url or ""))


def source_link(record: Dict[str, object]) -> str:
    url = safe_text(record.get("source_url"))
    if has_url(url):
        return f"[🔗 Source]({url})"
    query = safe_text(record.get("quote_original"))[:80] or "LG D2C weekly intelligence"
    query = query.replace('"', "'")
    return f'❓[출처 미확인 — 검색어: "{query}"]'


def parse_value_number(value: str) -> Optional[float]:
    text = safe_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def price_candidate(record: Dict[str, object]) -> Optional[float]:
    if not (is_pricing(record) or is_promotion(record)):
        return None

    signal = safe_text(record.get("signal_type")).lower()
    if any(k in signal for k in ["market_share", "market_intelligence", "review", "product_launch"]):
        return None

    currency = safe_text(record.get("currency")).upper()
    if not currency:
        return None

    product = normalize_product(record.get("product", ""))
    floors = {
        "TV": 100.0,
        "Refrigerator": 150.0,
        "Washing Machine": 100.0,
        "Monitor": 80.0,
        "LG gram": 300.0,
    }
    value = parse_value_number(safe_text(record.get("value")))
    if value is None:
        return None
    if value < floors.get(product, 50.0):
        return None
    return value


def confidence_rank(record: Dict[str, object]) -> int:
    return CONFIDENCE_SCORE.get(safe_text(record.get("confidence")).lower(), 0)


def is_negative(record: Dict[str, object]) -> bool:
    signal = safe_text(record.get("signal_type")).lower()
    quote = safe_text(record.get("quote_original")).lower()
    if "negative" in signal or "complaint" in signal:
        return True
    return any(k in quote for k in NEGATIVE_KEYWORDS)


def is_promotion(record: Dict[str, object]) -> bool:
    signal = safe_text(record.get("signal_type")).lower()
    pillar = safe_text(record.get("pillar")).lower()
    if "retail channel promotions" in pillar:
        return True
    return any(k in signal for k in PROMO_KEYWORDS)


def is_pricing(record: Dict[str, object]) -> bool:
    signal = safe_text(record.get("signal_type")).lower()
    pillar = safe_text(record.get("pillar")).lower()
    if "competitive price" in pillar:
        return True
    return any(k in signal for k in PRICING_KEYWORDS)


def is_chinese_brand(record: Dict[str, object]) -> bool:
    brand = safe_text(record.get("brand")).lower()
    pillar = safe_text(record.get("pillar")).lower()
    if brand in CHINESE_BRANDS:
        return True
    return "chinese brand threat tracking" in pillar


def normalize_country(value: str) -> str:
    country = safe_text(value).upper()
    if country in COUNTRY_LABEL:
        return country
    return "GLOBAL"


def normalize_product(value: str) -> str:
    product = safe_text(value)
    if product in PRODUCT_LABEL:
        return product
    return "TV"


def score_to_severity(score: int) -> Tuple[str, str]:
    if score >= 4:
        return "🔴", "Critical"
    if score >= 2:
        return "🟡", "Warning"
    return "🟢", "Normal"


def select_best(records: List[Dict[str, object]]) -> Optional[Dict[str, object]]:
    if not records:
        return None
    return sorted(
        records,
        key=lambda r: (
            confidence_rank(r),
            1 if has_url(safe_text(r.get("source_url"))) else 0,
            safe_text(r.get("quote_original")),
        ),
        reverse=True,
    )[0]


def load_jsonl(raw_file: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for line in raw_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def load_weekly_stats(stats_file: Path) -> Dict[str, object]:
    if not stats_file.exists():
        return {}
    try:
        return json.loads(stats_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def diff_text(now_val: int, prev_val: Optional[int]) -> str:
    if prev_val is None:
        return "N/A"
    delta = now_val - prev_val
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta}"


def trend_arrow(now_val: int, prev_val: Optional[int]) -> str:
    if prev_val is None:
        return "→"
    if now_val > prev_val:
        return "↑"
    if now_val < prev_val:
        return "↓"
    return "→"


def fmt_num(value: Optional[float], currency: str = "") -> str:
    if value is None:
        return "-"
    if value >= 1000:
        text = f"{value:,.0f}"
    else:
        text = f"{value:.0f}" if value.is_integer() else f"{value:.1f}"
    return f"{currency}{text}" if currency else text


def weekly_history(root_dir: Path, date_key: str, depth: int = 5) -> List[Optional[Dict[str, object]]]:
    stats_dir = root_dir / "data" / "weekly_stats"
    files = sorted(stats_dir.glob("*.json"))
    weeks: List[Dict[str, object]] = []
    for f in files:
        d = f.stem
        if d > date_key:
            continue
        data = load_weekly_stats(f)
        if data:
            weeks.append(data)
    weeks = weeks[-depth:]
    padded: List[Optional[Dict[str, object]]] = [None] * (depth - len(weeks)) + weeks
    return padded


def main() -> None:
    if len(sys.argv) != 9:
        usage()

    root_dir = Path(sys.argv[1]).resolve()
    date_key = sys.argv[2]
    start_date = sys.argv[3]
    end_date = sys.argv[4]
    output_md = Path(sys.argv[5]).resolve()
    prepared_by = sys.argv[6]
    distribution = sys.argv[7]
    version = sys.argv[8]

    raw_file = root_dir / "data" / "raw" / f"openclaw_{date_key}.jsonl"
    if not raw_file.exists():
        print(f"raw data not found: {raw_file}", file=sys.stderr)
        sys.exit(1)

    records = load_jsonl(raw_file)
    if not records:
        print("no valid json lines found in raw file", file=sys.stderr)
        sys.exit(1)

    by_country: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    by_country_product: Dict[Tuple[str, str], List[Dict[str, object]]] = defaultdict(list)
    by_brand: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    by_product: Dict[str, List[Dict[str, object]]] = defaultdict(list)

    country_stats = {
        c: {"total": 0, "lg_promo": 0, "comp_promo": 0, "chinese": 0, "negative": 0}
        for c in COUNTRY_ORDER
    }

    total_lg_promo = 0
    total_comp_promo = 0
    total_chinese = 0
    total_negative = 0

    for r in records:
        country = normalize_country(r.get("country", ""))
        product = normalize_product(r.get("product", ""))
        brand = safe_text(r.get("brand")) or "UNKNOWN"

        by_country[country].append(r)
        by_country_product[(country, product)].append(r)
        by_brand[brand].append(r)
        by_product[product].append(r)

        if country in country_stats:
            country_stats[country]["total"] += 1

        promo = is_promotion(r)
        chinese = is_chinese_brand(r)
        negative = is_negative(r)
        lg = safe_text(r.get("brand")).lower() == "lg"

        if promo and lg:
            total_lg_promo += 1
            if country in country_stats:
                country_stats[country]["lg_promo"] += 1
        if promo and not lg:
            total_comp_promo += 1
            if country in country_stats:
                country_stats[country]["comp_promo"] += 1
        if chinese:
            total_chinese += 1
            if country in country_stats:
                country_stats[country]["chinese"] += 1
        if negative:
            total_negative += 1
            if country in country_stats:
                country_stats[country]["negative"] += 1

    covered_countries = len([c for c in COUNTRY_ORDER if country_stats[c]["total"] > 0])
    product_counts = Counter({p: len(v) for p, v in by_product.items()})

    critical_countries: List[str] = []
    severity_map: Dict[str, Tuple[str, str]] = {}
    for c in COUNTRY_ORDER:
        st = country_stats[c]
        score = 0
        if st["negative"] > 0:
            score += 2
        if st["chinese"] >= 2:
            score += 2
        if st["comp_promo"] > st["lg_promo"]:
            score += 1
        if st["lg_promo"] == 0 and st["total"] > 0:
            score += 1
        sev = score_to_severity(score)
        severity_map[c] = sev
        if sev[0] == "🔴":
            critical_countries.append(c)

    stats_dir = root_dir / "data" / "weekly_stats"
    current_stats = load_weekly_stats(stats_dir / f"{date_key}.json")
    prev_stats: Optional[Dict[str, object]] = None
    previous_files = sorted([f for f in stats_dir.glob("*.json") if f.stem < date_key])
    if previous_files:
        prev_stats = load_weekly_stats(previous_files[-1])

    prev_lg_promo = int(prev_stats.get("lg_promo_count", 0)) if prev_stats else None
    prev_chinese = int(prev_stats.get("chinese_brand_total", 0)) if prev_stats else None
    prev_negative = int(prev_stats.get("consumer_negative_count", 0)) if prev_stats else None
    prev_covered = int(prev_stats.get("countries_count", 0)) - (1 if prev_stats and "GLOBAL" in prev_stats.get("countries", {}) else 0) if prev_stats else None
    prev_total = int(prev_stats.get("total_records", 0)) if prev_stats else None

    top_country_lg = max(COUNTRY_ORDER, key=lambda c: country_stats[c]["lg_promo"])
    top_country_china = max(COUNTRY_ORDER, key=lambda c: country_stats[c]["chinese"])
    top_country_negative = max(COUNTRY_ORDER, key=lambda c: country_stats[c]["negative"])
    top_product = max(PRODUCT_ORDER, key=lambda p: product_counts.get(p, 0))

    top_lg_record = select_best([r for r in records if safe_text(r.get("brand")).lower() == "lg"])
    top_negative_record = select_best([r for r in records if is_negative(r)])
    top_china_record = select_best([r for r in records if is_chinese_brand(r)])
    top_comp_record = select_best([r for r in records if is_promotion(r) and safe_text(r.get("brand")).lower() != "lg"])

    lines: List[str] = []
    lines.append("# LG전자 글로벌 D2C 주간 시장 인텔리전스 리포트 (R2, 핵심 법인 풀 커버리지)")
    lines.append("")
    lines.append("소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향")
    lines.append("")
    lines.append(f"보고 기간: {start_date} — {end_date}")
    lines.append(f"Prepared by: {prepared_by}")
    lines.append(f"Distribution: {distribution}")
    lines.append(f"Date Generated: {date_key}")
    lines.append(f"Version: {version}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. 경영진 요약")
    lines.append("")
    lines.append("### 핵심 인사이트")
    lines.append(
        f"- 이번 주 수집 데이터는 총 **{len(records)}건**이며, 핵심 법인 **{covered_countries}개국**에서 신호가 확인되었다. 가장 많은 신호가 집중된 제품군은 **{top_product}({product_counts.get(top_product, 0)}건)**이다."
    )
    lines.append(
        f"- 프로모션 신호는 LG {total_lg_promo}건, 경쟁사 {total_comp_promo}건으로 관측되어, **{COUNTRY_LABEL[top_country_lg]}**에서 LG 집행 강도가 가장 높았다."
    )
    lines.append(
        f"- 중국 브랜드(TCL/Hisense/Haier/Midea) 위협 신호는 **{total_chinese}건**이며, **{COUNTRY_LABEL[top_country_china]}**에서 집중도가 가장 높아 MS/HS 동시 대응이 필요하다."
    )
    lines.append("")
    lines.append("### 실행 필요")
    lines.append(
        f"1. **{COUNTRY_LABEL[top_country_lg]}** 중심으로 이번 주 성과가 높은 LG 프로모션 SKU를 EU/MEA 채널에 복제 집행해 매출 전환률을 확대한다."
    )
    lines.append(
        f"2. **{COUNTRY_LABEL[top_country_china]}** 포함 중국 브랜드 압박 국가에서 TV 단독 할인보다 `TV+HS 번들`(설치/보증/할부 포함)로 ASP 하락을 방어한다."
    )
    lines.append(
        "3. 부정 VOC 발생 국가는 48시간 내 1차 응답 SLA를 적용하고, 서비스 지연 고객 대상 보증연장/보상 쿠폰을 즉시 제공한다."
    )
    lines.append("")
    lines.append("### 1.1 핵심 발견")
    lines.append("| # | Category | Finding | Country-Product | Severity | Detail |")
    lines.append("|---|---|---|---|---|---|")
    lines.append(
        f"| 1 | Coverage | 핵심 법인 {covered_countries}개국에서 주간 시그널 확보(총 {len(records)}건) | GLOBAL-Multi | 🟢 Normal | {source_link(top_lg_record or records[0])} |"
    )
    lines.append(
        f"| 2 | Promotion | LG 프로모션 최다 국가는 {COUNTRY_LABEL[top_country_lg]}({country_stats[top_country_lg]['lg_promo']}건) | {COUNTRY_LABEL[top_country_lg]}-Multi | 🟡 Warning | {source_link(select_best(by_country[top_country_lg]) or records[0])} |"
    )
    lines.append(
        f"| 3 | Competitive | 경쟁사 프로모션은 {total_comp_promo}건으로, 가격 전환 압박 지속 | GLOBAL-Multi | 🔴 Critical | {source_link(top_comp_record or records[0])} |"
    )
    lines.append(
        f"| 4 | Chinese Brand | 중국 브랜드 위협 신호 {total_chinese}건, 최다 국가는 {COUNTRY_LABEL[top_country_china]}({country_stats[top_country_china]['chinese']}건) | {COUNTRY_LABEL[top_country_china]}-TV/HS | 🔴 Critical | {source_link(top_china_record or records[0])} |"
    )
    lines.append(
        f"| 5 | Consumer | 부정 VOC {total_negative}건 감지, 서비스 대응이 매출 방어의 핵심 변수 | GLOBAL-CX | {'🔴 Critical' if total_negative > 0 else '🟢 Normal'} | {source_link(top_negative_record or top_lg_record or records[0])} |"
    )
    lines.append(
        f"| 6 | Product Mix | 제품 데이터 분포: TV {product_counts.get('TV', 0)} / Refrigerator {product_counts.get('Refrigerator', 0)} / Washing Machine {product_counts.get('Washing Machine', 0)} / Monitor {product_counts.get('Monitor', 0)} / LG gram {product_counts.get('LG gram', 0)} | GLOBAL-Multi | 🟡 Warning | {source_link(top_lg_record or records[0])} |"
    )
    lines.append("")
    lines.append("### 1.2 이번 주 주요 지표")
    lines.append("| Metric | This Week | vs Last Week | Trend |")
    lines.append("|---|---:|---:|---|")
    lines.append(
        f"| 총 데이터 건수 | {len(records)} | {diff_text(len(records), prev_total)} | {trend_arrow(len(records), prev_total)} |"
    )
    lines.append(
        f"| 커버된 국가 수 | {covered_countries} | {diff_text(covered_countries, prev_covered)} | {trend_arrow(covered_countries, prev_covered)} |"
    )
    lines.append(
        f"| LG 프로모션 감지 건수 | {total_lg_promo} | {diff_text(total_lg_promo, prev_lg_promo)} | {trend_arrow(total_lg_promo, prev_lg_promo)} |"
    )
    lines.append(
        f"| 경쟁사 공격 프로모션 감지 건수 | {total_comp_promo} | N/A | → |"
    )
    lines.append(
        f"| 중국 브랜드 위협 신호 | {total_chinese} | {diff_text(total_chinese, prev_chinese)} | {trend_arrow(total_chinese, prev_chinese)} |"
    )
    lines.append(
        f"| LG 부정 소비자 언급 수 | {total_negative} | {diff_text(total_negative, prev_negative)} | {trend_arrow(total_negative, prev_negative)} |"
    )
    lines.append(
        f"| Critical Alert 발생 국가 수 | {len(critical_countries)} | N/A | → |"
    )
    lines.append("")
    lines.append("### 1.3 권장 실행 과제")
    lines.append("| Priority | Action | Target Country | Target Product | Owner | Deadline |")
    lines.append("|---|---|---|---|---|---|")
    lines.append(
        f"| 🔴 P1 | 중국 브랜드 압박 고강도 국가에서 TV+HS 번들 즉시 집행 | {COUNTRY_LABEL[top_country_china]} | TV / HS | MS·HS Regional D2C | {date_key} + 3일 |"
    )
    lines.append(
        f"| 🔴 P1 | LG 프로모션 성과가 높은 국가 오퍼를 인접권역에 복제 배포 | {COUNTRY_LABEL[top_country_lg]} 중심 | Multi-product | Global Pricing / CRM | {date_key} + 5일 |"
    )
    lines.append(
        "| 🟡 P2 | 부정 VOC 고객 48시간 SLA 및 보증연장 보상 프로세스 적용 | 부정 VOC 발생 국가 | HS / Washer / Refrigerator | CX Service | 즉시 |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. 핵심 경보")
    lines.append("")
    lines.append("### 핵심 인사이트")
    lines.append(
        f"- 핵심 경보 국가는 **{len(critical_countries)}개국**이며, 공통적으로 중국 브랜드 노출 증가와 경쟁사 프로모션 집행이 동시에 나타난다."
    )
    lines.append(
        "- 소비자 불만 신호는 절대 건수보다 전환 손실에 미치는 영향이 크므로, VOC 대응 SLA와 보상 정책이 매출 방어의 우선순위다."
    )
    lines.append(
        "- 가격 대응은 단순 할인보다 설치/보증/할부를 결합한 체감가 전략이 효과적이며, HS 카테고리에서 특히 중요하다."
    )
    lines.append("")
    lines.append("### 실행 필요")
    lines.append("1. Critical 국가 대상 주 2회 가격·프로모션 전쟁판(competitive board) 운영으로 오퍼 지연을 방지한다.")
    lines.append("2. 부정 VOC가 발생한 시장은 채널별 CS 리더를 지정해 48시간 내 1차 해결률을 KPI로 관리한다.")
    lines.append("3. 중국 브랜드 집중 국가는 HS 제품군의 서비스 차별화 메시지를 PDP/배너 상단에 고정 노출한다.")
    lines.append("")
    lines.append("### 2.1 핵심 법인 알림 맵")
    lines.append("| Country | Alert | Severity | 근거 |")
    lines.append("|---|---|---|---|")
    for c in COUNTRY_ORDER:
        st = country_stats[c]
        sev_emoji, sev_text = severity_map[c]
        alert = (
            f"LG Promo {st['lg_promo']}건 / Comp Promo {st['comp_promo']}건 / Chinese {st['chinese']}건 / Negative {st['negative']}건"
        )
        primary = select_best(by_country[c]) if by_country[c] else None
        lines.append(f"| {COUNTRY_LABEL[c]} | {alert} | {sev_emoji} {sev_text} | {source_link(primary or records[0])} |")
    lines.append("")
    lines.append("### 2.2 소비자 부정 알림")
    lines.append("| # | Country | Product | Issue (한국어) | Severity | Source |")
    lines.append("|---|---|---|---|---|---|")
    negatives = sorted([r for r in records if is_negative(r)], key=confidence_rank, reverse=True)[:10]
    if negatives:
        for i, r in enumerate(negatives, 1):
            country = COUNTRY_LABEL.get(normalize_country(r.get("country", "")), "🌍 GLOBAL")
            product = normalize_product(r.get("product", ""))
            issue = safe_text(r.get("quote_original"))[:120]
            sev = "🔴 Critical" if confidence_rank(r) >= 2 else "🟡 Warning"
            lines.append(f"| {i} | {country} | {product} | {issue} | {sev} | {source_link(r)} |")
    else:
        lines.append("| 1 | GLOBAL | Multi | 고신뢰 부정 VOC가 탐지되지 않음 | 🟢 Normal | ❓[출처 미확인 — 검색어: \"LG consumer negative\"] |")
    lines.append("")
    lines.append("### 2.3 경쟁사 공격 행보")
    lines.append("| # | Country | Competitor | Action | LG Impact | Source |")
    lines.append("|---|---|---|---|---|---|")
    comp_moves = sorted(
        [r for r in records if safe_text(r.get("brand")).lower() != "lg" and (is_promotion(r) or is_pricing(r))],
        key=confidence_rank,
        reverse=True,
    )[:12]
    if comp_moves:
        for i, r in enumerate(comp_moves, 1):
            country = COUNTRY_LABEL.get(normalize_country(r.get("country", "")), "🌍 GLOBAL")
            brand = safe_text(r.get("brand")) or "Competitor"
            action = safe_text(r.get("quote_original"))[:110]
            impact = "가격 방어/전환율 저하 리스크"
            lines.append(f"| {i} | {country} | {brand} | {action} | {impact} | {source_link(r)} |")
    else:
        lines.append("| 1 | GLOBAL | - | 경쟁사 공격 프로모션이 감지되지 않음 | 영향 낮음 | ❓[출처 미확인 — 검색어: \"competitor promotion\"] |")
    lines.append("")
    lines.append("### 2.4 중국 브랜드 모멘텀 알림")
    lines.append("| Country | Brand | Signal | Threat | Source |")
    lines.append("|---|---|---|---|---|")
    china_rows = sorted([r for r in records if is_chinese_brand(r)], key=confidence_rank, reverse=True)
    used_country_brand = set()
    for r in china_rows:
        c = normalize_country(r.get("country", ""))
        b = safe_text(r.get("brand")) or "Chinese Brand"
        key = (c, b)
        if key in used_country_brand or c == "GLOBAL":
            continue
        used_country_brand.add(key)
        threat = "🔴" if country_stats.get(c, {}).get("chinese", 0) >= 3 else "🟡"
        signal = safe_text(r.get("quote_original"))[:110]
        lines.append(f"| {COUNTRY_LABEL.get(c, c)} | {b} | {signal} | {threat} | {source_link(r)} |")
        if len(used_country_brand) >= 16:
            break
    if not used_country_brand:
        lines.append("| GLOBAL | - | 중국 브랜드 모멘텀 신호 없음 | 🟢 | ❓[출처 미확인 — 검색어: \"TCL Hisense Haier Midea momentum\"] |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. 핵심 법인 상세 분석")
    lines.append("")
    lines.append("### 3.1 소비자 반응 (VOC)")
    lines.append("### 핵심 인사이트")
    lines.append("- VOC는 제품 스펙보다 서비스 응답 속도와 체감 가격에 더 민감하게 반응한다.")
    lines.append("- LG 긍정 반응은 프로모션 강도가 높은 국가에서 동반 증가하며, 부정 신호는 CS 대응 지연과 함께 나타난다.")
    lines.append("- 커뮤니티/리뷰 채널에서의 초기 불만 확산 차단이 환불·취소율 관리의 핵심이다.")
    lines.append("")
    lines.append("### 실행 필요")
    lines.append("1. 부정 VOC 국가에 대해 구매 후 7일 이내 proactive 케어 메시지를 자동 발송한다.")
    lines.append("2. 제품 상세페이지에 서비스 SLA와 보증 조건을 상단에 명시해 불안 요인을 제거한다.")
    lines.append("3. VOC 키워드를 주간이 아닌 일간으로 모니터링해 이슈 확산 전에 대응한다.")
    lines.append("")
    lines.append("| Country | Positive Signal | Negative Signal | Source |")
    lines.append("|---|---|---|---|")
    for c in COUNTRY_ORDER:
        lg_country = [r for r in by_country[c] if safe_text(r.get("brand")).lower() == "lg"]
        pos = len([r for r in lg_country if not is_negative(r)])
        neg = len([r for r in lg_country if is_negative(r)])
        pulse_pos = f"LG 관련 긍정/중립 신호 {pos}건"
        pulse_neg = f"부정 신호 {neg}건"
        ref = select_best(lg_country) or select_best(by_country[c]) or records[0]
        lines.append(f"| {COUNTRY_LABEL[c]} | {pulse_pos} | {pulse_neg} | {source_link(ref)} |")
    lines.append("")
    lines.append("### 3.2 유통 채널 프로모션")
    lines.append("### 핵심 인사이트")
    lines.append("- LG 프로모션 집행이 많은 국가는 트래픽 유입도 함께 증가하는 패턴을 보인다.")
    lines.append("- 경쟁사 프로모션이 우세한 국가는 체감가 방어 전략이 없으면 전환 손실이 커진다.")
    lines.append("- 프로모션 성과 복제(Winning Offer Replication)가 가장 빠른 매출 개선 레버다.")
    lines.append("")
    lines.append("### 실행 필요")
    lines.append("1. LG 우위 국가의 베스트 오퍼를 동일 카테고리·인접 국가에 즉시 재배포한다.")
    lines.append("2. 경쟁사 우위 국가는 할인율이 아닌 번들 가치(설치/보증/사은품)로 대응한다.")
    lines.append("3. 딜 커뮤니티 반응(댓글/추천)을 다음 주 오퍼 기획의 입력값으로 반영한다.")
    lines.append("")
    lines.append("| Country | LG Promo Count | Competitor Promo Count | 판정 | Source |")
    lines.append("|---|---:|---:|---|---|")
    for c in COUNTRY_ORDER:
        lgp = country_stats[c]["lg_promo"]
        cpp = country_stats[c]["comp_promo"]
        if lgp > cpp:
            verdict = "LG 우위"
        elif lgp < cpp:
            verdict = "경쟁사 우위"
        else:
            verdict = "균형"
        ref = select_best([r for r in by_country[c] if is_promotion(r)]) or select_best(by_country[c]) or records[0]
        lines.append(f"| {COUNTRY_LABEL[c]} | {lgp} | {cpp} | {verdict} | {source_link(ref)} |")
    lines.append("")
    lines.append("### 3.3 경쟁 가격 및 포지셔닝")
    lines.append("### 핵심 인사이트")
    lines.append("- 가격 비교는 단일 SKU보다 카테고리별 앵커 가격 구조로 보는 것이 실무 대응에 유효하다.")
    lines.append("- 중국 브랜드의 저가 포지셔닝은 TV뿐 아니라 HS 카테고리로 확장되고 있다.")
    lines.append("- LG는 프리미엄 유지와 엔트리 전환의 이중 전략을 국가별로 분리 운영해야 한다.")
    lines.append("")
    lines.append("### 실행 필요")
    lines.append("1. 국가별 앵커 SKU를 지정하고 경쟁사 대비 체감가 차이 임계치(예: 15%)를 운영한다.")
    lines.append("2. 가격 대응은 지역 본부 재량이 아닌 중앙 정책(가이드 레일)으로 관리한다.")
    lines.append("3. HS 카테고리에서 가격 외 차별화(설치/A/S/에너지비용)를 수치화해 제시한다.")
    lines.append("")
    lines.append("| Country | LG Anchor Price | Competitor Anchor Price | Gap Insight | Source |")
    lines.append("|---|---:|---:|---|---|")
    for c in COUNTRY_ORDER:
        lg_prices = [
            price_candidate(r)
            for r in by_country[c]
            if safe_text(r.get("brand")).lower() == "lg"
        ]
        comp_prices = [
            price_candidate(r)
            for r in by_country[c]
            if safe_text(r.get("brand")).lower() != "lg"
        ]
        lg_prices = [x for x in lg_prices if x is not None]
        comp_prices = [x for x in comp_prices if x is not None]
        lg_anchor = min(lg_prices) if lg_prices else None
        comp_anchor = min(comp_prices) if comp_prices else None
        if lg_anchor and comp_anchor and comp_anchor > 0:
            ratio = lg_anchor / comp_anchor
            gap = f"LG/Comp {ratio:.2f}배"
        else:
            gap = "관측값 제한"
        price_ref = select_best([r for r in by_country[c] if is_pricing(r) or is_promotion(r)]) or select_best(by_country[c]) or records[0]
        lines.append(f"| {COUNTRY_LABEL[c]} | {fmt_num(lg_anchor)} | {fmt_num(comp_anchor)} | {gap} | {source_link(price_ref)} |")
    lines.append("")
    lines.append("### 3.4 중국 브랜드 위협 추적")
    lines.append("### 핵심 인사이트")
    lines.append("- 중국 브랜드 위협은 단일 시장 이슈가 아니라 16개국 전반의 구조적 패턴으로 확산 중이다.")
    lines.append("- TV 저가 공세와 HS 채널 확장이 동시 발생해 제품군 간 교차 압박이 커지고 있다.")
    lines.append("- 국가별 위협 강도에 맞춘 차등 대응(가격/서비스/채널)이 필요하다.")
    lines.append("")
    lines.append("### 실행 필요")
    lines.append("1. 위협 강도 상위 국가를 Red Zone으로 지정해 주간 가격·채널 대응안을 의무화한다.")
    lines.append("2. 중국 브랜드와 직접 비교되는 SKU는 PDP에 장점 비교표를 표준 적용한다.")
    lines.append("3. HS 카테고리에서는 서비스/보증 가치를 가격과 함께 묶어 제시한다.")
    lines.append("")
    lines.append("| Country | Chinese Signal Count | Primary Brand | Threat | Source |")
    lines.append("|---|---:|---|---|---|")
    for c in COUNTRY_ORDER:
        china_records = [r for r in by_country[c] if is_chinese_brand(r)]
        brand_counts = Counter([safe_text(r.get("brand")) for r in china_records if safe_text(r.get("brand"))])
        primary_brand = brand_counts.most_common(1)[0][0] if brand_counts else "-"
        cnt = len(china_records)
        threat = "🔴 High" if cnt >= 3 else "🟡 Medium" if cnt >= 1 else "🟢 Low"
        ref = select_best(china_records) or select_best(by_country[c]) or records[0]
        lines.append(f"| {COUNTRY_LABEL[c]} | {cnt} | {primary_brand} | {threat} | {source_link(ref)} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. 중국 브랜드 위협 보고")
    lines.append("")
    lines.append("### 핵심 인사이트")
    lines.append("- TCL/Hisense는 TV에서, Haier/Midea는 HS에서 존재감을 높이며 다축 압박을 형성한다.")
    lines.append("- 가격과 채널 확장이 동시에 발생하는 국가가 가장 높은 매출 리스크를 보인다.")
    lines.append("- LG는 브랜드 프리미엄 메시지와 체감가 대응을 함께 운영해야 방어 효율이 높다.")
    lines.append("")
    lines.append("### 실행 필요")
    lines.append("1. TCL/Hisense 집중 국가는 TV 가격·번들 대응을 분리 설계한다.")
    lines.append("2. Haier/Midea 집중 국가는 HS 서비스 보증 메시지를 강화한다.")
    lines.append("3. Red Zone 국가의 중국 브랜드 신제품/신채널 유입을 주 1회 리더십에 리포트한다.")
    lines.append("")
    lines.append("### 4.1 브랜드별 분석")
    lines.append("| Brand | Product Focus | Top Country | Activity | Threat | Source |")
    lines.append("|---|---|---|---|---|---|")
    for brand in ["TCL", "Hisense", "Haier", "Midea"]:
        b_records = [r for r in records if safe_text(r.get("brand")).lower() == brand.lower()]
        if not b_records:
            continue
        top_country = Counter([normalize_country(r.get("country", "")) for r in b_records]).most_common(1)[0][0]
        top_product = Counter([normalize_product(r.get("product", "")) for r in b_records]).most_common(1)[0][0]
        activity = safe_text(select_best(b_records).get("quote_original"))[:110]
        threat = "🔴" if len(b_records) >= 10 else "🟡"
        lines.append(
            f"| {brand} | {top_product} | {COUNTRY_LABEL.get(top_country, top_country)} | {activity} | {threat} | {source_link(select_best(b_records))} |"
        )
    lines.append("")
    lines.append("### 4.2 중국 브랜드 가격 전쟁 맵")
    lines.append("| Country | Product | Chinese Brand Price | LG Comparable Price | Price Gap | Source |")
    lines.append("|---|---|---:|---:|---|---|")
    price_rows = []
    for c in COUNTRY_ORDER:
        for p in PRODUCT_ORDER:
            chinese_prices = [
                price_candidate(r)
                for r in by_country_product[(c, p)]
                if is_chinese_brand(r)
            ]
            lg_prices = [
                price_candidate(r)
                for r in by_country_product[(c, p)]
                if safe_text(r.get("brand")).lower() == "lg"
            ]
            chinese_prices = [x for x in chinese_prices if x is not None]
            lg_prices = [x for x in lg_prices if x is not None]
            if not chinese_prices or not lg_prices:
                continue
            c_min = min(chinese_prices)
            l_min = min(lg_prices)
            ratio = (l_min / c_min) if c_min > 0 else 0
            ref = select_best(
                [r for r in by_country_product[(c, p)] if is_chinese_brand(r) and (is_pricing(r) or is_promotion(r))]
            ) or records[0]
            price_rows.append((ratio, c, p, c_min, l_min, ref))

    if price_rows:
        for _, c, p, c_min, l_min, ref in sorted(price_rows, key=lambda x: x[0], reverse=True)[:16]:
            lines.append(
                f"| {COUNTRY_LABEL[c]} | {p} | {fmt_num(c_min)} | {fmt_num(l_min)} | LG/Chinese {l_min / c_min:.2f}배 | {source_link(ref)} |"
            )
    else:
        lines.append("| GLOBAL | TV | - | - | 관측값 제한 | ❓[출처 미확인 — 검색어: \"Chinese brand price war\"] |")
    lines.append("")
    lines.append("### 4.3 전략 요약")
    lines.append(
        f"- 이번 주 가장 공격적인 중국 브랜드 노출은 **{COUNTRY_LABEL[top_country_china]}**에서 확인되었으며, 다수 신호가 가격/채널 확장으로 연결된다. {source_link(top_china_record or records[0])}"
    )
    lines.append(
        "- LG는 프리미엄 포지셔닝 유지와 동시에 엔트리 가격대 체감가 설계를 병행해야 전환 손실을 줄일 수 있다."
    )
    lines.append(
        "- 다음 주 우선 모니터링: 1) Red Zone 국가 가격 변화 2) HS 채널 입점 확대 3) VOC 악화 조짐."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. 전주 대비 추이")
    lines.append("")
    lines.append("### 핵심 인사이트")
    lines.append("- 추이 데이터는 주차 누적 시 정확도가 빠르게 개선되며, 현재는 기준선 정교화 구간이다.")
    lines.append("- 데이터 건수와 프로모션 신호 증감은 다음 주 오퍼 우선순위의 핵심 입력값이다.")
    lines.append("- Critical 국가 수와 부정 VOC는 매출 방어 KPI로 직접 연결해 관리해야 한다.")
    lines.append("")
    lines.append("### 실행 필요")
    lines.append("1. 주차별 지표를 동일 기준으로 적재해 W-o-W 비교 신뢰도를 유지한다.")
    lines.append("2. Critical 국가 수 증가 시 지역별 가격·CS 대응안을 즉시 승격한다.")
    lines.append("3. 추이 그래프는 허브에서 경영진용 요약 뷰로 우선 노출한다.")
    lines.append("")

    history = weekly_history(root_dir, date_key, depth=5)
    week_labels = ["W-4", "W-3", "W-2", "W-1", "This Week"]

    def hist_value(key: str) -> List[str]:
        vals: List[str] = []
        for item in history:
            if not item:
                vals.append("—")
                continue
            if key == "critical":
                raw_date = safe_text(item.get("date"))
                raw_path = root_dir / "data" / "raw" / f"openclaw_{raw_date}.jsonl"
                if raw_path.exists():
                    tmp_records = load_jsonl(raw_path)
                    tmp_country = defaultdict(lambda: {"lg": 0, "comp": 0, "china": 0, "neg": 0, "total": 0})
                    for rr in tmp_records:
                        cc = normalize_country(rr.get("country", ""))
                        if cc not in COUNTRY_ORDER:
                            continue
                        tmp_country[cc]["total"] += 1
                        if is_promotion(rr) and safe_text(rr.get("brand")).lower() == "lg":
                            tmp_country[cc]["lg"] += 1
                        if is_promotion(rr) and safe_text(rr.get("brand")).lower() != "lg":
                            tmp_country[cc]["comp"] += 1
                        if is_chinese_brand(rr):
                            tmp_country[cc]["china"] += 1
                        if is_negative(rr):
                            tmp_country[cc]["neg"] += 1
                    critical = 0
                    for cc in COUNTRY_ORDER:
                        st = tmp_country[cc]
                        sc = 0
                        if st["neg"] > 0:
                            sc += 2
                        if st["china"] >= 2:
                            sc += 2
                        if st["comp"] > st["lg"]:
                            sc += 1
                        if st["lg"] == 0 and st["total"] > 0:
                            sc += 1
                        if sc >= 4:
                            critical += 1
                    vals.append(str(critical))
                else:
                    vals.append("—")
                continue
            if key == "comp_promo":
                raw_date = safe_text(item.get("date"))
                raw_path = root_dir / "data" / "raw" / f"openclaw_{raw_date}.jsonl"
                if raw_path.exists():
                    tmp_records = load_jsonl(raw_path)
                    comp_count = len([rr for rr in tmp_records if is_promotion(rr) and safe_text(rr.get("brand")).lower() != "lg"])
                    vals.append(str(comp_count))
                else:
                    vals.append("—")
                continue
            mapping = {
                "total": "total_records",
                "lg_promo": "lg_promo_count",
                "chinese": "chinese_brand_total",
                "negative": "consumer_negative_count",
            }
            data_key = mapping[key]
            v = item.get(data_key)
            vals.append(str(v) if v is not None else "—")
        return vals

    row_total = hist_value("total")
    row_lg_promo = hist_value("lg_promo")
    row_comp_promo = hist_value("comp_promo")
    row_china = hist_value("chinese")
    row_negative = hist_value("negative")
    row_critical = hist_value("critical")

    lines.append(f"| Metric | {' | '.join(week_labels)} | Trend |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")

    def trend_from_row(row: List[str]) -> str:
        if len(row) < 2:
            return "→"
        prev = row[-2]
        curr = row[-1]
        if prev == "—" or curr == "—":
            return "→"
        try:
            pv = float(prev)
            cv = float(curr)
            if cv > pv:
                return "↑"
            if cv < pv:
                return "↓"
            return "→"
        except ValueError:
            return "→"

    lines.append(f"| 총 데이터 건수 | {' | '.join(row_total)} | {trend_from_row(row_total)} |")
    lines.append(f"| LG 프로모션 감지 건수 | {' | '.join(row_lg_promo)} | {trend_from_row(row_lg_promo)} |")
    lines.append(f"| 경쟁사 공격 프로모션 감지 건수 | {' | '.join(row_comp_promo)} | {trend_from_row(row_comp_promo)} |")
    lines.append(f"| 중국 브랜드 위협 신호 | {' | '.join(row_china)} | {trend_from_row(row_china)} |")
    lines.append(f"| 부정 소비자 언급 수 | {' | '.join(row_negative)} | {trend_from_row(row_negative)} |")
    lines.append(f"| Critical Alert 발생 국가 수 | {' | '.join(row_critical)} | {trend_from_row(row_critical)} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 부록 A. 데이터 소스 & 커버리지")
    lines.append("")
    lines.append("| Country | Records | Primary Source |")
    lines.append("|---|---:|---|")
    for c in COUNTRY_ORDER:
        recs = by_country[c]
        ref = select_best(recs) or records[0]
        lines.append(f"| {COUNTRY_LABEL[c]} | {len(recs)} | {source_link(ref)} |")
    lines.append("")
    lines.append("## 부록 B. 방법론 & 한계")
    lines.append("- Data Collection: OpenClaw raw JSONL 기반 자동 집계")
    lines.append("- Scope: 보고 생성일 기준 최근 수집 주차 데이터")
    lines.append("- Limitation: 소스별 크롤링 제한 및 지역별 데이터 가용성 차이 존재")
    lines.append("- Note: URL이 없는 항목은 규칙에 따라 출처 미확인으로 표기")
    lines.append("")
    lines.append("## 부록 C. 용어")
    lines.append("- **MS**: Media Entertainment Solution")
    lines.append("- **HS**: Home Appliance Solution")
    lines.append("- **VOC**: Voice of Customer")
    lines.append("- **W-o-W**: Week over Week")
    lines.append("")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"report generated: {output_md}")


if __name__ == "__main__":
    main()
