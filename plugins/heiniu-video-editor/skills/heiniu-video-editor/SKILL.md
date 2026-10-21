---
name: heiniu-video-editor
description: Edit talking-head short videos (Reels / TikTok / Shorts, 9:16) end to end from raw takes — transcript, pick the good takes, six styles to pick from (衝擊字、雜誌、極簡、新聞快報、電影感、開箱 — previewed on their own clip), a review room, one-sentence revisions (「字幕再大一點」「做成雜誌封面」), then render with premium 墨牛-style karaoke captions, giant words behind the head, AI-prompt boxes, before/after reveal, magazine-cover cold open, comment-CTA ending, SFX, loudness and lip-sync-safe cuts. Use this whenever someone uploads phone/camera footage and wants it cut, captioned, made "more premium", turned into a Reel, or says 剪影片、幫我剪、上字幕、短影音、口播、AI 剪輯 — even if they don't mention a skill.
---

# 黑牛 AI 剪輯 — chat with AI, get a finished video

The promise to the person: **you talk, AI edits.** They upload raw takes (NG included), approve a storyboard, and change anything by writing one sentence. They never open an editing app.

## When the skill starts without footage
Introduce it in a few lines (in the person's language — Traditional Chinese for Taiwan users), then ask for the takes:
> 把原始素材直接丟進來（NG 也沒關係）。我會先給你一份分鏡，你只要用一句話告訴我要改什麼，例如：
> 「字幕再大一點」「這句剪掉」「開場做成雜誌封面」「加留言 EDIT 的結尾」
Also ask for the script if they have one — it fixes transcription mistakes.

## Workflow
Work in a project folder; keep `edit.json` there as the single source of truth (format: `references/spec.md`).

1. **Check the machine** — `python3 scripts/check_env.py`. FULL = everything. LITE = no speech-to-text or no person cut-out: ask for an `.srt` (CapCut / phone auto-captions) and use `place:"low"` big words. Install missing core pieces with the command it prints when you are allowed to.
   Large 4K takes may be too big to upload in a chat; ask for 1080p exports or a linked folder if uploads fail.
2. **Transcribe** — `python3 scripts/transcribe.py take1.mov take2.mov … --out words.json`. Read the printed lines. Correct obvious mishearings against the script (ASR often gets names and slang wrong — e.g. 自己剪 heard as 第幾節). Keep the corrected text for captions.
3. **Pick the takes and plan beats.** For every line of the script choose the cleanest take, cut on word edges, drop NG/repeats and long pauses. Plan the hook in the first 1.5 s (a `cover` cold open, or a giant word on the most surprising phrase). One idea per beat; ~1–3 s per beat at 1.2–1.3×.
4. **Write `edit.json`.** Captions ≤ 9 characters per card with 1–2 key words lit. **The picture must change at least every 3 s** — a talking head that sits still longer is where people swipe. Pick effects by meaning, not decoration (`references/spec.md` → Movement effects): `punch` on the punchline word, `bubbles` when quoting the AI or someone, `checklist` for lists, `phone` when naming a tool, `ramp` over slow screen recordings, a `freeze` + 「等一下」 for a twist; for the one big moment: `pullback`, `headlines`, `framebreak`, `sticker`, `bg`, `doodle`, `chart`, a glass big word or a `zoom_in` cut. Budget: one big moment + 3–5 light effects per reel; `whip_in` on section changes, one `compare` at most, `cta` on the last beat. **Time every effect to a word** (`"words": "words.json"` + `"at": "@幾千塊"` — see spec.md → Word-locked timing), never by guessing seconds. Then run `python3 scripts/pacing.py edit.json` and fix every ⚠ before rendering the draft (the review room also shows them on the beats).
4b. **Pick a style (選風格)** — unless the person already named one (「用搞笑風」 → just `--apply comedy`). Add a one-line `topic` to edit.json, then
   `python3 scripts/template.py edit.json --previews` (≈ 3–4 min: ~3.5 s of THEIR opening in 衝擊字 · 雜誌 · 極簡 · 新聞快報 · 電影感 Vlog · 開箱／業配) and
   `python3 scripts/storyboard.py edit.json --version 0 --styles _render/styles` → publish that page (same capabilities and URL rules as step 5). They tap a card and press 用「…」開始粗剪, which sends `【黑牛剪輯室】<name> v0 選風格：<名稱>（<id>）`.
   Then `python3 scripts/template.py edit.json --apply <id>` and go on to step 5, adding `--styles _render/styles` to every storyboard.py call so 換風格 stays available. A 換風格 message = `--apply <new id>`, re-render the draft, republish to the same URL. Styles are reversible (see spec.md → Style templates); never copy another creator's template names or look.
5. **Rough cut → review room (剪輯室).** Render a draft first — `python3 scripts/render.py edit.json --preview --out _render/draft_v1.mp4 --work _render/w1` (≈ 1–2 min) — then build the room:
   `python3 scripts/storyboard.py edit.json --version 1 --video _render/draft_v1.mp4` → `storyboard.html` (draft embedded, ~1–3 MB).
   **Publish it as an artifact with `capabilities: {"comments": {}, "downloads": true}`** and remember its URL — every later round republishes to the SAME URL so the page they have open reloads itself. (If artifacts or capabilities aren't available, send the HTML file; the page falls back to copy-and-paste.)
   Tell them in two lines: play each beat (▶ 播這拍), mark 這拍 OK or 要改 with one sentence, then press the big button. The page only enables 送出 once every beat has a verdict — that is deliberate (a real review pass, not a skim).
6. **Revision rounds.** Notes arrive either as an artifact comment "sent to Claude" (the page's 送出 button) or pasted in chat. They start with `【黑牛剪輯室】<name> vN 修改` and list `第 NN 拍：…`; beats marked OK are listed as 保持不變 — do not touch them.
   a. `python3 scripts/preview.py edit.json --snapshot` (keeps vN), then translate each note with `references/edits.md` and edit only those beats. An ambiguous note: pick the most likely reading, do it, and say the alternative in the reply.
   b. Re-render the draft (`--preview --out _render/draft_v{N+1}.mp4 --work _render/w{N+1}`) and rebuild the room:
      `python3 scripts/storyboard.py edit.json --version N+1 --video _render/draft_v{N+1}.mp4 --prev _versions/edit.vN.json --change "2=<what you changed, in their words>" …`
   c. Republish to the same artifact URL (the open page reloads to v{N+1}: changed beats tagged 「已修改」, a banner listing the changes, and their previous OKs on untouched beats carried over).
   d. Reply in the comment thread (or chat) in one or two lines: what changed per beat, plus anything you interpreted. Optional for a single small change: `python3 scripts/preview.py edit.json --note "第 02 拍：…"` gives a 修改前｜修改後 clip to attach.
   Repeat until they press 全部 OK（輸出完整版）, which sends `【黑牛剪輯室】<name> vN 全部 OK，請輸出完整版`. That is picture lock: no more changes without a new request.
7. **Final render** — `python3 scripts/render.py edit.json` → `<name>.mp4` + `_render/qa.json`.
8. **QA before sending** — open `qa.json`: `av_gap_ms` < 40, `size_mb` ≤ the target, `dead_spots` and `face_collisions` empty. Extract and look at frames at: the first frame, every big word, the compare, the CTA reply, and the last second (`ffmpeg -ss T -i out.mp4 -frames:v 1 f.png`). Check text never covers eyes/mouth and nothing collides. Fix and re-render before delivering.
9. **Deliver** — send the mp4 in chat too (a full-quality copy they always have). Then rebuild the room with `--delivered <name>.mp4` and republish to the SAME URL **with the video attached**: the script prints the `files` mapping, e.g. `files: {"<name>.mp4": "/abs/path/<name>.mp4"}` (it makes `<name>_download.mp4` ≤ 14 MB when the master is larger, because one attached file can be at most 15 MB). The page switches to 已交片: a big 「⬇ 下載完整影片」 button (in the panel and the bottom bar), plus cover JPG and SRT subtitles. If attaching files isn't possible here, publish without `files` — the page then says the video is in the chat. One line on what's in it; suggest adding a trending sound in-app (or mix a royalty-free track via `music`).

## Style (墨牛)
Ink `#1A1A1C` cards with a faint white rim, ivory `#F3EEE4` text, ember `#FF6A1A` accents; serif (Noto Serif TC) for captions, big words and the cover; sans for UI. Calm, premium motion: ease-out entrances, staggered letters, no bouncy cartoons. Override per creator in `style` (brand name, avatar character, accent colour) — never copy another creator's exact look.

Read `references/lessons.md` before modifying any script — it records the bugs (lip-sync drift, loudnorm timestamps, white first frame, mid-sentence freezes) that the engine is built to avoid.

## Files
- `scripts/check_env.py` — FULL / LITE detection.
- `scripts/transcribe.py` — word-timed transcript (SenseVoice via sherpa-onnx, downloaded once) or `--srt`.
- `scripts/storyboard.py` — the review room (`assets/storyboard_template.html`): embedded draft, per-beat play, OK / 要改 verdicts, send-to-Claude with copy fallback, `--prev`/`--change` for revision rounds, `--delivered` for the hand-off.
- `scripts/preview.py` — `--snapshot` before editing; then a before/after clip of only the changed beats.
- `scripts/template.py` — style templates: `--list`, `--previews` (選風格 cards), `--apply <id>`, `--reel` (same opening in all six styles + 「你選哪一個？」 grid — a ready-made post).
- `scripts/captions.py` — caption engine v2: per-character timing aligned to the transcript, chunk / line modes, pop · rise · blur entrances, spoken-word highlight, strips, labels, scrims, emoji.
- `scripts/pacing.py` — dead-spot checker (also in `qa.json` and on the review-room beats).
- `scripts/render.py` — the renderer; `scripts/cover.py` (cover + compare beats), `scripts/colormatch.py`, `scripts/hn_common.py` (fonts, palette, person matte).
- `assets/sfx/` — whoosh, tick, pop, boom.
