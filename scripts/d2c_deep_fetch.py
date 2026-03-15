#!/usr/bin/env python3
"""
D2C Intel — Deep Fetch Enrichment Module (v1.0)
================================================
Brave Search로 수집된 고가치 URL을 Scrapling으로 2차 스크래핑하여
가격, 스펙, 리뷰, 커뮤니티 토론 등 구조화 데이터를 추출합니다.

Architecture:
    Round 1-8 (d2c_search.py) → JSONL → Deep Fetch (this module) → Enriched JSONL

Usage:
    python scripts/d2c_deep_fetch.py [YYYY-MM-DD]

Environment:
    ENABLE_DEEP_FETCH=1  — Enable deep fetching (default: 0)
    DEEP_FETCH_MAX=50    — Max URLs to deep-fetch per run (default: 50)
"""

import json
import logging
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("d2c_deep_fetch")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "raw"
LOG_DIR = ROOT_DIR / "logs"

# ──────────────────────────────────────────────────────────────
# Site-specific extraction configs
# ──────────────────────────────────────────────────────────────

# High-value domains worth deep-fetching, with CSS selectors
SITE_EXTRACTORS = {
    "rtings.com": {
        "type": "review",
        "selectors": {
            "rating": ".e-score_box .e-score_value, .overall-score .score-value",
            "pros": ".pros-list li, .pros li",
            "cons": ".cons-list li, .cons li",
            "verdict": ".bottom-line p, .review-conclusion",
        },
    },
    "cnet.com": {
        "type": "review",
        "selectors": {
            "rating": ".c-reviewCard_rating, [data-test='review-score']",
            "pros": ".c-reviewCard_pros li, .good li",
            "cons": ".c-reviewCard_cons li, .bad li",
            "verdict": ".c-reviewCard_verdict, .review-summary",
        },
    },
    "techradar.com": {
        "type": "review",
        "selectors": {
            "rating": ".chunk-review-verdict__rating, .review-rating",
            "pros": ".chunk-review-verdict__pros li, .review-pros li",
            "cons": ".chunk-review-verdict__cons li, .review-cons li",
            "verdict": ".chunk-review-verdict__text, .review-verdict",
        },
    },
    "tomsguide.com": {
        "type": "review",
        "selectors": {
            "rating": ".chunk-review-verdict__rating, .review-rating",
            "verdict": ".chunk-review-verdict__text, .review-verdict",
        },
    },
    "tomshw.it": {
        "type": "review",
        "selectors": {
            "rating": ".review-rating, .voto",
            "verdict": ".review-verdict, .verdetto",
        },
    },
    "amazon.com": {
        "type": "product",
        "selectors": {
            "price": "#priceblock_ourprice, .a-price .a-offscreen, #corePrice_feature_div .a-offscreen",
            "rating": "#acrPopover .a-icon-alt, [data-hook='rating-out-of-text']",
            "review_count": "#acrCustomerReviewText",
            "title": "#productTitle",
        },
    },
    "bestbuy.com": {
        "type": "product",
        "selectors": {
            "price": ".priceView-hero-price span, [data-testid='customer-price'] span",
            "rating": ".c-ratings-reviews-v4 .c-review-average",
            "review_count": ".c-ratings-reviews-v4 .c-total-reviews",
        },
    },
    "reddit.com": {
        "type": "community",
        "selectors": {
            "post_title": "h1, [data-testid='post-title']",
            "post_body": "[data-testid='post-content'] p, .RichTextJSON-root p",
            "comments": "._1qeIAgB0cPwnLhDF9XSiJM p, shreddit-comment p",
            "upvotes": "._1rZYMD_4xY3gRcSS3p8ODO, shreddit-post [score]",
        },
    },
    "pelando.com.br": {
        "type": "deal",
        "selectors": {
            "price": ".thread-price, .cept-tp",
            "original_price": ".thread-listPrice, .mute--text",
            "discount": ".thread-discount, .space--ml-1",
            "temperature": ".vote-temp, .cept-vote-temp",
        },
    },
    "ozbargain.com.au": {
        "type": "deal",
        "selectors": {
            "price": ".dollar-sign + span",
            "title": ".node-title a",
            "votes": ".voteup .votecount",
        },
    },
    "slickdeals.net": {
        "type": "deal",
        "selectors": {
            "price": ".dealPrice, .bp-p-dealCard_price",
            "original_price": ".originalPrice",
            "thumbs_up": ".ratingNum",
        },
    },
    "sikayetvar.com": {
        "type": "community",
        "selectors": {
            "complaint_title": ".complaint-title h1",
            "complaint_body": ".complaint-detail-description",
            "brand_response": ".brand-response-text",
            "status": ".complaint-status",
        },
    },
    "pantip.com": {
        "type": "community",
        "selectors": {
            "post_title": "h1.display-post-title",
            "post_body": ".display-post-story p",
            "comments": ".display-comment-story p",
        },
    },
    "mydealz.de": {
        "type": "deal",
        "selectors": {
            "price": ".thread-price, .threadItemCard-price",
            "original_price": ".mute--text .cept-strike-price",
            "temperature": ".vote-temp, .cept-vote-temp",
        },
    },
    "hotukdeals.com": {
        "type": "deal",
        "selectors": {
            "price": ".thread-price, .threadItemCard-price",
            "temperature": ".vote-temp, .cept-vote-temp",
        },
    },
}

