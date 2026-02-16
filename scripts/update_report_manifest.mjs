#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function usage() {
  console.error('Usage: node update_report_manifest.mjs <reports_html_root> <manifest_output>');
  process.exit(1);
}

function isDateDir(name) {
  return /^\d{4}-\d{2}-\d{2}$/.test(name);
}

function main() {
  const [, , reportsHtmlRoot, manifestOutput] = process.argv;
  if (!reportsHtmlRoot || !manifestOutput) usage();

  const root = path.resolve(reportsHtmlRoot);
  const out = path.resolve(manifestOutput);

  const entries = [];
  for (const name of fs.readdirSync(root)) {
    if (!isDateDir(name)) continue;
    const metaFile = path.join(root, name, 'metadata.json');
    if (!fs.existsSync(metaFile)) continue;
    try {
      const obj = JSON.parse(fs.readFileSync(metaFile, 'utf8'));
      entries.push(obj);
    } catch {
      // skip broken metadata
    }
  }

  entries.sort((a, b) => (a.week < b.week ? 1 : a.week > b.week ? -1 : 0));

  const manifest = {
    generated_at: new Date().toISOString(),
    total_weeks: entries.length,
    latest_week: entries[0]?.week ?? null,
    weeks: entries,
  };

  fs.writeFileSync(out, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  console.log(`Manifest written: ${out}`);
}

main();
