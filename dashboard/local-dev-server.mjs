/**
 * D2C Intel — Local Dev Server
 * ==============================
 * Vercel 없이 로컬에서 API + 정적파일을 함께 서빙.
 * 실제 GitHub 데이터를 직접 읽음 (public repo, 토큰 불필요).
 *
 * Usage:
 *   node dashboard/local-dev-server.mjs
 *   PORT=3100 node dashboard/local-dev-server.mjs
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { URL as NodeURL } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3100;

// ── API 핸들러 import ──────────────────────────────────────
// 로컬 버전이 있으면 우선 사용 (예: regional-reports.local.js)
async function loadHandler(name) {
  const localPath = new URL(`./api/${name}.local.js`, import.meta.url);
  try {
    if (fs.existsSync(fileURLToPath(localPath))) {
      const mod = await import(`./api/${name}.local.js?t=${Date.now()}`);
      return mod.default;
    }
  } catch {}
  const mod = await import(`./api/${name}.js?t=${Date.now()}`);
  return mod.default;
}

// ── MIME 타입 ──────────────────────────────────────────────
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.json': 'application/json',
  '.png':  'image/png',
  '.ico':  'image/x-icon',
  '.svg':  'image/svg+xml',
  '.woff2':'font/woff2',
};

// ── 가짜 Vercel req/res 래퍼 ──────────────────────────────
function makeReq(nodeReq, body) {
  const url = new URL(nodeReq.url, `http://localhost:${PORT}`);
  const query = {};
  url.searchParams.forEach((v, k) => { query[k] = v; });

  return {
    method: nodeReq.method,
    headers: nodeReq.headers,
    url: nodeReq.url,
    query,
    body,
  };
}

function makeRes(nodeRes) {
  const headers = {};
  let statusCode = 200;

  return {
    setHeader(k, v) { headers[k] = v; nodeRes.setHeader(k, v); },
    status(code) { statusCode = code; nodeRes.statusCode = code; return this; },
    json(data) {
      nodeRes.statusCode = statusCode;
      nodeRes.setHeader('Content-Type', 'application/json');
      nodeRes.setHeader('Access-Control-Allow-Origin', '*');
      nodeRes.end(JSON.stringify(data, null, 2));
    },
    send(data) {
      nodeRes.statusCode = statusCode;
      nodeRes.end(data);
    },
    end(data) { nodeRes.end(data); },
  };
}

// ── 요청 본문 읽기 ─────────────────────────────────────────
function readBody(req) {
  return new Promise(resolve => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try { resolve(JSON.parse(body)); }
      catch { resolve({}); }
    });
  });
}

// ── 서버 ──────────────────────────────────────────────────
const server = http.createServer(async (nodeReq, nodeRes) => {
  const url = new URL(nodeReq.url, `http://localhost:${PORT}`);
  const pathname = url.pathname;

  // CORS preflight
  if (nodeReq.method === 'OPTIONS') {
    nodeRes.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    return nodeRes.end();
  }

  // ── API 라우팅 ──
  if (pathname.startsWith('/api/')) {
    const apiName = pathname.replace('/api/', '').split('/')[0];
    try {
      const handler = await loadHandler(apiName);
      const body = nodeReq.method === 'POST' ? await readBody(nodeReq) : {};
      const req = makeReq(nodeReq, body);
      const res = makeRes(nodeRes);
      await handler(req, res);
    } catch (e) {
      console.error(`[API Error] ${apiName}:`, e.message);
      nodeRes.writeHead(500, { 'Content-Type': 'application/json' });
      nodeRes.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── 정적 파일 서빙 ──
  let filePath = path.join(__dirname, pathname === '/' ? 'index.html' : pathname);

  // 경로 순회 방지
  if (!filePath.startsWith(__dirname)) {
    nodeRes.writeHead(403);
    return nodeRes.end('Forbidden');
  }

  if (!fs.existsSync(filePath)) {
    // SPA fallback → index.html
    filePath = path.join(__dirname, 'index.html');
  }

  const ext = path.extname(filePath);
  const contentType = MIME[ext] || 'application/octet-stream';

  try {
    const content = fs.readFileSync(filePath);
    nodeRes.writeHead(200, { 'Content-Type': contentType });
    nodeRes.end(content);
  } catch {
    nodeRes.writeHead(404);
    nodeRes.end('Not found');
  }
});

server.listen(PORT, () => {
  console.log(`\n✅ D2C Intel Dev Server`);
  console.log(`   http://localhost:${PORT}\n`);
  console.log(`   API endpoints:`);
  console.log(`   → /api/kpis`);
  console.log(`   → /api/regions`);
  console.log(`   → /api/news`);
  console.log(`   → /api/search`);
  console.log(`   → /api/reports`);
  console.log(`   → /api/regional-reports`);
  console.log(`   → /api/agent  (ANTHROPIC_API_KEY 필요)\n`);
});
