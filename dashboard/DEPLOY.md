# D2C Intel Dashboard — Vercel Deployment Guide

## Quick Deploy

### 1. Vercel 프로젝트 설정
```bash
cd dashboard
vercel --prod
```

### 2. 환경 변수 (Vercel Dashboard → Settings → Environment Variables)

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub Personal Access Token (repo read) | Yes |
| `ANTHROPIC_API_KEY` | Claude API Key (AI Agent) | Yes |
| `CLAUDE_MODEL_AGENT` | Claude model for agent (default: claude-sonnet-4-20250514) | No |

### 3. GitHub Secrets (Repository → Settings → Secrets)

| Secret | Description |
|--------|-------------|
| `BRAVE_API_KEY` | Brave Search API Key |
| `ANTHROPIC_API_KEY` | Claude API Key |
| `SENDGRID_API_KEY` | SendGrid API (email) |

### 4. GitHub Variables (Repository → Settings → Variables)

| Variable | Description |
|----------|-------------|
| `CLAUDE_MODEL_REPORT` | Model for report generation |
| `CLAUDE_MODEL_TRANSLATE` | Model for translation |
| `REPORT_RECIPIENTS` | Email recipients |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/kpis` | GET | KPI metrics from weekly stats |
| `/api/regions` | GET | Regional breakdown from raw data |
| `/api/news` | GET | Daily news feed |
| `/api/search` | GET | Intelligence search |
| `/api/agent` | POST | AI agent (Claude API) |
| `/api/reports` | GET | Report list/content |
| `/api/regional-reports` | GET | Regional report data (JSON + Markdown) |

## GitHub Actions

- **Daily (06:00 UTC)**: `d2c-daily-news.yml` — Brave Search news clipping
- **Weekly (Sun 07:00 UTC)**: `d2c-weekly-report.yml` — Full pipeline
- **Monthly (1st 00:00 UTC)**: `d2c-monthly-report.yml` — Monthly deep dive

## Architecture

```
Browser → Vercel CDN → index.html (static)
       → Vercel Serverless → /api/* → GitHub Raw API → data/*.json(l)
       → /api/agent → Claude API

GitHub Actions → Brave Search API → data/daily_news/*.jsonl (daily)
              → Brave Search + Claude → data/raw/*.jsonl + reports/ (weekly)
```
