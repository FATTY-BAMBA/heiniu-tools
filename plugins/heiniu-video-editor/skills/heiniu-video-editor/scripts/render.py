"""黑牛 AI editor — render an edit.json into a finished vertical video.

usage:  python3 render.py edit.json [--out final.mp4] [--work workdir] [--preview]

Stages (each one keeps picture and sound exactly the same length, so lip-sync can't drift):
  1. segments   every timeline item → seg_###.mov (W x H @ FPS, PCM 48 kHz), frame-exact
  2. master     concat of the segments (stream copy)
  3. overlays   one pass that draws captions, big words, prompt boxes, the comment CTA and whip transitions
  4. audio      voice + generated SFX (+ optional music, ducked under the voice), then loudness normalisation
  5. encode     H.264 at a bitrate that fits output.max_mb, + a QA report (qa.json)
See references/spec.md for the edit.json format.
"""
import sys, os, json, math, argparse, subprocess, shutil
import numpy as np, cv2, soundfile as sf
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hn_common import *          # noqa: F401,F403
import cover as COVER

ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--out"); ap.add_argument("--work"); ap.add_argument("--preview", action="store_true")
args = ap.parse_args()
SPEC_DIR = os.path.dirname(os.path.abspath(args.spec)); spec = json.load(open(args.spec))
O = dict(w=1080, h=1920, fps=30, max_mb=30, lufs=-14); O.update(spec.get("output", {}))
if args.preview: O.update(w=540, h=960, max_mb=min(float(O["max_mb"]), 6))
W, H, FPS = int(O["w"]), int(O["h"]), int(O["fps"]); SR = 48000; SC = W / 1080.0
P = palette(spec.get("style")); INK, IV, EM = P["ink"], P["ivory"], P["accent"]
WORK = os.path.abspath(args.work or os.path.join(SPEC_DIR, "_render")); os.makedirs(WORK, exist_ok=True)
OUT = os.path.abspath(args.out or os.path.join(SPEC_DIR, spec.get("name", "final") + ".mp4"))
def src_path(p): return p if os.path.isabs(p) else os.path.join(SPEC_DIR, p)
def S(v): return int(round(v * SC))                                  # scale 1080-based layout values
GRADES = {
    "soft": "eq=contrast=1.04:saturation=1.03:gamma=1.02:brightness=0.01,colorbalance=rs=-0.05:bs=0.05:rm=0.02:bh=-0.02,vignette=PI/5",
    "warm": "eq=contrast=1.05:saturation=1.06:gamma=1.0,colorbalance=rs=0.03:bs=-0.03,vignette=PI/5",
    "none": "",
}
def BARS(): b = S(spec.get("bars_px", 200)); return f"drawbox=x=0:y=0:w=iw:h={b}:color=black:t=fill,drawbox=x=0:y=ih-{b}:w=iw:h={b}:color=black:t=fill"
def run(cmd): subprocess.run(cmd, check=True)
def has_audio(p): return any(s.get("codec_type") == "audio" for s in probe(p).get("streams", []))

