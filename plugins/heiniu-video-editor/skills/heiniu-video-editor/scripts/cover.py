"""Generated timeline items: the magazine-cover cold open ("cover") and the before/after grade reveal ("compare").
Both write a segment with exact frame count and silent PCM audio; their sound effects are returned as events
(seconds relative to the segment start) and mixed with the rest of the SFX by render.py."""
import subprocess, numpy as np, cv2
from PIL import Image, ImageDraw
from hn_common import F, eq, smooth, to_np, over, shadow, grab, person_mask, head_top

def _write(frames_iter, N, out, ctx):
    W, H, FPS = ctx["W"], ctx["H"], ctx["FPS"]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-f", "lavfi", "-t", f"{N / FPS:.6f}", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le",
                            "-frames:v", str(N), out], stdin=subprocess.PIPE)
    for f in frames_iter: enc.stdin.write(np.ascontiguousarray(f).tobytes())
    enc.stdin.close(); enc.wait()

# ---------------- magazine cover ----------------
def cover_grade(base, mask, scrim_from, W, H):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = np.clip(1 - 0.42 * (((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H * 0.45) / (H * 0.75)) ** 2), 0, 1)[..., None]
    m = mask if mask is not None else np.zeros((H, W, 1), np.float32)
    g = base * (1 - m) * np.array([0.78, 0.74, 0.72]) + base * m * 1.02
    g = np.clip((g - 0.5) * 1.06 + 0.5, 0, 1) * (0.55 + 0.45 * vig)
    top = np.clip(1 - yy / (H * 0.27), 0, 1)[..., None] ** 1.6 * 0.55
    bot = np.clip((yy - scrim_from) / (H - scrim_from) * 1.25, 0, 1)[..., None] ** 1.1 * 0.80
    return g * (1 - top) * (1 - bot)
