"""Caption engine v2 — captions that move with the voice.

Every character gets the time it is actually spoken (aligned against the transcript, so corrected caption text still
syncs), and a look decides what the viewer sees:
  impact     衝擊字   heavy white caps with a thick black outline, 1–5 characters at a time, the spoken character turns
                       yellow, keys green, each chunk pops in, optional emoji on key ideas
  editorial  雜誌     serif line that builds as it is spoken (each character rises in), keys in accent and slanted,
                       a thin accent rule grows under the line
  minimal    極簡     small clean sans, upcoming words faint, each character sharpens out of a blur as it is spoken
  news       新聞快報  white on a black strip that slides in, red edge, the spoken character in yellow
  vlog       電影感   small letter-spaced serif, the whole line fades up from a blur, no highlight
  label      開箱     each chunk on an ivory label that slides in (previous one lifts away), keys on an accent label
Legacy looks (card / clean / bold / meme) stay in render.py.
"""
import math, difflib, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from hn_common import F, hex2rgb, eq, spring

PUNCT = set("，。、！？：；,.!?:;…「」『』（）()[]—-~～·\"' ")
LOOKS = {
    "impact":    dict(face="black", size=92, y=1330, fill="#FFFFFF", stroke=0.15, active="#FFE14D", key="#3DFF8A", mode="chunk", max_chars=5,
                      anim="pop", active_scale=1.12, shadow=0.55, emoji=True, track=0.02),
    "editorial": dict(face="serif", size=84, y=1330, scrim=0.42, fill="#F3EEE4", stroke=0.0, active=None, key="accent", mode="line", reveal="build",
                      anim="rise", shear_keys=0.2, rule=True, shadow=0.5, track=0.06),
    "minimal":   dict(face="sans_m", size=58, y=1420, scrim=0.5, fill="#FFFFFF", stroke=0.0, active=None, key="accent", mode="line", reveal="dim",
                      anim="blur", dim=0.32, shadow=0.45, track=0.03),
    "news":      dict(face="sans", size=60, y=1400, fill="#FFFFFF", stroke=0.0, active="#FFD43B", key="#FFD43B", mode="line", reveal="all",
                      anim="none", box="strip", shadow=0.3, track=0.02),
    "vlog":      dict(face="serif", size=54, y=1440, scrim=0.5, fill="#F6F1E6", stroke=0.0, active=None, key="#F2C98A", mode="line", reveal="all",
                      anim="blur_line", shadow=0.55, track=0.12),
    "label":     dict(face="sans", size=64, y=1380, fill="#1A1A1C", stroke=0.0, active="accent", key="#FFFFFF", mode="chunk", max_chars=6,
                      anim="slide", box="label", shadow=0.35, track=0.02),
}
EMOJI = [("錢", "💸"), ("薪", "💰"), ("萬", "💰"), ("塊", "💸"), ("AI", "🤖"), ("工具", "🛠️"), ("時間", "⏰"), ("爆", "🔥"), ("火", "🔥"),
         ("吃", "🍜"), ("臭豆腐", "🤢"), ("想", "💭"), ("問", "❓"), ("哪", "❓"), ("知道", "💡"), ("學", "📚"), ("對", "✅"), ("錯", "❌"),
         ("快", "⚡"), ("免費", "🎁"), ("剪", "🎬"), ("影片", "🎬"), ("愛", "❤️"), ("笑", "😂"), ("等一下", "✋"), ("台灣", "🇹🇼"), ("手機", "📱")]
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

