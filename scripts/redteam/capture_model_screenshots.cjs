#!/usr/bin/env node
// Headless-Chromium (Playwright) screenshots and PDFs of the local form server, one filled form per model.
// Starts scripts/redteam/form_server.py on 127.0.0.1 against docs/demo (committed annotations holding each model's
// actual per-field answers), then for every annotated image x model x {boxes on, off} saves
// docs/demo/screenshots/models/<id>__<model>__boxes|noboxes.png, plus a PDF of the boxes-on view, and writes
// capture_manifest.json with the sha256 of every output. No external host is contacted. Synthetic data only.
//   node scripts/redteam/capture_model_screenshots.cjs
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path'), crypto = require('crypto'), http = require('http');
const R = path.resolve(__dirname, '../..'), D = path.join(R, 'docs/demo'), PORT = 8791;
const MODELS = ['qwen2.5vl:3b', 'apple_vision_parser', 'qwen2.5:1.5b', 'qwen3:1.7b'];
const up = () => new Promise(r => http.get(`http://127.0.0.1:${PORT}/`, res => { res.resume(); r(true); }).on('error', () => r(false)));
(async () => {
  const srv = spawn('python3', [path.join(R, 'scripts/redteam/form_server.py'), '--root', D, '--port', String(PORT)], { stdio: 'ignore' });
  try {
    for (let i = 0; i < 50 && !(await up()); i++) await new Promise(r => setTimeout(r, 200));
    const out = path.join(D, 'screenshots/models'); fs.mkdirSync(out, { recursive: true });
    const ids = fs.readdirSync(path.join(D, 'ann')).filter(f => f.endsWith('.json')).map(f => f.slice(0, -5)).sort();
    const br = await chromium.launch(); const pg = await br.newPage({ viewport: { width: 1440, height: 820 } });
    const made = [];
    for (const id of ids) for (const m of MODELS) for (const bx of ['1', '0']) {
      const stem = `${id}__${m.replace(':', '_')}__${bx === '1' ? 'boxes' : 'noboxes'}`;
      await pg.goto(`http://127.0.0.1:${PORT}/viewer.html?id=${id}&model=${encodeURIComponent(m)}&boxes=${bx}`, { waitUntil: 'networkidle' });
      await pg.screenshot({ path: path.join(out, stem + '.png'), fullPage: true }); made.push(stem + '.png');
      if (bx === '1') { await pg.emulateMedia({ media: 'screen' }); await pg.pdf({ path: path.join(out, stem + '.pdf'), width: '1440px', height: '900px', printBackground: true }); made.push(stem + '.pdf'); }
    }
    await pg.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'networkidle' });
    await pg.screenshot({ path: path.join(D, 'screenshots/index_models.png'), fullPage: true });
    const ver = br.version(); await br.close();
    const files = {}; for (const f of made) files[f] = crypto.createHash('sha256').update(fs.readFileSync(path.join(out, f))).digest('hex');
    fs.writeFileSync(path.join(out, 'capture_manifest.json'), JSON.stringify({ schema: 'redteam.model_screenshots.v1', browser: `headless Chromium ${ver} (Playwright)`,
      server: 'scripts/redteam/form_server.py on 127.0.0.1', images: ids.length, models: MODELS, files,
      note: "Each form is filled with that model's actual exported answers; green = matches the printed value, red = mismatch. Synthetic data only." }, null, 1) + '\n');
    console.log('CAPTURED', made.length, 'files for', ids.length, 'images x', MODELS.length, 'models');
  } finally { srv.kill(); }
})().catch(e => { console.error(e); process.exit(1); });
