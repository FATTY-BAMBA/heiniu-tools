# 黑牛 AI 剪輯 · heiniu-video-editor

A Claude skill (Agent Skills format) that edits talking-head short videos end to end: raw takes → transcript → six styles previewed on your own clip (衝擊字 · 雜誌 · 極簡 · 新聞快報 · 電影感 Vlog · 開箱) → a review room where every beat is approved or changed in one sentence → a finished 1080×1920 video with captions synced to every spoken character, giant words behind the head, prompt boxes, a before/after reveal, a magazine-cover cold open and a comment-CTA ending.

Step-by-step guide (繁體中文): https://fattybamba.com/edit/

## Install

**Claude (web / desktop app), paid plans** — Customize → Plugins → Add → Add marketplace → `FATTY-BAMBA/heiniu-tools` → Add **heiniu-video-editor**. It updates automatically. Turn on Settings → Capabilities → **Code execution and file creation** first.

**Free plan** — download [`heiniu-video-editor.zip`](../../edit/heiniu-video-editor.zip), then Customize → Skills → ＋ → Upload skill.

**Claude Code**

```bash
claude plugin marketplace add FATTY-BAMBA/heiniu-tools
claude plugin install heiniu-video-editor@heiniu-tools
```

## What's inside

`skills/heiniu-video-editor/` — `SKILL.md` (workflow), `references/` (edit.json spec, one-sentence edit catalogue, lessons learned), `scripts/` (environment check, transcription, style templates, caption engine, review room, renderer), `assets/` (storyboard template, sound effects).

Requires ffmpeg, Python 3 with numpy / opencv / Pillow / soundfile, and a Traditional Chinese font. Speech-to-text (sherpa-onnx SenseVoice) and the person matte (u2net human-seg) download once from GitHub on first use; without them the skill runs in a lighter mode.

Made by 黑牛 [@fatty_bamba](https://www.instagram.com/fatty_bamba).
