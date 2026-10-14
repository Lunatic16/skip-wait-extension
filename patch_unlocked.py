#!/usr/bin/env python3
"""
Skip Wait de-monetization patcher.
- Gates:      licensedCheck -> always true (unlimited, no eas-x dependency)
- Meter:      removes the used>=5 early-return so counters stay functional
              for the popup but can never block
- License fetches: public-key + validate/activate POSTs -> always fail locally
              (no network request is ever made; dead code, but zero eas-x contact)
- popup UI: "Using Free" badge logic unaffected (reads quota, can show 5/5 - harmless),
  purchase/activation card simply never succeeds -> can be left as-is.
Usage: python3 patch_unlocked.py <extdir>
"""
import re
import sys
import pathlib

GATE_BG = (
    "lt=async()=>!!(await(async()=>{if(await F())return!0;const t=await z();"
    "return!(!t||await D(t))&&!j(t.leaseExp)&&(await Q()).ok&&await F()})())"
    "||(async()=>(await it()).used<5)()"
)
GATE_CONTENT = (
    "nt=async()=>!!(await(async()=>{if(await _())return!0;const t=await A();"
    "return!(!t||await $(t))&&!T(t.leaseExp)&&(await et()).ok&&await _()})())"
    "||(async()=>(await R()).used<5)()"
)
GATE_STUB_BG = "lt=async()=>!0"
GATE_STUB_CONTENT = "nt=async()=>!0"

METER_BG = "ct=()=>{st=st.then(async()=>{if(await F())return;const t=await it();if(t.used>=5)return;"
METER_BG_NEW = "ct=()=>{st=st.then(async()=>{"

METER_CONTENT = "N=()=>{P=P.then(async()=>{if(await _())return;const t=await R();if(t.used>=5)return;"
METER_CONTENT_NEW = "N=()=>{P=P.then(async()=>{"

# eas-x public-key fetch: wrapped in try/catch, returns null on failure
# background/content versions
PK_FETCH_B = 'const e=await fetch("https://eas-x.com/api/v1/licenses/public-key",{cache:"no-store"});'
# popup version
PK_FETCH_P = 'const t=await fetch("https://eas-x.com/api/v1/licenses/public-key",{cache:"no-store"});'

# the license validate/activate POST endpoints (template literals)
POST_B = 'fetch(`https://eas-x.com/api/v1/licenses${t}`'
POST_P = 'fetch(`https://eas-x.com/api/v1/licenses${e}`'


def patch_file(path: pathlib.Path, ops: list, label: str):
    src = path.read_text()
    applied = []
    for old, new, desc in ops:
        if old not in src:
            print(f"  [{label}] MISSING: {desc}")
            continue
        n = src.count(old)
        if n > 1:
            print(f"  [{label}] AMBIGUOUS ({n}x): {desc} — SKIPPED")
            continue
        src = src.replace(old, new, 1)
        applied.append((desc, len(old), len(new)))
    path.write_text(src)
    return applied


def main():
    extdir = pathlib.Path(sys.argv[1])
    bg = extdir / "background.js"
    ct = extdir / "content.js"
    pp = extdir / "popup.js"

    print(f"Patching {extdir}:")

    # ---- background.js ----
    ops_bg = [
        (GATE_BG, GATE_STUB_BG, "gate lt() -> always-true"),
        (METER_BG, METER_BG_NEW, "meter ct(): drop quota ceiling"),
        (PK_FETCH_B, 'const e=await fetch("data:text/plain,{}",{cache:"no-store"});', "eas-x public-key fetch -> data: URL (bg)"),
        (POST_B, 'fetch(`data:text/plain,{"kind":"network"}`', "eas-x licenses POST -> data: URL (bg)"),
    ]
    patch_file(bg, ops_bg, "background")

    # ---- content.js ----
    ops_ct = [
        (GATE_CONTENT, GATE_STUB_CONTENT, "gate nt() -> always-true"),
        (METER_CONTENT, METER_CONTENT_NEW, "meter N(): drop quota ceiling"),
        (PK_FETCH_B, 'const e=await fetch("data:text/plain,{}",{cache:"no-store"});', "eas-x public-key fetch -> data: URL (content)"),
        (POST_B, 'fetch(`data:text/plain,{"kind":"network"}`', "eas-x licenses POST -> data: URL (content)"),
    ]
    patch_file(ct, ops_ct, "content")

    # ---- popup.js ----
    # popup has its own meter (v(t)) reading quota — reads are fine; its gate is
    # Le(e.entExp)&&Pe(e.leaseExp) inside status. Purchase/activation uses Qe().
    # Neutralize activation path: make Qe always return network-error.
    ops_pp = [
        (PK_FETCH_P, 'const t=await fetch("data:text/plain,{}",{cache:"no-store"});', "eas-x public-key fetch -> data: URL (popup)"),
        (POST_P, 'fetch(`data:text/plain,{"kind":"network"}`', "eas-x licenses POST -> data: URL (popup)"),
    ]
    patch_file(pp, ops_pp, "popup")


if __name__ == "__main__":
    main()
