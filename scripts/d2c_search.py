#!/usr/bin/env python3
"""
D2C Intel — Brave Search Data Collector (v2.0)
================================================
Brave Search API를 사용하여 17개국 × 5제품 × 4필라 데이터를 수집하고
OpenClaw JSONL 호환 포맷으로 출력합니다.

v2.0: 터키(TR) 추가, 커뮤니티/포럼 전용 검색(Round 7),
      경쟁사 동향 검색(Round 8), 강화된 signal_type 분류

Usage:
    python scripts/d2c_search.py [YYYY-MM-DD]

Output:
    data/raw/openclaw_YYYY-MM-DD.jsonl

Environment:
    BRAVE_API_KEY  — Brave Search API key (required)
"""

import hashlib
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
DDG_SEARCH_URL = "https://api.duckduckgo.com/"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"

# ──────────────────────────────────────────────────────────────
# Brave Search API
# ──────────────────────────────────────────────────────────────

COUNTRY_BRAVE_MAP = {
    "US": "us", "CA": "ca", "UK": "gb", "DE": "de", "FR": "fr",
    "ES": "es", "IT": "it", "BR": "br", "MX": "mx", "CL": "cl",
    "TH": "th", "AU": "au", "TW": "tw", "SG": "sg", "EG": "eg",
    "SA": "sa", "TR": "tr",
}

# Brave API가 지원하지 않는 국가 → 인접/유사 지역으로 fallback
COUNTRY_FALLBACK_MAP = {
    "th": "us",   # Thailand → US (+ loc:th로 지역 타게팅)
    "sg": "us",   # Singapore → US (+ loc:sg로 지역 타게팅)
    "eg": "us",   # Egypt → US (+ loc:eg로 지역 타게팅)
    "sa": "ae",   # Saudi Arabia → UAE
    "cl": "mx",   # Chile → Mexico (같은 스페인어권)
    "tr": "de",   # Turkey → Germany (fallback, 터키 미지원 시)
}

# 미지원 국가의 쿼리를 영어로 대체
COUNTRY_FORCE_ENGLISH = {"th", "sg", "eg"}

# loc: 연산자로 지역 타게팅 (country 파라미터 미지원 국가용)
COUNTRY_LOC_OPERATOR = {"th", "sg", "eg"}

# 422 에러가 발생한 국가 코드를 기억하여 반복 실패 방지
_unsupported_countries: set = set()

PILLAR_MAP = {
    "consumer_sentiment": "Consumer Sentiment",
    "retail_channel_promotion": "Retail Channel Promotions",
    "price_intelligence": "Competitive Price & Positioning",
    "chinese_brand_threat": "Chinese Brand Threat Tracking",
    "market_signal": "Market Signal",
}

CHINESE_BRANDS = {"tcl", "hisense", "haier", "midea"}

# Pre-compiled keyword sets for pillar classification (performance optimization)
_PROMO_KW = frozenset({
    "deal", "promotion", "discount", "sale", "coupon", "offer", "clearance",
    "promo", "offerta", "oferta", "angebot", "promoção", "โปรโมชั่น",
    "優惠", "折扣", "soldes", "rabatt", "sconto", "indirim", "kampanya",
    "fırsat", "promosyon", "ลดราคา", "特價",
})
_PRICE_KW = frozenset({
    "price", "vs", "comparison", "pricing", "worth buying",
    "preis", "prix", "precio", "prezzo", "preço",
    "ราคา", "價格", "比較", "fiyat", "karşılaştırma",
    "คุ้มค่า", "值得買", "değer",
})
_SENTIMENT_KW = frozenset({
    "review", "complaint", "problem", "issue", "experience",
    "broken", "regret", "worst", "refund", "고장",
    "bewertung", "avis", "reseña", "recensione", "avaliação",
    "รีวิว", "評價", "yorum", "şikayet", "sorun",
    "after service", "customer service", "forum", "reddit",
    "pantip", "ptt", "mobile01", "community",
    "ปัญหา", "ประสบการณ์", "問題", "müşteri",
})
# Dedicated complaint/A/S keywords for finer signal_type detection
_COMPLAINT_KW = frozenset({
    "complaint", "problem", "issue", "broken", "refund", "defect",
    "recall", "error code", "noise", "leak", "repair", "service center",
    "beschwerde", "reklamation", "plainte", "queja", "reclamação",
    "şikayet", "sorun", "arıza", "ปัญหา", "ศูนย์บริการ",
})
# Competitor move keywords
_COMPETITOR_MOVE_KW = frozenset({
    "launch", "new model", "new product", "market share", "strategy",
    "expansion", "partnership", "acquired", "patent",
    "neuheit", "nouveauté", "novedad", "novità",
    "เปิดตัว", "新品", "pazar payı", "yeni ürün",
})