def cover_layers(it, P, W, H, ht, layout="open"):
    """Returns (masthead(p), front(t)) layer functions. Layout 'open' = full-bleed cover; 'edit' = raised to leave room for UI chips."""
    s = W / 1080; S = lambda v: int(round(v * s)); IV, EM = P["ivory"], P["accent"]
    # keep every element inside the Reels/TikTok safe zone: above y≈1420 and left of x≈900 (caption bar + side buttons)
    L = dict(open=dict(kick=1000, h1=1046, h2=1174, row=1310), edit=dict(kick=960, h1=1006, h2=1134, row=1270))[layout]
    title = it.get("masthead", P["brand"]); msize = S(it.get("masthead_size", 440))
    MT = (ht - S(370)) if ht is not None else S(210)
    def mast(p):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); fm = F("serif", msize)
        ws = [d.textlength(c, font=fm) for c in title]; trk = S(-10 + 40 * (1 - p)); x = (W - sum(ws) - trk * (len(title) - 1)) / 2
        for i, c in enumerate(title):
            q = eq(p * 1.4 - i * 0.25); d.text((x, MT + (1 - q) * S(60)), c, font=fm, fill=IV + (int(255 * min(1, q * 1.3)),)); x += ws[i] + trk
        return to_np(shadow(im, (0, S(16)), S(26), 0.45))
    issue = it.get("issue", ["NO. 01", "", "AI 剪輯特刊"]); head = it.get("headline", ["一句話，", "剪完整支影片"]); stat = it.get("stat", [])
    kicker = it.get("kicker", "COVER STORY")
    def front(t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); a = lambda t0, dur=0.35: eq((t - t0) / dur)
        p = a(0.10); y = S(128) - (1 - p) * S(10)
        if len(issue) > 0 and issue[0]: d.text((S(72), y), issue[0], font=F("mono", S(24)), fill=IV + (int(220 * p),))
        if len(issue) > 1 and issue[1]: d.text(((W - d.textlength(issue[1], font=F("mono", S(24)))) / 2, y), issue[1], font=F("mono", S(24)), fill=IV + (int(170 * p),))
        if len(issue) > 2 and issue[2]:
            tw = d.textlength(issue[2], font=F("sans", S(26))); d.text((W - S(72) - tw, y - S(3)), issue[2], font=F("sans", S(26)), fill=IV + (int(220 * p),))
        lw = (W - S(144)) * eq((t - 0.05) / 0.5); d.line([(S(72), S(176)), (S(72) + lw, S(176))], fill=IV + (110,), width=max(1, S(2)))
        p1 = a(0.32); k = S(L["kick"]) + (1 - p1) * S(14); xx = S(128)
        d.rounded_rectangle([S(72), k + S(12), S(112), k + S(16)], S(2), fill=EM + (int(255 * p1),))
        for ch in kicker: d.text((xx, k), ch, font=F("mono", S(22)), fill=IV + (int(200 * p1),)); xx += d.textlength(ch, font=F("mono", S(22))) + S(5)
        for i, txt in enumerate(head[:2]):
            q = a(0.40 + i * 0.10, 0.45); f = F("serif", S(108 if i == 0 else 86)); yb = S(L["h1"] if i == 0 else L["h2"])
            d.text((S(66), yb + (1 - q) * S(26)), txt, font=f, fill=(EM if i == 0 else IV) + (int(255 * q),))
        q = a(0.62); sx, ry = S(282), S(L["row"])
        if stat:
            d.line([(sx, ry), (sx + S(300), ry)], fill=IV + (int(110 * q),), width=max(1, S(2)))
            d.text((sx, ry + S(10) + (1 - q) * S(10)), stat[0], font=F("serif", S(44)), fill=IV + (int(255 * q),))
            if len(stat) > 1: d.text((sx, ry + S(70) + (1 - q) * S(10)), stat[1], font=F("sans_m", S(26)), fill=EM + (int(255 * q),))
        if it.get("barcode", True):
            bx, by = S(72), ry + S(6); rng = np.random.default_rng(4); x = bx + S(10)
            d.rectangle([bx, by, bx + S(168), by + S(92)], fill=(248, 245, 238, int(240 * q)))
            while x < bx + S(158):
                w = max(1, int(rng.choice([2, 2, 3, 4]) * s)); d.rectangle([x, by + S(10), x + w - 1, by + S(62)], fill=(20, 20, 20, int(255 * q))); x += w + max(1, int(rng.choice([2, 3, 4]) * s))
            d.text((bx + S(12), by + S(64)), it.get("barcode_text", "NO.01"), font=F("sans_m", S(18)), fill=(20, 20, 20, int(255 * q)))
        return to_np(shadow(im, (0, S(6)), S(12), 0.45))
    return mast, front
