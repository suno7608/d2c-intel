#!/usr/bin/env python3
"""
D2C Intel — Brave Search Data Collector
========================================
Brave Search API를 사용하여 16개국 × 5제품 × 4필라 데이터를 수집하고
OpenClaw JSONL 호환 포맷으로 출력합니다.

Usage:
    python scripts/d2c_search.py [YYYY-MM-DD]

Output:
    data/raw/openclaw_YYYY-MM-DD.jsonl

Environment:
    BRAVE_API_KEY  — Brave Search API key (required)
"""

import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import yaml

# ──────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "brave_search_queries.yaml"
LOG_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data" / "raw"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("d2c_search")

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# ──────────────────────────────────────────────────────────────
# Brave Search API
# ──────────────────────────────────────────────────────────────

COUNTRY_BRAVE_MAP = {
    "US": "us", "CA": "ca", "UK": "gb", "DE": "de", "FR": "fr",
    "ES": "es", "IT": "it", "BR": "br", "MX": "mx", "CL": "cl",
    "TH": "th", "AU": "au", "TW": "tw", "SG": "sg", "EG": "eg",
    "SA": "sa",
}

PILLAR_MAP = {
    "consumer_sentiment": "Consumer Sentiment",
    "retail_channel_promotion": "Retail Channel Promotions",
    "price_intelligence": "Competitive Price & Positioning",
    "chinese_brand_threat": "Chinese Brand Threat Tracking",
}

CHINESE_BRANDS = {"tcl", "hisense", "haier", "midea"}