# Discount percentage extraction patterns
_DISCOUNT_PATTERNS = [
    # "53% off", "50% discount", "save 30%"
    re.compile(r'(\d{1,2})%\s?(?:off|discount|rabatt|de\s?réduction|descuento|sconto|indirim)', re.IGNORECASE),
    # "save $200" / "saving of $97"
    re.compile(r'sav(?:e|ing)[^$€£]*(?:[\$€£])(\d[\d,]*)', re.IGNORECASE),
    # "50% off" at end or standalone
    re.compile(r'(\d{1,2})%\s?off\b', re.IGNORECASE),
    # "up to 53% off"
    re.compile(r'up\s+to\s+(\d{1,2})%', re.IGNORECASE),
    # "-30%", "–25%"
    re.compile(r'[-–](\d{1,2})%', re.IGNORECASE),
]

# Star rating / review score extraction patterns
_RATING_PATTERNS = [
    # "4.5/5", "4.5 out of 5", "4.5 stars"
    re.compile(r'(\d(?:\.\d)?)\s?(?:/\s?5|out of 5|stars?\b|⭐)', re.IGNORECASE),
    # "rated 8.5/10", "score: 9/10", "8/10"
    re.compile(r'(?:rated?|score|rating)[:\s]*(\d(?:\.\d)?)\s?/\s?10', re.IGNORECASE),
    re.compile(r'\b(\d(?:\.\d)?)\s?/\s?10\b'),
    # "92%", "85/100" review scores
    re.compile(r'(?:score|rating)[:\s]*(\d{2,3})\s?(?:%|/\s?100)', re.IGNORECASE),
]

