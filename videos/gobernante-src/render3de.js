// usage: node render.js <w> <h> <fps> <startFrame> <endFrame> <outDir> | or: node render.js still <w> <h> t1,t2,... <outDir>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const a = process.argv.slice(2);
  const still = a[0] === 'still'; if (still) a.shift();
  const w = +a[0], h = +a[1];
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  page.on('console', m => { if (m.type() === 'error') console.log('ERR', m.text()); });
  page.on('pageerror', e => console.log('PAGEERR', e.message));
  await page.goto(`http://localhost:8765/index3de.html?w=${w}&h=${h}`);
  await page.waitForFunction('window.READY===true', null, { timeout: 120000 });
  const save = async (t, file) => { const d = await page.evaluate(t => window.grab(t), t); fs.writeFileSync(file, Buffer.from(d.split(',')[1], 'base64')); };
  if (still) { const out = a[3]; fs.mkdirSync(out, { recursive: true }); for (const t of a[2].split(',')) await save(+t, `${out}/t${(+t).toFixed(2)}.jpg`); }
  else { const fps = +a[2], s = +a[3], e = +a[4], out = a[5]; fs.mkdirSync(out, { recursive: true }); const t0 = Date.now();
    for (let f = s; f < e; f++) { await save(f / fps, `${out}/f${String(f).padStart(5, '0')}.jpg`); if ((f - s) % 50 === 0) console.log(f, ((Date.now() - t0) / 1000).toFixed(0) + 's'); } }
  await browser.close();
})();
