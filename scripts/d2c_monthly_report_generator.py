#!/usr/bin/env python3
"""
D2C Intel — Monthly Deep Dive Report Generator (Claude Opus 4.5)
=================================================================
월간 집계 데이터 + monthly_format_spec.md 기반으로
Claude Opus 4.5를 사용하여 Monthly Deep Dive 리포트를 생성합니다.

Usage:
    python scripts/d2c_monthly_report_generator.py [YYYY-MM]

Environment:
    ANTHROPIC_API_KEY          — Anthropic API key (required)
    CLAUDE_MODEL_REPORT        — 모델 지정 (default: claude-opus-4-5-20251101)

Input:
    data/monthly_stats/YYYY-MM.json              (월간 집계 통계)
    data/monthly_raw/openclaw_YYYY-MM_merged.jsonl (통합 JSONL)

Output:
    reports/md/LG_Global_D2C_Monthly_Intelligence_YYYY-MM.md
"""

import json
import logging
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from calendar import monthrange
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import anthropic

# ──────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports" / "md"
LOG_DIR = ROOT_DIR / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("d2c_monthly_report_generator")

DEFAULT_MODEL = "claude-opus-4-5-20251101"

COUNTRY_ORDER = [
    "US", "CA", "UK", "DE", "FR", "ES", "IT", "BR",
    "MX", "CL", "TH", "AU", "TW", "SG", "EG", "SA",
]
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
PRODUCT_ORDER = ["TV", "Refrigerator", "Washing Machine", "Monitor", "LG gram"]
CHINESE_BRANDS = {"tcl", "hisense", "haier", "midea"}


# ──────────────────────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────────────────────

def load_monthly_stats(year_month: str) -> dict:
    """월간 집계 통계를 로드합니다."""
    stats_path = DATA_DIR / "monthly_stats" / f"{year_month}.json"
    if not stats_path.exists():
        raise FileNotFoundError(f"Monthly stats not found: {stats_path}")
    return json.loads(stats_path.read_text(encoding="utf-8"))


def load_merged_jsonl(year_month: str) -> List[dict]:
    """통합 JSONL을 로드합니다."""
    jsonl_path = DATA_DIR / "monthly_raw" / f"openclaw_{year_month}_merged.jsonl"
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Merged JSONL not found: {jsonl_path}")
    records = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
        except json.JSONDecodeError:
            continue
    return records


# ──────────────────────────────────────────────────────────────
# Prompt Construction
# ──────────────────────────────────────────────────────────────

def build_monthly_summary(stats: dict) -> str:
    """월간 통계를 Claude 프롬프트용 요약 문자열로 변환합니다."""
    lines = []
    lines.append(f"## 월간 집계 요약 ({stats['year_month']})")
    lines.append(f"- 총 레코드: {stats['total_records']}건 (주간 {stats['weeks_count']}회분)")
    lines.append(f"- 국가 수: {stats['countries_count']}개")
    lines.append(f"- TV 비율: {stats['tv_ratio_pct']}%")
    lines.append(f"- 중국 브랜드 시그널: {stats['chinese_brand_total']}건")
    lines.append(f"- 소비자 부정 반응: {stats['consumer_negative_count']}건")
    lines.append(f"- LG 프로모션: {stats['lg_promo_count']}건")

    lines.append(f"\n### 국가별 건수:")
    for c in COUNTRY_ORDER:
        cnt = stats["countries"].get(c, 0)
        flag = COUNTRY_FLAG.get(c, "")
        name = COUNTRY_NAME_KO.get(c, c)
        lines.append(f"- {flag} {name} ({c}): {cnt}건")

    lines.append(f"\n### 제품별 건수:")
    for p in PRODUCT_ORDER:
        cnt = stats["products"].get(p, 0)
        ratio = cnt / stats["total_records"] * 100 if stats["total_records"] else 0
        lines.append(f"- {p}: {cnt}건 ({ratio:.1f}%)")

    lines.append(f"\n### 필라별 건수:")
    for pillar, cnt in stats.get("pillars", {}).items():
        lines.append(f"- {pillar}: {cnt}건")

    lines.append(f"\n### 주요 브랜드 (상위 15):")
    for brand, cnt in list(stats.get("brands", {}).items())[:15]:
        lines.append(f"- {brand}: {cnt}건")

    lines.append(f"\n### 중국 브랜드 상세:")
    for brand, cnt in stats.get("chinese_by_brand", {}).items():
        lines.append(f"- {brand}: {cnt}건")

    return "\n".join(lines)


