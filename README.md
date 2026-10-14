<div align="center">

<img src="icon.png" width="96" height="96" alt="Skip Wait icon" />

# Skip Wait — Unlocked

A de-monetized, license-free personal build of **Skip Wait — Bypass Timers & Countdowns** (v1.4.92).

Unofficial. Not affiliated with the original developer. Personal use only — see [Disclaimers](#disclaimers).

![Manifest](https://img.shields.io/badge/Manifest-V3-4285F4?style=flat-square&logo=chromewebstore&logoColor=white)
![Chromium](https://img.shields.io/badge/verified%20on-Chromium%20154-34A853?style=flat-square&logo=googlechrome&logoColor=white)
![Upstream](https://img.shields.io/badge/upstream-v1.4.92-8ab4f8?style=flat-square)
![Bypasses](https://img.shields.io/badge/site%20handlers-178%20·%20322%20hosts-f59e0b?style=flat-square)

</div>

---

## What is this?

The upstream extension automates past countdown timers, wait pages, and "click continue" gates on URL shorteners, file hosts, and safelink sites. It is genuinely well-engineered — per-site handlers replay CSRF-protected forms, declarativeNetRequest header surgery, MAIN-world WebSocket protocol forging (notably work.ink's XOR-keyed gate), and a live site-config fetched from GitHub.

It also ships a freemium envelope around all of it: **5 free bypasses/day**, a **$5/2-month license** (EdDSA-signed leases from `eas-x.com`), and per-device activation. Every one of the 178 handlers funnels through the same license-or-quota gate before doing anything.

This build removes that envelope. All bypass logic is untouched.

## What was changed

Surgical edits across the three minified bundles, applied by [`patch_unlocked.py`](patch_unlocked.py):

| # | File | Original | Patched | Effect |
|---|------|----------|---------|--------|
| 1 | `background.js` | gate: licensed check OR `used < 5` | `lt = async () => true` | Background gate always passes |
| 2 | `content.js` | gate: licensed check OR `used < 5` | `nt = async () => true` | Content-script gate always passes |
| 3 | `background.js` | meter writes daily counter | `ct = () => {}` | Quota counter never written |
| 4 | `content.js` | meter writes daily counter | `N = () => {}` | Content-side counter never written |
| 5 | all three | `fetch("https://eas-x.com/…")` | `fetch("data:text/plain,…")` | Zero license-server contact possible |
| 6 | `popup.js` | license section component | `return null` | "Using Free" / "Unlock Bypass" / "Paste Your EAS Key" cards removed |
| 7 | `popup.js` | status pill Free / Free-Used-Up branches | removed | Pill always shows **ACTIVE** |

<details>
<summary><strong>How the enforcement worked (reverse-engineering notes)</strong></summary>

The gate logic is duplicated three times — once per execution context (`background.js`, `content.js`, `popup.js`), minified with different identifier names per bundle. All 178 handlers call through the same two-function choke point per bundle:

```js
gate  = licensed ? true : (await readQuota()).used < 5
hosts = await getHosts(siteKey); return hosts.length && await gate() ? hosts : []
```

The licensed path: an EAS key activates against `eas-x.com/api/v1/licenses`, which returns an EdDSA (`Ed25519`) lease token — verified client-side against a fetched public key (`kid`-pinned, `iss`/`aud`/`nonce` checked), with offline lease expiry, entitlement expiry, one-key-per-device instance GUIDs, and idempotency keys on the POSTs. Genuinely competent licensing engineering — it just lives in the way.

The free path: a day-stamped `{day, used}` counter in `chrome.storage.local`, ceiling 5, incremented by a serialized-promise meter on every gated action.

Because the service worker is an ES module, the minified gate functions are module-lexical — unreachable from `Runtime.evaluate`, and invisible to everything downstream once stubbed in-source. Every handler, message listener, and DNR rule installer just sees "licensed".

</details>

<details>
<summary><strong>What still phones out (deliberately untouched)</strong></summary>

| Destination | Purpose |
|---|---|
| `raw.githubusercontent.com/sharoon7171/skip-wait-public` | Live site-config (`hosts.json`) — keeps the 178 handlers current; removing it would freeze the extension |
| Per-site bypass traffic | linkvertise GraphQL, `backendapi.dlsurf.com`, `icanhazip.com` (IP for one shortener's session PATCH), `rep.prmovies3.online` relay — upstream bypass behavior |
| GitHub issues / Telegram / email links | Support links in the popup footer |

Everything else — cookie writes (a single `ab=1` on adlinkfly hosts), DNR session rules, MAIN-world injections — is upstream behavior, unchanged.

</details>

## Verification

Behavioral, not static: the patched build was loaded unpacked into headless Chromium 154 and driven over CDP through its real public API surface (`chrome.runtime.sendMessage`, `chrome.storage`), with in-realm fetch watchdogs installed in both the service worker and popup contexts.

| Test | Method | Result |
|------|--------|--------|
| Gate passes through real message pipeline | `AROLINKS_HOP` must not return `err:"license"` | ✅ passes |
| Gate immune to hostile state | quota forced to `used: 9999`, re-tested | ✅ still unlocked |
| Meter dead | 20× meter invocations → `chrome.storage` read | ✅ counter never written |
| Zero license-server contact | `self.fetch` watchdog, SW + popup realms | ✅ 0 requests |
| Popup UI | innerText assertions on rendered popup | ✅ monetization gone, retained UI intact |
| Bundle syntax | `node --check` on all three | ✅ clean |

Run it yourself:

```bash
node verify.mjs      # gate / meter / eas-x behavioral tests
node verify_ui.mjs   # popup UI assertions
```

## Install

1. `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select this directory

> If you kept the pristine upstream copy locally (e.g. `../Skip Paywall/`), keep it outside the repo — it's useful for diffing, but shouldn't be published.

## Re-patching a future upstream release

The patcher is idempotent against pristine bundles and reports `MISSING` for any pattern upstream renamed:

```bash
# fetch the new CRX from the Chrome Web Store, unpack it, then:
python3 patch_unlocked.py /path/to/unpacked-copy
```

## Project layout

```
.
├── manifest.json        # untouched (MV3, <all_urls>, DNR, scripting)
├── background.js        # patched: gate stub, meter no-op, eas-x dead-end
├── content.js           # patched: same
├── popup.js             # patched: same + license section removed
├── hosts.json           # untouched site-config (178 handlers / 322 hosts)
├── patch_unlocked.py    # the patcher
├── verify.mjs           # CDP behavioral verification
└── verify_ui.mjs        # CDP popup verification
```

## ⚠️ Disclaimers

- **Unofficial.** This is a modified build of [Skip Wait](https://chromewebstore.google.com/detail/hdoecnlghjglmnjpnhaaeofcgocdgkhd) by sharoon7171. All credit for the bypass engineering belongs to the original developer.
- **Personal use.** This build removes the developer's licensing revenue. Don't redistribute it or upload it to the Chrome Web Store — and if the extension is useful to you, [buy a license](https://eas-x.com/products/skip-wait-bypass-timers-countdowns-chrome-extension-license); it's $5.
- **No warranty.** The extension's purpose is defeating wait/ad gates; using it against those sites violates their terms. That judgement call is yours.
- **No auto-updates.** Unpacked extensions don't receive Web Store updates; re-patch new versions manually.

---

<div align="center">
Published for research into MV3 extension enforcement architecture ·
Upstream: <a href="https://github.com/sharoon7171">sharoon7171</a> ·
<a href="https://chromewebstore.google.com/detail/hdoecnlghjglmnjpnhaaeofcgocdgkhd">Chrome Web Store</a>
</div>
