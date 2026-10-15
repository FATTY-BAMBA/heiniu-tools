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
  "captions_style": {"size": 64, "y": 1330},// caption box size and vertical centre (1080x1920 units)
  "music": {"src": "track.mp3", "gain_db": -20, "start": 0, "fade_out": 2.0},   // optional; ducked under the voice
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
| `bigwords` | `[{word, start, end, size?, place?: "auto"|"low"}]` giant serif word typed in letter by letter. `auto` puts it above the head with the head in front (needs the person matte); falls back to `low` (lower third) when there is no head-room. Captions hide while a low word shows. |
| `prompts` | `[{text, start, send?, end?, label?}]` the cream 「對 AI 說」 box at the top typing the instruction, pressing send, ✓. Time `send` to land on the word it refers to. |
| `cta` | comment call-to-action on glass cards: `{show, type_at?, heart_at?, reply_at?, keyword, headline?, sub, reply, author?}`. Captions hide once it shows. Put `reply_at` ≥ 1.2 s before the clip ends so people can read it. |
| `shot`, `transition`, `sound`, `notes` | text only, shown on the storyboard card. |

### `cover` — magazine-cover cold open (≈1.4 s)
`{type:"cover", src, at, dur:1.4, crop?, masthead, issue:[left, centre, right], kicker?, headline:[line1, line2], stat:[big, small], barcode?, barcode_text?, occlude?:true}`
Pick `at` on a frame where the person is smiling, eyes open, centred. The masthead sits behind the head when the matte is available.

### `compare` — before/after reveal on a freeze (≈2.6 s)
`{type:"compare", src, at, crop?, dur:2.625, sweep:1.9, grade_to:"soft", bars_after:true, label_after:"AI 調色", label_before:"原始"}`
Starts on the untouched frame; a slanted line slides slowly left→right revealing the graded frame. Place it **after** the sentence that announces the change, never mid-sentence. Use `at` = the clip's `out`, so the freeze matches the last frame.
