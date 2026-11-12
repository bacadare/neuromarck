// Exporta la animación de index.html a MP4, cuadro a cuadro.
// Requiere Node, Playwright (Chromium) y ffmpeg.
//
//   node render.js                     -> arquetipos-vertical.mp4   (1080x1920)
//   node render.js 1920 1080 salida.mp4
//   node render.js 1080 1920 prueba.png 7.2   -> un solo cuadro en t = 7.2 s
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const W = +process.argv[2] || 1080;
const H = +process.argv[3] || 1920;
const OUT = process.argv[4] || 'arquetipos-vertical.mp4';
const STILL = process.argv[5];
const FPS = 30, DURATION = 30;
const TYPES = { '.html': 'text/html', '.woff2': 'font/woff2', '.js': 'text/javascript' };

(async () => {
  const server = http.createServer((req, res) => {
    const file = path.join(__dirname, path.normalize(decodeURIComponent(req.url.split('?')[0])).replace(/^([/\\]|\.\.)+/, '') || 'index.html');
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
      res.end(data);
    });
  }).listen(0, '127.0.0.1');
  await new Promise(r => server.once('listening', r));

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html?w=${W}&h=${H}&capture=1`);
  await page.waitForFunction('window.ready === true');
  const canvas = page.locator('#c');

  if (STILL !== undefined) {
    await page.evaluate(t => window.renderFrame(t), +STILL);
    await canvas.screenshot({ path: OUT });
  } else {
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-f', 'image2pipe', '-c:v', 'png', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT],
      { stdio: ['pipe', 'inherit', 'inherit'] });
    const done = new Promise((res, rej) => ff.on('close', c => c ? rej(new Error('ffmpeg ' + c)) : res()));
    for (let f = 0; f < FPS * DURATION; f++) {
      await page.evaluate(t => window.renderFrame(t), f / FPS);
      const png = await canvas.screenshot({ type: 'png' });
      if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r));
      if (f % 150 === 0) console.log(`cuadro ${f}/${FPS * DURATION}`);
    }
    ff.stdin.end();
    await done;
  }
  await browser.close();
  server.close();
  console.log('listo:', OUT);
})().catch(e => { console.error(e); process.exit(1); });
