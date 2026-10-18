"""Shared helpers for the 黑牛 AI editor: fonts, the 墨牛 palette, drawing primitives, person mask, easing.

Everything that draws on a frame works in float RGB arrays (H, W, 3) in 0..1, and RGBA layers made with PIL.
"""
import os, subprocess, functools, math, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

# ---------------- palette (墨牛) ----------------
def hex2rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
STYLE = dict(ink="#1A1A1C", ivory="#F3EEE4", accent="#FF6A1A", red="#E84E40", seal="#D63027", brand="黑牛", avatar="牛")
def palette(style=None):
    s = dict(STYLE); s.update(style or {})
    return {k: (hex2rgb(v) if isinstance(v, str) and v.startswith("#") else v) for k, v in s.items()}

# ---------------- fonts ----------------
FONT_QUERIES = {
    "serif": ["Noto Serif CJK TC:style=Bold", "Noto Serif TC:style=Bold", "Source Han Serif TC:style=Bold", "serif:lang=zh-tw:style=Bold"],
    "sans": ["Noto Sans CJK TC:style=Bold", "Noto Sans TC:style=Bold", "Source Han Sans TC:style=Bold", "PingFang TC:style=Semibold", "sans:lang=zh-tw:style=Bold"],
    "sans_m": ["Noto Sans CJK TC:style=Medium", "Noto Sans TC:style=Medium", "Noto Sans CJK TC", "sans:lang=zh-tw"],
    "black": ["Noto Sans CJK TC:style=Black", "Noto Sans TC:style=Black", "Noto Sans CJK TC:style=Bold"],
    "lat_serif": ["DejaVu Serif:style=Bold", "Liberation Serif:style=Bold", "serif:style=Bold"],
    "mono": ["DejaVu Sans:style=Bold", "Liberation Sans:style=Bold", "sans:style=Bold"],
}
@functools.lru_cache(None)
def font_path(kind):
    for q in FONT_QUERIES[kind]:
        try:
            out = subprocess.run(["fc-match", "-f", "%{file}:%{index}", q], capture_output=True, text=True, timeout=10).stdout.strip()
            if out and os.path.exists(out.rsplit(":", 1)[0]): p, i = out.rsplit(":", 1); return p, int(i or 0)
        except Exception: pass
    raise RuntimeError(f"No font found for {kind}. Install fonts-noto-cjk (apt) or Noto Sans/Serif TC.")
@functools.lru_cache(None)
def F(kind, size):
    p, i = font_path(kind); return ImageFont.truetype(p, int(size), index=i)

# ---------------- maths / layers ----------------
def ease(p): p = min(max(p, 0.0), 1.0); return 1 - (1 - p) ** 3
def eq(p): p = min(max(p, 0.0), 1.0); return 1 - (1 - p) ** 5              # ease-out quint, used for premium entrances
def smooth(p): p = min(max(p, 0.0), 1.0); return p * p * (3 - 2 * p)
def to_np(im): return np.asarray(im, dtype=np.float32) / 255.0
def over(base, layer, a=1.0):
    al = layer[..., 3:4] * a; return base * (1 - al) + layer[..., :3] * al
def shadow(im, off=(0, 10), blur=18, op=0.4):
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * op))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.paste(Image.new("RGBA", im.size, (0, 0, 0, 255)), off, a)
    return Image.alpha_composite(sh, im)
def zoom(img_u8, z, yfrac=0.5):
    if abs(z - 1) < 1e-4: return img_u8
    import cv2
    H, W = img_u8.shape[:2]; cw, ch = int(W / z), int(H / z); x0, y0 = (W - cw) // 2, int((H - ch) * yfrac)
    return cv2.resize(img_u8[y0:y0 + ch, x0:x0 + cw], (W, H), interpolation=cv2.INTER_LINEAR)

# ---------------- person mask (optional: text behind the head) ----------------
MASK_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx"
MODEL_DIR = os.environ.get("HN_MODELS", os.path.expanduser("~/.cache/heiniu"))
_sess = None
def mask_available():
    global _sess
    if _sess is not None: return _sess is not False
    try:
        import onnxruntime as ort
        path = os.path.join(MODEL_DIR, "u2net_human_seg.onnx")
        if not os.path.exists(path):
            os.makedirs(MODEL_DIR, exist_ok=True); urllib.request.urlretrieve(MASK_URL, path + ".part"); os.replace(path + ".part", path)
        _sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    except Exception as e:
        print("[mask] unavailable, falling back to text without occlusion:", e); _sess = False
    return _sess is not False
