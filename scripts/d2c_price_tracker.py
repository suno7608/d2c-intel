#!/usr/bin/env python3
"""
D2C Intel — Price History Tracker (v1.0)
=========================================
주간 수집 데이터에서 가격 정보를 추출하여 SKU/모델별 가격 히스토리를
추적하고 주간 변동을 분석합니다.

Data flow:
    openclaw_YYYY-MM-DD.jsonl → price_tracker → price_history.jsonl
                                              → price_alerts.json

Usage:
    python scripts/d2c_price_tracker.py [YYYY-MM-DD]

Output:
    data/price_history/price_history.jsonl    — 누적 가격 히스토리
    data/price_history/price_alerts_DATE.json — 주간 가격 변동 알림
"""

import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("d2c_price_tracker")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "raw"
PRICE_DIR = ROOT_DIR / "data" / "price_history"

# Model/SKU extraction patterns
_MODEL_PATTERNS = [
    # Brand + model: "LG C5", "TCL QM6K", "Samsung QN85D", "Hisense U8N"
    re.compile(r'\b(?:LG|Samsung|TCL|Hisense|Haier|Midea|Sony|Bosch)\s+(?:OLED\s+)?([A-Z][A-Z0-9]{1,8})\b', re.IGNORECASE),
    # LG specific product lines: UltraGear, gram, WashCombo
    re.compile(r'\b(UltraGear|LG\s+gram|WashCombo|InstaView|ThinQ)\b', re.IGNORECASE),
    # TV size + model: "77-inch B5", "85" QM6K"
    re.compile(r'(\d{2,3})["\-\s]*(?:inch|")\s+(?:LG\s+|TCL\s+|Samsung\s+|Hisense\s+)?([A-Z][A-Z0-9]{1,6})', re.IGNORECASE),
    # Specific model numbers: 27GS95QE, OLED77B5, QN85D
    re.compile(r'\b(\d{2}[A-Z]{1,3}\d{2,4}[A-Z]?\w{0,3})\b'),
    re.compile(r'\b([A-Z]{2,5}\d{2,4}[A-Z]{1,2}\w{0,3})\b'),
]


def extract_model(title: str, brand: str = "") -> str:
    """제목에서 모델명/SKU를 추출합니다."""
    # Try brand-specific patterns first
    for pattern in _MODEL_PATTERNS[:6]:
        m = pattern.search(title)
        if m:
            groups = [g for g in m.groups() if g]
            model = " ".join(groups).strip()
            if len(model) >= 2:
                return model.upper()
    return ""


def normalize_price(price_str: str, currency: str = "") -> Optional[float]:
    """가격 문자열을 float로 변환합니다."""
    if not price_str:
        return None
    # Remove currency symbols and spaces
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    if not cleaned:
        return None
    # Handle European format: 1.234,56 → 1234.56
    if ',' in cleaned and '.' in cleaned:
        if cleaned.index('.') < cleaned.index(','):
            # European: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US: 1,234.56
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Could be 1,234 (US) or 1234,56 (EU)
        parts = cleaned.split(',')
        if len(parts[-1]) == 2:
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return None


def build_price_key(record: dict) -> str:
    """레코드에서 가격 추적 키를 생성합니다.

    형식: {brand}|{product}|{model}|{country}
    """
    brand = record.get("brand", "Unknown")
    product = record.get("product", "")
    title = record.get("value", "")
    country = record.get("country", "")
    model = extract_model(title, brand)

    if not model:
        return ""
    return f"{brand}|{product}|{model}|{country}"


def extract_weekly_prices(records: List[dict], date_key: str) -> List[dict]:
    """주간 수집 데이터에서 가격 레코드를 추출합니다."""
    price_entries = []

    for r in records:
        price_str = r.get("price_value", "")
        currency = r.get("currency", "")
        if not price_str:
            continue

        price_val = normalize_price(price_str, currency)
        if price_val is None or price_val <= 0:
            continue

        price_key = build_price_key(r)
        if not price_key:
            continue

        brand, product, model, country = price_key.split("|")

        entry = {
            "price_key": price_key,
            "brand": brand,
            "product": product,
            "model": model,
            "country": country,
            "currency": currency,
            "price": price_val,
            "price_raw": price_str,
            "discount": r.get("discount", ""),
            "source_url": r.get("source_url", ""),
            "source": r.get("source", ""),
            "date": date_key,
        }
        price_entries.append(entry)

    return price_entries


