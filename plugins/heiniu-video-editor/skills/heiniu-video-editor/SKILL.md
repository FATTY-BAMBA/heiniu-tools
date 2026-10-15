---
name: heiniu-video-editor
description: Edit talking-head short videos (Reels / TikTok / Shorts, 9:16) end to end from raw takes — transcript, pick the good takes, storyboard page to review, one-sentence revisions (「字幕再大一點」「做成雜誌封面」), then render with premium 墨牛-style karaoke captions, giant words behind the head, AI-prompt boxes, before/after reveal, magazine-cover cold open, comment-CTA ending, SFX, loudness and lip-sync-safe cuts. Use this whenever someone uploads phone/camera footage and wants it cut, captioned, made "more premium", turned into a Reel, or says 剪影片、幫我剪、上字幕、短影音、口播、AI 剪輯 — even if they don't mention a skill.
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
4. **Write `edit.json`.** Captions ≤ 9 characters per card with 1–2 key words lit. Effects sparingly: a big word or prompt box every 2–3 beats, `whip_in` on section changes, one `compare` at most, `cta` on the last beat.
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
8. **QA before sending** — open `qa.json`: `av_gap_ms` < 40, `size_mb` ≤ the target. Extract and look at frames at: the first frame, every big word, the compare, the CTA reply, and the last second (`ffmpeg -ss T -i out.mp4 -frames:v 1 f.png`). Check text never covers eyes/mouth and nothing collides. Fix and re-render before delivering.
9. **Deliver** — send the mp4 in chat (that is where they download the full-quality file), then rebuild the room once more with `--delivered <name>.mp4` and republish to the same URL: the page switches to 已交片 with the spec and size, plus one-tap downloads for the cover JPG and an SRT subtitle file. One line on what's in it; suggest adding a trending sound in-app (or mix a royalty-free track via `music`).

## Style (墨牛)
Ink `#1A1A1C` cards with a faint white rim, ivory `#F3EEE4` text, ember `#FF6A1A` accents; serif (Noto Serif TC) for captions, big words and the cover; sans for UI. Calm, premium motion: ease-out entrances, staggered letters, no bouncy cartoons. Override per creator in `style` (brand name, avatar character, accent colour) — never copy another creator's exact look.

Read `references/lessons.md` before modifying any script — it records the bugs (lip-sync drift, loudnorm timestamps, white first frame, mid-sentence freezes) that the engine is built to avoid.

## Files
- `scripts/check_env.py` — FULL / LITE detection.
- `scripts/transcribe.py` — word-timed transcript (SenseVoice via sherpa-onnx, downloaded once) or `--srt`.
- `scripts/storyboard.py` — the review room (`assets/storyboard_template.html`): embedded draft, per-beat play, OK / 要改 verdicts, send-to-Claude with copy fallback, `--prev`/`--change` for revision rounds, `--delivered` for the hand-off.
- `scripts/preview.py` — `--snapshot` before editing; then a before/after clip of only the changed beats.
- `scripts/render.py` — the renderer; `scripts/cover.py` (cover + compare beats), `scripts/colormatch.py`, `scripts/hn_common.py` (fonts, palette, person matte).
- `assets/sfx/` — whoosh, tick, pop, boom.