def build_weekly_trend_section(stats: dict) -> str:
    """주차별 추이 데이터를 프롬프트용으로 포맷합니다."""
    trend = stats.get("weekly_trend", {})
    labels = trend.get("labels", [])
    if not labels:
        return "## 주차별 추이: 데이터 없음"

    lines = ["## 주차별 추이 데이터"]

    # 주차별 총건수
    lines.append("\n### 주차별 총 레코드:")
    for label, total in zip(labels, trend.get("totals", [])):
        lines.append(f"- {label}: {total}건")

    # 주차별 제품 시계열
    products = trend.get("products", {})
    lines.append("\n### 주차별 제품 시계열:")
    for p in PRODUCT_ORDER:
        series = products.get(p, [])
        series_str = ", ".join(f"{label}:{v}" for label, v in zip(labels, series))
        lines.append(f"- {p}: {series_str}")

    # 주차별 중국 브랜드
    lines.append("\n### 주차별 중국 브랜드 시그널:")
    for label, cnt in zip(labels, trend.get("chinese", [])):
        lines.append(f"- {label}: {cnt}건")

    # 주차별 부정 반응
    lines.append("\n### 주차별 소비자 부정 반응:")
    for label, cnt in zip(labels, trend.get("negative", [])):
        lines.append(f"- {label}: {cnt}건")

    return "\n".join(lines)


def build_mom_section(stats: dict) -> str:
    """MoM 비교 데이터를 프롬프트용으로 포맷합니다."""
    mom = stats.get("mom_comparison", {})
    if not mom:
        return "## MoM 비교: 전월 데이터 없음 (첫 월간 리포트)"

    lines = ["## Month-over-Month 비교"]
    for key, val in mom.items():
        lines.append(f"- {key}: {val['prev']} → {val['this']} ({val['change_pct']:+.1f}%)")
    return "\n".join(lines)


def build_chart_data_section(stats: dict) -> str:
    """Chart.js 데이터를 프롬프트에 포함합니다."""
    chart_data = stats.get("chart_data", {})
    if not chart_data:
        return ""

    lines = ["## Chart.js 사전 계산 데이터 (리포트에 삽입할 것)"]
    lines.append("아래 JSON을 해당 차트 마커 위치에 ```json:chart 블록으로 삽입하세요.\n")

    for chart_id, data in chart_data.items():
        lines.append(f"### {chart_id}:")
        lines.append("```json")
        lines.append(json.dumps(data, ensure_ascii=False, indent=2))
        lines.append("```\n")

    return "\n".join(lines)


def format_data_samples(records: List[dict], max_per_group: int = 3) -> str:
    """국가/제품별 대표 데이터 샘플을 포맷합니다."""
    groups: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for r in records:
        key = (r.get("country", "?"), r.get("product", "?"))
        groups[key].append(r)

    lines = ["## 국가/제품별 주요 데이터 샘플 (월간 통합)\n"]
    for country in COUNTRY_ORDER:
        for product in PRODUCT_ORDER:
            group = groups.get((country, product), [])
            if not group:
                continue
            flag = COUNTRY_FLAG.get(country, "")
            lines.append(f"\n### {flag} {country} - {product} ({len(group)}건)")
            for r in group[:max_per_group]:
                brand = r.get("brand", "?")
                signal = r.get("signal_type", "?")
                value = r.get("value", "")[:200]
                url = r.get("source_url", "")
                confidence = r.get("confidence", "?")
                lines.append(
                    f"- [{brand}] ({signal}, {confidence}) {value}"
                    + (f" [🔗]({url})" if url else "")
                )

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Claude API Interaction
# ──────────────────────────────────────────────────────────────