def caption_times(chars, text, c0, c1):
    """per-character spoken time (source seconds) for `text` shown c0..c1; aligned to the transcript when there is one"""
    n = len(text); tgt = [j for j, ch in enumerate(text) if ch not in PUNCT and ch.strip()]
    times = [None] * n
    seq = [(ch, t) for ch, t in (chars or []) if ch.strip() and ch not in PUNCT and c0 - 0.35 <= t <= c1 + 0.1]
    if seq and tgt:
        sm = difflib.SequenceMatcher(None, [text[j].lower() for j in tgt], [ch.lower() for ch, _ in seq], autojunk=False)
        for a, b, k in sm.get_matching_blocks():
            for q in range(k): times[tgt[a + q]] = max(c0, min(c1 - 0.05, seq[b + q][1]))
    # anchors at both ends, then interpolate the rest (and keep it monotonic)
    known = [(j, times[j]) for j in tgt if times[j] is not None]
    lo, hi = (c0, c1 - min(0.25, (c1 - c0) * 0.15))
    if not known: known = [(tgt[0] if tgt else 0, lo), (tgt[-1] if tgt else n - 1, lo + (hi - lo) * 0.85)]
    pts = [(-1, lo if known[0][1] > lo + 0.02 else known[0][1] - 0.001)] + known + [(n, max(hi, known[-1][1] + 0.08))]
    for j in range(n):
        if times[j] is not None: continue
        a = max((p for p in pts if p[0] < j), key=lambda p: p[0]); b = min((p for p in pts if p[0] > j), key=lambda p: p[0])
        times[j] = a[1] + (b[1] - a[1]) * (j - a[0]) / max(1, b[0] - a[0])
    for j in range(1, n): times[j] = max(times[j], times[j - 1])
    return times

def chunks_of(text, times, keys, max_chars):
    """split into what is on screen at once: never break a key or a latin word, prefer punctuation / spaces / pauses"""
    n = len(text); keep = set()
    for kw in keys:
        j = text.find(kw)
        if j >= 0: keep |= set(range(j + 1, j + len(kw)))                  # no break inside a key
    for j in range(1, n):
        if text[j - 1].isascii() and text[j].isascii() and text[j - 1].isalnum() and text[j].isalnum(): keep.add(j)
    out, cur = [], []
    for j in range(n):
        ch = text[j]
        if ch.strip() == "" or ch in "，。、！？,.!?":
            if cur: out.append(cur); cur = []
            continue
        vis = sum(1 for k in cur if text[k].strip())
        gap = j > 0 and cur and times[j] - times[cur[-1]] > 0.38
        if cur and j not in keep and (vis >= max_chars or gap): out.append(cur); cur = []
        cur.append(j)
    if cur: out.append(cur)
    merged = []                                                              # a lone trailing character joins its neighbour
    for c in out:
        if merged and len(c) == 1 and len(merged[-1]) <= max_chars: merged[-1] = merged[-1] + c
        else: merged.append(c)
    return merged

