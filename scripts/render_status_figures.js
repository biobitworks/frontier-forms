// Render docs/figures/accomplishment_heatmap.html to a static PNG (light theme).
// Usage: node scripts/render_status_figures.js   (needs Playwright + Chromium)
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const root = path.resolve(__dirname, '..');
  const b = await chromium.launch(process.env.PW_EXECUTABLE ? { executablePath: process.env.PW_EXECUTABLE } : {});
  const p = await b.newPage({ viewport: { width: 1220, height: 900 }, deviceScaleFactor: 1.5, colorScheme: 'light' });
  const errors = [];
  p.on('pageerror', e => errors.push(e.message));
  const name = process.argv[2] === 'gains' ? 'gains_heatmap' : 'accomplishment_heatmap';
  await p.goto('file://' + path.join(root, 'docs/figures/' + name + '.html'));
  await p.waitForTimeout(300);
  await p.evaluate(() => { const t = document.getElementById('theme'); if (t) t.style.display = 'none'; });
  await p.screenshot({ path: path.join(root, 'docs/figures/' + name + '.png'), fullPage: true });
  await b.close();
  if (errors.length) { console.error(errors); process.exit(1); }
  console.log('wrote docs/figures/' + name + '.png');
})();