# ================= 1. segments =================
segs = []                                                            # dicts: kind, start, N, keff, item
events = []                                                          # (t, name, gain) SFX in output seconds
t_cursor = 0.0
def frame_chain(c):
    z = float(c.get("crop", 1.0)); ch = [f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={W}:{H}"]
    if z > 1.0001: ch.append(f"crop=iw/{z}:ih/{z}:(iw-ow)/2:(ih-oh)*0.4,scale={W}:{H}:flags=lanczos")
    g = GRADES.get(c.get("grade", spec.get("grade", "soft")), c.get("grade", ""))
    if g: ch.append(g)
    if c.get("bars", spec.get("bars", False)): ch.append(BARS())
    return ch
for i, it in enumerate(spec["timeline"]):
    kind = it.get("type", "clip"); out = os.path.join(WORK, f"seg_{i:03d}.mov")
    if kind == "clip":
        src = src_path(it["src"]); a, b = float(it["in"]), float(it["out"]); k = float(it.get("speed", spec.get("speed", 1.0)))
        N = max(1, round((b - a) / k * FPS)); keff = (b - a) / (N / FPS); NS = round(N * SR / FPS)
        vf = ",".join([f"trim=0:{b - a:.6f}", "setpts=PTS-STARTPTS"] + frame_chain(it) +
                      [f"setpts=PTS/{keff:.8f}", f"fps={FPS}", "tpad=stop_mode=clone:stop=8", f"trim=end_frame={N}", "setsar=1", "format=yuv420p"])
        lufs = "loudnorm=I=-18:TP=-2:LRA=7,aresample=48000," if it.get("normalize", True) else ""
        af = (f"atrim=0:{b - a:.6f},asetpts=N/SR/TB,aformat=sample_rates=48000:channel_layouts=stereo,{lufs}asetpts=N/SR/TB,"
              f"atempo={keff:.8f},asetpts=N/SR/TB,afade=t=in:d=0.012,apad,atrim=end_sample={NS},afade=t=out:st={N / FPS - 0.015:.4f}:d=0.015")
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", src]
        if not has_audio(src): cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]; amap = "1:a"
        else: amap = "0:a"
        cmd += ["-filter_complex", f"[0:v]{vf}[v];[{amap}]{af}[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-c:a", "pcm_s16le", out]
        run(cmd)
        if it.get("match_color"):                                    # colour/contrast match to a reference clip
            ref = spec["timeline"][int(it["match_color"]) if not isinstance(it["match_color"], bool) else 0]
            subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "colormatch.py"), out,
                            src_path(ref["src"]), str(float(ref.get("in", 0)) + 0.5), out + ".m.mov"], check=True)
            os.replace(out + ".m.mov", out)
        segs.append(dict(kind="clip", start=t_cursor, N=N, keff=keff, item=it, a=a))
        if it.get("whip_in") and i > 0: events.append((t_cursor - 0.45, "whoosh", 0.7))
    elif kind in ("compare", "cover"):
        fn = COVER.build_compare if kind == "compare" else COVER.build_cover
        N, ev = fn(it, out, dict(W=W, H=H, FPS=FPS, SR=SR, P=P, chain=frame_chain, grades=GRADES, bars=BARS, src_path=src_path,
                                 next_item=spec["timeline"][i + 1] if i + 1 < len(spec["timeline"]) else None))
        events += [(t_cursor + t, n, g) for t, n, g in ev]
        segs.append(dict(kind=kind, start=t_cursor, N=N, keff=1.0, item=it, a=0.0))
    else:
        raise SystemExit(f"unknown timeline type {kind}")
    t_cursor += segs[-1]["N"] / FPS
    print(f"[seg {i}] {kind:7s} {segs[-1]['N']:4d} frames  ends {t_cursor:7.3f}s", flush=True)
TOTAL_N = sum(s["N"] for s in segs); DUR = TOTAL_N / FPS

# ================= 2. master =================
lst = os.path.join(WORK, "segs.txt")
open(lst, "w").write("".join(f"file '{os.path.join(WORK, f'seg_{i:03d}.mov')}'\n" for i in range(len(segs))))
MASTER = os.path.join(WORK, "master.mov")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", MASTER])

# ================= timeline helpers =================
def seg_at(t):
    for s in segs:
        if s["start"] <= t < s["start"] + s["N"] / FPS: return s
    return segs[-1]
def to_out(s, src_t): return s["start"] + (src_t - s["a"]) / s["keff"]   # source seconds in a clip → output seconds

# ---- overlay layers ----
cache = {}
def cached(key, fn):
    if key not in cache:
        if len(cache) > 40: cache.pop(next(iter(cache)))
        cache[key] = fn()
    return cache[key]