def person_mask(rgb_u8, blur=3.0):
    """Soft person matte (H, W, 1) in 0..1, or None when the model is unavailable."""
    if not mask_available(): return None
    import cv2
    H, W = rgb_u8.shape[:2]; inp = _sess.get_inputs()[0].name
    x = cv2.resize(rgb_u8, (320, 320), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = ((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype(np.float32)
    m = _sess.run(None, {inp: x})[0][0, 0]; m = (m - m.min()) / (m.max() - m.min() + 1e-6)
    m = np.clip((cv2.resize(m, (W, H)) - 0.35) / 0.3, 0, 1)
    return cv2.GaussianBlur(m, (0, 0), blur)[..., None]
def head_top(mask, default=520):
    if mask is None: return default
    H, W = mask.shape[:2]
    band = (mask[220:H - 220, int(W * 0.25):int(W * 0.75), 0] > 0.5).mean(axis=1); idx = np.where(band > 0.18)[0] + 220
    return int(idx[0]) if len(idx) else default

# ---------------- media helpers ----------------
def probe(path):
    import json
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,duration:format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(out)
def grab(path, t, w=1080, h=1920, vf=None):
    """One frame at time t as uint8 RGB, scaled/cropped to cover w x h."""
    chain = vf or f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", path, "-frames:v", "1", "-vf", chain,
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).reshape(h, w, 3).copy()
def sfx(name):
    import soundfile as sf
    x, sr = sf.read(os.path.join(ASSETS, "sfx", name + ".wav"), dtype="float32")
    return x if x.ndim == 2 else np.stack([x, x], 1)

# ---------------- timeline expansion (speed ramps) ----------------
def expand_timeline(timeline, default_speed=1.0):
    """A clip with "ramp": [{from, to, speed, mute?}] becomes several clip pieces (frame-exact cuts at the ramp edges).
    Every piece keeps the item's captions/overlays (each only draws inside its own time range) and remembers its beat
    index in "_beat"; later pieces drop whip_in/push so the beat still reads as one shot."""
    out = []
    for bi, it in enumerate(timeline):
        if it.get("type", "clip") != "clip" or not it.get("ramp"):
            d = dict(it); d["_beat"] = bi; out.append(d); continue
        a, b = float(it["in"]), float(it["out"]); base = float(it.get("speed", default_speed)); cur = a; pieces = []
        for r in sorted(it["ramp"], key=lambda r: float(r["from"])):
            r0, r1 = max(a, float(r["from"])), min(b, float(r["to"]))
            if r1 <= r0: continue
            if r0 > cur + 1e-3: pieces.append((cur, r0, base, False))
            pieces.append((r0, r1, float(r.get("speed", 3.0)), bool(r.get("mute", True)))); cur = r1
        if cur < b - 1e-3: pieces.append((cur, b, base, False))
        for k, (x, y, sp, mu) in enumerate(pieces):
            d = dict(it); d.pop("ramp", None); d.update({"in": x, "out": y, "speed": sp, "_beat": bi})
            if k > 0: d["whip_in"] = False; d["push"] = 0
            if mu: d["_mute"] = True; d["normalize"] = False
            if sp >= 1.5: d["_fast"] = sp
            out.append(d)
    return out

# ---------------- word-locked timing ----------------
TIME_START_KEYS = {"at", "start", "send", "show", "type_at", "heart_at", "reply_at", "from"}
TIME_END_KEYS = {"end", "until", "to"}
def load_chars(words_path):
    """words.json (transcribe.py) → {file basename: [(char, t), …]} in source seconds"""
    import json
    out = {}
    for f in json.load(open(words_path)):
        cs = []
        for ph in f.get("phrases", []): cs += [(c, float(t)) for c, t in ph.get("chars", [])]
        out[os.path.basename(f["file"])] = cs
    return out
def resolve_words(spec, spec_dir, lead=0.067):
    """Any time field may name a word instead of a number: "@6萬", "@6萬#2" (2nd time it is said), or
    {"word": "6萬", "n": 1, "offset": -0.067}. Start-type fields land `lead` (2 frames) before the word starts —
    editors cut on anticipation; end-type fields land just after the word ends. Search is limited to the clip."""
    wp = spec.get("words")
    if not wp: return spec
    chars = load_chars(wp if os.path.isabs(wp) else os.path.join(spec_dir, wp))
    def find(src, a, b, word, n):
        cs = chars.get(os.path.basename(src)) or chars.get(os.path.basename(os.path.realpath(os.path.join(spec_dir, src))), [])
        w = word.replace(" ", ""); seq = [(c, t) for c, t in cs if c.strip() and a - 0.3 <= t <= b + 0.3]; s_ = "".join(c for c, _ in seq); k, pos = 0, -1
        while k < n:
            pos = s_.find(w, pos + 1)
            if pos < 0: raise ValueError(f"word 「{word}」 (#{n}) not found in {src} {a:.2f}–{b:.2f}s")
            k += 1
        t0 = seq[pos][1]; j = pos + len(w); t1 = seq[j][1] if j < len(seq) else seq[pos + len(w) - 1][1] + 0.28
        return t0, t1
    def walk(x, it, key=None):
        if isinstance(x, dict) and "word" in x and set(x) <= {"word", "n", "offset"}:
            t0, t1 = find(it["src"], float(it.get("in", 0)), float(it.get("out", 1e9)), x["word"], int(x.get("n", 1)))
            return (t1 + float(x.get("offset", 0.03))) if key in TIME_END_KEYS else (t0 + float(x.get("offset", -lead)))
        if isinstance(x, str) and x.startswith("@") and key in TIME_START_KEYS | TIME_END_KEYS:
            w, _, n = x[1:].partition("#"); return walk({"word": w, "n": int(n or 1)}, it, key)
        if isinstance(x, dict): return {k: walk(v, it, k) for k, v in x.items()}
        if isinstance(x, list): return [walk(v, it, key) for v in x]
        return x
    spec = dict(spec); spec["timeline"] = [walk(it, it) if it.get("src") and it.get("type", "clip") in ("clip", "freeze") else it for it in spec["timeline"]]
    return spec
def spring(p):
    """ease-out with ~6% overshoot — for pops (bubbles, cards, ticks)"""
    p = min(max(p, 0.0), 1.0); return 1 - math.exp(-7 * p) * math.cos(8.5 * p) if p < 1 else 1.0