def build_cover(it, out, ctx):
    W, H, FPS, P = ctx["W"], ctx["H"], ctx["FPS"], ctx["P"]
    vf = ",".join([c for c in ctx["chain"](dict(it, grade="none", bars=False)) if c])
    u8 = grab(ctx["src_path"](it["src"]), float(it.get("at", 0)), W, H, vf); base = u8.astype(np.float32) / 255
    mask = person_mask(u8, 4) if it.get("occlude", True) else None; ht = head_top(mask) if mask is not None else None
    g = cover_grade(base, mask, H * 0.45, W, H); mast, front = cover_layers(it, P, W, H, ht, "open")
    dur = float(it.get("dur", 1.4)); N = int(round(dur * FPS)); whip = int(round(0.3 * FPS)); ink = np.array(P["ink"], np.float32) / 255
    def frames():
        for k in range(N):
            t = k / FPS; fr = over(g, mast(min(1, t / 0.75)))
            if mask is not None: fr = fr * (1 - mask) + g * mask
            fr = over(fr, front(t)); fl = 1 - eq(t / 0.22); fr = fr * (1 - 0.7 * fl) + ink * 0.7 * fl
            img = (np.clip(fr, 0, 1) * 255).astype(np.uint8); z = 1.05 - 0.05 * eq(t / max(0.1, dur - 0.3))
            kw = k - (N - whip)
            if kw >= 0:                                                       # whip out: zoom + vertical smear
                z += 0.12 * (kw / whip) ** 2; L = 9 + int(kw * 90 / whip); ker = np.zeros((L, L), np.float32); ker[:, L // 2] = 1.0 / L
            cw, ch = int(W / z), int(H / z); img = cv2.resize(img[(H - ch) // 2:(H - ch) // 2 + ch, (W - cw) // 2:(W - cw) // 2 + cw], (W, H), interpolation=cv2.INTER_LANCZOS4)
            if kw >= 0: img = cv2.filter2D(img, -1, ker)
            yield img
    _write(frames(), N, out, ctx)
    ev = [(0.0, "shutter", 0.9), (0.0, "boom", 0.5)] + [(t0, "tick", 0.35) for t0 in (0.32, 0.42, 0.52, 0.64)] + [(dur - 0.3, "whoosh_rev", 0.7)]
    return N, ev

# ---------------- before / after reveal ----------------
def build_compare(it, out, ctx):
    W, H, FPS, P = ctx["W"], ctx["H"], ctx["FPS"], ctx["P"]; s = W / 1080; S = lambda v: int(round(v * s)); IV, EM = P["ivory"], P["accent"]
    src = ctx["src_path"](it["src"]); at = float(it.get("at", 0))
    U = grab(src, at, W, H, ",".join([c for c in ctx["chain"](dict(it, grade="none", bars=False)) if c])).astype(np.float32) / 255
    G = grab(src, at, W, H, ",".join([c for c in ctx["chain"](dict(it, grade=it.get("grade_to", "soft"), bars=it.get("bars_after", True))) if c])).astype(np.float32) / 255
    T0, TS = 0.30, float(it.get("sweep", 1.9)); dur = float(it.get("dur", 2.625)); N = int(round(dur * FPS))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); u = xx / W + yy / H
    la, lb = it.get("label_after", "AI 調色"), it.get("label_before", "原始")
    def labels(aa, ab):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); fl = F("sans", S(52))
        for txt, x, y, col, a in [(la, S(60), S(470), EM, aa), (lb, W - S(60), S(1560), (200, 200, 200), ab)]:
            if a <= 0: continue
            tw = d.textlength(txt, font=fl); bx = x if x < W / 2 else x - tw - S(64)
            d.rounded_rectangle([bx, y, bx + tw + S(64), y + S(76)], S(38), fill=P["ink"] + (int(215 * a),), outline=(255, 255, 255, int(40 * a)), width=max(1, S(2)))
            d.ellipse([bx + S(22), y + S(31), bx + S(36), y + S(45)], fill=col + (int(255 * a),)); d.text((bx + S(44), y + S(9)), txt, font=fl, fill=IV + (int(255 * a),))
        return to_np(im)
    def line(c):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        p0 = (c * W, 0) if c <= 1 else (W, (c - 1) * H); p1 = (0, c * H) if c <= 1 else ((c - 1) * W, H)
        d.line([p0, p1], fill=(255, 255, 255, 245), width=max(2, S(7))); hx, hy, r = c * W / 2, c * H / 2, S(40)
        d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 255, 255, 250)); return to_np(im)
    def frames():
        for k in range(N):
            t = k / FPS; p = smooth((t - T0) / TS); c = -0.03 + 2.08 * p
            m = np.clip((c - u) * 60 + 0.5, 0, 1)[..., None]; fr = G * m + U * (1 - m)
            if 0 < c < 2: l = line(c); fr = fr * (1 - l[..., 3:4]) + l[..., :3] * l[..., 3:4]
            aa = eq((c - 0.55) / 0.25); ab = eq(t / 0.15) * min(1, max(0, (1.55 - c) / 0.2))
            if aa > 0 or ab > 0: fr = over(fr, labels(aa, ab))
            img = (np.clip(fr, 0, 1) * 255).astype(np.uint8); z = 1 + 0.025 * eq(t / dur); cw, ch = int(W / z), int(H / z)
            yield cv2.resize(img[(H - ch) // 2:(H - ch) // 2 + ch, (W - cw) // 2:(W - cw) // 2 + cw], (W, H))
    _write(frames(), N, out, ctx)
    return N, [(T0 - 0.05, "whoosh", 0.55), (T0, "shimmer:%.2f" % TS, 1.0), (T0 + TS - 0.02, "tick", 0.9), (T0 + TS - 0.02, "boom", 0.22), (dur - 0.06, "pop", 0.5)]
