// Render served HTML forms to PNG with gold field boxes from the DOM.
// node tools/render/render_forms.js <base_url> <jobs.json> <out_dir>
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const [base, jobsPath, out] = process.argv.slice(2);
  const jobs = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 1100 }, deviceScaleFactor: 1 });
  await page.addStyleTag({ content: '' }).catch(() => {});
  const gold = {};
  for (const job of jobs) {
    await page.goto(`${base}/forms/${job.template_key}`);
    await page.addStyleTag({ content: 'body{font:15px Helvetica,Arial,sans-serif;margin:24px;width:820px} .row{margin:8px 0} label{display:block;margin-bottom:3px} input,select{width:600px;height:26px;font:14px Helvetica} textarea{width:600px;height:64px;font:13px Helvetica} .banner,.notice{font-size:12px;color:#444}' });
    for (const [k, v] of Object.entries(job.values)) {
      const el = await page.$(`[name="${k}"]`);
      const tag = await el.evaluate(e => e.tagName);
      if (tag === 'SELECT') await el.selectOption(v); else await el.fill(v);
    }
    const fields = await page.$$eval('[name]', els => els.map(e => {
      const r = e.getBoundingClientRect();
      const lab = document.querySelector(`label[for="${e.id}"]`);
      return { field_key: e.name, label: lab ? lab.textContent : '', value: e.value,
               bbox: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)] };
    }));
    const file = `${job.id}.png`;
    await page.screenshot({ path: path.join(out, file), fullPage: true });
    gold[job.id] = { image: file, template_key: job.template_key, patient_id: job.patient_id || null, fields };
  }
  fs.writeFileSync(path.join(out, 'GOLD_BOXES.json'), JSON.stringify(gold, null, 1));
  await browser.close();
})();