CAP = dict(size=64, y=1330); CAP.update(spec.get("captions_style", {}))
def caption(text, keys, lit, keycol, pop, size, cy):
    def mk():
        sz = S(size); fnt = F("serif", sz); track = S(4)
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        widths = [d.textlength(ch, font=fnt) + track for ch in text]; tw = sum(widths) - track
        bar, gap, padx, pady, y = S(7), S(26), S(40), S(22), S(cy)
        bw = bar + gap + tw; bx0 = (W - bw) / 2 - padx; bx1 = (W + bw) / 2 + padx; by0, by1 = y - sz / 2 - pady, y + sz / 2 + pady + S(8)
        d.rounded_rectangle([bx0, by0, bx1, by1], S(16), fill=INK + (200,), outline=(255, 255, 255, 34), width=max(1, S(2)))
        x0 = bx0 + padx; d.rounded_rectangle([x0, by0 + S(22), x0 + bar, by1 - S(22)], S(3), fill=EM + (255,))
        ki = set()
        for kw in keys:
            j = text.find(kw)
            if j >= 0: ki |= set(range(j, j + len(kw)))
        x = x0 + bar + gap
        for j, ch in enumerate(text):
            on = j < lit; col = (keycol if j in ki else IV) if on else IV
            d.text((x, y - sz / 2 - S(6)), ch, font=fnt, fill=col + (255 if on else 90,)); x += widths[j]
        im = shadow(im, (0, S(10)), S(18), 0.40)
        if pop != 1.0:
            im2 = im.resize((int(W * pop), int(H * pop)), Image.LANCZOS); c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            c.paste(im2, ((W - im2.width) // 2, int(y - y * pop))); im = c
        return to_np(im)
    return cached(("cap", text, lit, pop, size, cy), mk)
def bigword(word, n, size, top):
    def mk():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        fnt = lambda ch: F("lat_serif" if ch.isascii() and ch.strip() else "serif", size * (0.92 if ch.isascii() else 1))
        ws = [d.textlength(ch, font=fnt(ch)) for ch in word]; x = (W - sum(ws)) / 2
        for j, ch in enumerate(word[:n]): d.text((x, top), ch, font=fnt(ch), fill=IV + (255,)); x += ws[j]
        return to_np(shadow(im, (0, S(12)), S(18), 0.4))
    return cached(("big", word, n, size, top), mk)
def prompt_box(text, state, label):
    def mk():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([S(70), S(250), W - S(70), S(400)], S(34), fill=(246, 241, 230, 248))
        d.text((S(110), S(272)), label, font=F("sans_m", S(26)), fill=(140, 130, 112))
        f = F("sans", S(46))
        if text: d.text((S(110), S(310)), text + ("|" if state == "typing" else ""), font=f, fill=INK)
        else: d.text((S(110), S(310)), "|", font=f, fill=INK)
        cx, cy, r = W - S(145), S(325), S(36 if state != "pressed" else 31)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=EM)
        if state == "done": d.line([(cx - S(16), cy + S(1)), (cx - S(4), cy + S(14)), (cx + S(18), cy - S(14))], fill="white", width=S(7))
        else:
            d.line([(cx, cy + S(16)), (cx, cy - S(16))], fill="white", width=S(6)); d.line([(cx - S(13), cy - S(3)), (cx, cy - S(16)), (cx + S(13), cy - S(3))], fill="white", width=S(6))
        return to_np(shadow(im, (0, S(10)), S(16), 0.45))
    return cached(("box", text, state, label), mk)

# ---- comment CTA (glass cards) ----
def rrmask(box, r):
    def mk():
        m = Image.new("L", (W * 2, H * 2), 0); ImageDraw.Draw(m).rounded_rectangle([v * 2 for v in box], r * 2, fill=255)
        return np.asarray(m.resize((W, H), Image.LANCZOS), np.float32)[..., None] / 255
    return cached(("rr",) + tuple(box) + (r,), mk)
def glass(comp, box, r, a):
    x0, y0, x1, y1 = box; m = rrmask(box, r) * a; ya, yb = max(0, y0 - 40), min(H, y1 + 40); reg = comp[ya:yb]
    sm = cv2.resize(reg, (W // 4, max(1, (yb - ya) // 4)), interpolation=cv2.INTER_AREA)
    bl = cv2.resize(cv2.GaussianBlur(sm, (0, 0), 6), (W, yb - ya)); g = bl * 0.30 + np.array(INK, np.float32) / 255 * 0.70
    out = comp.copy(); mm = m[ya:yb]; out[ya:yb] = reg * (1 - mm) + g * mm; return out
def heart(d, cx, cy, r, fill):
    pts = [(cx + 16 * math.sin(th) ** 3 * r / 16, cy - (13 * math.cos(th) - 5 * math.cos(2 * th) - 2 * math.cos(3 * th) - math.cos(4 * th)) * r / 16)
           for th in np.linspace(0, 2 * math.pi, 64)]
    d.polygon(pts, fill=fill)
def cta_comp(comp, t, C, s):
    ts = to_out(s, C["show"]); u = t - ts
    if u < 0: return comp
    ty = to_out(s, C["type_at"]) if "type_at" in C else ts + 0.9
    th_ = to_out(s, C["heart_at"]) if "heart_at" in C else ty + 0.45
    tr = to_out(s, C["reply_at"]) if "reply_at" in C else th_ + 0.5
    kw = C.get("keyword", "EDIT"); CARD = (S(48), S(900), S(930), S(1212)); REPLY = (S(134), S(1240), S(930), S(1400))   # Reels safe zone
    e = eq(u / 0.55); dy = int((1 - e) * S(46)); rr_ = t - tr; er = eq(rr_ / 0.5) if rr_ > 0 else 0; dyr = int((1 - er) * S(40))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    ds.rounded_rectangle([CARD[0], CARD[1] + dy + S(22), CARD[2], CARD[3] + dy + S(22)], S(34), fill=(0, 0, 0, int(150 * e)))
    if er > 0: ds.rounded_rectangle([REPLY[0], REPLY[1] + dyr + S(18), REPLY[2], REPLY[3] + dyr + S(18)], S(30), fill=(0, 0, 0, int(140 * er)))
    comp = over(comp, to_np(sh.filter(ImageFilter.GaussianBlur(S(28)))))
    comp = glass(comp, (CARD[0], CARD[1] + dy, CARD[2], CARD[3] + dy), S(34), e)
    if er > 0: comp = glass(comp, (REPLY[0], REPLY[1] + dyr, REPLY[2], REPLY[3] + dyr), S(30), er)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); A = lambda v: int(255 * max(0, min(1, v)))
    x0, y0 = CARD[0], CARD[1] + dy
    d.rounded_rectangle([CARD[0], y0, CARD[2], CARD[3] + dy], S(34), outline=(255, 255, 255, int(30 * e)), width=max(1, S(2)))
    la = eq((u - 0.12) / 0.35); xx = x0 + S(72)
    d.ellipse([x0 + S(44), y0 + S(44), x0 + S(56), y0 + S(56)], fill=EM + (A(la),))
    for ch in C.get("label", "COMMENTS"): d.text((xx, y0 + S(37)), ch, font=F("mono", S(22)), fill=(170, 165, 156, A(la))); xx += d.textlength(ch, font=F("mono", S(22))) + S(5)
    head = C.get("headline", f"留言「{kw}」"); xx = x0 + S(40)
    for j, ch in enumerate(head):
        p = eq((u - 0.18 - j * 0.035) / 0.4); isk = ch in kw and ch.isascii(); fn = F("lat_serif", S(58)) if ch.isascii() else F("serif", S(62))
        d.text((xx, y0 + S(76) + (1 - p) * S(18) + (S(4) if ch.isascii() else 0)), ch, font=fn, fill=(EM if isk else IV) + (A(p),)); xx += d.textlength(ch, font=fn) + S(2)
    ps = eq((u - 0.42) / 0.4); d.text((xx + S(22), y0 + S(98) + (1 - ps) * S(10)), C.get("sub", ""), font=F("sans_m", S(32)), fill=(190, 184, 174, A(ps)))
    pi = eq((u - 0.50) / 0.45); iy = y0 + S(196) + (1 - pi) * S(14)
    d.rounded_rectangle([x0 + S(32), iy, CARD[2] - S(32), iy + S(84)], S(42), fill=(255, 255, 255, int(20 * pi)), outline=(255, 255, 255, int(36 * pi)), width=max(1, S(2)))
    d.ellipse([x0 + S(46), iy + S(14), x0 + S(102), iy + S(70)], fill=(70, 70, 74, A(pi)))
    n = 0 if t < ty else min(len(kw), 1 + int((t - ty) / 0.077)); tx = x0 + S(124)
    if n == 0: d.text((tx, iy + S(18)), C.get("placeholder", "新增留言⋯"), font=F("sans_m", S(32)), fill=(140, 136, 128, A(pi)))
    else: d.text((tx, iy + S(16)), kw[:n], font=F("lat_serif", S(40)), fill=IV + (255,)); tx += d.textlength(kw[:n], font=F("lat_serif", S(40)))
    sent = t >= th_; bx, by = CARD[2] - S(80), iy + S(42)
    if not sent:
        if n > 0 or int(u * 2.2) % 2 == 0: d.rounded_rectangle([tx + S(6), iy + S(20), tx + S(10), iy + S(64)], S(2), fill=EM + (A(pi),))
        rdy = n >= len(kw); d.ellipse([bx - S(30), by - S(30), bx + S(30), by + S(30)], fill=(EM if rdy else (80, 80, 84)) + (A(pi),))
        d.polygon([(bx - S(11), by - S(13)), (bx + S(15), by), (bx - S(11), by + S(13)), (bx - S(5), by)], fill=(22, 22, 24, A(pi)) if rdy else (160, 160, 160, A(pi)))
    else:
        q = t - th_; heart(d, bx, by + S(2), S(26) * (1 + 0.35 * math.sin(min(1, q / 0.28) * math.pi)), EM + (255,))
        if q < 0.45:
            for k in range(8):
                ang = 2 * math.pi * k / 8; r2 = S(30) + S(38) * eq(q / 0.45); sz = S(7) * (1 - q / 0.45)
                cx, cy = bx + r2 * math.cos(ang), by + r2 * math.sin(ang); d.ellipse([cx - sz, cy - sz, cx + sz, cy + sz], fill=EM + (A(1 - q / 0.45),))
    if er > 0:
        rx, ry = REPLY[0], REPLY[1] + dyr
        d.rounded_rectangle([REPLY[0], ry, REPLY[2], REPLY[3] + dyr], S(30), outline=(255, 255, 255, int(30 * er)), width=max(1, S(2)))
        d.line([(x0 + S(74), CARD[3] + dy - S(2)), (x0 + S(74), ry + S(52)), (rx - S(2), ry + S(52))], fill=EM + (int(150 * er),), width=max(1, S(3)))
        ca = eq((rr_ - 0.10) / 0.4)
        d.ellipse([rx + S(26), ry + S(22), rx + S(110), ry + S(106)], fill=(16, 16, 17, A(ca)), outline=EM + (A(ca),), width=max(1, S(3)))
        d.text((rx + S(46), ry + S(32)), P["avatar"], font=F("serif", S(44)), fill=IV + (A(ca),))
        fnm = F("sans", S(32)); d.text((rx + S(134), ry + S(24)), C.get("author", P["brand"]), font=fnm, fill=IV + (A(ca),))
        bw_ = d.textlength(C.get("author", P["brand"]), font=fnm)
        d.rounded_rectangle([rx + S(146) + bw_, ry + S(31), rx + S(146) + bw_ + S(64), ry + S(63)], S(16), outline=EM + (A(ca),), width=max(1, S(2)))
        d.text((rx + S(146) + bw_ + S(10), ry + S(33)), "作者", font=F("sans", S(22)), fill=EM + (A(ca),))
        d.text((REPLY[2] - S(30) - d.textlength("剛剛", font=F("sans", S(22))), ry + S(33)), "剛剛", font=F("sans", S(22)), fill=(150, 145, 136, A(ca)))
        cb = eq((rr_ - 0.22) / 0.4); msg = C.get("reply", "流程傳給你了"); fr2 = F("sans_m", S(34))
        d.text((rx + S(134), ry + S(76) + (1 - cb) * S(10)), msg, font=fr2, fill=(232, 226, 214, A(cb)))
        cx, cy = rx + S(134) + d.textlength(msg, font=fr2) + S(34), ry + S(98); ck = eq((rr_ - 0.45) / 0.3)
        if ck > 0:
            rc = S(17) * (1 + 0.25 * math.sin(min(1, (rr_ - 0.45) / 0.3) * math.pi))
            d.ellipse([cx - rc, cy - rc, cx + rc, cy + rc], fill=EM + (A(ck),)); d.line([(cx - S(8), cy), (cx - S(2), cy + S(6)), (cx + S(9), cy - S(7))], fill=(22, 22, 24, A(ck)), width=max(1, S(4)))
    return over(comp, to_np(im))

# ---- schedule overlay SFX from the spec ----
for s in segs:
    if s["kind"] != "clip": continue
    it = s["item"]
    for pr in it.get("prompts", []):
        t0 = to_out(s, pr["start"]); n = len(pr["text"])
        for k in range(n): events.append((t0 + k * 0.08, "click", 1.0))
        tsend = to_out(s, pr["send"]) if "send" in pr else t0 + n * 0.08 + 0.1
        events += [(tsend, "tick", 0.9), (tsend + 0.07, "pop", 0.8)]
    for bw in it.get("bigwords", []): events.append((to_out(s, bw["start"]), "boom", 0.35))
    C = it.get("cta")
    if C:
        events.append((to_out(s, C["show"]) - 0.04, "swish", 0.8))
        ts_ = to_out(s, C["show"]); ty = to_out(s, C["type_at"]) if "type_at" in C else ts_ + 0.9
        th_ = to_out(s, C["heart_at"]) if "heart_at" in C else ty + 0.45; tr = to_out(s, C["reply_at"]) if "reply_at" in C else th_ + 0.5
        for k in range(len(C.get("keyword", "EDIT"))): events.append((ty + k * 0.077, "click", 1.0))
        events += [(th_, "pop", 0.9), (tr, "pop", 0.8)]

# ================= 3. overlay pass =================
VID = os.path.join(WORK, "video.mp4")
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", MASTER, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", VID], stdin=subprocess.PIPE)
whips = [s["start"] for s in segs if s["item"].get("whip_in") and s["start"] > 0]
bigpos = {}
for n in range(TOTAL_N):
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    t = n / FPS; rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy(); s = seg_at(t); it = s["item"]
    if s["kind"] == "clip":
        push = float(it.get("push", 0)); d0 = s["N"] / FPS
        if push: rgb = zoom(rgb, 1 + push * (0.5 - 0.5 * math.cos(math.pi * (t - s["start"]) / d0)), 0.4)
        fr = rgb.astype(np.float32) / 255; comp = fr.copy(); low = False
        C = it.get("cta"); cta_on = C is not None and t >= to_out(s, C["show"])
        for bw in it.get("bigwords", []):
            t0, t1 = to_out(s, bw["start"]), to_out(s, bw["end"])
            if not (t0 <= t < t1): continue
            word = bw["word"]; nch = len(word); p = (t - t0) / 0.32; k = min(nch, int(p * nch) + 1); frac = min(1, p * nch - (k - 1))
            place = bw.get("place", "auto"); m = person_mask(rgb) if place != "low" else None
            key = (id(bw),)
            if key not in bigpos:
                ht = head_top(m) if m is not None else None
                size = int(max(S(170), min(S(bw.get("size", 300)), (ht + S(20) - S(120)) / 1.12, W * 0.9 / max(1, nch)))) if ht else 0
                if m is None or size <= S(170) or place == "low": bigpos[key] = ("low", int(min(S(bw.get("size", 300)), W * 0.9 / max(1, nch))), S(1150))
                else: bigpos[key] = ("top", size, max(S(120), int(ht + 0.10 * size - size * 1.18)))
            mode, size, top = bigpos[key]
            if k > 1: comp = over(comp, bigword(word, k - 1, size, top))
            comp = over(comp, bigword(word, k, size, top), frac)
            if mode == "top": comp = comp * (1 - m) + fr * m
            else: low = True
        for pr in it.get("prompts", []):
            t0 = to_out(s, pr["start"]); n_ = len(pr["text"]); tsend = to_out(s, pr["send"]) if "send" in pr else t0 + n_ * 0.08 + 0.1
            tend = to_out(s, pr["end"]) if "end" in pr else tsend + 1.2
            if not (t0 - 0.3 <= t < tend + 0.3): continue
            a = eq((t - t0 + 0.3) / 0.3) * (1 - eq((t - tend) / 0.3) if t > tend else 1)
            if t < t0: st = ("", "typing")
            elif t < tsend: st = (pr["text"][:min(n_, 1 + int((t - t0) / 0.08))], "typing")
            elif t < tsend + 0.07: st = (pr["text"], "pressed")
            else: st = (pr["text"], "done")
            comp = over(comp, prompt_box(st[0], st[1], pr.get("label", "對 AI 說")), a)
        if C is not None: comp = cta_comp(comp, t, C, s)
        if not low and not cta_on and it.get("captions_on", True):
            for c in it.get("captions", []):
                t0, t1 = to_out(s, c["start"]), to_out(s, c["end"])
                if t0 <= t < t1:
                    text = c["text"]; nch = len(text); lit = nch if c.get("instant") else min(nch, 1 + int((t - t0) / max(1e-3, (t1 - t0) * 0.85) * nch))
                    pop = round(1.0 + (0.08 * (1 - ease((t - t0) / 0.12)) if t - t0 < 0.12 else 0), 2)
                    kc = P.get(c.get("color", "accent"), EM) if isinstance(c.get("color", "accent"), str) else EM
                    comp = over(comp, caption(text, c.get("keys", []), lit, kc, pop, c.get("size", CAP["size"]), c.get("y", CAP["y"]))); break
    else:
        comp = rgb.astype(np.float32) / 255
    for b in whips:
        dt = t - b
        if abs(dt) < 0.12:
            w = 1 - abs(dt) / 0.12; img = zoom((np.clip(comp, 0, 1) * 255).astype(np.uint8), 1 + 0.10 * w)
            L = max(3, int(S(90) * w)); ker = np.zeros((L, L), np.float32); ker[:, L // 2] = 1.0 / L
            comp = cv2.filter2D(img, -1, ker).astype(np.float32) / 255
    enc.stdin.write((np.clip(comp, 0, 1) * 255).astype(np.uint8).tobytes())
    if n % (FPS * 5) == 0: print(f"[overlay] {t:6.1f}/{DUR:.1f}s", flush=True)
enc.stdin.close(); enc.wait(); dec.kill()

# ================= 4. audio =================
NS = round(DUR * SR); fx = np.zeros((NS + SR, 2), np.float32); rng = np.random.default_rng(3)
def gen(name):
    if name == "click":
        k = int(0.018 * SR); x = rng.standard_normal(k) * np.exp(-np.arange(k) / SR * 300) * 0.25; return np.stack([x, x], 1).astype(np.float32)
    if name == "swish":
        k = int(0.16 * SR); tt = np.arange(k) / SR; x = np.convolve(rng.standard_normal(k) * np.sin(np.pi * tt / tt[-1]) ** 2 * 0.35, np.ones(6) / 6, "same")
        return np.stack([x, x], 1).astype(np.float32)
    if name == "shutter":
        k = int(0.03 * SR); x = rng.standard_normal(k) * np.exp(-np.arange(k) / SR * 160) * 0.5; return np.stack([x, x], 1).astype(np.float32)
    if name == "whoosh_rev": return sfx("whoosh")[::-1][-int(0.3 * SR):].copy()
    if name.startswith("shimmer"):
        d = float(name.split(":")[1]); k = int(d * SR); tt = np.arange(k) / SR
        x = np.convolve(rng.standard_normal(k), np.ones(3) / 3, "same") * 0.022 + 0.018 * np.sin(2 * np.pi * (900 + 500 * tt / d) * tt) * np.sin(2 * np.pi * 2.5 * tt) ** 2
        x *= np.minimum(1, tt / 0.4) * np.minimum(1, (d - tt) / 0.25); return np.stack([x, x], 1).astype(np.float32)
    return sfx(name)
for t0, name, g in events:
    x = gen(name); i0 = max(0, int(t0 * SR)); j = min(len(fx), i0 + len(x)); fx[i0:j] += x[:j - i0] * g
FXW = os.path.join(WORK, "sfx.wav"); sf.write(FXW, fx[:NS], SR)
AUD = os.path.join(WORK, "audio.wav")
mus = spec.get("music"); inputs = ["-i", MASTER, "-i", FXW]
if mus:
    inputs += ["-stream_loop", "-1", "-i", src_path(mus["src"])]
    g = mus.get("gain_db", -20); st = mus.get("start", 0)
    fc = (f"[2:a]atrim={st}:{st + DUR},asetpts=N/SR/TB,aformat=sample_rates=48000:channel_layouts=stereo,volume={g}dB,"
          f"afade=t=in:d=0.8,afade=t=out:st={max(0, DUR - mus.get('fade_out', 2.0)):.3f}:d={mus.get('fade_out', 2.0)}[m];"
          "[0:a]asplit=2[v][vsc];[m][vsc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[md];"
          "[v][1:a][md]amix=inputs=3:duration=first:normalize=0[mix];")
else:
    fc = "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[mix];"
fc += f"[mix]acompressor=threshold=-20dB:ratio=3:attack=10:release=200:makeup=2,loudnorm=I={O['lufs']}:TP=-1.5:LRA=7,aresample=48000,apad,atrim=end_sample={NS}[a]"
run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", fc, "-map", "[a]", "-c:a", "pcm_s16le", AUD])

# ================= 5. encode to size =================
abr = 160_000; vbr = int(max(1.5e6, min(12e6, (O["max_mb"] * 8 * 1024 * 1024 * 0.94) / DUR - abr)))
run(["ffmpeg", "-v", "error", "-y", "-i", VID, "-i", AUD, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-b:v", str(vbr), "-maxrate", str(int(vbr * 1.2)),
     "-bufsize", str(int(vbr * 2.4)), "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", OUT])
pr = probe(OUT); durs = {s["codec_type"]: float(s.get("duration", 0)) for s in pr["streams"]}
qa = dict(output=OUT, seconds=round(DUR, 3), size_mb=round(os.path.getsize(OUT) / 1048576, 2), video_s=durs.get("video"), audio_s=durs.get("audio"),
          av_gap_ms=round(abs(durs.get("video", 0) - durs.get("audio", 0)) * 1000, 1), segments=[dict(kind=s["kind"], start=round(s["start"], 3), frames=s["N"]) for s in segs])
json.dump(qa, open(os.path.join(WORK, "qa.json"), "w"), indent=1, ensure_ascii=False); print(json.dumps(qa, ensure_ascii=False))
