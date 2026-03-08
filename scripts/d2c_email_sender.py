#!/usr/bin/env python3
"""
D2C Intel — Email Sender (SendGrid)
=====================================
주간/월간 리포트를 이메일로 발송합니다.

Usage:
    python scripts/d2c_email_sender.py [YYYY-MM-DD] [--monthly]

Environment:
    SENDGRID_API_KEY   — SendGrid API key (required)
    REPORT_RECIPIENTS  — 수신자 이메일 (GitHub Variables)
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
from pathlib import Path

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    ContentId,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
    To,
)

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
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(
            token_path, ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
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

    # 간단한 Markdown → HTML 변환
    html_lines = []
    for line in section.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("### 핵심 인사이트") or line.startswith("### Key Insight"):
            html_lines.append('<h3 style="color:#0b4f88;">📊 핵심 인사이트</h3>')
        elif line.startswith("### 실행 필요") or line.startswith("### Action Required"):
            html_lines.append('<h3 style="color:#b8860b;">⚡ 실행 필요</h3>')
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif re.match(r"^\d+\.\s", line):
            html_lines.append(f"<li>{re.sub(r'^[0-9]+. ', '', line)}</li>")
        elif line.startswith("|"):
            continue  # 테이블은 이메일에서 생략
        else:
            html_lines.append(f"<p>{line}</p>")

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

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;font-family:'Noto Sans KR',-apple-system,sans-serif;background:#f5f8fc;">
<div style="max-width:640px;margin:0 auto;padding:20px;">

<!-- Header -->
<div style="background:linear-gradient(135deg,{color},#0a7ac4);border-radius:12px 12px 0 0;padding:24px;color:#fff;">
  <h1 style="margin:0;font-size:20px;">LG전자 글로벌 D2C {report_type} 리포트</h1>
  <p style="margin:8px 0 0;opacity:0.9;font-size:14px;">
    소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향
  </p>
  <p style="margin:8px 0 0;opacity:0.85;font-size:13px;">Date: {date_key}</p>
</div>

<!-- Summary -->
<div style="background:#fff;border:1px solid #d9e2ec;padding:24px;border-radius:0 0 12px 12px;">
  <h2 style="color:{color};font-size:16px;margin:0 0 16px;">📋 경영진 요약</h2>
  {summary_html}

  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">

  <p style="font-size:13px;color:#64748b;">
    📎 전체 리포트는 첨부된 PDF를 확인하세요.<br>
    {"🔗 <a href='" + hub_url + "'>온라인 Hub에서 보기</a>" if hub_url else ""}
  </p>
</div>

<!-- Footer -->
<div style="padding:16px;text-align:center;font-size:11px;color:#94a3b8;">
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
    """SendGrid로 이메일을 발송합니다."""
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        logger.error("SENDGRID_API_KEY not set")
        return False

    from_email = os.environ.get("D2C_EMAIL_FROM", DEFAULT_FROM)
    from_name = os.environ.get("D2C_EMAIL_FROM_NAME", DEFAULT_FROM_NAME)

    message = Mail(
        from_email=(from_email, from_name),
        to_emails=[To(e) for e in to_emails],
        subject=subject,
        html_content=html_content,
    )

    # CC
    if cc_emails:
        message.cc = [To(e) for e in cc_emails]

    # PDF 첨부
    if pdf_path and pdf_path.exists():
        with open(pdf_path, "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode("utf-8")

        attachment = Attachment(
            FileContent(pdf_data),
            FileName(pdf_path.name),
            FileType("application/pdf"),
            Disposition("attachment"),
        )
        message.attachment = attachment
        logger.info(f"Attached PDF: {pdf_path.name} ({pdf_path.stat().st_size / 1024:.0f}KB)")

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info(f"Email sent: status={response.status_code}, to={to_emails}")
        return response.status_code in (200, 201, 202)
    except Exception as e:
        logger.error(f"SendGrid error: {e}")
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
