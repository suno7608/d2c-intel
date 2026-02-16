#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/config/pipeline.env"
PRESET_OBSIDIAN_WEEKLY_ROOT="${OBSIDIAN_WEEKLY_ROOT:-}"
PRESET_OBSIDIAN_WEEKLY_FOLDER="${OBSIDIAN_WEEKLY_FOLDER:-}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -n "$PRESET_OBSIDIAN_WEEKLY_ROOT" ]]; then
  export OBSIDIAN_WEEKLY_ROOT="$PRESET_OBSIDIAN_WEEKLY_ROOT"
fi
if [[ -n "$PRESET_OBSIDIAN_WEEKLY_FOLDER" ]]; then
  export OBSIDIAN_WEEKLY_FOLDER="$PRESET_OBSIDIAN_WEEKLY_FOLDER"
fi

TZ_VALUE="${TZ:-Asia/Seoul}"
DATE_KEY="${1:-$(TZ="$TZ_VALUE" date +%F)}"
INPUT_REPORT="${2:-}"

if [[ -z "$INPUT_REPORT" ]]; then
  for candidate in \
    "$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.md" \
    "$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_claude.md" \
    "$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"; do
    if [[ -f "$candidate" ]]; then
      INPUT_REPORT="$candidate"
      break
    fi
  done
fi

if [[ -z "$INPUT_REPORT" || ! -f "$INPUT_REPORT" ]]; then
  echo "input report not found for date: $DATE_KEY" >&2
  exit 1
fi

if [[ -z "${OBSIDIAN_WEEKLY_ROOT:-}" ]]; then
  echo "OBSIDIAN_WEEKLY_ROOT is not set. export skipped." >&2
  exit 1
fi

WEEK_FOLDER="${OBSIDIAN_WEEKLY_FOLDER:-${DATE_KEY} Weekly Intelligence}"
WEEK_DIR="$OBSIDIAN_WEEKLY_ROOT/$WEEK_FOLDER"

REPORT_BASENAME="$(basename "$INPUT_REPORT" .md)"
REPORT_FILENAME="$(basename "$INPUT_REPORT")"
HTML_WEEK="$ROOT_DIR/reports/html/$DATE_KEY/index.html"
HTML_LATEST="$ROOT_DIR/reports/html/latest/index.html"
HUB_HTML="$ROOT_DIR/reports/html/latest/hub.html"
SHARE_WEEK="$ROOT_DIR/reports/html/$DATE_KEY/share.html"
PDF_WEEK="$ROOT_DIR/reports/pdf/${REPORT_BASENAME}.pdf"
if [[ ! -f "$PDF_WEEK" ]]; then
  PDF_WEEK="$ROOT_DIR/reports/pdf/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.pdf"
fi
PDF_LATEST="$ROOT_DIR/reports/pdf/LG_Global_D2C_Weekly_Intelligence_latest.pdf"

mkdir -p "$WEEK_DIR"
cp "$INPUT_REPORT" "$WEEK_DIR/$REPORT_FILENAME"

cat > "$WEEK_DIR/README.md" <<EOF
# ${DATE_KEY} Global D2C Weekly Intelligence

## 페이지 구성
- [[01_최종_보고서_산출물]]
- [[02_핵심_인사이트_Action_구조]]
- [[03_자동화_운영_플랜]]
- [[04_다음주_실행체크리스트]]
- [[05_허브_및_스케줄_업데이트]]
- [[${REPORT_BASENAME}]]

