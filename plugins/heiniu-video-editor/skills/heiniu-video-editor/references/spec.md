# edit.json — the single source of truth for an edit

`render.py` and `storyboard.py` both read this file. Every one-sentence change the person asks for becomes a change here, then you re-render.
All times inside a clip are **source seconds of that clip's file** (what `transcribe.py` prints), so you never have to recompute the output timeline yourself.

```json
{
  "name": "my-video",                       // output file name (my-video.mp4) and storyboard id
  "output": {"w": 1080, "h": 1920, "fps": 30, "max_mb": 30, "lufs": -14},
  "style": {"brand": "黑牛", "avatar": "牛", "accent": "#FF6A1A", "ink": "#1A1A1C", "ivory": "#F3EEE4"},
  "grade": "soft",                          // default for clips: soft | warm | none | any ffmpeg filter string
  "speed": 1.0,                             // default clip speed
  "bars": false, "bars_px": 200,            // cinematic black bars (default off)
  "captions_style": {"size": 64, "y": 1330, "look": "card"},// size, vertical centre (1080x1920 units), look: card | clean | bold | meme | label
  "topic": "月薪 6 萬，錢去哪了？",          // one-line topic: the header bar of the 知識乾貨 / 開箱 styles (else the first caption)
  "template": "knowledge",                  // written by scripts/template.py — never edit by hand (see Style templates below)
  "music": {"src": "track.mp3", "gain_db": -20, "start": 0, "fade_out": 2.0},   // optional; ducked under the voice
  "voice": "auto",                          // voice clean-up: auto (sized to each take's noise) | strong | off — qa.json "voice" reports SNR per take
  "timeline": [ ...items, played in order... ]
}
```

## Timeline items

### `clip` — a piece of a take
| field | meaning |
|---|---|
| `src`, `in`, `out` | file and source seconds. Cut on word boundaries from the transcript (start ≈ 0.05 s before the first character, end ≈ 0.2 s after the last). |
| `speed` | 1.0–1.4 for talking (1.2–1.3 feels "energetic" without chipmunk voice). Use 1.0 on beats people must read. |
| `crop` | 1.0 = full frame; 1.1–1.2 = tighter "punch-in" shot for variety. |
| `grade`, `bars` | override the defaults for this clip. |
| `push` | slow push-in amount across the clip, e.g. 0.035. |
| `whip_in` | zoom + motion-blur transition into this clip, with a whoosh. |
| `match_color` | `true` (or a timeline index) when this take was shot in different light — matches brightness/colour to that clip. |
| `normalize` | per-clip loudness levelling (default true). |
| `captions` | `[{text, keys:[...], start, end, size?, y?, instant?}]` karaoke captions; `keys` are lit in the accent colour. Keep each ≤ 9 characters, split long lines. |
| `bigwords` | `[{word, start, end, size?, place?: "auto"|"low", overlap?}]` giant serif word typed in letter by letter. `auto` puts it above the head with the head in front (needs the person matte); falls back to `low` (lower third) when there is no head-room. `overlap` (0.10 default … 0.5) sets how much of the letters the head covers — use ~0.45 for 「放在頭後面」. Captions hide while a low word shows. |
| `prompts` | `[{text, start, send?, end?, label?}]` the cream 「對 AI 說」 box at the top typing the instruction, pressing send, ✓. Time `send` to land on the word it refers to. |
| `cta` | comment call-to-action on glass cards: `{show, type_at?, heart_at?, reply_at?, keyword, headline?, sub, reply, author?}`. Captions hide once it shows. Put `reply_at` ≥ 1.2 s before the clip ends so people can read it. |
| `shot`, `transition`, `sound`, `notes` | text only, shown on the storyboard card. |

### `cover` — magazine-cover cold open (≈1.4 s)
`{type:"cover", src, at, dur:1.4, crop?, masthead, issue:[left, centre, right], kicker?, headline:[line1, line2], stat:[big, small], barcode?, barcode_text?, occlude?:true}`
Pick `at` on a frame where the person is smiling, eyes open, centred. The masthead sits behind the head when the matte is available.

