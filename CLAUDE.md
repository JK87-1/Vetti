# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository shape

This repo is a single self-contained prototype: **`vetti_toss.html`** (~1350 lines, ~5 MB). No build system, no package manager, no tests. HTML, CSS, and JS all live in this one file, with base64-encoded product images embedded inline in the `IMGS` object (this is why the file is multi-megabyte — do not try to read the whole file in one `Read` call; it will blow the token budget).

UI copy and comments are in Korean. The product is "VETTI", a mobile-first (max-width 430px) custom leather-goods configurator styled after Toss.

## Running / previewing

Just open the file in a browser:

```sh
open vetti_toss.html
```

No server, no compile step. Edits are live on reload.

## Architecture

**Screen model.** Five `<div class="scr">` sections switched by `go(id)` (line ~1011) which toggles the `.on` class. IDs: `s-home`, `s-step1`, `s-result`, `s-workorder`, `s-sent`. Only one screen is visible at a time.

**State.** A single mutable object `S = {mat, col, sz, hw, mono, cv, rv}` (line ~953) holds the current configuration. Lookup helpers `gm/gc/gs/gh` resolve the selected option from the `MATS`, `COLS`, `SZS`, `HWS` arrays. Price is derived via `gtot()` = `BASE + deltas`; any option change must flow through `updatePrice()` / `updateTag()` / `updateColName()` to keep the UI in sync.

**Image pipeline.** Product previews are rendered on `<canvas>`:
1. `loadImg(v)` decodes a base64 entry from `IMGS` into an `ImageBitmap`-like cache (`CACHE`).
2. `colorize(canvas, cache, cr, cg, cb)` recolors the cached pixels per the selected `COLS` RGB.
3. `drawOrig` / `renderPreview` / `setView(n)` / `setRV(n)` drive which angle (front/side/back, `VL`) is shown.

When adding a new material or color, update the matching array **and** ensure an `IMGS` entry exists for each view index used by `setView`/`setRV`.

**Flow.** `home → step1 (configure) → result (AI preview) → workorder (summary) → sent`. `goAI()` (line ~1146) is the async handoff from step1 to result. `buildWO()` assembles the work-order payload and `sendWO()` finalizes it (currently just a `toast`).

## Conventions worth knowing

- CSS uses Korean-labeled section banners (`/* ══════════ HOME ══════════ */`) — keep that style when adding screens so the file stays navigable.
- Color tokens live in `:root` (`--black`, `--gold`, etc.). Prefer these over hard-coded hex.
- The `IMGS` blob dominates the file. When diffing or searching, restrict tools to line ranges outside ~915–920 or use `Grep` rather than `Read` on the whole file.
