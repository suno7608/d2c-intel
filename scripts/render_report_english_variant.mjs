#!/usr/bin/env node
console.error(
  'Deprecated: render_report_english_variant.mjs is no longer supported.\n' +
    'Use build_publishable_report.sh, which now runs:\n' +
    '1) translate_report_to_english.sh (KO MD -> EN MD)\n' +
    '2) render_professional_report.mjs <en.md> <index_en.html> en',
);
process.exit(1);
