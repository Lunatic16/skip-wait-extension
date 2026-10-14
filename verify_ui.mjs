// Popup UI verification: load the patched extension headless, open popup.html,
// assert the monetization elements are GONE and the popup renders cleanly.
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const EXT_DIR = '/home/god/Downloads/Skip Paywall (unlocked)';

function launch() {
  const args = [
    '--headless=new', '--no-sandbox', '--disable-dev-shm-usage',
    `--load-extension=${EXT_DIR}`,
    `--disable-extensions-except=${EXT_DIR}`,
    '--remote-debugging-port=9226',
    '--user-data-dir=/tmp/skipwait-ui-profile',
    '--no-first-run', 'about:blank',
  ];
  return spawn('/usr/bin/chromium-browser', args, { stdio: ['ignore', 'pipe', 'pipe'] });
}

async function getWsUrl(port) {
  for (let i = 0; i < 30; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/version`);
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch {}
    await sleep(300);
  }
  throw new Error('DevTools endpoint never came up');
}

let ws, msgId = 1;
const pending = new Map();
function send(method, params = {}, sessionId) {
  return new Promise((res, rej) => {
    const id = msgId++;
    const env = { id, method, params };
    if (sessionId) env.sessionId = sessionId;
    pending.set(id, { res, rej });
    ws.send(JSON.stringify(env));
  });
}
function handle(msg) {
  if (msg.id && pending.has(msg.id)) {
    const p = pending.get(msg.id); pending.delete(msg.id);
    msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
  }
}

(async () => {
  const proc = launch();
  const wsUrl = await getWsUrl(9226);
  ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = ev => handle(JSON.parse(ev.data));

  await send('Target.setDiscoverTargets', { discover: true });

  let extId;
  for (let i = 0; i < 40; i++) {
    const r = await send('Target.getTargets');
    const sw = r.targetInfos.find(t => t.type === 'service_worker' && t.url.startsWith('chrome-extension://'));
    if (sw) { extId = new URL(sw.url).host; break; }
    await sleep(300);
  }
  console.log('extension id:', extId);

  const { targetId } = await send('Target.createTarget', { url: `chrome-extension://${extId}/popup.html` });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
  const tab = (m, p = {}) => send(m, p, sessionId);
  const ev = (expression) => tab('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });

  await sleep(2000); // React mount + storage reads

  const r = await ev(`(() => {
    const txt = document.body.innerText || '';
    const checks = {
      hasUsingFree: txt.includes('Using Free'),
      hasFreeToday: txt.includes('Free today'),
      hasUnlockBypass: txt.includes('Unlock Bypass'),
      hasPasteEAS: txt.includes('Paste Your EAS Key'),
      hasActivateBtn: txt.includes('Activate Bypass'),
      hasEASPlaceholder: !!document.querySelector('input[placeholder*="EAS-"]'),
      hasActivePill: txt.includes('Active'),
      hasSupportedSites: txt.includes('Supported Sites'),
      hasSupportSection: txt.includes('Bypass Fix or New Request'),
      textSnippet: txt.replace(/\\s+/g, ' ').slice(0, 400)
    };
    return JSON.stringify(checks);
  })()`);

  const c = JSON.parse(r?.result?.value ?? '{}');
  const gone = ['hasUsingFree', 'hasFreeToday', 'hasUnlockBypass', 'hasPasteEAS', 'hasActivateBtn', 'hasEASPlaceholder'];
  const kept = ['hasActivePill', 'hasSupportedSites', 'hasSupportSection'];

  console.log('--- removed elements ---');
  for (const k of gone) console.log(`  ${k}: ${c[k] ? 'FAIL — still present' : 'PASS — gone'}`);
  console.log('--- retained UI ---');
  for (const k of kept) console.log(`  ${k}: ${c[k] ? 'PASS' : 'FAIL — missing'}`);
  console.log('--- popup text ---');
  console.log(c.textSnippet);

  // React error check: an error boundary crash would blank the popup
  const errCount = await ev(`window.__reactErrors ?? 0`);
  console.log('react error count:', errCount?.result?.value ?? 'n/a');

  proc.kill('SIGTERM');
  process.exit(0);
})().catch(e => { console.error('VERIFICATION ERROR:', e.message); process.exit(1); });
