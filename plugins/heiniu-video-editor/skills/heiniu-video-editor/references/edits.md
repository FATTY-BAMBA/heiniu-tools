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
| 放成頭後面的大字 / 字要在頭後面 | `bigwords` entry with `overlap: 0.45` (head covers the lower part of the letters) and a large `size` (400+); 1–3 chars reads best. |
| 這裡太無聊 / 畫面都沒變 / 太平了 | run `scripts/pacing.py`; fix each dead spot with the cheapest effect that fits the line: `punch` on the key word, `bubbles` if it quotes someone/AI, `checklist` for lists or numbers, a `freeze` + 「等一下」 for a twist. |
| 在「X」推近 / 這個字放大畫面 | `punch` at the time of X (scale 1.15–1.2). |
| 做成對話 / 對話泡泡 | `bubbles` with the exchange in short lines (≤ 14 chars each). |
| 做成清單 / 一項一項打勾 | `checklist` with 2–4 items timed to when each is said. |
| 加手機畫面 / 給大家看工具 | `phone` with a phone screenshot or screen recording of the thing named. |
| 打字太慢 / 快轉 | `ramp` on the slow part at 3–4× (muted), real speed for the result. |
| 暫停一下 / 等一下 / 圈起來 | timeline `freeze` (+ `circle` on what to look at). |
| 螢幕錄影被切掉了 | `fit: true` on that clip. |
| 開場從臉拉開 / 拉遠 | `pullback` on the first beat. |
| 穿越轉場 / 衝進去 | `zoom_in: true` on the next clip. |
| 做成圖表 / 數字長出來 | `chart` (2–4 bars; title = the spoken line; 示意 when illustrative). |
| 新聞標題 / 很多標題飛出來 | `headlines` with 2–4 short cards. |
| 換背景 / 綠幕 / 背景放 X | `bg` with the image or clip of X. |
| 剪成貼紙 / 拼貼風 | `sticker` on that beat. |
| 從相框衝出來 | `framebreak`. |
| 加塗鴉 / 手繪框 | `doodle`. |
| 玻璃字 / 毛玻璃 | `style: "glass"` on the big word. |
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
| 換風格 / 換成搞笑、衝擊一點 / 改成 vlog 感 / 想要雜誌感 / 新聞感 | `python3 scripts/template.py edit.json --apply impact` (impact · editorial · minimal · news · vlog · product). Keeps the cut; re-render the draft and republish the room. |
| 標題列改成… / 期數改成 03 | `topic`, `issue` (雜誌), `badge` (新聞快報 / 開箱), then re-apply the same style. |
| 這裡加 emoji / 不要 emoji | caption `emoji: "🔥"` / `emoji: false` (衝擊字). |
| 字幕一次少一點字 | `captions_style.max_chars` 3–4 (衝擊字 / 開箱). |
| 聲音好吵 / 背景很多雜音 / 夜市太吵 | `"voice": "strong"` (default `auto` already cleans; strong removes more but can thin the voice). |
| 聲音不要處理 / 保留原音 | `"voice": "off"`. |
| 加檔案卡 / 顯示素材檔名 | `ui: [{kind:"file", start, files:[{name, meta, badge}]}]` on that beat. |
| 做成進度清單 / 一項一項打勾（剪掉 NG、字幕…） | `ui: [{kind:"steps", start, items:[{text, at:"@word"}…]}]`. |
| 做一個安裝按鈕被點下去 / 游標點 Install | `ui: [{kind:"install", start, name, click_at:"@word"}]`. |
