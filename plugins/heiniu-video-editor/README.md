# 黑牛 AI 剪輯 · heiniu-video-editor

A Claude skill (Agent Skills format) that edits talking-head short videos end to end: raw takes → transcript → storyboard to approve → one-sentence revisions → a finished 1080×1920 video with karaoke captions, giant words behind the head, prompt boxes, a before/after reveal, a magazine-cover cold open and a comment-CTA ending.

Step-by-step guide (繁體中文): https://heiniu-tools.vercel.app/edit/

## Install

**Claude (web / desktop / mobile)** — download [`heiniu-video-editor.zip`](../../edit/heiniu-video-editor.zip), then Customize → Skills → ＋ → Create skill → Upload a skill. Code execution must be enabled.

**Claude Code**

```bash
claude plugin marketplace add FATTY-BAMBA/heiniu-tools
claude plugin install heiniu-video-editor@heiniu-tools
```

## What's inside

`skills/heiniu-video-editor/` — `SKILL.md` (workflow), `references/` (edit.json spec, one-sentence edit catalogue, lessons learned), `scripts/` (environment check, transcription, storyboard page, renderer), `assets/` (storyboard template, sound effects).

Requires ffmpeg, Python 3 with numpy / opencv / Pillow / soundfile, and a Traditional Chinese font. Speech-to-text (sherpa-onnx SenseVoice) and the person matte (u2net human-seg) download once from GitHub on first use; without them the skill runs in a lighter mode.

Made by 黑牛 [@fatty_bamba](https://www.instagram.com/fatty_bamba).
