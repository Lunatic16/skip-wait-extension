#!/usr/bin/env python3
"""
Skip Wait de-monetization patcher — complete patch set (v1.4.92, CWS
hdoecnlghjglmnjpnhaaeofcgocdgkhd).

Reproduces every modification in this repository when run against a pristine
unpacked copy of the upstream CRX.

Patch set:
  background.js
    1. License/quota gate `lt` -> always-true stub
    2. Daily meter `ct`       -> no-op (skipWaitFreeDaily never written)
    3. eas-x public-key fetch -> data: URL (never leaves the machine)
    4. eas-x licenses POST    -> data: URL (validate/activate/deactivate fail
                                closed locally, like an offline license server)
  content.js
    5-8. Same four (content-side twins: `nt`, `N`)
  popup.js
    9.  eas-x public-key fetch -> data: URL
    10. eas-x licenses POST    -> data: URL
    11. License section component `nt()` -> returns null
        (removes "Using Free / Free today: 0/5", the "Unlock Bypass" pitch
        card, and the "Paste Your EAS Key" activation card)
    12. Status pill -> always "ACTIVE" (Free / Free-Used-Up branches removed)

Left untouched: manifest.json, hosts.json, the GitHub hosts.json auto-update,
all 178 site-bypass handlers, DNR rules, MAIN-world injections.

Usage: python3 patch_unlocked.py /path/to/unpacked-extension-dir
"""
import sys
import pathlib

# --------------------------------------------------------------------------
# background.js / content.js (parameterized twins)
# --------------------------------------------------------------------------

GATE_BG = (
    "lt=async()=>!!(await(async()=>{if(await F())return!0;"
    "const t=await z();"
    "return!(!t||await D(t))&&!j(t.leaseExp)&&(await Q()).ok&&await F()})())"
    "||(async()=>(await it()).used<5)()"
)
GATE_BG_STUB = "lt=async()=>!0"

METER_BG = (
    "ct=()=>{st=st.then(async()=>{"
    "if(await F())return;"
    "const t=await it();"
    "if(t.used>=5)return;"
    "const e={day:t.day,used:t.used+1};"
    "await(async t=>{await chrome.storage.local.set({[rt]:t})})(e)"
    "})}"
)
METER_BG_STUB = "ct=()=>{}"

GATE_CONTENT = (
    "nt=async()=>!!(await(async()=>{if(await _())return!0;"
    "const t=await A();"
    "return!(!t||await $(t))&&!T(t.leaseExp)&&(await et()).ok&&await _()})())"
    "||(async()=>(await R()).used<5)()"
)
GATE_CONTENT_STUB = "nt=async()=>!0"

METER_CONTENT = (
    "N=()=>{P=P.then(async()=>{"
    "if(await _())return;"
    "const t=await R();"
    "if(t.used>=5)return;"
    "const e={day:t.day,used:t.used+1};"
    "await(async t=>{await chrome.storage.local.set({[M]:t})})(e)"
    "})}"
)
METER_CONTENT_STUB = "N=()=>{}"

# eas-x network dead-ends (background/content use `e`, popup uses `t`)
PK_FETCH_BG = 'const e=await fetch("https://eas-x.com/api/v1/licenses/public-key",{cache:"no-store"});'
PK_FETCH_BG_NEW = 'const e=await fetch("data:text/plain,{}",{cache:"no-store"});'
POST_BG = "fetch(`https://eas-x.com/api/v1/licenses${t}`"
POST_BG_NEW = 'fetch(`data:text/plain,{"kind":"network"}`'

PK_FETCH_POPUP = 'const t=await fetch("https://eas-x.com/api/v1/licenses/public-key",{cache:"no-store"});'
PK_FETCH_POPUP_NEW = 'const t=await fetch("data:text/plain,{}",{cache:"no-store"});'
POST_POPUP = "fetch(`https://eas-x.com/api/v1/licenses${e}`"
POST_POPUP_NEW = 'fetch(`data:text/plain,{"kind":"network"}`'

# popup: status pill — keep only the Active branch
PILL_OLD = (
    '"active"===e?(0,I.jsx)(Ue,{label:Q.statusActive,tone:"live"})'
    ':"freeDone"===e?(0,I.jsx)(Ue,{label:Q.freeExhaustedStatus,tone:"need"})'
    ':(0,I.jsx)(Ue,{label:Q.freeStatus,tone:"busy"})'
)
PILL_NEW = '(0,I.jsx)(Ue,{label:Q.statusActive,tone:"live"})'


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def replace_function_body(src: str, start_marker: str, replacement_body: str):
    """Replace `function NAME(){...}` (start_marker incl. opening brace,
    brace-balanced, string-literal aware) with `function NAME(){replacement_body}`.
    Returns (new_src, bytes_removed) or (src, None) if not found/unbalanced."""
    i = src.find(start_marker)
    if i == -1:
        return src, None
    depth = 0
    k = i + len(start_marker) - 1  # position of the opening '{'
    in_str = None
    while k < len(src):
        ch = src[k]
        if in_str:
            if ch == "\\":
                k += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in "\"'`":
                in_str = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
        k += 1
    if depth != 0:
        return src, None
    end = k + 1
    return src[:i] + start_marker + replacement_body + "}" + src[end:], end - i


def apply(path: pathlib.Path, ops, label: str):
    src = path.read_text()
    for old, new, desc in ops:
        n = src.count(old)
        if n == 0:
            print(f"  [{label}] MISSING: {desc}")
            sys.exit(1)
        if n > 1:
            print(f"  [{label}] AMBIGUOUS ({n}x): {desc}")
            sys.exit(1)
        src = src.replace(old, new, 1)
        print(f"  [{label}] ok: {desc}")
    path.write_text(src)


def main():
    extdir = pathlib.Path(sys.argv[1]).resolve()
    print(f"Patching {extdir}")

    # ---- background.js ----
    apply(extdir / "background.js", [
        (GATE_BG, GATE_BG_STUB, "license/quota gate lt -> always-true"),
        (METER_BG, METER_BG_STUB, "daily meter ct -> no-op"),
        (PK_FETCH_BG, PK_FETCH_BG_NEW, "eas-x public-key fetch -> data: URL"),
        (POST_BG, POST_BG_NEW, "eas-x licenses POST -> data: URL"),
    ], "background")

    # ---- content.js ----
    apply(extdir / "content.js", [
        (GATE_CONTENT, GATE_CONTENT_STUB, "license/quota gate nt -> always-true"),
        (METER_CONTENT, METER_CONTENT_STUB, "daily meter N -> no-op"),
        (PK_FETCH_BG, PK_FETCH_BG_NEW, "eas-x public-key fetch -> data: URL"),
        (POST_BG, POST_BG_NEW, "eas-x licenses POST -> data: URL"),
    ], "content")

    # ---- popup.js ----
    popup = extdir / "popup.js"
    apply(popup, [
        (PK_FETCH_POPUP, PK_FETCH_POPUP_NEW, "eas-x public-key fetch -> data: URL"),
        (POST_POPUP, POST_POPUP_NEW, "eas-x licenses POST -> data: URL"),
        (PILL_OLD, PILL_NEW, "status pill -> always ACTIVE"),
    ], "popup")

    src = popup.read_text()
    new_src, removed = replace_function_body(src, "function nt(){", "return null")
    if removed is None:
        print("  [popup] MISSING: license section nt()")
        sys.exit(1)
    popup.write_text(new_src)
    print(f"  [popup] ok: license section nt() removed ({removed} bytes)")

    print("Done.")


if __name__ == "__main__":
    main()
