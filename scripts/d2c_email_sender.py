#!/usr/bin/env python3
"""
D2C Intel — Email Sender (Gmail API)
=====================================
주간/월간 리포트를 이메일로 발송합니다.

Usage:
    python scripts/d2c_email_sender.py [YYYY-MM-DD] [--monthly]

Environment:
    REPORT_RECIPIENTS  — 수신자 이메일 (콤마 구분)
    D2C_SUBSCRIBER_SPREADSHEET_ID — Google Sheets 구독자 스프레드시트 ID
    GOOGLE_TOKEN_PATH  — Google OAuth token path (default: ~/.openclaw/workspace/tools/google-token.json)

Output:
    이메일 발송 (PDF 첨부 + 경영진 요약 HTML)
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ──────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
LOG_DIR = ROOT_DIR / "logs"

# Google Sheets subscriber config
D2C_SUBSCRIBER_SPREADSHEET_ID = "1pRSw05o8UKOzFZxvvX2zvq02N2NFJ25uPyZQy31EzJg"
D2C_SUBSCRIBER_RANGE = "설문지 응답 시트1!B2:B"
DEFAULT_TOKEN_PATH = os.path.expanduser("~/.openclaw/workspace/tools/google-token.json")
EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}$", re.IGNORECASE)

BLOCKED_EMAILS: set = {
    "ektjs88@gmail.com",
}


def get_sheet_subscribers() -> list:
    """Fetch subscriber emails from Google Sheets."""
    spreadsheet_id = os.environ.get("D2C_SUBSCRIBER_SPREADSHEET_ID", D2C_SUBSCRIBER_SPREADSHEET_ID)
    token_path = os.environ.get("GOOGLE_TOKEN_PATH", DEFAULT_TOKEN_PATH)

    if not os.path.exists(token_path):
        logger.warning(f"Google token not found: {token_path}, skipping sheet subscribers")
        return []

    try:
        creds = Credentials.from_authorized_user_file(
            token_path, ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        creds.refresh(Request())
        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=D2C_SUBSCRIBER_RANGE)
            .execute()
        )
        rows = result.get("values", [])
        emails = []
        for row in rows:
            email = (row[0] if row else "").strip().lower()
            if email and EMAIL_PATTERN.match(email) and email not in BLOCKED_EMAILS:
                emails.append(email)
        logger.info(f"Google Sheets subscribers: {len(emails)} valid emails from {len(rows)} rows")
        return emails
    except Exception as e:
        logger.warning(f"Failed to fetch sheet subscribers: {e}")
        return []

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("d2c_email_sender")

DEFAULT_FROM = "d2c-intel@d2c-intel.github.io"
DEFAULT_FROM_NAME = "D2C Global Intelligence"


# ──────────────────────────────────────────────────────────────
# Extract Executive Summary from Markdown
# ──────────────────────────────────────────────────────────────

def extract_executive_summary(md_path: Path) -> str:
    """Markdown에서 경영진 요약 섹션을 추출하여 HTML로 변환합니다."""
    if not md_path.exists():
        return "<p>리포트가 성공적으로 생성되었습니다. 첨부된 PDF를 확인하세요.</p>"

    text = md_path.read_text(encoding="utf-8")

    # 섹션 1 (경영진 요약) 추출
    match = re.search(
        r"##\s*1\.\s*경영진 요약(.*?)(?=##\s*2\.|$)",
        text, re.DOTALL
    )
    if not match:
        match = re.search(
            r"##\s*1\.\s*Executive Summary(.*?)(?=##\s*2\.|$)",
            text, re.DOTALL
        )
    if not match:
        return "<p>리포트가 성공적으로 생성되었습니다. 첨부된 PDF를 확인하세요.</p>"

    section = match.group(1).strip()

    # Markdown → HTML 변환 (li를 ul로 감싸기, 서브섹션 필터링)
    html_lines = []
    in_list = False

    for line in section.split("\n"):
        line = line.strip()
        if not line or line.startswith("---") or line.startswith("<!-- "):
            continue
        # 서브섹션 (1.1, 1.2 등)은 이메일에서 생략
        if re.match(r"^###\s*1\.\d", line):
            continue
        if line.startswith("|"):
            continue

        is_item = line.startswith("- ") or re.match(r"^\d+\.\s", line)

        if is_item and not in_list:
            html_lines.append('<ul style="margin:8px 0;padding-left:20px;color:#1e293b;">')
            in_list = True
        elif not is_item and in_list:
            html_lines.append("</ul>")
            in_list = False

        if line.startswith("### 핵심 인사이트") or line.startswith("### Key Insight"):
            html_lines.append('<h3 style="color:#0b4f88;font-size:15px;margin:20px 0 8px;">📊 핵심 인사이트</h3>')
        elif line.startswith("### 실행 필요") or line.startswith("### Action Required"):
            html_lines.append('<h3 style="color:#92400e;font-size:15px;margin:20px 0 8px;">⚡ 실행 필요</h3>')
        elif line.startswith("### "):
            html_lines.append(f'<h3 style="color:#334155;font-size:14px;margin:16px 0 6px;">{line[4:]}</h3>')
        elif line.startswith("- "):
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line[2:])
            html_lines.append(f'<li style="margin-bottom:8px;line-height:1.6;color:#1e293b;font-size:14px;">{text}</li>')
        elif re.match(r"^\d+\.\s", line):
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', re.sub(r'^[0-9]+\.\s*', '', line))
            html_lines.append(f'<li style="margin-bottom:8px;line-height:1.6;color:#1e293b;font-size:14px;">{text}</li>')
        else:
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            html_lines.append(f'<p style="margin:6px 0;line-height:1.6;color:#334155;font-size:14px;">{text}</p>')

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


# ──────────────────────────────────────────────────────────────
# Build Email HTML
# ──────────────────────────────────────────────────────────────

def build_email_html(
    date_key: str, summary_html: str, is_monthly: bool = False,
    hub_url: str = ""
) -> str:
    """이메일 HTML 본문을 생성합니다."""
    report_type = "월간 Deep Dive" if is_monthly else "주간 시장 인텔리전스"
    color = "#3b1f7a" if is_monthly else "#003a66"

    hub_link = f'🔗 <a href="{hub_url}" style="color:#2563eb;text-decoration:underline;">온라인 Hub에서 보기</a>' if hub_url else ""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;font-family:-apple-system,'Noto Sans KR',sans-serif;background:#eef2f7;">
<div style="max-width:640px;margin:0 auto;padding:24px;">

<!-- Header -->
<div style="background:{color};border-radius:12px 12px 0 0;padding:28px 24px;">
  <h1 style="margin:0;font-size:20px;color:#ffffff;font-weight:700;">
    LG전자 글로벌 D2C {report_type} 리포트
  </h1>
  <p style="margin:10px 0 0;color:#cfe2f3;font-size:14px;">
    소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향
  </p>
  <p style="margin:6px 0 0;color:#a3c4e0;font-size:13px;">📅 {date_key}</p>
</div>

<!-- Summary -->
<div style="background:#ffffff;border-left:1px solid #d1d9e6;border-right:1px solid #d1d9e6;padding:28px 24px;">
  <h2 style="color:#0f172a;font-size:17px;margin:0 0 16px;border-bottom:2px solid {color};padding-bottom:8px;">
    📋 경영진 요약
  </h2>
  {summary_html}
</div>

<!-- CTA -->
<div style="background:#f8fafc;border:1px solid #d1d9e6;border-top:none;padding:20px 24px;border-radius:0 0 12px 12px;">
  <p style="margin:0 0 8px;font-size:14px;color:#334155;">
    📎 전체 리포트는 첨부된 PDF를 확인하세요.
  </p>
  <p style="margin:0;font-size:14px;color:#334155;">{hub_link}</p>
</div>

<!-- Footer -->
<div style="padding:20px;text-align:center;font-size:11px;color:#64748b;">
  D2C Global Intelligence · Automated Report · Confidential
</div>

</div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# Send Email
# ──────────────────────────────────────────────────────────────

def send_email(
    to_emails: list,
    cc_emails: list,
    subject: str,
    html_content: str,
    pdf_path: Path = None,
) -> bool:
    """Gmail API로 이메일을 발송합니다."""
    token_path = os.environ.get("GOOGLE_TOKEN_PATH", DEFAULT_TOKEN_PATH)

    if not os.path.exists(token_path):
        logger.error(f"Google token not found: {token_path}")
        return False

    try:
        creds = Credentials.from_authorized_user_file(token_path)
        creds.refresh(Request())
        gmail = build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Gmail API init failed: {e}")
        return False

    from_email = "suno7608@gmail.com"

    # Build MIME message
    msg = MIMEMultipart()
    msg["From"] = f"D2C Global Intelligence <{from_email}>"
    msg["To"] = ", ".join(to_emails)
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # PDF 첨부
    if pdf_path and pdf_path.exists():
        with open(pdf_path, "rb") as f:
            att = MIMEApplication(f.read(), _subtype="pdf")
            att.add_header("Content-Disposition", "attachment", filename=pdf_path.name)
            msg.attach(att)
            logger.info(f"Attached PDF: {pdf_path.name} ({pdf_path.stat().st_size / 1024:.0f}KB)")

    try:
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info(f"Email sent via Gmail API: id={result['id']}, to={to_emails}")
        return True
    except Exception as e:
        logger.error(f"Gmail API send error: {e}")
        return False


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="D2C Email Sender")
    parser.add_argument("date_key", nargs="?", default=date.today().isoformat())
    parser.add_argument("--monthly", action="store_true", help="Monthly Deep Dive mode")
    args = parser.parse_args()

    date_key = args.date_key
    is_monthly = args.monthly

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / f"email_sender_{date_key}.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(fh)

    logger.info(f"D2C Email Sender — date={date_key}, monthly={is_monthly}")

    # Recipients: env var + Google Sheets subscribers (deduplicated)
    recipients_str = os.environ.get("REPORT_RECIPIENTS", "suno7608@gmail.com")
    env_emails = [e.strip().lower() for e in recipients_str.split(",") if e.strip()]
    sheet_emails = get_sheet_subscribers()

    seen = set()
    to_emails = []
    for e in env_emails + sheet_emails:
        if e not in seen and e not in BLOCKED_EMAILS:
            to_emails.append(e)
            seen.add(e)

    logger.info(f"Final recipients: {len(to_emails)} (env={len(env_emails)}, sheet={len(sheet_emails)})")

    cc_str = os.environ.get("D2C_EMAIL_CC", "")
    cc_emails = [e.strip() for e in cc_str.split(",") if e.strip()]

    # Find files
    if is_monthly:
        md_pattern = f"LG_Global_D2C_Monthly_DeepDive_{date_key[:7]}*.md"
        pdf_pattern = f"LG_Global_D2C_Monthly_DeepDive_{date_key[:7]}*.pdf"
        subject = f"[LG D2C] 월간 Deep Dive 리포트 - {date_key[:7]}"
    else:
        md_pattern = f"LG_Global_D2C_Weekly_Intelligence_{date_key}_R2_16country.md"
        pdf_pattern = f"*{date_key}*.pdf"
        subject = f"[LG D2C] 주간 시장 인텔리전스 리포트 - {date_key}"

    # Find markdown
    md_files = list(REPORTS_DIR.glob(f"md/{md_pattern}"))
    md_path = md_files[0] if md_files else None

    # Find PDF
    pdf_files = list(REPORTS_DIR.glob(f"pdf/{pdf_pattern}"))
    if not pdf_files:
        pdf_files = list(REPORTS_DIR.glob(f"html/{date_key}/*.pdf"))
    pdf_path = pdf_files[0] if pdf_files else None

    # Hub URL
    hub_url = os.environ.get("PAGES_URL", "https://suno7608.github.io/d2c-intel/")

    # Build email
    summary_html = extract_executive_summary(md_path) if md_path else ""
    html_content = build_email_html(date_key, summary_html, is_monthly, hub_url)

    # Send
    success = send_email(to_emails, cc_emails, subject, html_content, pdf_path)

    if success:
        print(f"[d2c_email_sender] Email sent to {to_emails}")
    else:
        logger.error("Email sending failed")
        # 이메일 실패가 전체 파이프라인을 중단시키지 않도록 soft fail
        print("[d2c_email_sender] WARNING: Email sending failed (soft fail)")


if __name__ == "__main__":
    main()