def generate_monthly_report_with_claude(
    records: List[dict],
    stats: dict,
    year_month: str,
    format_spec: str,
) -> str:
    """Claude Opus 4.5로 Monthly Deep Dive 리포트를 생성합니다."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    model = os.environ.get("CLAUDE_MODEL_REPORT", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    # 프롬프트 구성 요소
    monthly_summary = build_monthly_summary(stats)
    weekly_trend = build_weekly_trend_section(stats)
    mom_section = build_mom_section(stats)
    chart_data_section = build_chart_data_section(stats)
    data_samples = format_data_samples(records, max_per_group=3)

    year, month = int(year_month[:4]), int(year_month[5:7])
    _, last_day_num = monthrange(year, month)
    start_date = f"{year_month}-01"
    end_date = f"{year_month}-{last_day_num:02d}"

    # 시스템 프롬프트
    system_prompt = f"""당신은 LG전자 글로벌 D2C 시장 인텔리전스 수석 애널리스트입니다.
아래 포맷 명세를 100% 준수하여 **월간 심화 분석(Monthly Deep Dive) 리포트**를 작성하세요.

## 핵심 원칙
1. monthly_format_spec.md의 모든 섹션 구조, 표기 규칙, 콘텐츠 균형 규칙을 엄격히 따릅니다.
2. 주간 리포트와 달리, **월간 추세와 패턴 분석**에 초점을 맞춥니다.
3. 모든 테이블의 Source 열에 실제 URL 링크를 포함합니다.
4. TV 관련 콘텐츠가 전체의 50%를 초과하지 않도록 합니다.
5. 16개국 모두 주요 테이블에 빠짐없이 포함합니다.
6. 핵심 인사이트(5개 bullet)와 실행 필요(5개 numbered)는 모든 주요 섹션에 필수입니다.
7. 중국 브랜드: TV(TCL/Hisense)와 가전(Haier/Midea)을 분리하여 월간 추이 분석합니다.
8. **주차별(W1~W4) 데이터 추이**를 분석에 활용하세요.
9. MoM(전월 대비) 비교를 포함하세요 (데이터 없으면 N/A).
10. Chart.js 차트 마커와 JSON 데이터 블록을 적절한 위치에 삽입합니다.

## 차트 마커 + JSON 삽입 규칙
차트 마커 아래에 JSON 코드블록을 삽입합니다:
```
<!-- CHART:monthly_product_trend -->
```json:chart
{{"type":"line","title":"제품별 4주 추이","labels":[...],"datasets":[...]}}
```
```
지원 차트: line, bar, doughnut, polarArea
필수 필드: type, title, labels, datasets (각 dataset에 label, data, color)

## 출력 형식
- 순수 Markdown만 출력합니다 (코드블록 래핑 금지).
- 첫 줄부터 헤더로 시작합니다.

{format_spec}"""

    # 유저 프롬프트
    user_prompt = f"""아래 월간 집계 데이터를 기반으로 Monthly Deep Dive 리포트를 작성하세요.

## 문서 헤더 정보
- 보고 기간: {start_date} — {end_date}
- 데이터 기반: 주간 리포트 {stats['weeks_count']}회분
- Prepared by: D2C Global Intelligence (OpenClaw Automated)
- Distribution: D2C Leadership / Confidential
- Date Generated: {date.today().isoformat()}
- Version: Monthly Vol.{year_month}

{monthly_summary}

{weekly_trend}

{mom_section}

{chart_data_section}

{data_samples}

