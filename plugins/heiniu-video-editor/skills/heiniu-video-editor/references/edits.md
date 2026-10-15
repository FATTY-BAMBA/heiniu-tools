# One-sentence edits → what to change in edit.json

People talk in outcomes. Translate the sentence, change the spec, re-render, and say in one line what changed. If a request is ambiguous ("make it pop"), pick the most likely reading, do it, and mention the alternative.

| They say | Change |
|---|---|
| 字幕再大一點 / bigger captions | `captions_style.size` +12 (max ~88). Check the longest caption still fits (≤ 9 chars at 80). |
| 這拍字幕再大一點（one beat） | `size` on each caption of that beat only (global +12 → e.g. 80). |
| 「幾千塊」換成紅色 | add the word to that caption's `keys` and set `color:"red"`. |
| 字幕小一點 | size −8 (min 52). |
| 字幕往上 / 往下 | `captions_style.y` ∓80; keep it out of the face and above the bottom UI zone (y ≤ 1500). |
| 重點字換顏色 / 這個字要亮 | add the word to that caption's `keys`; `color:"red"` for a correction or punchline. |
| 加大字 / 這句要很大 | add a `bigwords` entry on the key word (1–4 chars). |
| 太慢了 / 節奏快一點 | `speed` 1.2→1.3 on talking clips; trim pauses by moving `in`/`out` to word edges. |
| 太快聽不懂 | speed 1.0–1.15 on that clip. |
| 剪掉 NG / 這句不要 | remove the clip or shorten `in`/`out`. Never cut inside a word. |
| 加轉場 | `whip_in: true` on the next clip. Don't use on every cut — every 2–3 beats feels intentional. |
| 推近一點 / 更有電影感 | `push: 0.035`, `crop: 1.12` on alternate clips, `bars: true`, `grade:"soft"`. |
| 讓它更有質感 / 調色 | `grade:"soft"` (or "warm"); optionally add a `compare` item to show before/after. |
| 顏色不一樣 / 這段對比太高 | `match_color: true` on the clips from a different recording. |
| 做成雜誌封面 / 開場要更吸睛 | add a `cover` item at the start. |
| 加留言 CTA / 叫大家留言 | `cta` on the last clip with their keyword and a concrete offer in `sub` ("分鏡模板＋修改指令"). |
| 加音樂 | ask for a royalty-free track (or suggest adding a trending sound in-app), then set `music` at −20 dB; it ducks under the voice automatically. |
| 檔案太大 / 要傳 IG | `output.max_mb` (IG/Threads fine at 30–50, LINE ≤ 25). |

## Things that always look amateur — fix without being asked
- A freeze or effect that starts in the middle of a sentence.
- Text over the face or eyes; captions colliding with a big word or a UI card.
- Long silences between sentences (> 0.35 s at 1.3×).
- Two takes with visibly different colour back-to-back (use `match_color`).
- Voice levels jumping between takes (per-clip `normalize` is on by default — keep it).