class Engine:
    def __init__(self, W, H, S, P, base):
        self.W, self.H, self.S, self.P = W, H, S, P; self.base = dict(base); self.glyphs = {}; self.prep = {}; self.emoji_used = []
        try: self.efont = ImageFont.truetype(EMOJI_FONT, 109)
        except Exception: self.efont = None
    def col(self, v, fallback):
        if v is None: return None
        if v == "accent": return tuple(self.P["accent"])
        if v in ("red", "seal"): return tuple(self.P["seal"])
        return hex2rgb(v) if isinstance(v, str) and v.startswith("#") else fallback
    def look(self, c):
        name = c.get("look", self.base.get("look")); L = dict(LOOKS[name]); L.update({k: v for k, v in self.base.items() if k not in ("look",)})
        if c.get("size"): L["size"] = c["size"]
        if c.get("y"): L["y"] = c["y"]
        L["size"] = L["size"] * float(self.base.get("scale", 1.0)); L["y"] = L["y"] + float(self.base.get("dy", 0))   # 全片字幕大小／位置 (review room)
        return name, L
    # ---- glyphs ----
    def glyph(self, ch, face, size, fill, stroke_px, shear=0.0):
        key = (ch, face, size, fill, stroke_px, round(shear, 2))
        g = self.glyphs.get(key)
        if g is None:
            f = F(face, size); asc, desc = f.getmetrics(); pad = stroke_px + 4; w = int(f.getlength(ch)) + 2 * pad + int(abs(shear) * size)
            im = Image.new("RGBA", (max(1, w), asc + desc + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.text((pad, pad + asc), ch, font=f, fill=fill + (255,), anchor="ls", stroke_width=stroke_px, stroke_fill=(0, 0, 0, 255))
            if shear: im = im.transform(im.size, Image.AFFINE, (1, shear, -shear * im.height * 0.75, 0, 1, 0), resample=Image.BICUBIC)
            g = (im, f.getlength(ch), pad, asc); self.glyphs[key] = g
            if len(self.glyphs) > 3000: self.glyphs.pop(next(iter(self.glyphs)))
        return g
    def emoji(self, e, px):
        key = ("emoji", e, px)
        if key not in self.glyphs:
            im = Image.new("RGBA", (150, 150), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10, 10), e, font=self.efont, embedded_color=True)
            bb = im.getbbox() or (0, 0, 150, 150); self.glyphs[key] = im.crop(bb).resize((px, px), Image.LANCZOS)
        return self.glyphs[key]
    # ---- per caption preparation (once) ----
    def prepare(self, c, chars, to_out, seg_key=None):
        k = (id(c), seg_key)
        if k in self.prep: return self.prep[k]
        name, L = self.look(c); text = c["text"]; keys = c.get("keys", [])
        st = caption_times(chars, text, float(c["start"]), float(c["end"])); ot = [to_out(x) for x in st]
        t0, t1 = to_out(float(c["start"])), to_out(float(c["end"]))
        ki = set()
        for kw in keys:
            j = text.find(kw)
            if j >= 0: ki |= set(range(j, j + len(kw)))
        S = self.S; size = S(L["size"]); maxw = self.W * 0.86 - (S(80) if L.get("box") else 0)
        groups = chunks_of(text, ot, keys, L.get("max_chars", 99)) if L["mode"] == "chunk" else [[j for j in range(len(text))]]
        def width(idx, sz):
            f = F(L["face"], sz); tr = L.get("track", 0) * sz; return sum(f.getlength(text[j]) + tr for j in idx) - tr
        while max(width(g, size) for g in groups) > maxw and size > S(28): size = int(size * 0.94)
        emo = None
        if L.get("emoji") and self.efont is not None:
            emo = c.get("emoji")
            if emo is None and len(self.emoji_used) < 3 and all(abs(t0 - u) > 3.0 for u in self.emoji_used):
                hay = "".join(keys) or ""
                emo = next((e for w_, e in EMOJI if w_ in hay), None)
            if emo:
                self.emoji_used.append(t0)
                kj = min(ki) if ki else 0; emo = (emo, ot[kj] if ki else t0)
        p = dict(name=name, L=L, text=text, ot=ot, t0=t0, t1=t1, ki=ki, size=size, groups=groups, emo=emo)
        self.prep[k] = p; return p
    # ---- draw ----
    def draw(self, comp, t, c, chars, to_out, rects=None, seg_key=None):
        p = self.prepare(c, chars, to_out, seg_key); L = p["L"]; W, H, S = self.W, self.H, self.S
        if not (p["t0"] <= t < p["t1"]): return comp
        text, ot, size, ki = p["text"], p["ot"], p["size"], p["ki"]; n = len(text)
        nxt = lambda j: next((ot[k] for k in range(j + 1, n) if text[k].strip() and text[k] not in PUNCT and ot[k] > ot[j]), p["t1"])
        INK_ = tuple(self.P["ink"]); fill = self.col(L["fill"], (255, 255, 255)); act = self.col(L.get("active"), None); kc = self.col(L.get("key"), fill)
        stroke = int(round(size * L.get("stroke", 0))); tr = L.get("track", 0) * size
        # which group is on screen
        groups = p["groups"]; gi = 0
        if L["mode"] == "chunk":
            starts = [ot[g[0]] - 0.05 for g in groups]
            gi = max([i for i, s0 in enumerate(starts) if s0 <= t] or [0])
        vis = groups[gi]; g_start = max(p["t0"], ot[vis[0]] - 0.05) if L["mode"] == "chunk" else p["t0"]
        f = F(L["face"], size); widths = [f.getlength(text[j]) + tr for j in vis]; tw = sum(widths) - tr
        cy = S(L["y"]); top = cy - int(size * 2.9); BH = int(size * 4.4)
        band = Image.new("RGBA", (W, BH), (0, 0, 0, 0)); d = ImageDraw.Draw(band); base_y = cy - top + int(size * 0.36)   # baseline in band coords
        x = (W - tw) / 2
        u_cap = t - g_start; x_clip = 1e9
        # ---- soft dark scrim behind light, outline-free text (stays readable over a white shirt or sky) ----
        if L.get("scrim"):
            tw_full = max(sum(f.getlength(text[j]) + tr for j in g) - tr for g in groups)
            key = ("scrim", int(tw_full), size, L["scrim"])
            if key not in self.glyphs:
                pw, ph = int(tw_full + size * 2.2), int(size * 2.6); sim = Image.new("L", (pw, ph), 0)
                ImageDraw.Draw(sim).rounded_rectangle([size * 0.8, size * 0.75, pw - size * 0.8, ph - size * 0.75], int(size * 0.5), fill=int(255 * L["scrim"]))
                sim = sim.filter(ImageFilter.GaussianBlur(size * 0.42)); blk = Image.new("RGBA", (pw, ph), (8, 8, 10, 0)); blk.putalpha(sim); self.glyphs[key] = blk
            sc_ = self.glyphs[key]; fa = min(1, (t - p["t0"]) / 0.2)
            if fa < 1: sc_ = sc_.copy(); sc_.putalpha(sc_.getchannel("A").point(lambda v: int(v * fa)))
            band.alpha_composite(sc_, (int((W - sc_.width) / 2), int(base_y - size * 0.32 - sc_.height / 2)))
        # ---- boxes behind the text ----
        if L.get("box") == "strip":
            q = eq(u_cap / 0.16); px = S(34); x0 = x - px; x1 = x0 + (tw + 2 * px) * q
            d.rectangle([x0, base_y - size * 0.98, x1, base_y + size * 0.42], fill=(12, 12, 14, 228))
            d.rectangle([x0, base_y - size * 0.98, x0 + S(10), base_y + size * 0.42], fill=tuple(self.P["seal"]) + (255,))
            if q < 1: x_clip = x1 - S(10)
        if L.get("box") == "label":
            q = eq(u_cap / 0.2); dx = (1 - q) * S(70); iskey = any(j in ki for j in vis)
            bg = (tuple(self.P["accent"]) if iskey else (248, 245, 238)) + (int(250 * min(1, u_cap / 0.08)),)
            d.rounded_rectangle([x - S(30) + dx, base_y - size * 1.0, x + tw + S(30) + dx, base_y + size * 0.38], S(10), fill=bg)
            x += dx
            if gi > 0 and u_cap < 0.28:                                       # previous label lifts away
                pv = groups[gi - 1]; pw = sum(f.getlength(text[j]) + tr for j in pv) - tr; a = 1 - eq(u_cap / 0.28); ly = -eq(u_cap / 0.28) * size * 1.3
                d.rounded_rectangle([(W - pw) / 2 - S(30), base_y - size * 1.0 + ly, (W + pw) / 2 + S(30), base_y + size * 0.38 + ly], S(10), fill=(248, 245, 238, int(170 * a)))
        if L.get("rule"):
            spoken = sum(1 for j in vis if ot[j] <= t) / max(1, len(vis)); q = eq(min(1, (t - p["t0"]) / 0.3)) * max(0.12, spoken)
            d.rectangle([(W - tw * q) / 2, base_y + size * 0.30, (W + tw * q) / 2, base_y + size * 0.30 + max(2, S(4))], fill=tuple(self.P["accent"]) + (255,))
        # ---- characters ----
        xs = []
        for j, wdt in zip(vis, widths): xs.append(x); x += wdt
        for j, x0 in zip(vis, xs):
            ch = text[j]
            if not ch.strip(): continue
            tc = ot[j]; tn = nxt(j); a = 1.0; sc = 1.0; dy = 0.0; blur = 0.0
            spoken = t >= tc; active = act is not None and tc <= t < max(tn, tc + 0.14)
            anim, rev = L.get("anim"), L.get("reveal", "all")
            if L["mode"] == "line" and rev == "build" and not spoken: continue
            if L["mode"] == "line" and rev == "dim" and not spoken: a = L.get("dim", 0.3)
            pr = (t - tc) if (L["mode"] == "line" and rev in ("build", "dim")) else u_cap
            if anim == "pop": sc = 0.72 + 0.28 * spring(min(1, pr / 0.22)); a *= min(1, pr / 0.06)
            elif anim == "rise": q = eq(min(1, pr / 0.24)); dy = (1 - q) * size * 0.32; a *= q
            elif anim == "blur" and spoken:
                q = eq(min(1, pr / 0.26)); blur = (1 - q) * size * 0.12; dm = L.get("dim", 0.3) if rev == "dim" else 0.0; a = dm + (1 - dm) * q
            elif anim == "blur_line": q = eq(min(1, u_cap / 0.4)); blur = (1 - q) * size * 0.14; a *= q
            elif anim == "slide": a *= min(1, u_cap / 0.1)
            col = fill
            if j in ki and (spoken or L["mode"] == "chunk" or rev == "all"): col = kc
            if active: col = act; sc *= L.get("active_scale", 1.0)
            if L.get("box") == "label" and any(k in ki for k in vis): col = INK_ if active else (255, 255, 255)   # accent label: white text, spoken char dark
            if x0 > x_clip: continue
            sh = L.get("shear_keys", 0) if j in ki else 0
            g, adv, pad, asc = self.glyph(ch, L["face"], size, col, stroke, sh)
            im = g
            if abs(sc - 1) > 0.01: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
            if blur > 0.4: im = im.filter(ImageFilter.GaussianBlur(round(blur * 2) / 2))
            if a < 0.999: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v, a=a: int(v * a)))
            gx = x0 + adv / 2 - im.width / 2; gy = base_y - (pad + asc) * sc + dy - (sc - 1) * size * 0.1
            band.alpha_composite(im, (int(round(gx)), int(round(gy))))
        # ---- emoji on the key idea ----
        if p["emo"] and t >= p["emo"][1] - 0.04:
            e, te = p["emo"]; q = spring(min(1, (t - te) / 0.3)); px_ = max(8, int(size * 1.25 * (0.6 + 0.4 * q)))
            im = self.emoji(e, px_).rotate(-8 * (1 - q) + 6, expand=True, resample=Image.BICUBIC)
            ex = int(min(W - im.width - S(24), (W + tw) / 2 + size * 0.12)); ey = int(base_y - size * 0.42 - im.height / 2 - size * 0.18)
            band.alpha_composite(im, (ex, ey))                                # beside the words, never over the mouth
        # ---- composite (soft drop shadow, then the band) ----
        arr = np.asarray(band, np.float32) / 255; al = arr[..., 3:4]
        y0, y1 = max(0, top), min(H, top + BH); a0 = y0 - top; reg = comp[y0:y1]
        if L.get("shadow"):
            shd = cv2.GaussianBlur(al[a0:a0 + (y1 - y0), :, 0], (0, 0), max(1, size * 0.09))
            shd = np.roll(shd, int(size * 0.05), 0)[..., None] * L["shadow"]; reg = reg * (1 - shd)
        out = comp.copy(); out[y0:y1] = reg * (1 - al[a0:a0 + (y1 - y0)]) + arr[a0:a0 + (y1 - y0), :, :3] * al[a0:a0 + (y1 - y0)]
        if rects is not None:
            bb = band.getbbox()
            if bb: rects.append(("字幕", bb[0], top + bb[1], bb[2], top + bb[3]))
        return out
