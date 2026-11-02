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
    if (job.css) await page.addStyleTag({ content: job.css });  // optional layout randomization (detector training)
    for (const [k, v] of Object.entries(job.values)) {
      const el = await page.$(`[name="${k}"]`);
      const tag = await el.evaluate(e => e.tagName);
      if (tag === 'SELECT') await el.selectOption(v); else await el.fill(v);
    }
    if (job.inject) {
      await page.evaluate(t => { const p = document.createElement('p'); p.className = 'inject';
        p.textContent = t; p.style.cssText = 'font:14px Helvetica;margin-top:10px';
        document.querySelector('form').appendChild(p); }, job.inject);
    }
    if (job.forge) {  // forged look-alike text printed next to a field (not inside it)
      await page.evaluate(f => { const el = document.querySelector(`[name="${f.field_key}"]`);
        const s = document.createElement('span'); s.className = 'forge'; s.textContent = f.text;
        s.style.cssText = 'font:14px Helvetica;margin-left:8px'; el.insertAdjacentElement('afterend', s); }, job.forge);
    }
    const fields = await page.$$eval('[name]', els => els.map(e => {
      const r = e.getBoundingClientRect();
      const lab = document.querySelector(`label[for="${e.id}"]`);
      return { field_key: e.name, label: lab ? lab.textContent : '', value: e.value,
               tag: e.tagName.toLowerCase(),
               bbox: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)] };
    }));
    const file = `${job.id}.png`;
    await page.screenshot({ path: path.join(out, file), fullPage: true });
    gold[job.id] = { image: file, split: job.split || null, perturbation: job.perturbation || null, plan_values: job.plan_values || null, template_key: job.template_key, patient_id: job.patient_id || null, injected_text: job.inject || null, injection_target: job.injection_target || null, fields };
  }
  fs.writeFileSync(path.join(out, 'GOLD_BOXES.json'), JSON.stringify(gold, null, 1));
  await browser.close();
})();