# Domains that need Stealthy/Dynamic fetcher (anti-bot protection)
STEALTH_DOMAINS = {"amazon.com", "bestbuy.com", "walmart.com", "reddit.com"}
DYNAMIC_DOMAINS = set()  # JS-heavy sites needing full browser


def _domain_match(url: str) -> Optional[str]:
    """URL에서 SITE_EXTRACTORS 매칭 도메인을 찾습니다."""
    netloc = urlparse(url).netloc.lower().replace("www.", "")
    for domain in SITE_EXTRACTORS:
        if domain in netloc:
            return domain
    return None


def _needs_stealth(domain: str) -> bool:
    return any(sd in domain for sd in STEALTH_DOMAINS)


def _needs_dynamic(domain: str) -> bool:
    return any(dd in domain for dd in DYNAMIC_DOMAINS)


def _select_fetcher(domain: str):
    """도메인에 맞는 Scrapling fetcher를 선택합니다."""
    try:
        if _needs_dynamic(domain):
            from scrapling import PlaywrightFetcher
            return PlaywrightFetcher(headless=True)
        elif _needs_stealth(domain):
            from scrapling import StealthyFetcher
            return StealthyFetcher(headless=True)
        else:
            from scrapling import Fetcher
            return Fetcher()
    except ImportError:
        return None


def _extract_text(page, selector: str, limit: int = 5) -> List[str]:
    """CSS 셀렉터로 텍스트 추출 (여러 셀렉터 쉼표 구분 지원)."""
    results = []
    for sel in selector.split(","):
        sel = sel.strip()
        try:
            elements = page.css(sel)
            for el in elements[:limit]:
                text = el.text.strip() if hasattr(el, 'text') else str(el).strip()
                if text and len(text) > 2:
                    results.append(text)
        except Exception:
            continue
    return results


def deep_fetch_url(url: str, domain_key: str) -> Dict[str, Any]:
    """단일 URL을 deep fetch하여 구조화 데이터를 추출합니다."""
    config = SITE_EXTRACTORS[domain_key]
    selectors = config["selectors"]
    site_type = config["type"]

    fetcher = _select_fetcher(domain_key)
    if fetcher is None:
        logger.warning(f"Scrapling not available, skipping deep fetch for {url}")
        return {}

    try:
        page = fetcher.get(url, timeout=15)
        if page is None or page.status != 200:
            logger.warning(f"Failed to fetch {url}: status={getattr(page, 'status', 'N/A')}")
            return {}
    except Exception as e:
        logger.warning(f"Deep fetch error for {url}: {e}")
        return {}

    enriched = {"deep_fetch_type": site_type, "deep_fetch_source": domain_key}

    for field, selector in selectors.items():
        texts = _extract_text(page, selector)
        if texts:
            if field in ("rating", "price", "original_price", "discount",
                         "temperature", "upvotes", "votes", "thumbs_up",
                         "review_count", "status"):
                enriched[f"deep_{field}"] = texts[0]
            elif field in ("pros", "cons", "comments"):
                enriched[f"deep_{field}"] = texts[:10]
            elif field in ("verdict", "post_body", "complaint_body",
                           "brand_response", "post_title", "complaint_title", "title"):
                enriched[f"deep_{field}"] = " ".join(texts[:3])[:1000]
            else:
                enriched[f"deep_{field}"] = texts[0] if len(texts) == 1 else texts[:5]

    return enriched


