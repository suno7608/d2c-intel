/**
 * POST /api/agent
 * AI Agent endpoint powered by Claude API.
 * Uses accumulated D2C intelligence data as context.
 *
 * Request body:
 *   { "message": "user question", "history": [...previous messages] }
 *
 * Response:
 *   { "reply": "...", "sources": [...] }
 */

import {
  fetchJSON,
  fetchJSONL,
  getLatestWeeklyDate,
  getReportDates,
} from './_lib/github.js';

const ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';

/**
 * Build context from latest data for the AI agent
 */
async function buildContext() {
  const dateKey = await getLatestWeeklyDate();
  if (!dateKey) return { text: 'No data available.', dateKey: null };

  const stats = await fetchJSON(`data/weekly_stats/${dateKey}.json`);

  // Get recent raw signals (sample for context window efficiency)
  let signals = [];
  try {
    const allSignals = await fetchJSONL(`data/raw/openclaw_${dateKey}.jsonl`);
    // Sample: top confidence signals, diverse by product/country
    const highConf = allSignals.filter(s => s.confidence === 'high');
    const medConf = allSignals.filter(s => s.confidence === 'medium');
    signals = [...highConf.slice(0, 40), ...medConf.slice(0, 60)];
  } catch (e) { /* fallback to stats only */ }

  // Get historical stats for trend analysis
  let history = [];
  try {
    const dates = await getReportDates();
    for (const d of dates.slice(0, 4)) {
      const s = await fetchJSON(`data/weekly_stats/${d}.json`);
      history.push(s);
    }
  } catch (e) { /* only current stats available */ }

  // Build structured context
  const contextParts = [
    `## Current Week: ${dateKey}`,
    `Total Signals Collected: ${stats.total_records}`,
    `Countries: ${stats.countries_count} — ${Object.entries(stats.countries).map(([k,v]) => `${k}(${v})`).join(', ')}`,
    `Products: ${Object.entries(stats.products).map(([k,v]) => `${k}(${v})`).join(', ')}`,
    `Brands: ${Object.entries(stats.brands).map(([k,v]) => `${k}(${v})`).join(', ')}`,
    `Intelligence Pillars: ${Object.entries(stats.pillars).map(([k,v]) => `${k}(${v})`).join(', ')}`,
    `Chinese Brand Threats: ${stats.chinese_brand_total} signals across ${stats.chinese_countries_count} countries`,
    `Chinese by Country: ${Object.entries(stats.chinese_by_country || {}).map(([k,v]) => `${k}(${v})`).join(', ')}`,
    `LG Promo Count: ${stats.lg_promo_count}`,
    `TV Ratio: ${stats.tv_ratio_pct}%`,
  ];

  if (history.length > 1) {
    contextParts.push('\n## Weekly Trend (last 4 weeks)');
    for (const h of history) {
      contextParts.push(`- ${h.date}: ${h.total_records} signals, ${h.chinese_brand_total} Chinese threats, ${h.countries_count} countries`);
    }
  }

  if (signals.length > 0) {
    contextParts.push('\n## Sample Intelligence Signals');
    for (const s of signals.slice(0, 30)) {
      contextParts.push(`- [${s.country}/${s.product}/${s.brand}] ${s.value} (${s.pillar}, ${s.confidence})`);
    }
  }

  return {
    text: contextParts.join('\n'),
    dateKey,
    stats,
  };
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return res.status(500).json({
      error: 'AI Agent not configured',
      message: 'ANTHROPIC_API_KEY environment variable is not set.',
    });
  }

  try {
    const { message, history = [] } = req.body;

    if (!message || typeof message !== 'string') {
      return res.status(400).json({ error: 'Message is required' });
    }

    // Build intelligence context
    const context = await buildContext();

    const systemPrompt = `You are the D2C Intelligence Analyst, an AI agent for LG's Global Direct-to-Consumer intelligence platform. You have access to the latest weekly intelligence data collected from 16 countries across 5 product categories (TV, Refrigerator, Washing Machine, Monitor, LG gram).

Your role:
- Analyze market intelligence signals and provide strategic insights
- Track Chinese brand threats (TCL, Hisense, Haier, Midea) across global markets
- Monitor retail channel promotions, consumer sentiment, and competitive pricing
- Provide actionable recommendations for LG's D2C strategy

Current Intelligence Context:
${context.text}

Guidelines:
- Answer in the same language as the user's question (Korean or English)
- Be specific with data points and cite countries/products when relevant
- Highlight trends, risks, and opportunities
- Keep responses concise but insightful (2-4 paragraphs)
- If asked about data you don't have, say so clearly`;

    // Build messages array
    const messages = [];
    for (const h of history.slice(-6)) {
      messages.push({
        role: h.role === 'user' ? 'user' : 'assistant',
        content: h.content,
      });
    }
    messages.push({ role: 'user', content: message });

    // Call Claude API
    const response = await fetch(ANTHROPIC_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: process.env.CLAUDE_MODEL_AGENT || 'claude-sonnet-4-20250514',
        max_tokens: 1024,
        system: systemPrompt,
        messages,
      }),
    });

    if (!response.ok) {
      const errBody = await response.text();
      console.error('Claude API error:', response.status, errBody);
      return res.status(502).json({
        error: 'AI service error',
        message: `Claude API returned ${response.status}`,
      });
    }

    const result = await response.json();
    const reply = result.content?.[0]?.text || 'No response generated.';

    return res.status(200).json({
      success: true,
      data: {
        reply,
        dataDate: context.dateKey,
        model: result.model,
        usage: result.usage,
      },
    });
  } catch (error) {
    console.error('Agent API error:', error);
    return res.status(500).json({
      error: 'Failed to process AI request',
      message: error.message,
    });
  }
}