# Price extraction patterns: currency symbol/code + numeric value
_PRICE_PATTERNS = [
    # $1,234.56 / USD 1,234.56
    re.compile(r'(?:USD|\$)\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE),
    # €1.234,56 / EUR 1.234,56
    re.compile(r'(?:EUR|€)\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', re.IGNORECASE),
    # £1,234.56 / GBP 1,234.56
    re.compile(r'(?:GBP|£)\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE),
    # R$1.234,56 / BRL 1.234,56
    re.compile(r'(?:BRL|R\$)\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', re.IGNORECASE),
    # ₩1,234,567 / KRW
    re.compile(r'(?:KRW|₩)\s?(\d{1,3}(?:,\d{3})*)', re.IGNORECASE),
    # ¥12,345 / JPY / CNY
    re.compile(r'(?:JPY|CNY|¥)\s?(\d{1,3}(?:,\d{3})*)', re.IGNORECASE),
    # ฿12,345 / THB
    re.compile(r'(?:THB|฿)\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE),
    # SAR / AED / EGP + number
    re.compile(r'(?:SAR|AED|EGP|TRY|MXN|CLP|TWD|SGD|AUD|CAD)\s?(\d{1,3}(?:[,.]?\d{3})*(?:[.,]\d{2})?)', re.IGNORECASE),
    # NT$ (Taiwan)
    re.compile(r'NT\$\s?(\d{1,3}(?:,\d{3})*)', re.IGNORECASE),
    # ₺ (Turkish Lira)
    re.compile(r'(?:₺|TL)\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', re.IGNORECASE),
]

_CURRENCY_SYMBOL_MAP = {
    "$": "USD", "€": "EUR", "£": "GBP", "₩": "KRW", "¥": "JPY",
    "฿": "THB", "₺": "TRY", "R$": "BRL", "NT$": "TWD",
}

# Country → default currency
_COUNTRY_CURRENCY = {
    "US": "USD", "CA": "CAD", "UK": "GBP", "DE": "EUR", "FR": "EUR",
    "ES": "EUR", "IT": "EUR", "BR": "BRL", "MX": "MXN", "CL": "CLP",
    "TH": "THB", "AU": "AUD", "TW": "TWD", "SG": "SGD", "EG": "EGP",
    "SA": "SAR", "TR": "TRY",
}

# Freshness parameter by signal type
_SIGNAL_FRESHNESS = {
    "promo": "pd",           # promotions: past day (most time-sensitive)
    "price_discount": "pw",  # price: past week
    "pricing_comparison": "pm",  # comparisons: past month (evergreen)
    "competitive_move": "pw",    # competitor moves: past week
    "consumer_complaint": "pm",  # complaints: past month
    "community_reaction": "pw",  # community: past week
    "expert_review": "pm",       # reviews: past month
    "market_signal": "pw",       # general: past week
}


class BraveSearchCollector:
    """Brave Search API를 사용하여 D2C 데이터를 수집합니다."""

    def __init__(self, api_key: str, config: dict):
        self.api_key = api_key
        self.config = config
        self.search_params = config.get("search_params", {})
        self.rate_delay = self.search_params.get("rate_limit_delay_ms", 1100) / 1000
        self.max_retries = self.search_params.get("max_retries", 5)
        self.retry_delay = self.search_params.get("retry_delay_ms", 3000) / 1000
        self.count = self.search_params.get("count", 10)
        self.freshness = self.search_params.get("freshness", "pw")
        self.consecutive_429_abort = self.search_params.get("consecutive_429_abort", 10)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        })
        self.total_api_calls = 0
        self.total_results = 0
        self.seen_urls: set = set()
        self.consecutive_429_count = 0
        self.quota_exhausted = False

    def search(self, query: str, country: str = "us", count: int = 10,
               freshness: str = "") -> List[dict]:
        """Brave Search API 호출 (재시도 + 연속 429 감지 + 422 즉시 스킵 포함).

        Args:
            freshness: 검색 시간 범위. 비어있으면 인스턴스 기본값 사용.
                       "pd"=past day, "pw"=past week, "pm"=past month
        """
        if self.quota_exhausted:
            return []

        # 이미 422로 실패한 국가는 즉시 fallback
        if country in _unsupported_countries:
            fallback = COUNTRY_FALLBACK_MAP.get(country)
            if fallback and fallback not in _unsupported_countries:
                logger.info(f"Using fallback country {country}→{fallback} for query: '{query}'")
                country = fallback
            else:
                logger.debug(f"Skipping unsupported country {country}")
                return []

        params = {
            "q": query,
            "country": country,
            "count": count,
            "freshness": freshness or self.freshness,
            "text_decorations": "false",
            "safesearch": "moderate",
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                time.sleep(self.rate_delay)
                resp = self.session.get(BRAVE_SEARCH_URL, params=params, timeout=15)
                self.total_api_calls += 1

                if resp.status_code == 422:
                    # 422: 국가 코드 미지원 등 영구적 에러 → 재시도 무의미
                    _unsupported_countries.add(country)
                    logger.warning(
                        f"422 Unprocessable Entity for country={country}. "
                        f"Marked as unsupported. Trying fallback..."
                    )
                    fallback = COUNTRY_FALLBACK_MAP.get(country)
                    if fallback and fallback not in _unsupported_countries:
                        logger.info(f"Retrying with fallback country: {country}→{fallback}")
                        params["country"] = fallback
                        time.sleep(self.rate_delay)
                        resp = self.session.get(BRAVE_SEARCH_URL, params=params, timeout=15)
                        self.total_api_calls += 1
                        if resp.status_code == 422:
                            _unsupported_countries.add(fallback)
                            logger.warning(f"Fallback {fallback} also unsupported")
                            return []
                        elif resp.status_code == 429:
                            pass  # 429 처리 아래에서
                        else:
                            resp.raise_for_status()
                            data = resp.json()
                            return data.get("web", {}).get("results", [])
                    else:
                        return []

                if resp.status_code == 429:
                    self.consecutive_429_count += 1
                    if self.consecutive_429_count >= self.consecutive_429_abort:
                        logger.error(
                            f"QUOTA EXHAUSTED: {self.consecutive_429_count} consecutive 429 errors. "
                            f"Monthly API quota likely depleted. Aborting collection."
                        )
                        self.quota_exhausted = True
                        return []
                    wait = self.retry_delay * attempt
                    logger.warning(
                        f"Rate limited (429). Waiting {wait:.1f}s... "
                        f"[{attempt}/{self.max_retries}] "
                        f"(consecutive 429: {self.consecutive_429_count}/{self.consecutive_429_abort})"
                    )
                    time.sleep(wait)
                    continue

                # 성공 시 연속 429 카운터 리셋
                self.consecutive_429_count = 0
                resp.raise_for_status()
                data = resp.json()
                results = data.get("web", {}).get("results", [])
                return results

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout for query '{query}' [{attempt}/{self.max_retries}]")
                time.sleep(self.retry_delay)
            except requests.exceptions.RequestException as e:
                if "422" in str(e):
                    # raise_for_status에서 발생한 422
                    _unsupported_countries.add(country)
                    logger.warning(f"422 error caught for country={country}, marked unsupported")
                    return []
                logger.error(f"Request error for query '{query}': {e} [{attempt}/{self.max_retries}]")
                time.sleep(self.retry_delay)

        logger.error(f"All retries failed for query: '{query}'")
        return []

    def classify_pillar(self, title: str, snippet: str, query: str) -> str:
        """검색 결과의 pillar를 가중치 점수로 분류합니다.

        기존의 순서 의존적 first-match 대신, 각 pillar의 키워드 매칭 횟수를
        가중치로 합산하여 가장 높은 점수의 pillar를 반환합니다.
        title 매칭은 2배 가중치를 부여합니다.
        """
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        query_lower = query.lower()
        text = f"{title_lower} {snippet_lower} {query_lower}"

        # Chinese brand는 명시적 브랜드명 매칭이므로 우선 처리
        if any(brand in text for brand in CHINESE_BRANDS):
            return "chinese_brand_threat"

        scores = {
            "retail_channel_promotion": 0,
            "price_intelligence": 0,
            "consumer_sentiment": 0,
        }

        for kw in _PROMO_KW:
            if kw in title_lower:
                scores["retail_channel_promotion"] += 2
            if kw in snippet_lower or kw in query_lower:
                scores["retail_channel_promotion"] += 1

        for kw in _PRICE_KW:
            if kw in title_lower:
                scores["price_intelligence"] += 2
            if kw in snippet_lower or kw in query_lower:
                scores["price_intelligence"] += 1

        for kw in _SENTIMENT_KW:
            if kw in title_lower:
                scores["consumer_sentiment"] += 2
            if kw in snippet_lower or kw in query_lower:
                scores["consumer_sentiment"] += 1

        max_score = max(scores.values())
        if max_score == 0:
            return "market_signal"

        # 가장 높은 점수의 pillar 반환
        return max(scores, key=scores.get)

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
        for kw, brand in brand_map.items():
            if kw in text:
                return brand
        return "Unknown"

    def extract_price(self, text: str, country: str = "") -> Tuple[str, str]:
        """검색 결과 텍스트에서 가격과 통화를 추출합니다.

        Returns:
            (currency, price_value) tuple. 추출 실패 시 ("", "").
        """
        for pattern in _PRICE_PATTERNS:
            m = pattern.search(text)
            if m:
                price_str = m.group(1)
                # Determine currency from the match
                full_match = m.group(0).upper().strip()
                currency = ""
                for sym, cur in _CURRENCY_SYMBOL_MAP.items():
                    if sym in full_match or sym.upper() in full_match:
                        currency = cur
                        break
                if not currency:
                    # Try explicit currency codes in the match
                    for code in ["USD", "EUR", "GBP", "BRL", "KRW", "JPY", "CNY",
                                 "THB", "SAR", "AED", "EGP", "TRY", "MXN", "CLP",
                                 "TWD", "SGD", "AUD", "CAD"]:
                        if code in full_match:
                            currency = code
                            break
                if not currency and country:
                    currency = _COUNTRY_CURRENCY.get(country, "")
                return currency, price_str
        return "", ""

    def extract_discount(self, text: str) -> str:
        """텍스트에서 할인율을 추출합니다. 예: '53% off' → '53%'"""
        for pattern in _DISCOUNT_PATTERNS:
            m = pattern.search(text)
            if m:
                val = m.group(1)
                # If it's a dollar amount saved, return as-is with $
                if "$" in m.group(0) or "€" in m.group(0) or "£" in m.group(0):
                    return m.group(0).strip()
                return f"{val}%"
        return ""

    def extract_rating(self, text: str) -> str:
        """텍스트에서 별점/리뷰 점수를 추출합니다. 예: '4.5/5' → '4.5/5'"""
        for pattern in _RATING_PATTERNS:
            m = pattern.search(text)
            if m:
                val = m.group(1)
                full = m.group(0).strip()
                # Normalize: "4.5 stars" → "4.5/5", "8/10" → "8/10"
                if "10" in full:
                    return f"{val}/10"
                if "100" in full or "%" in full:
                    return f"{val}%"
                return f"{val}/5"
        return ""

    def detect_confidence(self, result: dict) -> str:
        """검색 결과의 신뢰도를 평가합니다."""
        url = result.get("url", "")
        domain = urlparse(url).netloc.lower()

        high_trust = {"reddit.com", "amazon.com", "bestbuy.com", "cnet.com",
                      "rtings.com", "techradar.com", "tomsguide.com",
                      "slickdeals.net", "mydealz.de", "hotukdeals.com",
                      "ozbargain.com.au", "pelando.com.br", "dealabs.com",
                      "pantip.com", "ptt.cc", "mobile01.com", "hardwarezone.com.sg",
                      "sikayetvar.com", "donanimhaber.com", "redflagdeals.com",
                      "whirlpool.net.au", "computerbase.de", "tomshw.it",
                      "promodescuentos.com", "hardmob.com.br"}
        medium_trust = {"youtube.com", "twitter.com", "x.com", "facebook.com",
                        "dcard.tw", "forocoches.com", "mediavida.com"}

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

        # Extract structured data from title + snippet
        price_text = f"{title} {snippet}"
        currency, price_value = self.extract_price(price_text, country)
        discount = self.extract_discount(price_text)
        rating = self.extract_rating(price_text)

        record = {
            "country": country,
            "product": product,
            "pillar": PILLAR_MAP.get(classified_pillar, classified_pillar),
            "brand": brand,
            "signal_type": self._infer_signal_type(classified_pillar, title, snippet),
            "value": title,
            "currency": currency,
            "price_value": price_value,
            "discount": discount,
            "rating": rating,
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
            if "vs" in text or "comparison" in text or "karşılaştırma" in text:
                return "pricing_comparison"
            return "price_discount"
        if pillar == "chinese_brand_threat":
            return "competitive_move"
        # More granular consumer sentiment classification
        if any(kw in text for kw in _COMPLAINT_KW):
            return "consumer_complaint"
        if any(kw in text for kw in _COMPETITOR_MOVE_KW):
            return "competitive_move"
        if any(kw in text for kw in ["reddit", "forum", "pantip", "ptt", "community", "dcard", "mobile01"]):
            return "community_reaction"
        if any(kw in text for kw in ["review", "rating", "star", "test", "bewertung", "avis", "yorum"]):
            return "expert_review"
        return "market_signal"

    def collect_product_queries(
        self, country_cfg: dict, product_cfg: dict,
        collected_at: str, max_queries: int = 0
    ) -> List[dict]:
        """특정 국가 × 제품 조합에 대해 검색을 수행합니다."""
        records = []
        country = country_cfg["code"]
        brave_country = COUNTRY_BRAVE_MAP.get(country, country.lower())
        lang = country_cfg.get("lang", "en")
        tier = country_cfg.get("tier", 3)
        product = product_cfg["name"]
        queries = product_cfg.get("queries", {})

        # 미지원 국가는 영어 쿼리로 강제 전환 + fallback 국가 사용 + loc: 연산자
        original_brave_country = brave_country
        use_loc = False
        if brave_country in COUNTRY_FORCE_ENGLISH or brave_country in _unsupported_countries:
            lang_queries = queries.get("en", [])
            fallback = COUNTRY_FALLBACK_MAP.get(brave_country, "us")
            if fallback not in _unsupported_countries:
                brave_country = fallback
            else:
                brave_country = "us"
            # loc: 연산자로 원래 국가의 웹페이지를 우선 반환
            if original_brave_country in COUNTRY_LOC_OPERATOR:
                use_loc = True
                logger.info(
                    f"  → {country}: English queries via country={brave_country} "
                    f"+ loc:{original_brave_country} (location targeting)"
                )
            else:
                logger.info(f"  → {country}: using English queries via country={brave_country}")
        else:
            # 해당 언어의 쿼리 선택 (없으면 en fallback)
            lang_queries = queries.get(lang, queries.get("en", []))

        # Tier별 쿼리 수 제한 (max_queries 가 지정되면 그 값 사용)
        if max_queries > 0:
            limit = max_queries
        elif tier == 1:
            limit = min(len(lang_queries), 4)
        elif tier == 2:
            limit = min(len(lang_queries), 3)
        else:
            limit = min(len(lang_queries), 2)

        for query in lang_queries[:limit]:
            # loc: 연산자 추가 — 미지원 국가도 지역 타게팅 유지
            search_query = f"{query} loc:{original_brave_country}" if use_loc else query
            results = self.search(search_query, country=brave_country, count=self.count)
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

        # 미지원 국가는 영어 패턴 + fallback 국가 + loc: 연산자
        original_brave_country = brave_country
        use_loc = False
        if brave_country in COUNTRY_FORCE_ENGLISH or brave_country in _unsupported_countries:
            lang_patterns = patterns.get("en", [])
            if original_brave_country in COUNTRY_LOC_OPERATOR:
                use_loc = True
            brave_country = COUNTRY_FALLBACK_MAP.get(brave_country, "us")
        else:
            lang_patterns = patterns.get(lang, patterns.get("en", []))

        # 중국 브랜드 - TV: TCL/Hisense, 가전: Haier/Midea
        relevant_brands = []
        if product == "TV":
            relevant_brands = [b for b in brands if b.lower() in ("tcl", "hisense")]
        elif product in ("Refrigerator", "Washing Machine"):
            relevant_brands = [b for b in brands if b.lower() in ("haier", "midea")]
        else:
            return records  # Monitor/gram은 중국 브랜드 검색 생략

        # 패턴 1개만 사용하여 API 호출 최소화
        for brand in relevant_brands:
            pattern = lang_patterns[0] if lang_patterns else "{brand} {product} price"
            query = pattern.replace("{brand}", brand).replace("{product}", product)
            search_query = f"{query} loc:{original_brave_country}" if use_loc else query
            results = self.search(search_query, country=brave_country, count=5)
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
        total_steps = len(products) * len(countries)
        step = 0

        # ── Round 1-5: 제품별 × 국가별 검색 ──
        for product_cfg in products:
            if self.quota_exhausted:
                logger.warning("Quota exhausted — skipping remaining products")
                break
            product_name = product_cfg["name"]
            logger.info(f"=== Collecting: {product_name} ===")

            for country_cfg in countries:
                step += 1
                if self.quota_exhausted:
                    logger.warning("Quota exhausted — skipping remaining queries")
                    break
                country = country_cfg["code"]
                records = self.collect_product_queries(country_cfg, product_cfg, collected_at)
                all_records.extend(records)
                logger.info(
                    f"  [{step}/{total_steps}] {country} ({product_name}): "
                    f"{len(records)} records (total: {len(all_records)}, "
                    f"API calls: {self.total_api_calls})"
                )

        logger.info(f"Product rounds complete: {len(all_records)} records, {self.total_api_calls} API calls")

        if self.quota_exhausted:
            logger.warning("Quota exhausted — skipping Chinese brand round")
            return all_records

        # ── Round 6: 중국 브랜드 전용 검색 (Tier 1+2만) ──
        if chinese_pillar:
            logger.info("=== Collecting: Chinese Brand Threat (Tier 1+2 countries) ===")
            tier12_countries = [c for c in countries if c.get("tier", 3) <= 2]
            for country_cfg in tier12_countries:
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

        logger.info(f"Rounds 1-6 complete: {len(all_records)} records, {self.total_api_calls} API calls")

        if self.quota_exhausted:
            logger.warning("Quota exhausted — skipping community and competitor rounds")
            return all_records

        # ── Round 7: 커뮤니티/포럼 반응 전용 검색 ──
        community_queries = self.config.get("community_queries", {})
        if community_queries:
            logger.info("=== Collecting: Community/Forum Reactions (Round 7) ===")
            community_sites = self.config.get("country_community_sites", {})
            for country_cfg in countries:
                if self.quota_exhausted:
                    break
                country = country_cfg["code"]
                lang = country_cfg.get("lang", "en")
                brave_country = COUNTRY_BRAVE_MAP.get(country, country.lower())
                original_brave_country = brave_country
                use_loc = False

                # Fallback logic for unsupported countries
                if brave_country in COUNTRY_FORCE_ENGLISH or brave_country in _unsupported_countries:
                    lang_queries = community_queries.get("en", [])
                    fallback = COUNTRY_FALLBACK_MAP.get(brave_country, "us")
                    if fallback not in _unsupported_countries:
                        brave_country = fallback
                    else:
                        brave_country = "us"
                    if original_brave_country in COUNTRY_LOC_OPERATOR:
                        use_loc = True
                else:
                    lang_queries = community_queries.get(lang, community_queries.get("en", []))

                # Use country-specific community sites with site: operator
                sites = community_sites.get(country, [])
                site_queries = []
                for q in lang_queries[:2]:
                    if sites:
                        # Add site-specific query for the first community site
                        site_queries.append(f"{q} site:{sites[0]}")
                    site_queries.append(q)

                for query in site_queries[:3]:  # Max 3 queries per country
                    search_query = f"{query} loc:{original_brave_country}" if use_loc else query
                    results = self.search(search_query, country=brave_country, count=self.count,
                                          freshness="pw")
                    for r in results:
                        rec = self.build_record(r, country, "TV", "auto", query, collected_at)
                        if rec:
                            # Detect product from content
                            text_lower = f"{rec['value']} {rec['quote_original']}".lower()
                            for prod in ["refrigerator", "fridge", "냉장고", "kühlschrank", "ตู้เย็น", "buzdolabı"]:
                                if prod in text_lower:
                                    rec["product"] = "Refrigerator"
                                    break
                            for prod in ["washing machine", "washer", "세탁기", "waschmaschine", "เครื่องซักผ้า", "çamaşır"]:
                                if prod in text_lower:
                                    rec["product"] = "Washing Machine"
                                    break
                            for prod in ["monitor", "모니터", "มอนิเตอร์"]:
                                if prod in text_lower:
                                    rec["product"] = "Monitor"
                                    break
                            for prod in ["gram", "laptop", "notebook"]:
                                if prod in text_lower:
                                    rec["product"] = "LG gram"
                                    break
                            all_records.append(rec)

                if site_queries:
                    comm_count = sum(1 for r in all_records if r.get("country") == country and r.get("signal_type") in ("community_reaction", "consumer_complaint", "expert_review"))
                    logger.info(f"  {country} community: {comm_count} sentiment/community records")

            logger.info(f"Round 7 complete: {len(all_records)} total records")

        if self.quota_exhausted:
            logger.warning("Quota exhausted — skipping competitor round")
            return all_records

        # ── Round 8: 경쟁사 동향 전용 검색 (Tier 1+2 국가) ──
        competitor_queries = self.config.get("competitor_queries", {})
        if competitor_queries:
            logger.info("=== Collecting: Competitor Intelligence (Round 8) ===")
            tier12_countries = [c for c in countries if c.get("tier", 3) <= 2]
            for country_cfg in tier12_countries:
                if self.quota_exhausted:
                    break
                country = country_cfg["code"]
                lang = country_cfg.get("lang", "en")
                brave_country = COUNTRY_BRAVE_MAP.get(country, country.lower())
                original_brave_country = brave_country
                use_loc = False

                if brave_country in COUNTRY_FORCE_ENGLISH or brave_country in _unsupported_countries:
                    lang_queries = competitor_queries.get("en", [])
                    fallback = COUNTRY_FALLBACK_MAP.get(brave_country, "us")
                    brave_country = fallback if fallback not in _unsupported_countries else "us"
                    if original_brave_country in COUNTRY_LOC_OPERATOR:
                        use_loc = True
                else:
                    lang_queries = competitor_queries.get(lang, competitor_queries.get("en", []))

                for query in lang_queries[:2]:  # Max 2 competitor queries per country
                    search_query = f"{query} loc:{original_brave_country}" if use_loc else query
                    results = self.search(search_query, country=brave_country, count=self.count,
                                          freshness="pw")
                    for r in results:
                        rec = self.build_record(r, country, "TV", "auto", query, collected_at)
                        if rec:
                            # Detect product from content
                            text_lower = f"{rec['value']} {rec['quote_original']}".lower()
                            if any(kw in text_lower for kw in ["fridge", "refrigerator", "냉장고", "kühlschrank", "buzdolabı"]):
                                rec["product"] = "Refrigerator"
                            elif any(kw in text_lower for kw in ["washer", "washing", "세탁기", "waschmaschine", "çamaşır"]):
                                rec["product"] = "Washing Machine"
                            elif any(kw in text_lower for kw in ["monitor", "모니터"]):
                                rec["product"] = "Monitor"
                            all_records.append(rec)

                logger.info(f"  {country} competitor: done")

            logger.info(f"Round 8 complete: {len(all_records)} total records")

        logger.info(f"Rounds 1-8 complete: {len(all_records)} records, {self.total_api_calls} API calls")

        # ── Round 9: DuckDuckGo 보조 검색 (Brave 결과 보강) ──
        if os.environ.get("ENABLE_DDG_SUPPLEMENT", "1") == "1":
            ddg_records = self._collect_ddg_supplement(all_records, countries, products, collected_at)
            all_records.extend(ddg_records)
            if ddg_records:
                logger.info(f"Round 9 (DDG) complete: +{len(ddg_records)} records → {len(all_records)} total")

        logger.info(f"All rounds complete: {len(all_records)} records, {self.total_api_calls} API calls")
        return all_records

    def _search_ddg(self, query: str, max_results: int = 10) -> List[dict]:
        """DuckDuckGo 검색 (API 키 불필요, 속도 제한 관대).

        1차: DDG HTML 엔드포인트 (웹 검색 결과 직접 파싱)
        2차: DDG Instant Answer API (관련 주제에서 URL 추출)
        """
        results = []

        # ── Method 1: DDG HTML endpoint ──
        try:
            time.sleep(1.5)
            resp = requests.post(
                DDG_HTML_URL,
                data={"q": query, "b": ""},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://duckduckgo.com/",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=10,
                allow_redirects=True,
            )
            if resp.status_code == 200:
                html = resp.text
                # Multiple patterns for DDG HTML result parsing
                # Pattern 1: result__a links
                blocks = re.findall(
                    r'href="([^"]*)"[^>]*class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>',
                    html, re.DOTALL
                )
                if not blocks:
                    # Pattern 2: reverse attr order
                    blocks = re.findall(
                        r'class="[^"]*result__a[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                        html, re.DOTALL
                    )
                if not blocks:
                    # Pattern 3: any link with result class
                    blocks = re.findall(
                        r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                        html, re.DOTALL
                    )

                snippets = re.findall(
                    r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|td|div|span)',
                    html, re.DOTALL
                )

                for i, (url_raw, title_raw) in enumerate(blocks[:max_results]):
                    title = re.sub(r'<[^>]+>', '', title_raw).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                    url = url_raw
                    # Decode DDG redirect URLs
                    if "uddg=" in url:
                        m = re.search(r'uddg=([^&]+)', url)
                        if m:
                            from urllib.parse import unquote
                            url = unquote(m.group(1))
                    if title and url.startswith("http"):
                        results.append({
                            "url": url,
                            "title": title,
                            "description": snippet,
                        })

        except Exception as e:
            logger.debug(f"DDG HTML search failed for '{query}': {e}")

        # ── Method 2: DDG Instant Answer API (fallback) ──
        if not results:
            try:
                time.sleep(1.0)
                resp = requests.get(
                    DDG_SEARCH_URL,
                    params={"q": query, "format": "json", "no_redirect": "1", "no_html": "1"},
                    headers={"User-Agent": "D2C-Intel/2.0 (Market Intelligence)"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Extract from RelatedTopics
                    for topic in data.get("RelatedTopics", [])[:max_results]:
                        if isinstance(topic, dict) and "FirstURL" in topic:
                            results.append({
                                "url": topic["FirstURL"],
                                "title": topic.get("Text", "")[:200],
                                "description": topic.get("Text", "")[:500],
                            })
                    # Extract from Results
                    for r in data.get("Results", [])[:max_results]:
                        if isinstance(r, dict) and "FirstURL" in r:
                            results.append({
                                "url": r["FirstURL"],
                                "title": r.get("Text", "")[:200],
                                "description": r.get("Text", "")[:500],
                            })
            except Exception as e:
                logger.debug(f"DDG API search failed for '{query}': {e}")

        return results[:max_results]

    def _collect_ddg_supplement(
        self, existing_records: List[dict],
        countries: List[dict], products: List[dict],
        collected_at: str,
    ) -> List[dict]:
        """DuckDuckGo로 Brave Search 결과를 보강합니다.

        부족한 국가/제품 조합에 대해 DDG 검색을 수행하여 커버리지를 확대합니다.
        API 키 불필요, 월 호출 제한 없음.
        """
        logger.info("=== Collecting: DuckDuckGo Supplement (Round 9) ===")

        # Identify underrepresented country-product combos
        combo_counts = {}
        for r in existing_records:
            key = f"{r['country']}|{r['product']}"
            combo_counts[key] = combo_counts.get(key, 0) + 1

        ddg_records = []
        ddg_queries = 0
        max_ddg_queries = int(os.environ.get("DDG_MAX_QUERIES", "30"))

        for product_cfg in products:
            product_name = product_cfg["name"]
            for country_cfg in countries:
                if ddg_queries >= max_ddg_queries:
                    break
                country = country_cfg["code"]
                combo_key = f"{country}|{product_name}"

                # Only supplement combos with < 3 records
                if combo_counts.get(combo_key, 0) >= 3:
                    continue

                # Build query
                lang = country_cfg.get("lang", "en")
                queries = product_cfg.get("queries", {})
                lang_queries = queries.get(lang, queries.get("en", []))
                if not lang_queries:
                    continue

                query = lang_queries[0]  # Use first query
                results = self._search_ddg(query, max_results=5)
                ddg_queries += 1

                for r in results:
                    rec = self.build_record(r, country, product_name, "auto", query, collected_at)
                    if rec:
                        rec["search_engine"] = "duckduckgo"
                        ddg_records.append(rec)

                if results:
                    logger.info(f"  {country} ({product_name}): +{len(results)} DDG results")

            if ddg_queries >= max_ddg_queries:
                break

        logger.info(f"DDG supplement: {ddg_queries} queries, {len(ddg_records)} new records")
        return ddg_records


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
    max_extra_calls: int = 30,
) -> List[dict]:
    """품질 미달 항목에 대해 추가 수집을 수행합니다 (API 호출 제한 포함)."""
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
    calls_before = collector.total_api_calls

    # 제품별 미달 보강 (Tier 1 국가만 대상)
    product_gates = {
        "TV": gates.get("min_tv", 80),
        "Refrigerator": gates.get("min_refrigerator", 80),
        "Washing Machine": gates.get("min_washing_machine", 80),
        "Monitor": gates.get("min_monitor", 40),
        "LG gram": gates.get("min_gram", 20),
    }

    tier1_countries = [c for c in countries if c.get("tier", 3) == 1]

    for product, min_count in product_gates.items():
        actual = product_counts.get(product, 0)
        if actual < min_count:
            logger.info(f"Supplementing {product}: {actual}/{min_count}")
            pcfg = products_cfg.get(product)
            if not pcfg:
                continue
            for country_cfg in tier1_countries:
                if collector.total_api_calls - calls_before >= max_extra_calls:
                    logger.warning("Supplement API call limit reached")
                    return supplement
                recs = collector.collect_product_queries(
                    country_cfg, pcfg, collected_at, max_queries=2
                )
                supplement.extend(recs)

    # 국가별 미달 보강 (최소 3건, Tier 1 제품만)
    for country_cfg in countries:
        cc = country_cfg["code"]
        if country_counts.get(cc, 0) < 3:
            if collector.total_api_calls - calls_before >= max_extra_calls:
                break
            logger.info(f"Supplementing country {cc}: low coverage")
            pcfg = products_cfg.get("TV")
            if pcfg:
                recs = collector.collect_product_queries(
                    country_cfg, pcfg, collected_at, max_queries=1
                )
                supplement.extend(recs)

    return supplement


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    # Date key
    if len(sys.argv) > 1 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
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

    if collector.quota_exhausted and len(records) == 0:
        logger.error("API quota exhausted with 0 records. Cannot proceed.")
        logger.error("Check your Brave Search API plan quota at https://api.search.brave.com/app/keys")
        sys.exit(1)
    elif collector.quota_exhausted:
        logger.warning(f"API quota exhausted but collected {len(records)} records. Saving partial data.")

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

    # Deduplicate by URL + content hash (catches syndicated/reposted content)
    seen_urls = set()
    seen_content = set()
    unique_records = []
    dupe_url_count = 0
    dupe_content_count = 0
    for r in records:
        url = r.get("source_url", "")
        if url in seen_urls:
            dupe_url_count += 1
            continue
        seen_urls.add(url)
        # Content-based dedup: hash of normalized title + first 200 chars of snippet
        content_key = hashlib.md5(
            f"{r.get('value', '').strip().lower()}|{r.get('quote_original', '')[:200].strip().lower()}".encode()
        ).hexdigest()
        if content_key in seen_content:
            dupe_content_count += 1
            continue
        seen_content.add(content_key)
        unique_records.append(r)

    if dupe_content_count > 0:
        logger.info(f"Dedup: removed {dupe_url_count} URL dupes + {dupe_content_count} content dupes")

    # Deep fetch enrichment (optional, requires scrapling)
    if os.environ.get("ENABLE_DEEP_FETCH", "0") == "1":
        try:
            from d2c_deep_fetch import enrich_records
            max_urls = int(os.environ.get("DEEP_FETCH_MAX", "50"))
            logger.info(f"Starting deep fetch enrichment (max {max_urls} URLs)...")
            unique_records, deep_stats = enrich_records(unique_records, max_urls=max_urls)
            logger.info(f"Deep fetch: {deep_stats['enriched']} URLs enriched")
        except ImportError:
            logger.warning("Deep fetch skipped: scrapling not installed (pip install scrapling)")
        except Exception as e:
            logger.warning(f"Deep fetch failed (non-fatal): {e}")

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