### `compare` — before/after reveal on a freeze (≈2.6 s)
`{type:"compare", src, at, crop?, dur:2.625, sweep:1.9, grade_to:"soft", bars_after:true, label_after:"AI 調色", label_before:"原始"}`
Starts on the untouched frame; a slanted line slides slowly left→right revealing the graded frame. Place it **after** the sentence that announces the change, never mid-sentence. Use `at` = the clip's `out`, so the freeze matches the last frame.


## Movement effects (keep the picture changing every ≤ 3 s)
Times are source seconds, like captions. Budget per reel: one big moment + 3–5 light effects; `python3 scripts/pacing.py edit.json` lists dead spots.

| Field | Shape | What it does |
|---|---|---|
| `punch` | `[{at, scale?: 1.18, until?, y?: 0.38}]` | Hard punch-in (60 ms snap) on a word, held until `until` or the clip end. Use on the punchline / key number. |
| `bubbles` | `[{who: "me"|"ai", text, start, end?}]` | Chat bubbles stack up from just above the bottom UI zone (below the chin); newest at the bottom, max 3. Captions step aside while they show (`captions_over: true` keeps them). `pop` SFX. |
| `checklist` | `{start, end?, title?, side?: "left"|"right"|"center", width?: 360, bottom?: 1240, items: [{text, at}]}` | Glass card; each item ticks at `at` with a `tick`. Side card keeps the face clear. |
| `phone` | `{src, start, end?, width?: 0.46, x?: 0.5, top?: 1060, scroll?: 1.0, src_in?: 0}` | Phone slides up from the bottom edge and stops below the chin. `src` = a phone screenshot (scrolls by `scroll`) or a video. Captions hide under it. |
| `ramp` | `[{from, to, speed?: 3, mute?: true}]` | Speed ramp inside one clip (e.g. typing at 3× then real speed for the result). Fast part shows a 「▶▶ 3×」 badge — never hide a speed-up. |
| `fit` | `true` (+ `fit_width?`, `fit_y?`) | Landscape screen recording shown whole on a blurred, dimmed copy of itself (instead of cropping to 9:16). |
| timeline `freeze` | `{type: "freeze", src, at, dur?: 1.0, text?: "等一下", circle?: [cx, cy, r], text_y?}` | Held frame with drained colour, a red 「等一下」 stamp and an optional self-drawing red circle (1080×1920 coords); record scratch. Put the next clip's `in` at `at`. |

### Cut-out & depth effects (need the person matte — FULL mode)
| Field | Shape | What it does |
|---|---|---|
| `pullback` | `{at?, from?: 1.6, dur?: 0.8, y?: 0.32}` | Pull-back reveal: starts tight on the face and releases to the full shot. Best on the first beat. |
| `zoom_in` | `true` | Zoom-through transition into this clip (the cut zooms through the frame). Use instead of `whip_in` once or twice per reel. |
| `chart` | `{start, end?, title?, unit?, bars: [{label, value}], width?: 820, height?: 330, bottom?: 1510}` | Bar chart grows with counting numbers (highest bar in ember). The `title` replaces the caption while it shows — write the spoken line there. Mark made-up numbers as 示意. |
| `headlines` | `{start, end?, behind?: true, cards: [{text, src?, at, slot?: [x, y, rot]}]}` | Headline wall: paper clippings slam in around the head — behind the person. Up to 6 slots. Never imitate a real news brand; `src` is a short label like 「帳單 · 03/01」. |
| `bg` | `{src, start, end?, blur?, dim?}` | Green screen without a green screen: replaces the background behind the person with an image or video. |
| `sticker` | `{start, end?, paper?: "#F3EEE4", outline?: 16, tilt?: -3, scale?: 0.86}` | The person as a die-cut sticker (white outline, shadow, paper grain), tilted. |
| `framebreak` | `{start, end?, box?: [x0, y0, x1, y1], paper?: "#1A1A1C", border?: 22}` | The shot sits in a framed photo and the head breaks out over the top edge. Without `box` the frame is placed from the head automatically. |
| `doodle` | `{start, end?, color?: "#FFFFFF", gap?: 22, doodles?: true}` | Hand-drawn outline around the person that "boils" (re-draws every 3 frames), plus a heart and an ember star by the head. |
| `bigwords[].style` | `"glass"` | Frosted-glass letters (blurred background, white rim, soft shadow) instead of solid ivory. |
Not built on purpose: vertigo (dolly zoom) and orbit — they need a moving camera when filming; faking them from a locked-off shot looks cheap.