def load_price_history(path: Path) -> Dict[str, List[dict]]:
    """누적 가격 히스토리를 로드합니다."""
    history = defaultdict(list)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    key = entry.get("price_key", "")
                    if key:
                        history[key].append(entry)
    return history


def detect_price_changes(
    history: Dict[str, List[dict]],
    new_entries: List[dict],
    threshold_pct: float = 5.0,
) -> List[dict]:
    """가격 변동 알림을 생성합니다.

    Args:
        threshold_pct: 알림을 생성할 최소 변동률 (%)
    """
    alerts = []

    # Group new entries by price_key
    new_by_key = defaultdict(list)
    for entry in new_entries:
        new_by_key[entry["price_key"]].append(entry)

    for key, new_list in new_by_key.items():
        prev_entries = history.get(key, [])
        if not prev_entries:
            continue

        # Use most recent previous price
        prev_entries.sort(key=lambda x: x.get("date", ""), reverse=True)
        prev = prev_entries[0]
        prev_price = prev.get("price", 0)

        if prev_price <= 0:
            continue

        # Average new price for this key
        new_prices = [e["price"] for e in new_list if e["price"] > 0]
        if not new_prices:
            continue
        new_price = sum(new_prices) / len(new_prices)

        change_pct = ((new_price - prev_price) / prev_price) * 100

        if abs(change_pct) >= threshold_pct:
            brand, product, model, country = key.split("|")
            alert = {
                "price_key": key,
                "brand": brand,
                "product": product,
                "model": model,
                "country": country,
                "currency": new_list[0].get("currency", ""),
                "prev_price": prev_price,
                "new_price": round(new_price, 2),
                "change_pct": round(change_pct, 1),
                "direction": "drop" if change_pct < 0 else "increase",
                "prev_date": prev.get("date", ""),
                "new_date": new_list[0].get("date", ""),
                "source_url": new_list[0].get("source_url", ""),
            }
            alerts.append(alert)

    # Sort by absolute change percentage (biggest changes first)
    alerts.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return alerts


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if len(sys.argv) > 1 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
        date_key = sys.argv[1]
    else:
        date_key = date.today().isoformat()

    input_path = DATA_DIR / f"openclaw_{date_key}.jsonl"
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    history_path = PRICE_DIR / "price_history.jsonl"
    alerts_path = PRICE_DIR / f"price_alerts_{date_key}.json"

    # Load records
    with open(input_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    logger.info(f"Loaded {len(records)} records from {input_path}")

    # Extract weekly prices
    new_prices = extract_weekly_prices(records, date_key)
    logger.info(f"Extracted {len(new_prices)} price entries")

    if not new_prices:
        logger.info("No price data to track this week")
        return

    # Load existing history
    history = load_price_history(history_path)
    logger.info(f"Existing price history: {len(history)} tracked items")

    # Detect price changes
    alerts = detect_price_changes(history, new_prices, threshold_pct=5.0)

    # Append new prices to history
    with open(history_path, "a", encoding="utf-8") as f:
        for entry in new_prices:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(f"Appended {len(new_prices)} entries to {history_path}")

    # Save alerts
    alert_data = {
        "date": date_key,
        "total_tracked": len(new_prices),
        "unique_items": len(set(e["price_key"] for e in new_prices)),
        "alerts_count": len(alerts),
        "alerts": alerts,
    }
    with open(alerts_path, "w", encoding="utf-8") as f:
        json.dump(alert_data, f, ensure_ascii=False, indent=2)

    # Summary
    if alerts:
        logger.info(f"=== Price Alerts ({len(alerts)}) ===")
        for a in alerts[:10]:
            direction = "📉" if a["direction"] == "drop" else "📈"
            logger.info(
                f"  {direction} {a['brand']} {a['model']} ({a['country']}): "
                f"{a['currency']} {a['prev_price']} → {a['new_price']} "
                f"({a['change_pct']:+.1f}%)"
            )
    else:
        logger.info("No significant price changes detected")

    print(
        f"[price_tracker] {len(new_prices)} prices tracked, "
        f"{len(alerts)} alerts → {alerts_path}"
    )


if __name__ == "__main__":
    main()