def prioritize_urls(records: List[dict], max_urls: int = 50) -> List[Tuple[int, str, str]]:
    """Deep fetch 우선순위에 따라 URL을 선택합니다.

    Returns:
        List of (record_index, url, domain_key) tuples.
    """
    candidates = []
    for idx, r in enumerate(records):
        url = r.get("source_url", "")
        domain_key = _domain_match(url)
        if not domain_key:
            continue

        # Priority scoring
        score = 0
        site_type = SITE_EXTRACTORS[domain_key]["type"]
        confidence = r.get("confidence", "medium")

        # Review sites: highest priority (deepest enrichment potential)
        if site_type == "review":
            score += 10
        # Deal sites: high priority (price + discount details)
        elif site_type == "deal":
            score += 8
        # Product pages: high priority (specs + price)
        elif site_type == "product":
            score += 7
        # Community: medium priority
        elif site_type == "community":
            score += 6

        # High-trust sources get priority
        if confidence == "high":
            score += 3

        # Records missing price data get priority
        if not r.get("price_value"):
            score += 2

        candidates.append((score, idx, url, domain_key))

    # Sort by priority (descending), take top N
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [(idx, url, dk) for _, idx, url, dk in candidates[:max_urls]]


def enrich_records(records: List[dict], max_urls: int = 50,
                   rate_delay: float = 1.5) -> Tuple[List[dict], dict]:
    """수집된 레코드를 deep fetch로 보강합니다.

    Args:
        records: 기존 JSONL 레코드 리스트
        max_urls: 최대 deep fetch URL 수
        rate_delay: 요청 간 딜레이 (초)

    Returns:
        (enriched_records, stats) tuple
    """
    targets = prioritize_urls(records, max_urls)
    stats = {
        "total_targets": len(targets),
        "fetched": 0,
        "enriched": 0,
        "failed": 0,
        "by_type": {},
    }

    if not targets:
        logger.info("No high-value URLs found for deep fetching")
        return records, stats

    logger.info(f"Deep fetching {len(targets)} high-value URLs...")

    for i, (idx, url, domain_key) in enumerate(targets):
        try:
            time.sleep(rate_delay)
            logger.info(f"  [{i+1}/{len(targets)}] {domain_key}: {url[:80]}...")

            enriched_data = deep_fetch_url(url, domain_key)
            stats["fetched"] += 1

            if enriched_data:
                # Merge enriched data into the record
                records[idx].update(enriched_data)
                stats["enriched"] += 1

                site_type = enriched_data.get("deep_fetch_type", "unknown")
                stats["by_type"][site_type] = stats["by_type"].get(site_type, 0) + 1

                # Override shallow fields with deep data if available
                if "deep_rating" in enriched_data and not records[idx].get("rating"):
                    records[idx]["rating"] = enriched_data["deep_rating"]
                if "deep_price" in enriched_data and not records[idx].get("price_value"):
                    records[idx]["price_value"] = enriched_data["deep_price"]
                if "deep_discount" in enriched_data and not records[idx].get("discount"):
                    records[idx]["discount"] = enriched_data["deep_discount"]
            else:
                stats["failed"] += 1

        except Exception as e:
            logger.error(f"Deep fetch failed for {url}: {e}")
            stats["failed"] += 1

    logger.info(
        f"Deep fetch complete: {stats['enriched']}/{stats['fetched']} enriched, "
        f"{stats['failed']} failed. Types: {stats['by_type']}"
    )
    return records, stats


# ──────────────────────────────────────────────────────────────
# Standalone CLI
# ──────────────────────────────────────────────────────────────

def main():
    """기존 JSONL 파일에 deep fetch enrichment를 적용합니다."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if len(sys.argv) > 1 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
        date_key = sys.argv[1]
    else:
        date_key = date.today().isoformat()

    enabled = os.environ.get("ENABLE_DEEP_FETCH", "0") == "1"
    if not enabled:
        logger.info("Deep fetch disabled (set ENABLE_DEEP_FETCH=1 to enable)")
        return

    max_urls = int(os.environ.get("DEEP_FETCH_MAX", "50"))

    input_path = DATA_DIR / f"openclaw_{date_key}.jsonl"
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # Load records
    with open(input_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    logger.info(f"Loaded {len(records)} records from {input_path}")

    # Enrich
    records, stats = enrich_records(records, max_urls=max_urls)

    # Write enriched JSONL (overwrite)
    with open(input_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logger.info(f"Enriched JSONL written to {input_path}")

    # Save deep fetch stats
    stats_path = ROOT_DIR / "data" / "weekly_stats" / f"{date_key}_deep_fetch.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"[deep_fetch] {stats['enriched']}/{stats['total_targets']} URLs enriched → {input_path}")


if __name__ == "__main__":
    main()
