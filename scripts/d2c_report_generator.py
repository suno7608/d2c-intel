#!/usr/bin/env python3
"""
D2C Intel — Report Generator (Claude Opus 4.5)
================================================
Brave Search JSONL 데이터 + report_format_spec.md 기반으로
Claude Opus 4.5를 사용하여 주간 리포트 Markdown을 생성합니다.

기존 Codex synthesis + Claude cowork 2단계를 하나로 통합.

Usage:
    python scripts/d2c_report_generator.py [YYYY-MM-DD]

Environment:
    ANTHROPIC_API_KEY      — Anthropic API key (required)
    CLAUDE_MODEL_REPORT    — 모델 지정 (default: claude-opus-4-5-20251101)

Output:
    reports/md/LG_Global_D2C_Weekly_Intelligence_YYYY-MM-DD_R2_16country.md
    reports/md/LG_Global_D2C_Weekly_Intelligence_YYYY-MM-DD_claude.md (사본)
"""

import json
import logging
import os
import re
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
PROMPTS_DIR = ROOT_DIR / "prompts"
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports" / "md"
LOG_DIR = ROOT_DIR / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("d2c_report_generator")

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
# Data Loading & Preprocessing
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


def load_weekly_stats(date_key: str) -> Optional[dict]:
    """주간 통계 파일을 로드합니다."""
    stats_path = DATA_DIR / "weekly_stats" / f"{date_key}.json"
    if stats_path.exists():
        try:
            return json.loads(stats_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def get_previous_stats(date_key: str) -> Optional[dict]:
    """전주 통계를 찾습니다."""
    stats_dir = DATA_DIR / "weekly_stats"
    if not stats_dir.exists():
        return None
    files = sorted(stats_dir.glob("*.json"), reverse=True)
    for f in files:
        d = f.stem
        if d < date_key:
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
    return None


def compute_report_period(date_key: str) -> Tuple[str, str]:
    """보고 기간을 계산합니다 (전주 일요일 ~ 토요일)."""
    d = date.fromisoformat(date_key)
    # 전주 토요일 = date_key가 일요일이면 어제, 아니면 지난 토요일
    days_since_saturday = (d.weekday() + 2) % 7
    end = d - timedelta(days=max(days_since_saturday, 1))
    start = end - timedelta(days=6)
    return start.isoformat(), end.isoformat()


def summarize_data(records: List[dict]) -> str:
    """JSONL 데이터를 Claude 프롬프트용 요약 문자열로 변환합니다."""
    # 통계 계산
    total = len(records)
    countries = Counter(r.get("country", "?") for r in records)
    products = Counter(r.get("product", "?") for r in records)
    pillars = Counter(r.get("pillar", "?") for r in records)
    brands = Counter(r.get("brand", "?") for r in records)

    chinese_records = [r for r in records if r.get("brand", "").lower() in CHINESE_BRANDS]
    chinese_by_country = Counter(r.get("country", "?") for r in chinese_records)
    chinese_by_product = Counter(r.get("product", "?") for r in chinese_records)

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

    summary = []
    summary.append(f"## 수집 데이터 요약 (총 {total}건)")
    summary.append(f"\n### 국가별 건수:")
    for c in COUNTRY_ORDER:
        cnt = countries.get(c, 0)
        flag = COUNTRY_FLAG.get(c, "")
        name = COUNTRY_NAME_KO.get(c, c)
        summary.append(f"- {flag} {name} ({c}): {cnt}건")

    summary.append(f"\n### 제품별 건수:")
    for p in PRODUCT_ORDER:
        cnt = products.get(p, 0)
        ratio = cnt / total * 100 if total > 0 else 0
        summary.append(f"- {p}: {cnt}건 ({ratio:.1f}%)")

    summary.append(f"\n### 인텔리전스 필라별 건수:")
    for p, cnt in pillars.most_common():
        summary.append(f"- {p}: {cnt}건")

    summary.append(f"\n### 주요 브랜드:")
    for b, cnt in brands.most_common(10):
        summary.append(f"- {b}: {cnt}건")

    summary.append(f"\n### 중국 브랜드 위협: {len(chinese_records)}건")
    for c, cnt in chinese_by_country.most_common():
        summary.append(f"- {COUNTRY_FLAG.get(c, '')} {c}: {cnt}건")

    summary.append(f"\n### 부정 소비자 반응: {len(negative_records)}건")
    summary.append(f"### LG 프로모션 감지: {len(promo_records)}건")

    return "\n".join(summary)


def format_data_samples(records: List[dict], max_per_group: int = 5) -> str:
    """국가/제품별 대표 데이터 샘플을 포맷합니다."""
    groups: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for r in records:
        key = (r.get("country", "?"), r.get("product", "?"))
        groups[key].append(r)

    lines = ["## 국가/제품별 주요 데이터 샘플\n"]
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

def generate_report_with_claude(
    records: List[dict],
    date_key: str,
    start_date: str,
    end_date: str,
    format_spec: str,
    prev_stats: Optional[dict],
) -> str:
    """Claude Opus 4.5로 리포트를 생성합니다."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    model = os.environ.get("CLAUDE_MODEL_REPORT", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    # 데이터 요약
    data_summary = summarize_data(records)
    data_samples = format_data_samples(records, max_per_group=3)

    # 전주 비교 데이터
    prev_context = ""
    if prev_stats:
        prev_context = f"""
## 전주 통계 (비교용):
- 총 데이터: {prev_stats.get('total_records', 'N/A')}건
- TV 비율: {prev_stats.get('tv_ratio_pct', 'N/A')}%
- 중국 브랜드: {prev_stats.get('chinese_brand_total', 'N/A')}건
- 부정 소비자 반응: {prev_stats.get('consumer_negative_count', 'N/A')}건
- LG 프로모션: {prev_stats.get('lg_promo_count', 'N/A')}건
- 국가 수: {prev_stats.get('countries', 'N/A')}개
"""

    # 전체 raw 데이터 (최대 토큰 관리를 위해 핵심 필드만)
    raw_lines = []
    for r in records:
        compact = {
            "country": r.get("country"),
            "product": r.get("product"),
            "pillar": r.get("pillar"),
            "brand": r.get("brand"),
            "signal_type": r.get("signal_type"),
            "value": r.get("value", "")[:300],
            "source_url": r.get("source_url", ""),
            "confidence": r.get("confidence"),
        }
        raw_lines.append(json.dumps(compact, ensure_ascii=False))

    raw_data_block = "\n".join(raw_lines)

    # 시스템 프롬프트
    system_prompt = f"""당신은 LG전자 글로벌 D2C 시장 인텔리전스 수석 애널리스트입니다.
아래 포맷 명세를 100% 준수하여 주간 리포트를 작성하세요.

## 핵심 원칙
1. report_format_spec.md의 모든 섹션 구조, 표기 규칙, 콘텐츠 균형 규칙을 엄격히 따릅니다.
2. 모든 테이블의 Source 열에 실제 URL 링크를 포함합니다. URL이 없으면 Google 검색 URL로 대체합니다.
3. TV 관련 콘텐츠가 전체의 50%를 초과하지 않도록 합니다.
4. 16개국 모두 주요 테이블에 빠짐없이 포함합니다.
5. 핵심 인사이트(3개 bullet)와 실행 필요(3개 numbered)는 모든 주요 섹션/서브섹션에 필수입니다.
6. 국가 표기: 국기 + 국가명 + 국가코드 형식 (예: 🇺🇸 미국 (US))
7. 용어: MS = Media Entertainment Solution (TV), HS = Home appliance solution (생활가전)
8. 중국 브랜드 분석: TV(TCL/Hisense)와 가전(Haier/Midea)을 분리하여 분석합니다.
9. Key Findings에 TV 외 제품(냉장고/세탁기/모니터/gram) 최소 3건을 포함합니다.
10. Chart.js 차트 마커를 적절한 위치에 삽입합니다.

## 차트 마커 삽입 규칙
- 섹션 1.2 이번 주 주요 지표 테이블 바로 아래: `<!-- CHART:product_donut -->`
- 섹션 5 전주 대비 추이 상단: `<!-- CHART:wow_bar -->`

## 출력 형식
- 순수 Markdown만 출력합니다 (코드블록 래핑 금지).
- 첫 줄부터 `# LG전자 글로벌 D2C 주간 시장 인텔리전스 리포트` 헤더로 시작합니다.

{format_spec}"""

    # 유저 프롬프트
    user_prompt = f"""아래 데이터를 기반으로 주간 리포트를 작성하세요.

## 문서 헤더 정보
- 보고 기간: {start_date}(일) — {end_date}(토)
- Prepared by: D2C Global Intelligence (OpenClaw Automated)
- Distribution: D2C Leadership / Confidential
- Date Generated: {date_key}
- Version: Weekly Vol.{date_key}-R2

{data_summary}

{prev_context}

{data_samples}

## 전체 수집 데이터 (JSONL, {len(records)}건):
{raw_data_block}

위 데이터를 분석하여 report_format_spec.md에 정의된 포맷대로
5개 주요 섹션 + 3개 부록으로 구성된 완전한 주간 리포트를 작성하세요.
모든 테이블에 실제 source_url을 [🔗 Source](URL) 형식으로 포함하세요.
"""

    logger.info(f"Calling Claude {model}...")
    logger.info(f"System prompt: {len(system_prompt)} chars")
    logger.info(f"User prompt: {len(user_prompt)} chars")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        raise

    # 응답 추출
    content = response.content[0].text if response.content else ""
    usage = response.usage
    logger.info(
        f"Claude response: {len(content)} chars, "
        f"input_tokens={usage.input_tokens}, output_tokens={usage.output_tokens}"
    )

    return content


# ──────────────────────────────────────────────────────────────
# Post-processing
# ──────────────────────────────────────────────────────────────

def clean_markdown(text: str) -> str:
    """Claude 응답에서 불필요한 래핑을 제거합니다."""
    # Remove markdown code block wrappers
    text = re.sub(r"^```(?:markdown)?\s*\n", "", text.strip())
    text = re.sub(r"\n```\s*$", "", text)

    # Ensure starts with header
    if not text.startswith("# "):
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("# "):
                text = "\n".join(lines[i:])
                break

    return text.strip() + "\n"


def validate_report(md: str, records: List[dict]) -> List[str]:
    """리포트 품질을 검증합니다."""
    issues = []

    # 섹션 존재 확인
    required_sections = [
        "경영진 요약", "핵심 경보", "핵심 법인 풀 커버리지 대시보드",
        "중국 브랜드 위협 보고", "전주 대비 추이",
    ]
    for section in required_sections:
        if section not in md:
            issues.append(f"Missing section: {section}")

    # 핵심 인사이트/실행 필요 블록 확인
    insight_count = md.count("### 핵심 인사이트")
    action_count = md.count("### 실행 필요")
    if insight_count < 5:
        issues.append(f"핵심 인사이트 blocks: {insight_count} (expected 5+)")
    if action_count < 5:
        issues.append(f"실행 필요 blocks: {action_count} (expected 5+)")

    # Source 링크 확인
    source_links = re.findall(r"\[🔗 Source\]\(https?://", md)
    if len(source_links) < 10:
        issues.append(f"Source links: {len(source_links)} (expected 10+)")

    # 16개국 포함 확인
    for c in COUNTRY_ORDER:
        flag = COUNTRY_FLAG.get(c, "")
        if flag not in md and c not in md:
            issues.append(f"Country missing from report: {c}")

    # 차트 마커 확인
    if "<!-- CHART:product_donut -->" not in md:
        issues.append("Missing chart marker: product_donut")
    if "<!-- CHART:wow_bar -->" not in md:
        issues.append("Missing chart marker: wow_bar")

    # 파일 크기 확인 (최소 55KB)
    size_kb = len(md.encode("utf-8")) / 1024
    if size_kb < 55:
        issues.append(f"Report size: {size_kb:.1f}KB (expected 55KB+)")

    return issues


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    # Date key
    if len(sys.argv) > 1 and re.match(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
        date_key = sys.argv[1]
    else:
        date_key = date.today().isoformat()

    # Prepare directories
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Add file handler
    log_path = LOG_DIR / f"report_generator_{date_key}.log"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(fh)

    logger.info(f"D2C Report Generator — date={date_key}")

    # Load raw data
    raw_path = DATA_DIR / "raw" / f"openclaw_{date_key}.jsonl"
    if not raw_path.exists():
        logger.error(f"Raw data not found: {raw_path}")
        sys.exit(1)
    records = load_jsonl(raw_path)
    logger.info(f"Loaded {len(records)} records from {raw_path}")

    if not records:
        logger.error("No valid records found")
        sys.exit(1)

    # Load format spec
    format_spec_path = PROMPTS_DIR / "report_format_spec.md"
    if format_spec_path.exists():
        format_spec = format_spec_path.read_text(encoding="utf-8")
    else:
        logger.warning(f"Format spec not found: {format_spec_path}")
        format_spec = ""

    # Compute dates
    start_date, end_date = compute_report_period(date_key)
    logger.info(f"Report period: {start_date} — {end_date}")

    # Load previous stats
    prev_stats = get_previous_stats(date_key)
    if prev_stats:
        logger.info(f"Previous stats loaded (total: {prev_stats.get('total_records', '?')})")

    # Generate report
    report_md = generate_report_with_claude(
        records, date_key, start_date, end_date, format_spec, prev_stats
    )

    # Clean up
    report_md = clean_markdown(report_md)

    # Validate
    issues = validate_report(report_md, records)
    if issues:
        logger.warning(f"Report validation issues ({len(issues)}):")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("Report validation passed")

    # Write output
    output_name = f"LG_Global_D2C_Weekly_Intelligence_{date_key}_R2_16country.md"
    output_path = REPORTS_DIR / output_name
    output_path.write_text(report_md, encoding="utf-8")
    logger.info(f"Report written: {output_path} ({len(report_md)} bytes)")

    # Copy as _claude.md (기존 파이프라인 호환)
    claude_name = f"LG_Global_D2C_Weekly_Intelligence_{date_key}_claude.md"
    claude_path = REPORTS_DIR / claude_name
    claude_path.write_text(report_md, encoding="utf-8")
    logger.info(f"Claude copy: {claude_path}")

    # Summary
    size_kb = len(report_md.encode("utf-8")) / 1024
    print(f"[d2c_report_generator] Report generated: {output_path.name} ({size_kb:.1f}KB)")


if __name__ == "__main__":
    main()