## 이번 주 핵심
- 16개국 풀 커버리지 리포트 기준으로 최신 산출물 동기화
- 섹션별 \`Key Insight\` + \`Action Required\` 구조 유지
- 보고서 내 실행 항목은 매출/고객 대응 중심으로 운영
- Hub의 Weekly Archive 누적 및 Week-over-Week 그래프(추이/선택 A-B) 반영
- \`run_weekly.sh\` 1회 실행으로 HTML/PDF/Hub/Obsidian까지 연동

## 생성 정보
- Generated at: $(TZ="$TZ_VALUE" date +"%Y-%m-%d %H:%M:%S %Z")
- Source report: \`$INPUT_REPORT\`
EOF

cat > "$WEEK_DIR/01_최종_보고서_산출물.md" <<EOF
# 최종 보고서 산출물

## 주차 산출물
- MD: \`$INPUT_REPORT\`
- HTML(주차): \`$HTML_WEEK\`
- HTML Share(주차): \`$SHARE_WEEK\`
- PDF(주차): \`$PDF_WEEK\`

## 최신 공유 산출물
- HTML(latest): \`$HTML_LATEST\`
- Hub(latest): \`$HUB_HTML\`
- PDF(latest): \`$PDF_LATEST\`

## Obsidian 복사본
- \`$WEEK_DIR/$REPORT_FILENAME\`
EOF

cat > "$WEEK_DIR/02_핵심_인사이트_Action_구조.md" <<EOF
# 핵심 인사이트 / Action 구조

## 적용 원칙
- 본문 주요 섹션(1~5)마다 \`Key Insight\`와 \`Action Required\`를 한 세트로 유지
- Appendix A/B/C에는 \`Key Insight\`, \`Action Required\`를 작성하지 않음
- 실행 항목은 매출/전환/재구매/이탈 방지 관점으로 작성
- 국가/채널/SKU 단위로 즉시 실행 가능한 문구를 우선

## 품질 체크 기준
- 섹션별 Action 누락 없음
- 실행 항목은 기간/대상/목표가 명시됨
- 링크 규칙: \`[🔗 Source](URL)\`, 미확인 시 \`❓\`
EOF

cat > "$WEEK_DIR/03_자동화_운영_플랜.md" <<EOF
# 주간 자동화 운영 플랜

## 기본 실행 흐름
1. \`scripts/run_weekly.sh\` 실행
2. 데이터 수집(OpenClaw) + 초안 합성(Codex) + 검수(Claude)
3. HTML/PDF 빌드(\`build_publishable_report.sh\`)
4. Obsidian 주차 폴더/페이지 자동 생성(\`export_obsidian_weekly.sh\`)

## 운영 핵심 파일
- \`$ROOT_DIR/scripts/run_weekly.sh\`
- \`$ROOT_DIR/scripts/build_publishable_report.sh\`
- \`$ROOT_DIR/scripts/export_obsidian_weekly.sh\`
- \`$ROOT_DIR/scripts/install_launchd_weekly.sh\`
- \`$ROOT_DIR/scripts/uninstall_launchd_weekly.sh\`
- \`$ROOT_DIR/config/pipeline.env\`

## 스케줄 자동화 (macOS launchd)
- 설치: \`bash $ROOT_DIR/scripts/install_launchd_weekly.sh\`
- 해제: \`bash $ROOT_DIR/scripts/uninstall_launchd_weekly.sh\`
- 상태: \`launchctl print gui/\${UID}/com.soonho.d2c.weekly | sed -n '1,80p'\`
- 기본 스케줄: 매주 월요일 04:00 KST
EOF

cat > "$WEEK_DIR/04_다음주_실행체크리스트.md" <<EOF
# 다음 주 실행 체크리스트

## 발행 전
- [ ] \`pipeline.env\`의 runner/env 설정 확인
- [ ] OpenClaw/Claude command 정상 확인
- [ ] 보고 기간(date key) 확인

## 발행 중
- [ ] 핵심 섹션 \`Key Insight / Action Required\` 자동 생성 확인
- [ ] 링크 규칙 준수 확인
- [ ] HTML/PDF 산출 확인

## 발행 후
- [ ] Obsidian 주차 폴더 자동 생성 확인
- [ ] \`latest/hub.html\` 반영 확인
- [ ] 공유 링크 배포
EOF

cat > "$WEEK_DIR/05_허브_및_스케줄_업데이트.md" <<EOF
# 허브 및 스케줄 업데이트

## Hub 주요 업데이트
- 메인 접근 경로: \`$ROOT_DIR/reports/html/index.html\` (latest hub로 리다이렉트)
- Hub 페이지: \`$HUB_HTML\`
- Weekly Archive는 주차별 metadata 누적 기준으로 카드가 자동 추가됨
- Week-over-Week Compare는 표 + 그래프 2종 제공
  - 주차별 추이 그래프 (Critical / LG Promo / Comp Promo / China Threat)
  - 선택 주차 A/B 비교 그래프

## 발행 자동화 상태
- \`run_weekly.sh\`에서 publishable build 자동 호출
- launchd 등록 스크립트 제공 및 운영 가능
- 결과적으로 주간 실행 시 MD/HTML/PDF/Hub/Obsidian 동기화 가능

## 운영 확인 명령
- 수동 실행: \`bash $ROOT_DIR/scripts/run_weekly.sh\`
- Hub 확인: \`$HUB_HTML\`
- 최신 PDF: \`$PDF_LATEST\`
- launchd 상태: \`launchctl print gui/\${UID}/com.soonho.d2c.weekly | sed -n '1,80p'\`
EOF

echo "Obsidian weekly workspace created: $WEEK_DIR"
echo "Main note: $WEEK_DIR/README.md"