## Word-locked timing (how effects land on the right spot)
Set `"words": "words.json"` (the transcribe.py output) at the top of edit.json. Then any time field can name the word instead of a number:
`"at": "@幾千塊"` · `"start": "@工具"` · `"@知道#2"` (the 2nd time it's said in that clip) · `{"word": "6萬", "offset": -0.1}`.
Start-type fields (`at`, `start`, `send`, `show`, `from`…) land 2 frames **before** the word starts — editors cut on anticipation;
end-type fields (`end`, `until`, `to`) land just **after** the word ends. The search stays inside the clip's `in`–`out`.
Rules the engine also enforces: whoosh/swish peaks land exactly on the cut or impact; effects that run to the end of their shot leave with the cut (no fade mid-word); impacts (big words, stamps, slams) get a 5-frame decaying shake; pops overshoot ~6%; punch snaps are motion-blurred. `qa.json` lists `face_collisions` (any card, bubble, chart or phone covering > 6 % of the face) — fix every one before delivering.

## Style templates (風格) — `scripts/template.py`
One cut, six looks, built on the style families top short-form editors and caption tools converge on (impact word-by-word,
editorial serif, minimal, news strip, cinematic vlog, product labels) — in our own look, never a copy of one creator.
Write the base `edit.json` as usual (takes, captions with `keys`, effects chosen by meaning, a one-line `topic`), then:
`template.py edit.json --previews` renders ~3.5 s of the person's own opening in every style (≈ 3–4 min) into `_render/styles/` + `styles.json`;
`storyboard.py edit.json --version 0 --styles _render/styles` is the 選風格 page; `template.py edit.json --apply <id>` rewrites edit.json in that style.
Switching is safe: the template keeps everything it removed in `_off`, marks what it added (`_tpl_keys`, `_tpl` items, `_dropped`), and
`--apply` restores the base before applying the new one. Make content edits on the templated file as normal.

| id | name | captions (`captions_style.look`) | grade | also | picture changes at least every |
|---|---|---|---|---|---|
| `impact` | 衝擊字 | heavy white + thick black outline, 2–5 characters at a time synced to the voice, spoken character yellow, keys green, chunk pops, emoji on up to 3 key ideas (never over the mouth) | `punchy` | punch 1.25× held 0.5 s on keys, freeze 「蛤？」 after the first red-caption beat, shake ×1.5 | 2.5 s |
| `editorial` | 雜誌 | serif line building as it is spoken (characters rise in), keys slanted in accent, accent rule grows under the line | `soft` | masthead (brand · `issue` · topic), glass big words behind the head | 3 s |
| `minimal` | 極簡 | small clean sans, upcoming words faint, each character sharpens out of a blur | `muted` (desaturated, one accent) | strips big graphics, slow push, quiet SFX | 4.5 s |
| `news` | 新聞快報 | white on a black strip that slides in (red edge), spoken character yellow | `crisp` | red 快報 tag + headline bar (`badge`, `topic`), numbers punch, big words in the lower third | 3 s |
| `vlog` | 電影感 Vlog | small letter-spaced serif, whole line fades up from a blur | `film` (lifted blacks) | letterbox bars, film grain (`grain`), date stamp (`place`), slow push, almost no SFX | 5 s |
| `product` | 開箱／業配 | each chunk on an ivory label sliding in (previous lifts away), key chunks on an accent label | `clean` | product label header (`badge`), comment CTA (LINK) on the last clip | 3 s |
Light, outline-free looks get a soft dark scrim so they stay readable over a white shirt; big words switch to ink on bright backgrounds.
Caption timing comes from the transcript (`words`): every character lights when it is spoken, even when the caption text was corrected.
`captions_style.scale` / `dy` (set by the room's 全片字幕 buttons) resize / move every caption in any look. Per-caption overrides: `look`, `size`, `y`, `emoji` (`"🔥"` or `false`). Spec fields: `header: {kind: bar|label|stamp|masthead|news, text, badge?}`,
`sfx_gain`, `grain`, `pacing.max_gap`; grades `airy`, `crisp`, `punchy`, `cinema`, `clean`, `muted`, `film`.