위 데이터를 분석하여 monthly_format_spec.md에 정의된 포맷대로
7개 주요 섹션 + 2개 부록으로 구성된 완전한 월간 심화 분석 리포트를 작성하세요.
주차별 추이와 MoM 비교를 핵심 분석에 활용하세요.
Chart.js 데이터 블록을 차트 마커 위치에 삽입하세요.
"""

    logger.info(f"Calling Claude {model}...")
    logger.info(f"System prompt: {len(system_prompt)} chars")
    logger.info(f"User prompt: {len(user_prompt)} chars")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=32000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        raise

    content = response.content[0].text if response.content else ""
    usage = response.usage
    logger.info(
        f"Claude response: {len(content)} chars, "
        f"input_tokens={usage.input_tokens}, output_tokens={usage.output_tokens}"
    )

    return content


# ──────────────────────────────────────────────────────────────
# Post-processing & Validation
# ──────────────────────────────────────────────────────────────

def clean_markdown(text: str) -> str:
    """Claude 응답에서 불필요한 래핑을 제거합니다."""
    text = re.sub(r"^```(?:markdown)?\s*\n", "", text.strip())
    text = re.sub(r"\n```\s*$", "", text)

    if not text.startswith("# "):
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("# "):
                text = "\n".join(lines[i:])
                break

    return text.strip() + "\n"


def validate_monthly_report(md: str) -> List[str]:
    """Monthly 리포트 품질을 검증합니다."""
    issues = []

    # 섹션 존재 확인
    required_sections = [
        "경영진 요약", "핵심 경보", "대시보드",
        "Deep Dive", "중국 브랜드", "Month-over-Month",
    ]
    for section in required_sections:
        if section not in md:
            issues.append(f"Missing section keyword: {section}")

    # 핵심 인사이트/실행 필요 블록 확인
    insight_count = md.count("### 핵심 인사이트")
    action_count = md.count("### 실행 필요")
    if insight_count < 6:
        issues.append(f"핵심 인사이트 blocks: {insight_count} (expected 6+)")
    if action_count < 6:
        issues.append(f"실행 필요 blocks: {action_count} (expected 6+)")

    # Source 링크 확인
    source_links = re.findall(r"\[🔗[^\]]*\]\(https?://", md)
    if len(source_links) < 15:
        issues.append(f"Source links: {len(source_links)} (expected 15+)")

    # 차트 마커 확인
    chart_markers = re.findall(r"<!-- CHART:\w+ -->", md)
    if len(chart_markers) < 3:
        issues.append(f"Chart markers: {len(chart_markers)} (expected 3+)")

    # Chart JSON 블록 확인
    chart_json_blocks = re.findall(r"```json:chart", md)
    if len(chart_json_blocks) < 3:
        issues.append(f"Chart JSON blocks: {len(chart_json_blocks)} (expected 3+)")

    # 16개국 포함 확인
    for c in COUNTRY_ORDER:
        flag = COUNTRY_FLAG.get(c, "")
        if flag not in md and c not in md:
            issues.append(f"Country missing: {c}")

    # 파일 크기 확인
    size_kb = len(md.encode("utf-8")) / 1024
    if size_kb < 80:
        issues.append(f"File size {size_kb:.0f}KB < 80KB minimum")

    return issues


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    # 대상 월 결정
    if len(sys.argv) > 1 and re.match(r"\d{4}-\d{2}", sys.argv[1]):
        year_month = sys.argv[1][:7]
    else:
        today = date.today()
        if today.month == 1:
            year_month = f"{today.year - 1}-12"
        else:
            year_month = f"{today.year}-{today.month - 1:02d}"

    logger.info(f"D2C Monthly Report Generation — target: {year_month}")

    # 디렉토리 준비
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 로그 파일 핸들러
    log_path = LOG_DIR / f"monthly_report_{year_month}.log"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(fh)

    # 데이터 로드
    stats = load_monthly_stats(year_month)
    records = load_merged_jsonl(year_month)
    logger.info(f"Loaded: {len(records)} records, {stats['weeks_count']} weeks")

    # Format Spec 로드
    format_spec_path = PROMPTS_DIR / "monthly_format_spec.md"
    if not format_spec_path.exists():
        logger.error(f"Format spec not found: {format_spec_path}")
        sys.exit(1)
    format_spec = format_spec_path.read_text(encoding="utf-8")

    # Claude 리포트 생성
    raw_md = generate_monthly_report_with_claude(
        records, stats, year_month, format_spec
    )

    # 후처리
    md = clean_markdown(raw_md)

    # 검증
    issues = validate_monthly_report(md)
    if issues:
        logger.warning(f"Validation issues ({len(issues)}):")
        for issue in issues:
            logger.warning(f"  - {issue}")
        logger.warning("Proceeding with available content (soft gate)")
    else:
        logger.info("✅ All validation checks passed")

    # 저장
    output_path = REPORTS_DIR / f"LG_Global_D2C_Monthly_Intelligence_{year_month}.md"
    output_path.write_text(md, encoding="utf-8")
    logger.info(f"Monthly report saved: {output_path}")

    size_kb = len(md.encode("utf-8")) / 1024
    logger.info(f"File size: {size_kb:.1f}KB")

    print(f"[d2c_monthly_report] {year_month}: {size_kb:.1f}KB → {output_path}")


if __name__ == "__main__":
    main()
