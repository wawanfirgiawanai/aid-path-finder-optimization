// Capture README screenshots of the running app (backend :8001 + frontend :3000) with headless Chrome.
// Usage (from the project root, app running):  node docs/capture_screenshots.js
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const WebSocket = require(path.join(__dirname, '..', 'frontend', 'node_modules', 'ws'));

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(__dirname, 'images');
const SESSION = path.join(ROOT, 'dataset', 'test_cases', 'app_sessions', 'MA-MD-01.json');
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].find(p => fs.existsSync(p));
const PORT = 9333;
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function waitForChrome() {
  for (let i = 0; i < 50; i++) {
    try { return await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); } catch { await sleep(200); }
  }
  throw new Error('Chrome did not start');
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'optiroute-shot-'));
  const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
    '--no-first-run', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
  try {
    await waitForChrome();
    const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise(r => ws.once('open', r));
    let id = 0;
    const pending = new Map();
    ws.on('message', m => { const d = JSON.parse(m); if (pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } });
    const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
    const evaluate = async expr => (await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
    const click = text => evaluate(`(() => { const b = [...document.querySelectorAll('button')].find(e => e.textContent.trim() === ${JSON.stringify(text)}); if (!b) return 'not found'; b.click(); return 'ok'; })()`);
    // Real mouse click at the element's centre (Radix tabs ignore element.click())
    const mouseClick = async text => {
      const pos = await evaluate(`(() => { const b = [...document.querySelectorAll('button')].find(e => e.textContent.trim() === ${JSON.stringify(text)}); if (!b) return null; const r = b.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
      if (!pos) return 'not found';
      for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
        await send('Input.dispatchMouseEvent', { type, x: pos[0], y: pos[1], button: 'left', clickCount: 1 });
      }
      return 'ok';
    };
    const shot = async name => {
      const r = await send('Page.captureScreenshot', { format: 'png' });
      fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, 'base64'));
      console.log('saved', name);
    };

    await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 860, deviceScaleFactor: 2, mobile: false });
    await send('Page.enable');
    await send('Page.navigate', { url: 'http://localhost:3000' });
    await sleep(6000);

    console.log('initialize:', await click('Initialize'));
    await sleep(12000);
    await shot('app_network.png');

    const doc = await send('DOM.getDocument');
    const q = await send('DOM.querySelector', { nodeId: doc.result.root.nodeId, selector: 'input[type=file]' });
    await send('DOM.setFileInputFiles', { nodeId: q.result.nodeId, files: [SESSION] });
    await sleep(2000);
    console.log('compare:', await click('Compare All Algorithms'));
    for (let i = 0; i < 90; i++) {  // wait for the comparison to finish, then open its tab
      await sleep(2000);
      await mouseClick('Comparison');
      const done = await evaluate(`[...document.querySelectorAll('button')].some(e => e.textContent.trim() === 'Hybrid A*-GA')`);
      if (done) break;
    }
    console.log('select Hybrid A*-GA:', await mouseClick('Hybrid A*-GA'));
    await sleep(3000);
    await shot('app_comparison.png');

    console.log('experiments:', await click('Run Paper Experiments'));
    await sleep(4000);
    await shot('app_experiments.png');
    ws.close();
  } finally {
    chrome.kill();
  }
})().catch(e => { console.error(e); process.exit(1); });