class BraveSearchCollector:
    """Brave Search API를 사용하여 D2C 데이터를 수집합니다."""

    def __init__(self, api_key: str, config: dict):
        self.api_key = api_key
        self.config = config
        self.search_params = config.get("search_params", {})
        self.rate_delay = self.search_params.get("rate_limit_delay_ms", 500) / 1000
        self.max_retries = self.search_params.get("max_retries", 3)
        self.retry_delay = self.search_params.get("retry_delay_ms", 2000) / 1000
        self.count = self.search_params.get("count", 10)
        self.freshness = self.search_params.get("freshness", "pw")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        })
        self.total_api_calls = 0
        self.total_results = 0
        self.seen_urls: set = set()

    def search(self, query: str, country: str = "us", count: int = 10) -> List[dict]:
        """Brave Search API 호출 (재시도 포함)."""
        params = {
            "q": query,
            "country": country,
            "count": count,
            "freshness": self.freshness,
            "text_decorations": False,
            "safesearch": "off",
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                time.sleep(self.rate_delay)
                resp = self.session.get(BRAVE_SEARCH_URL, params=params, timeout=15)
                self.total_api_calls += 1

                if resp.status_code == 429:
                    wait = self.retry_delay * attempt
                    logger.warning(f"Rate limited (429). Waiting {wait:.1f}s... [{attempt}/{self.max_retries}]")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                results = data.get("web", {}).get("results", [])
                return results

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout for query '{query}' [{attempt}/{self.max_retries}]")
                time.sleep(self.retry_delay)
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for query '{query}': {e} [{attempt}/{self.max_retries}]")
                time.sleep(self.retry_delay)

        logger.error(f"All retries failed for query: '{query}'")
        return []

    def classify_pillar(self, title: str, snippet: str, query: str) -> str:
        """검색 결과의 pillar를 분류합니다."""
        text = f"{title} {snippet} {query}".lower()

        # Chinese brand detection
        if any(brand in text for brand in CHINESE_BRANDS):
            return "chinese_brand_threat"

        promo_kw = {"deal", "promotion", "discount", "sale", "coupon", "offer",
                     "promo", "offerta", "oferta", "angebot", "promoção", "โปรโมชั่น",
                     "優惠", "折扣", "soldes", "rabatt", "sconto"}
        if any(kw in text for kw in promo_kw):
            return "retail_channel_promotion"

        price_kw = {"price", "vs", "comparison", "pricing", "preis", "prix",
                     "precio", "prezzo", "preço", "ราคา", "價格", "比較"}
        if any(kw in text for kw in price_kw):
            return "price_intelligence"

        sentiment_kw = {"review", "complaint", "problem", "issue", "experience",
                        "broken", "regret", "worst", "refund", "고장",
                        "bewertung", "avis", "reseña", "recensione", "avaliação",
                        "รีวิว", "評價"}
        if any(kw in text for kw in sentiment_kw):
            return "consumer_sentiment"

        return "consumer_sentiment"  # default

    def detect_brand(self, title: str, snippet: str) -> str:
        """검색 결과에서 브랜드를 감지합니다."""
        text = f"{title} {snippet}".lower()
        brand_map = {
            "lg": "LG", "samsung": "Samsung", "tcl": "TCL",
            "hisense": "Hisense", "haier": "Haier", "midea": "Midea",
            "sony": "Sony", "panasonic": "Panasonic", "whirlpool": "Whirlpool",
            "bosch": "Bosch", "electrolux": "Electrolux", "xiaomi": "Xiaomi",
            "海爾": "Haier", "美的": "Midea", "海信": "Hisense",
        }
        found = []
        for kw, brand in brand_map.items():
            if kw in text:
                found.append(brand)
        return found[0] if found else "LG"

    def detect_confidence(self, result: dict) -> str:
        """검색 결과의 신뢰도를 평가합니다."""
        url = result.get("url", "")
        domain = urlparse(url).netloc.lower()

        high_trust = {"reddit.com", "amazon.com", "bestbuy.com", "cnet.com",
                      "rtings.com", "techradar.com", "tomsguide.com",
                      "slickdeals.net", "mydealz.de", "hotukdeals.com",
                      "ozbargain.com.au", "pelando.com.br", "dealabs.com"}
        medium_trust = {"youtube.com", "twitter.com", "x.com", "facebook.com"}

        for trusted in high_trust:
            if trusted in domain:
                return "high"
        for med in medium_trust:
            if med in domain:
                return "medium"
        return "medium"

    def build_record(
        self, result: dict, country: str, product: str,
        pillar: str, query: str, collected_at: str
    ) -> Optional[dict]:
        """Brave Search 결과를 OpenClaw JSONL 호환 레코드로 변환합니다."""
        url = result.get("url", "")
        if not url or url in self.seen_urls:
            return None
        self.seen_urls.add(url)

        title = result.get("title", "").strip()
        snippet = result.get("description", "").strip()
        if not title and not snippet:
            return None

        domain = urlparse(url).netloc.replace("www.", "")

        brand = self.detect_brand(title, snippet)
        confidence = self.detect_confidence(result)
        classified_pillar = self.classify_pillar(title, snippet, query)

        # Chinese brand pillar override
        if pillar == "chinese_brand_threat":
            classified_pillar = "chinese_brand_threat"

        record = {
            "country": country,
            "product": product,
            "pillar": PILLAR_MAP.get(classified_pillar, classified_pillar),
            "brand": brand,
            "signal_type": self._infer_signal_type(classified_pillar, title, snippet),
            "value": title,
            "currency": "",
            "quote_original": snippet[:500] if snippet else "",
            "source_url": url,
            "source": domain,
            "collected_at": collected_at,
            "confidence": confidence,
        }
        return record

    def _infer_signal_type(self, pillar: str, title: str, snippet: str) -> str:
        """signal_type을 추론합니다."""
        text = f"{title} {snippet}".lower()
        if pillar == "retail_channel_promotion":
            return "promo"
        if pillar == "price_intelligence":
            if "vs" in text or "comparison" in text:
                return "pricing_comparison"
            return "price_discount"
        if pillar == "chinese_brand_threat":
            return "competitive_move"
        if any(kw in text for kw in ["review", "rating", "star"]):
            return "expert_review"
        if any(kw in text for kw in ["complaint", "problem", "issue", "broken", "refund"]):
            return "consumer_complaint"
        return "market_signal"

    def collect_product_queries(
        self, country_cfg: dict, product_cfg: dict,
        collected_at: str
    ) -> List[dict]:
        """특정 국가 × 제품 조합에 대해 검색을 수행합니다."""
        records = []
        country = country_cfg["code"]
        brave_country = COUNTRY_BRAVE_MAP.get(country, country.lower())
        lang = country_cfg.get("lang", "en")
        product = product_cfg["name"]
        queries = product_cfg.get("queries", {})

        # 해당 언어의 쿼리 선택 (없으면 en fallback)
        lang_queries = queries.get(lang, queries.get("en", []))

        for query in lang_queries:
            results = self.search(query, country=brave_country, count=self.count)
            for r in results:
                rec = self.build_record(r, country, product, "auto", query, collected_at)
                if rec:
                    records.append(rec)

        return records

    def collect_chinese_brand_queries(
        self, country_cfg: dict, product_cfg: dict,
        pillar_cfg: dict, collected_at: str
    ) -> List[dict]:
        """중국 브랜드 위협 전용 검색을 수행합니다."""
        records = []
        country = country_cfg["code"]
        brave_country = COUNTRY_BRAVE_MAP.get(country, country.lower())
        lang = country_cfg.get("lang", "en")
        product = product_cfg["name"]
        brands = pillar_cfg.get("brands", [])
        patterns = pillar_cfg.get("query_patterns", {})
        lang_patterns = patterns.get(lang, patterns.get("en", []))

        # 중국 브랜드 - TV: TCL/Hisense, 가전: Haier/Midea
        relevant_brands = []
        if product == "TV":
            relevant_brands = [b for b in brands if b.lower() in ("tcl", "hisense")]
        elif product in ("Refrigerator", "Washing Machine"):
            relevant_brands = [b for b in brands if b.lower() in ("haier", "midea", "hisense")]
        else:
            relevant_brands = brands[:2]  # Monitor/gram은 상위 2개

        for brand in relevant_brands:
            for pattern in lang_patterns[:2]:  # 패턴당 2개로 제한
                query = pattern.replace("{brand}", brand).replace("{product}", product)
                results = self.search(query, country=brave_country, count=5)
                for r in results:
                    rec = self.build_record(
                        r, country, product, "chinese_brand_threat", query, collected_at
                    )
                    if rec:
                        rec["brand"] = brand
                        records.append(rec)

        return records

    def collect_all(self, date_key: str) -> List[dict]:
        """전체 수집을 실행합니다."""
        collected_at = f"{date_key}T{datetime.now().strftime('%H:%M:%S')}+09:00"
        countries = self.config.get("countries", [])
        products = self.config.get("products", [])
        pillars = self.config.get("pillars", [])
        chinese_pillar = next((p for p in pillars if p["id"] == "chinese_brand_threat"), None)

        all_records: List[dict] = []

        # ── Round 1-5: 제품별 × 국가별 검색 ──
        for product_cfg in products:
            product_name = product_cfg["name"]
            logger.info(f"=== Collecting: {product_name} ===")

            for country_cfg in countries:
                country = country_cfg["code"]
                tier = country_cfg.get("tier", 3)

                # Tier에 따라 검색 쿼리 수 조절
                records = self.collect_product_queries(country_cfg, product_cfg, collected_at)
                all_records.extend(records)
                logger.info(f"  {country} ({product_name}): {len(records)} records")

        # ── Round 6: 중국 브랜드 전용 검색 ──
        if chinese_pillar:
            logger.info("=== Collecting: Chinese Brand Threat ===")
            for country_cfg in countries:
                country = country_cfg["code"]
                for product_cfg in products:
                    product_name = product_cfg["name"]
                    if product_name in ("TV", "Refrigerator", "Washing Machine"):
                        records = self.collect_chinese_brand_queries(
                            country_cfg, product_cfg, chinese_pillar, collected_at
                        )
                        all_records.extend(records)
                        if records:
                            logger.info(f"  {country} ({product_name}, Chinese): {len(records)} records")

        return all_records


# ──────────────────────────────────────────────────────────────
# Quality Gate
# ──────────────────────────────────────────────────────────────

def check_quality(records: List[dict], config: dict) -> Tuple[bool, List[str]]:
    """수집 데이터 품질을 검사합니다."""
    gates = config.get("quality_gates", {})
    issues = []

    total = len(records)
    min_total = gates.get("min_total_records", 400)
    if total < min_total:
        issues.append(f"Total records {total} < {min_total}")

    countries = set(r["country"] for r in records)
    min_countries = gates.get("min_countries", 16)
    if len(countries) < min_countries:
        missing = set(COUNTRY_BRAVE_MAP.keys()) - countries
        issues.append(f"Countries {len(countries)}/{min_countries}, missing: {missing}")

    product_counts = {}
    for r in records:
        p = r["product"]
        product_counts[p] = product_counts.get(p, 0) + 1

    product_gates = {
        "TV": gates.get("min_tv", 80),
        "Refrigerator": gates.get("min_refrigerator", 80),
        "Washing Machine": gates.get("min_washing_machine", 80),
        "Monitor": gates.get("min_monitor", 40),
        "LG gram": gates.get("min_gram", 20),
    }

    for product, min_count in product_gates.items():
        actual = product_counts.get(product, 0)
        if actual < min_count:
            issues.append(f"{product}: {actual} < {min_count}")

    tv_count = product_counts.get("TV", 0)
    max_ratio = gates.get("max_tv_ratio", 0.45)
    if total > 0 and tv_count / total > max_ratio:
        issues.append(f"TV ratio {tv_count/total:.1%} > {max_ratio:.0%}")

    return len(issues) == 0, issues


# ──────────────────────────────────────────────────────────────
# Supplementary Collection (품질 미달 시 보강)
# ──────────────────────────────────────────────────────────────

def supplement_collection(
    collector: BraveSearchCollector,
    records: List[dict],
    config: dict,
    date_key: str,
) -> List[dict]:
    """품질 미달 항목에 대해 추가 수집을 수행합니다."""
    gates = config.get("quality_gates", {})
    collected_at = f"{date_key}T{datetime.now().strftime('%H:%M:%S')}+09:00"
    countries = config.get("countries", [])
    products_cfg = {p["name"]: p for p in config.get("products", [])}

    product_counts = {}
    for r in records:
        product_counts[r["product"]] = product_counts.get(r["product"], 0) + 1

    country_counts = {}
    for r in records:
        country_counts[r["country"]] = country_counts.get(r["country"], 0) + 1

    supplement = []

    # 제품별 미달 보강
    product_gates = {
        "TV": gates.get("min_tv", 80),
        "Refrigerator": gates.get("min_refrigerator", 80),
        "Washing Machine": gates.get("min_washing_machine", 80),
        "Monitor": gates.get("min_monitor", 40),
        "LG gram": gates.get("min_gram", 20),
    }

    for product, min_count in product_gates.items():
        actual = product_counts.get(product, 0)
        if actual < min_count:
            deficit = min_count - actual
            logger.info(f"Supplementing {product}: need {deficit} more records")
            pcfg = products_cfg.get(product)
            if not pcfg:
                continue

            for country_cfg in countries:
                if deficit <= 0:
                    break
                recs = collector.collect_product_queries(country_cfg, pcfg, collected_at)
                supplement.extend(recs)
                deficit -= len(recs)

    # 국가별 미달 보강 (최소 5건)
    for country_cfg in countries:
        cc = country_cfg["code"]
        if country_counts.get(cc, 0) < 5:
            logger.info(f"Supplementing country {cc}: low coverage")
            for pcfg in config.get("products", [])[:3]:  # TV, Refrigerator, Washing Machine
                recs = collector.collect_product_queries(country_cfg, pcfg, collected_at)
                supplement.extend(recs)

    return supplement


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    # Date key
    if len(sys.argv) > 1 and re.match(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
        date_key = sys.argv[1]
    else:
        date_key = date.today().isoformat()

    # API key
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        logger.error("BRAVE_API_KEY environment variable is not set")
        sys.exit(1)

    # Load config
    if not CONFIG_PATH.exists():
        logger.error(f"Config not found: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Prepare directories
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DATA_DIR / f"openclaw_{date_key}.jsonl"
    log_path = LOG_DIR / f"brave_search_{date_key}.log"

    # Add file handler
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(fh)

    logger.info(f"D2C Brave Search Collection — date={date_key}")
    logger.info(f"Output: {output_path}")

    # Collect
    collector = BraveSearchCollector(api_key, config)
    records = collector.collect_all(date_key)
    logger.info(f"Initial collection: {len(records)} records, {collector.total_api_calls} API calls")

    # Quality check
    passed, issues = check_quality(records, config)
    if not passed:
        logger.warning(f"Quality gate issues: {issues}")
        logger.info("Starting supplementary collection...")
        extra = supplement_collection(collector, records, config, date_key)
        records.extend(extra)
        logger.info(f"After supplement: {len(records)} records")

        passed2, issues2 = check_quality(records, config)
        if not passed2:
            logger.warning(f"Quality gate still not fully met: {issues2}")
            logger.warning("Proceeding with available data (soft gate)")

    # Deduplicate by URL
    seen = set()
    unique_records = []
    for r in records:
        url = r.get("source_url", "")
        if url not in seen:
            seen.add(url)
            unique_records.append(r)

    # Write JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for r in unique_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Summary
    product_summary = {}
    country_summary = {}
    for r in unique_records:
        product_summary[r["product"]] = product_summary.get(r["product"], 0) + 1
        country_summary[r["country"]] = country_summary.get(r["country"], 0) + 1

    logger.info(f"=== Collection Summary ===")
    logger.info(f"Total records: {len(unique_records)}")
    logger.info(f"Total API calls: {collector.total_api_calls}")
    logger.info(f"Countries: {len(country_summary)}")
    logger.info(f"Products: {product_summary}")
    logger.info(f"Countries detail: {dict(sorted(country_summary.items()))}")
    logger.info(f"Output: {output_path}")

    tv_count = product_summary.get("TV", 0)
    tv_ratio = tv_count / len(unique_records) * 100 if unique_records else 0
    logger.info(f"TV ratio: {tv_ratio:.1f}%")

    print(f"[d2c_search] {len(unique_records)} records → {output_path}")


if __name__ == "__main__":
    main()
