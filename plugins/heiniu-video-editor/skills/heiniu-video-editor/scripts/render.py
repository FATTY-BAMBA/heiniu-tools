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
import captions as CAPV2
import uicards as UICARDS

ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--out"); ap.add_argument("--work"); ap.add_argument("--preview", action="store_true")
args = ap.parse_args()
SPEC_DIR = os.path.dirname(os.path.abspath(args.spec)); spec = resolve_words(json.load(open(args.spec)), os.path.dirname(os.path.abspath(args.spec)))
O = dict(w=1080, h=1920, fps=30, max_mb=30, lufs=-14); O.update(spec.get("output", {}))
if args.preview: O.update(w=540, h=960, max_mb=min(float(O["max_mb"]), 6))
W, H, FPS = int(O["w"]), int(O["h"]), int(O["fps"]); SR = 48000; SC = W / 1080.0
P = palette(spec.get("style")); INK, IV, EM = P["ink"], P["ivory"], P["accent"]; RED = P["seal"]
spec["timeline"] = expand_timeline(spec["timeline"], float(spec.get("speed", 1.0)))   # speed ramps → clip pieces
WORK = os.path.abspath(args.work or os.path.join(SPEC_DIR, "_render")); os.makedirs(WORK, exist_ok=True)
OUT = os.path.abspath(args.out or os.path.join(SPEC_DIR, spec.get("name", "final") + ".mp4"))
def src_path(p): return p if os.path.isabs(p) else os.path.join(SPEC_DIR, p)
def S(v): return int(round(v * SC))                                  # scale 1080-based layout values
GRADES = {
    "soft": "eq=contrast=1.04:saturation=1.03:gamma=1.02:brightness=0.01,colorbalance=rs=-0.05:bs=0.05:rm=0.02:bh=-0.02,vignette=PI/5",
    "warm": "eq=contrast=1.05:saturation=1.06:gamma=1.0,colorbalance=rs=0.03:bs=-0.03,vignette=PI/5",
    "airy": "eq=contrast=0.96:saturation=1.07:gamma=1.07:brightness=0.025,colorbalance=rs=0.03:bs=-0.02:rh=0.03:bh=-0.03",     # 日常 Vlog: lifted, warm, soft
    "crisp": "eq=contrast=1.07:saturation=1.0:gamma=1.01,unsharp=5:5:0.45",                                                  # 知識乾貨: neutral and sharp
    "punchy": "eq=contrast=1.12:saturation=1.3:gamma=0.99",                                                                  # 搞笑: loud colour
    "cinema": "eq=contrast=1.12:saturation=0.9:gamma=0.97,colorbalance=rs=-0.06:bs=0.07:rh=0.07:bh=-0.07,vignette=PI/4",     # Showcase: teal shadows, warm skin
    "clean": "eq=contrast=1.03:saturation=1.05:gamma=1.05:brightness=0.02",                                                  # 開箱: bright, true colour
    "muted": "eq=contrast=1.06:saturation=0.42:gamma=1.02,colorbalance=bs=0.02:bh=-0.01",                                      # 極簡: desaturated, one accent colour carries
    "film": "eq=contrast=1.06:saturation=0.9:gamma=1.02,colorbalance=rs=-0.03:bs=0.04:rh=0.05:bh=-0.04,curves=all='0/0.045 0.5/0.5 1/0.965',vignette=PI/4.5",   # 電影感: lifted blacks, warm skin
    "none": "",
}
def BARS(): b = S(spec.get("bars_px", 200)); return f"drawbox=x=0:y=0:w=iw:h={b}:color=black:t=fill,drawbox=x=0:y=ih-{b}:w=iw:h={b}:color=black:t=fill"
def run(cmd): subprocess.run(cmd, check=True)
# ---- voice clean-up: RNNoise (ffmpeg arnndn) sized to how noisy each take is, plus a light "studio" EQ ----
def _rnn_model():
    """the RNNoise model ships as plain-text parts (each < 256 KiB); join them once into the work folder"""
    import glob
    parts = sorted(glob.glob(os.path.join(ASSETS, "rnnoise", "sh.rnnn.part*")), key=lambda p: int(p.rsplit("part", 1)[1]))
    if not parts: return ""
    dst = os.path.join(WORK, "sh.rnnn")
    if not os.path.exists(dst): open(dst, "w").write("".join(open(p).read() for p in parts))
    return dst
RNN = _rnn_model(); VOICE = spec.get("voice", "auto"); _snr = {}
def take_snr(path):
    """rough SNR of a take: loud speech frames vs the quietest frames (dB)"""
    if path not in _snr:
        b = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-t", "240", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
        x = np.frombuffer(b, np.float32)
        if len(x) < 16000: _snr[path] = 99.0
        else:
            fr = x[:len(x) // 480 * 480].reshape(-1, 480); r = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-7)
            _snr[path] = float(np.percentile(r, 92) - np.percentile(r, 8))
    return _snr[path]
def voice_chain(path):
    """filters that run BEFORE the clip is cut (arnndn adds 480 samples of latency, trimmed right after so lip-sync stays exact)"""
    if VOICE == "off" or not os.path.exists(RNN): return "", None
    snr = take_snr(path); mix = 1.0 if VOICE == "strong" or snr < 22 else 0.85 if snr < 32 else 0.55
    m = RNN.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    eq = "highpass=f=80,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=2.5,deesser=i=0.3,"
    return f"aformat=sample_rates=48000,{eq}arnndn=m='{m}':mix={mix},atrim=start_sample=480,asetpts=N/SR/TB,", dict(snr_db=round(snr, 1), mix=mix)
VOICE_QA = {}
def has_audio(p): return any(s.get("codec_type") == "audio" for s in probe(p).get("streams", []))

# ================= 1. segments =================
segs = []                                                            # dicts: kind, start, N, keff, item
events = []                                                          # (t, name, gain) SFX in output seconds
t_cursor = 0.0
def frame_chain(c):
    if c.get("fit"):                                                  # screen recording: whole frame visible on a blurred, dimmed copy of itself
        fw = int(W * float(c.get("fit_width", 0.94)) // 2 * 2)
        return [f"split=2[fa][fb];[fa]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:2,eq=brightness=-0.22:saturation=0.8[fbg];"
                f"[fb]scale={fw}:-2:flags=lanczos[ffg];[fbg][ffg]overlay=(W-w)/2:(H-h)/2*{float(c.get('fit_y', 0.86)):.3f}"]
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
        if it.get("_mute"): lufs = "volume=0,"
        vc, vq = voice_chain(src) if not it.get("_mute") and has_audio(src) else ("", None)
        if vq: VOICE_QA[os.path.basename(src)] = vq
        af = (f"{vc}atrim=0:{b - a:.6f},asetpts=N/SR/TB,aformat=sample_rates=48000:channel_layouts=stereo,{lufs}asetpts=N/SR/TB,"
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
        if it.get("whip_in") and i > 0: events.append((t_cursor, "whoosh", 0.7))          # peak lands on the cut
    elif kind == "freeze":                                           # held frame: 「等一下」 stamp, optional self-drawing red circle, record scratch
        src = src_path(it["src"]); N = max(1, round(float(it.get("dur", 1.0)) * FPS)); NS = round(N * SR / FPS)
        vf = ",".join(["trim=end_frame=1"] + frame_chain(it) + [f"loop=loop={N}:size=1:start=0", f"setpts=N/({FPS}*TB)", f"fps={FPS}", f"trim=end_frame={N}", "setsar=1", "format=yuv420p"])
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{float(it['at']):.4f}", "-i", src, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-filter_complex", f"[0:v]{vf}[v];[1:a]atrim=end_sample={NS}[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-c:a", "pcm_s16le", out])
        segs.append(dict(kind="freeze", start=t_cursor, N=N, keff=1.0, item=it, a=0.0))
        events += [(t_cursor, "scratch", 0.9), (t_cursor + 0.05, "boom", 0.3)]
        if it.get("circle"): events.append((t_cursor + 0.18, "swish", 0.5))
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
CAPE = CAPV2.Engine(W, H, S, P, {k: v for k, v in CAP.items() if k not in ("size", "y")})        # v2 looks: impact / editorial / minimal / news / vlog / label
try: CHARS = load_chars(spec["words"] if os.path.isabs(spec["words"]) else os.path.join(SPEC_DIR, spec["words"])) if spec.get("words") else {}
except Exception: CHARS = {}
GRAIN = float(spec.get("grain", 0)); _grain = [cv2.resize(np.random.default_rng(k).standard_normal((H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for k in range(6)] if GRAIN else []
def caption(text, keys, lit, keycol, pop, size, cy, look="card"):
    """karaoke caption in one of the template looks: card (墨牛 ink card) | clean (vlog) | bold (marker highlight) | meme | label"""
    def mk():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        face = {"card": "serif", "clean": "sans", "bold": "black", "meme": "black", "label": "sans"}.get(look, "serif")
        track = S({"card": 4, "clean": 2, "bold": 2, "meme": 1, "label": 2}.get(look, 3))
        sz = S(size)
        while True:                                                       # shrink to fit 88% of the width
            fnt = F(face, sz); widths = [d.textlength(ch, font=fnt) + track for ch in text]; tw = sum(widths) - track
            if tw <= W * 0.88 - (S(120) if look in ("card", "label") else 0) or sz <= S(30): break
            sz = int(sz * 0.94)
        ki = set(); spans = []
        for kw in keys:
            j = text.find(kw)
            if j >= 0: ki |= set(range(j, j + len(kw))); spans.append((j, j + len(kw)))
        y = S(cy)
        if look == "card":
            bar, gap, padx, pady = S(7), S(26), S(40), S(22)
            bw = bar + gap + tw; bx0 = (W - bw) / 2 - padx; bx1 = (W + bw) / 2 + padx; by0, by1 = y - sz / 2 - pady, y + sz / 2 + pady + S(8)
            d.rounded_rectangle([bx0, by0, bx1, by1], S(16), fill=INK + (200,), outline=(255, 255, 255, 34), width=max(1, S(2)))
            x0 = bx0 + padx; d.rounded_rectangle([x0, by0 + S(22), x0 + bar, by1 - S(22)], S(3), fill=EM + (255,))
            x = x0 + bar + gap
            for j, ch in enumerate(text):
                on = j < lit; col = (keycol if j in ki else IV) if on else IV
                d.text((x, y - sz / 2 - S(6)), ch, font=fnt, fill=col + (255 if on else 90,)); x += widths[j]
            return to_np(shadow(im, (0, S(10)), S(18), 0.40))
        x0 = (W - tw) / 2; xs = [x0 + sum(widths[:j]) for j in range(len(text))]
        if look == "label":                                               # ivory tag with an accent block, like a price label
            padx, pady, blk = S(34), S(20), S(14)
            bx0, bx1 = x0 - padx - blk - S(8), x0 + tw + padx; by0, by1 = y - sz / 2 - pady, y + sz / 2 + pady
            d.rounded_rectangle([bx0, by0, bx1, by1], S(8), fill=(248, 245, 238, 250))
            d.rectangle([bx0, by0, bx0 + blk, by1], fill=keycol + (255,))
            for j, ch in enumerate(text):
                on = j < lit; col = keycol if (j in ki and on) else INK
                d.text((xs[j], y), ch, font=fnt, fill=col + (255 if on else 105,), anchor="lm")
            return to_np(shadow(im, (0, S(8)), S(14), 0.35))
        if look == "bold":                                                # heavy white text, key words on a marker stroke that wipes in
            for j0, j1 in spans:
                if lit <= j0: continue
                k = min(lit, j1); mx0 = xs[j0] - S(10); mx1 = xs[k - 1] + widths[k - 1] - track + S(10)
                d.rounded_rectangle([mx0, y - sz * 0.50, mx1, y + sz * 0.52], S(10), fill=keycol + (255,))
            for j, ch in enumerate(text):
                marked = j in ki and any(j0 <= j < min(lit, j1) for j0, j1 in spans)
                d.text((xs[j], y), ch, font=fnt, fill=(INK if marked else (255, 255, 255)) + (255,), anchor="lm",
                       stroke_width=0 if marked else S(5), stroke_fill=(20, 20, 22, 255))
            return to_np(shadow(im, (0, S(6)), S(12), 0.45))
        if look == "meme":                                                # big black-stroked letters that pop in one by one
            for j, ch in enumerate(text[:lit]):
                d.text((xs[j], y), ch, font=fnt, fill=(keycol if j in ki else (255, 255, 255)) + (255,), anchor="lm", stroke_width=S(10), stroke_fill=(0, 0, 0, 255))
            return to_np(shadow(im, (0, S(8)), S(6), 0.55))
        for j, ch in enumerate(text):                                     # clean: plain white sans, soft outline, keys tinted
            on = j < lit; a_ = 255 if on else 150
            d.text((xs[j], y), ch, font=fnt, fill=(keycol if j in ki else (255, 255, 255)) + (a_,), anchor="lm", stroke_width=S(2), stroke_fill=(0, 0, 0, int(90 * a_ / 255)))
        return to_np(shadow(im, (0, S(4)), S(10), 0.55))
    def popped():
        base = mk()
        if pop == 1.0: return base
        sc = pop; im = Image.fromarray((base * 255).astype(np.uint8), "RGBA"); w2, h2 = int(W * sc), int(H * sc)
        im2 = im.resize((w2, h2), Image.LANCZOS); c = Image.new("RGBA", (W, H), (0, 0, 0, 0)); yy = S(cy)
        c.paste(im2, ((W - w2) // 2, int(yy - yy * sc))); return to_np(c)
    return cached(("cap", look, text, lit, pop, size, cy, tuple(keys), keycol), popped)
def bigword(word, n, size, top, col=None):
    col = col or IV
    def mk():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        fnt = lambda ch: F("lat_serif" if ch.isascii() and ch.strip() else "serif", size * (0.92 if ch.isascii() else 1))
        ws = [d.textlength(ch, font=fnt(ch)) for ch in word]; x = (W - sum(ws)) / 2
        for j, ch in enumerate(word[:n]): d.text((x, top), ch, font=fnt(ch), fill=col + (255,)); x += ws[j]
        return to_np(shadow(im, (0, S(12)), S(18), 0.4 if col == IV else 0.18))
    return cached(("big", word, n, size, top, col), mk)
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

HDR = spec.get("header")
def header_img(hd):
    """persistent top line set by a style template: bar (知識乾貨 topic + episode badge) | label (開箱 tag) | stamp (vlog date / place)"""
    def mk():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); kind = hd.get("kind", "bar"); text = hd.get("text", ""); badge = hd.get("badge", "")
        y0 = S(hd.get("y", 205))
        if kind == "stamp":
            f = F("mono", S(36)); d.ellipse([S(64), y0 + S(12), S(84), y0 + S(32)], fill=(232, 60, 50, 255))
            d.text((S(122), y0), text, font=f, fill=(255, 255, 255, 240), stroke_width=S(2), stroke_fill=(0, 0, 0, 90))
            return to_np(shadow(im, (0, S(3)), S(6), 0.5))
        if kind == "masthead":                                             # 雜誌: brand + issue on the left, topic on the right, hairline rule
            fb_, fi, ft = F("serif", S(64)), F("mono", S(28)), F("sans_m", S(32)); x0 = S(64); x1 = W - S(64)
            d.text((x0, y0 + S(60)), P["brand"], font=fb_, fill=IV + (255,), anchor="ls"); bx = x0 + d.textlength(P["brand"], font=fb_) + S(18)
            d.text((bx, y0 + S(56)), badge or "N°01", font=fi, fill=EM + (255,), anchor="ls")
            d.text((x1, y0 + S(56)), text, font=ft, fill=IV + (235,), anchor="rs")
            d.rectangle([x0, y0 + S(78), x1, y0 + S(78) + max(2, S(3))], fill=IV + (190,))
            return to_np(shadow(im, (0, S(3)), S(8), 0.45))
        if kind == "news":                                                 # 新聞快報: red tag + white headline bar + red rule
            ftag, fh = F("sans", S(32)), F("sans", S(38)); tag = badge or "快報"; x0 = S(56)
            tw_ = d.textlength(tag, font=ftag) + S(36); hw = min(W - S(56) - x0 - tw_, d.textlength(text, font=fh) + S(44)); y1 = y0 + S(74)
            d.rectangle([x0, y0, x0 + tw_, y1], fill=RED + (255,)); d.text((x0 + tw_ / 2, (y0 + y1) / 2), tag, font=ftag, fill=(255, 255, 255), anchor="mm")
            d.rectangle([x0 + tw_, y0, x0 + tw_ + hw, y1], fill=(250, 248, 244, 250)); d.text((x0 + tw_ + S(22), (y0 + y1) / 2), text, font=fh, fill=INK, anchor="lm")
            d.rectangle([x0, y1, x0 + tw_ + hw, y1 + S(6)], fill=RED + (255,))
            return to_np(shadow(im, (0, S(6)), S(12), 0.35))
        f = F("sans", S(40)); fb = F("mono", S(30)) if badge.isascii() else F("sans", S(30)); tw = d.textlength(text, font=f); bw = (d.textlength(badge, font=fb) + S(36)) if badge else 0
        x0 = (W - (tw + bw + S(56))) / 2; x1 = x0 + tw + bw + S(56); y1 = y0 + S(78)
        if kind == "label":
            d.rounded_rectangle([x0, y0, x1, y1], S(10), fill=(248, 245, 238, 245)); col = INK
        else:
            d.rounded_rectangle([x0, y0, x1, y1], S(39), fill=INK + (225,), outline=(255, 255, 255, 40), width=max(1, S(2))); col = IV
        if badge:
            d.rounded_rectangle([x0 + S(14), y0 + S(14), x0 + S(14) + bw - S(8), y1 - S(14)], S(25 if kind != "label" else 6), fill=EM + (255,))
            d.text((x0 + S(14) + (bw - S(8)) / 2, (y0 + y1) / 2), badge, font=fb, fill=INK if kind != "label" else (255, 255, 255), anchor="mm")
        d.text((x0 + S(28) + bw, (y0 + y1) / 2), text, font=f, fill=col + (255,), anchor="lm")
        return to_np(shadow(im, (0, S(6)), S(12), 0.35))
    return cached(("hdr", json.dumps(hd, ensure_ascii=False)), mk)

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

# ---- batch-1 effects: chat bubbles, checklist, phone mockup, freeze stamp, speed badge ----
def bubble_img(text, who):
    def mk():
        f = F("sans", S(40)); pad, av = S(30), S(64); tw = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(text, font=f))
        ai = who != "me"; w = tw + pad * 2 + (av + S(18) if ai else 0); h = S(104)
        im = Image.new("RGBA", (w + S(40), h + S(40)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x0, y0 = S(20), S(14)
        fill = (246, 241, 230, 250) if ai else INK + (236,); col = INK if ai else IV
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], S(34), fill=fill, outline=(255, 255, 255, 40 if not ai else 0), width=max(1, S(2)))
        tx = x0 + pad
        if ai:
            d.ellipse([tx, y0 + (h - av) // 2, tx + av, y0 + (h + av) // 2], fill=EM)
            d.text((tx + av / 2, y0 + h / 2), "AI", font=F("mono", S(24)), fill=(255, 255, 255), anchor="mm"); tx += av + S(18)
        d.text((tx, y0 + h / 2 - S(2)), text, font=f, fill=col, anchor="lm")
        return shadow(im, (0, S(8)), S(14), 0.38)
    return cached(("bub", text, who), mk)
def bubbles_comp(comp, t, items, s, seg_end):
    vis = [(to_out(s, b["start"]), b) for b in items if to_out(s, b["start"]) <= t]
    if not vis: return comp
    ends = [to_out(s, b["end"]) for b in items if "end" in b]; gend = min(ends or [seg_end])
    fade = (1 - eq((t - (gend - 0.18)) / 0.18) if t > gend - 0.18 else 1) if ends else 1
    if fade <= 0: return comp
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); base = S(1480); step = S(118); n = len(vis)
    for k, (t0, b) in enumerate(vis[-3:]):
        rank = len(vis[-3:]) - 1 - k                                     # 0 = newest (bottom)
        newer = [tt for tt, _ in vis[-3:][k + 1:]]; shift = sum(eq((t - tt) / 0.22) for tt in newer)
        im = bubble_img(b["text"], b.get("who", "ai")); u = eq((t - t0) / 0.16); sc = 0.78 + 0.22 * spring((t - t0) / 0.34)
        im2 = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
        a = u * (1 - 0.35 * max(0, rank - 1)) * fade
        if a <= 0.01: continue
        im2.putalpha(im2.getchannel("A").point(lambda v, a=a: int(v * a)))
        y = int(base - im2.height - shift * step + (1 - u) * S(18))
        x = S(50) if b.get("who", "ai") != "me" else W - S(50) - im2.width
        lay.alpha_composite(im2, (x, max(0, y))); RECTS.append(("對話泡泡", x + S(20), max(0, y) + S(14), x + im2.width - S(20), max(0, y) + im2.height - S(26)))
    return over(comp, to_np(lay))
def checklist_comp(comp, t, ck, s, seg_end):
    t0 = to_out(s, ck["start"]); t1 = to_out(s, ck["end"]) if "end" in ck else seg_end
    if not (t0 <= t < t1): return comp
    a = eq((t - t0) / 0.3) * ((1 - eq((t - (t1 - 0.18)) / 0.18) if t > t1 - 0.18 else 1) if "end" in ck else 1)
    items = ck["items"]; title = ck.get("title", ""); rh = S(86); top_pad = S(84) if title else S(30)
    hh = top_pad + rh * len(items) + S(24); side = ck.get("side", "left"); cw = S(ck.get("width", 360))
    x0 = S(44) if side == "left" else (W - S(44) - cw if side == "right" else (W - cw) // 2); x1 = x0 + cw
    y1 = S(ck.get("bottom", 1240)); y0 = y1 - hh + int((1 - a) * S(30))
    comp = glass(comp, (x0, y0, x1, y0 + hh), S(30), a); RECTS.append(("清單", x0, y0, x1, y0 + hh))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); A = lambda v: int(255 * max(0, min(1, v)) * a)
    d.rounded_rectangle([x0, y0, x1, y0 + hh], S(30), outline=(255, 255, 255, A(0.14)), width=max(1, S(2)))
    if title: d.text((x0 + S(34), y0 + S(26)), title, font=F("sans", S(30)), fill=(190, 184, 174, A(1)))
    for k, row in enumerate(items):
        ta = to_out(s, row["at"]); done = t >= ta; q = eq((t - ta) / 0.22) if done else 0
        cy = y0 + top_pad + rh * k + rh // 2; cx = x0 + S(58); r = S(22) * (1 + 0.25 * math.sin(min(1, (t - ta) / 0.22) * math.pi) if done else 1)
        if done:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=EM + (A(1),))
            d.line([(cx - S(10), cy), (cx - S(3), cy + S(8)), (cx + S(11), cy - S(8))], fill=(22, 22, 24, A(1)), width=max(1, S(5)))
        else: d.ellipse([cx - S(22), cy - S(22), cx + S(22), cy + S(22)], outline=(160, 155, 146, A(1)), width=max(1, S(3)))
        d.text((cx + S(48), cy), row["text"], font=F("sans", S(42)), fill=(IV if done else (150, 146, 138)) + (A(1),), anchor="lm")
    return over(comp, to_np(im))
def phone_frames(ph, n_frames, sw, sh):
    def mk():
        src = src_path(ph["src"])
        if os.path.splitext(src)[1].lower() in (".png", ".jpg", ".jpeg", ".webp"):
            im = Image.open(src).convert("RGB"); im = im.resize((sw, max(sh, int(im.height * sw / im.width))), Image.LANCZOS); return ("img", np.asarray(im))
        vf = f"scale={sw}:{sh}:force_original_aspect_ratio=decrease,pad={sw}:{sh}:(ow-iw)/2:(oh-ih)/2:color=0x101012,fps={FPS}"
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{float(ph.get('src_in', 0)):.3f}", "-i", src, "-frames:v", str(n_frames), "-vf", vf,
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        fr = np.frombuffer(b, np.uint8); k = len(fr) // (sw * sh * 3)
        return ("vid", fr[:k * sw * sh * 3].reshape(k, sh, sw, 3) if k else np.zeros((1, sh, sw, 3), np.uint8))
    return cached(("phone", id(ph)), mk)
def phone_shell(pw, ph_, sw, sh, inset):
    def mk():
        im = Image.new("RGBA", (pw + S(80), ph_ + S(80)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); o = S(40)
        d.rounded_rectangle([o, o, o + pw, o + ph_], S(70), fill=(16, 16, 18, 255), outline=(90, 90, 96, 255), width=max(1, S(3)))
        im = shadow(im, (0, S(24)), S(34), 0.55)
        hole = Image.new("L", (sw, sh), 0); ImageDraw.Draw(hole).rounded_rectangle([0, 0, sw - 1, sh - 1], S(54), fill=255)
        return im, np.asarray(hole, np.float32)[..., None] / 255
    return cached(("shell", pw, ph_), mk)
def phone_comp(comp, t, ph, s, seg_end):
    t0 = to_out(s, ph["start"]); t1 = to_out(s, ph["end"]) if "end" in ph else seg_end
    if not (t0 <= t < t1): return comp
    pw = int(W * float(ph.get("width", 0.46))); ph_ = int(pw * 2.08); inset = S(18); sw, sh = pw - 2 * inset, ph_ - 2 * inset
    kind, frames = phone_frames(ph, int((t1 - t0) * FPS) + 2, sw, sh)
    u_in = eq((t - t0) / 0.38); u_out = (eq((t - (t1 - 0.3)) / 0.3) if t > t1 - 0.3 else 0) if "end" in ph and t1 < seg_end - 0.05 else 0
    x = int(W * float(ph.get("x", 0.5)) - pw / 2); y_rest = max(S(ph.get("top", 1060)), H - S(140) - ph_); y = int(y_rest + (1 - u_in) * (H - y_rest) + u_out * (H - y_rest))
    if kind == "img":
        sc = float(ph.get("scroll", 1.0)); maxoff = max(0, frames.shape[0] - sh); off = int(maxoff * sc * smooth((t - t0) / max(0.1, t1 - t0)))
        scr = frames[off:off + sh]
    else: scr = frames[min(len(frames) - 1, int((t - t0) * FPS))]
    shell, hole = phone_shell(pw, ph_, sw, sh, inset)
    lay = to_np(shell); o = S(40); gx, gy = x - o, y - o
    sx, sy = o + inset, o + inset; lay[sy:sy + sh, sx:sx + sw, :3] = lay[sy:sy + sh, sx:sx + sw, :3] * (1 - hole) + scr.astype(np.float32) / 255 * hole
    pill_w, pill_h = int(sw * 0.3), S(30); px0 = sx + (sw - pill_w) // 2
    lay[sy + S(18):sy + S(18) + pill_h, px0:px0 + pill_w, :3] = 0.04
    ya, yb = max(0, gy), min(H, gy + lay.shape[0]); xa, xb = max(0, gx), min(W, gx + lay.shape[1])
    if yb <= ya or xb <= xa: return comp
    sub = lay[ya - gy:yb - gy, xa - gx:xb - gx]; reg = comp[ya:yb, xa:xb]; RECTS.append(("手機", x, y, x + pw, y + ph_))
    comp = comp.copy(); comp[ya:yb, xa:xb] = reg * (1 - sub[..., 3:4]) + sub[..., :3] * sub[..., 3:4]; return comp
def freeze_comp(comp, u, it):
    g = comp.mean(axis=2, keepdims=True); comp = comp * 0.72 + g * 0.28                         # drained colour = "time stopped"
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if it.get("circle"):
        cx, cy, r = [S(v) for v in it["circle"]]; p = smooth((u - 0.15) / 0.35)
        if p > 0:
            for k in range(3): d.arc([cx - r - k * S(3), cy - r * 0.92 - k * S(3), cx + r + k * S(3), cy + r * 0.92 + k * S(3)], -100, -100 + 360 * p, fill=RED + (255,), width=S(9) - k * S(2))
    text = it.get("text", "等一下"); q = eq(u / 0.18); sc = 1.5 - 0.5 * q
    f = F("serif", int(S(118) * sc)); tw = d.textlength(text, font=f); ty = S(it.get("text_y", 230))
    bx0, by0 = (W - tw) / 2 - S(40) * sc, ty - S(22) * sc; bx1, by1 = (W + tw) / 2 + S(40) * sc, ty + S(150) * sc
    st = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(st)
    ds.rounded_rectangle([bx0, by0, bx1, by1], S(16), fill=(246, 241, 230, int(238 * q)), outline=RED + (int(255 * q),), width=S(8))
    ds.text(((W - tw) / 2, ty - S(6) * sc), text, font=f, fill=RED + (int(255 * q),))
    st = st.rotate(-4, center=(W / 2, ty + S(40)), resample=Image.BICUBIC)
    im.alpha_composite(st); return over(comp, to_np(shadow(im, (0, S(8)), S(12), 0.35)))
def badge(text, y=240):
    def mk():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = F("mono", S(30)); tw = d.textlength(text, font=f)
        x1, y0 = W - S(60), S(y); d.rounded_rectangle([x1 - tw - S(44), y0, x1, y0 + S(60)], S(30), fill=INK + (220,))
        d.text((x1 - tw - S(22), y0 + S(13)), text, font=f, fill=IV); return to_np(im)
    return cached(("badge", text, y), mk)


# ---- batch-2 effects (from the "17 effects" reference, in 墨牛 style) ----
_mprev = {"seg": None, "m": None}
def smooth_mask(rgb, seg_id):
    """person matte with light temporal smoothing inside one segment, so cut-out edges don't flicker"""
    m = person_mask(rgb)
    if m is None: return None
    if _mprev["seg"] == seg_id and _mprev["m"] is not None: m = 0.6 * m + 0.4 * _mprev["m"]
    _mprev.update(seg=seg_id, m=m); return m
def span(fx, s, seg_end):
    return to_out(s, fx["start"]), (to_out(s, fx["end"]) if "end" in fx else seg_end)
def hex_rgb01(h, default=(0.953, 0.933, 0.894)):
    try: return np.array(hex2rgb(h), np.float32) / 255
    except Exception: return np.array(default, np.float32)
def media_frames(path, n, w, h):
    """still image or video → list of float frames covering w×h (videos loop)"""
    def mk():
        src = src_path(path)
        if os.path.splitext(src)[1].lower() in (".png", ".jpg", ".jpeg", ".webp"):
            im = Image.open(src).convert("RGB"); sc = max(w / im.width, h / im.height); im = im.resize((int(im.width * sc) + 1, int(im.height * sc) + 1), Image.LANCZOS)
            x0, y0 = (im.width - w) // 2, (im.height - h) // 2; return [np.asarray(im.crop((x0, y0, x0 + w, y0 + h)), np.float32) / 255]
        b = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-frames:v", str(n), "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        k = len(b) // (w * h * 3); a = np.frombuffer(b[:k * w * h * 3], np.uint8).reshape(k, h, w, 3)
        return [x.astype(np.float32) / 255 for x in a] or [np.zeros((h, w, 3), np.float32)]
    return cached(("media", path, n), mk)
def bg_comp(fr, m, t, fx, s, seg_end):
    t0, t1 = span(fx, s, seg_end); frames = media_frames(fx["src"], int((t1 - t0) * FPS) + 2, W, H)
    bg = frames[int((t - t0) * FPS) % len(frames)]
    if fx.get("blur"): bg = cv2.GaussianBlur(bg, (0, 0), S(fx["blur"]))
    if fx.get("dim"): bg = bg * (1 - float(fx["dim"]))
    a = eq((t - t0) / 0.2) * (1 - eq((t - (t1 - 0.2)) / 0.2) if t > t1 - 0.2 else 1)
    return fr * (1 - (1 - m) * a) + bg * (1 - m) * a
def sticker_comp(fr, m, t, fx, s, seg_end):
    t0, t1 = span(fx, s, seg_end); u = eq((t - t0) / 0.28)
    paper = hex_rgb01(fx.get("paper", "#F3EEE4")); ol = S(fx.get("outline", 16))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ol + 1, 2 * ol + 1))
    mb = (m[..., 0] > 0.5).astype(np.uint8); outl = cv2.dilate(mb, k).astype(np.float32)
    outl = cv2.GaussianBlur(outl, (0, 0), 1.2)[..., None]
    sc = float(fx.get("scale", 0.86)) * (0.7 + 0.3 * u); ang = float(fx.get("tilt", -3)) * u
    M = cv2.getRotationMatrix2D((W / 2, H * 0.55), ang, sc)
    warp = lambda img, bv=0: cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=bv)
    pf = warp(fr); pm = warp(m[..., 0])[..., None]; po = warp(outl[..., 0])[..., None]
    shp = cv2.GaussianBlur(np.roll(np.roll(po[..., 0], S(14), 0), S(6), 1), (0, 0), S(14))[..., None] * 0.35
    out = np.ones_like(fr) * paper
    grain = (np.random.default_rng(int(t * FPS) // 4).standard_normal((H // 4, W // 4)).astype(np.float32) * 0.012)
    out = out + cv2.resize(grain, (W, H))[..., None]
    out = out * (1 - shp); out = out * (1 - po) + po; out = out * (1 - pm) + pf * pm
    a = min(1, (t - t0) / 0.12) * (1 - eq((t - (t1 - 0.15)) / 0.15) if t > t1 - 0.15 else 1)
    return fr * (1 - a) + out * a
def framebreak_comp(fr, m, t, fx, s, seg_end):
    t0, t1 = span(fx, s, seg_end); u = eq((t - t0) / 0.3)
    if "box" in fx: x0, y0, x1, y1 = [S(v) for v in fx["box"]]
    else:
        key = ("fbbox", id(fx))
        if key not in cache: ht = head_top(m); y0_ = min(H - S(900), ht + S(200)); cache[key] = (S(110), y0_, W - S(110), min(H - S(300), y0_ + S(820)))
        x0, y0, x1, y1 = cache[key]
    paper = hex_rgb01(fx.get("paper", "#1A1A1C")); bw_ = S(fx.get("border", 22))
    out = np.ones_like(fr) * paper
    out[y0:y1, x0:x1] = fr[y0:y1, x0:x1]
    sh = np.zeros((H, W), np.float32); sh[y0 + S(18):y1 + S(18), x0 + S(8):x1 + S(8)] = 1
    sh = cv2.GaussianBlur(sh, (0, 0), S(18))[..., None] * 0.45
    ring = np.zeros((H, W), np.float32); ring[y0 - bw_:y1 + bw_, x0 - bw_:x1 + bw_] = 1; ring[y0:y1, x0:x1] = 0; ring = ring[..., None]
    out = out * (1 - sh * (1 - ring)) ; out = out * (1 - ring) + np.array([0.97, 0.955, 0.93], np.float32) * ring
    out[y0:y1, x0:x1] = fr[y0:y1, x0:x1]
    yy = np.arange(H)[:, None, None]; brk = m * (yy < y1 - S(40))           # only the head/shoulders break out (never below the frame)
    out = out * (1 - brk) + fr * brk
    a = u * (1 - eq((t - (t1 - 0.2)) / 0.2) if t > t1 - 0.2 else 1)
    return fr * (1 - a) + out * a
HEAD_SLOTS = [(0.05, 0.12, -4), (0.53, 0.09, 3), (0.03, 0.29, 2), (0.57, 0.27, -3), (0.28, 0.04, -1), (0.06, 0.45, -2)]
def clip_card(text, source):
    def mk():
        cw = S(440); f = F("serif", S(40)); fs = F("mono", S(18))
        lines, cur = [], ""
        for ch in text:
            if ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(cur + ch, font=f) > cw - S(56): lines.append(cur); cur = ch
            else: cur += ch
        lines.append(cur); lines = lines[:3]; ch_ = S(64) + S(52) * len(lines) + S(20)
        im = Image.new("RGBA", (cw + S(40), ch_ + S(40)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); o = S(20)
        d.rectangle([o, o, o + cw, o + ch_], fill=(246, 241, 230, 255))
        d.rectangle([o, o, o + cw, o + S(8)], fill=EM + (255,))
        d.text((o + S(28), o + S(26)), (source or "NEWS").upper(), font=fs, fill=(140, 130, 112))
        for i, ln in enumerate(lines): d.text((o + S(28), o + S(58) + i * S(52)), ln, font=f, fill=INK)
        return shadow(im, (0, S(10)), S(14), 0.45)
    return cached(("card", text, source), mk)
def headlines_comp(comp, fr, m, t, fx, s, seg_end):
    t0, t1 = span(fx, s, seg_end); fade = (1 - eq((t - (t1 - 0.18)) / 0.18) if t > t1 - 0.18 else 1) if "end" in fx else 1
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); any_ = False
    for k, c in enumerate(fx.get("cards", [])):
        ta = to_out(s, c.get("at", fx["start"]))
        if t < ta: continue
        u = eq((t - ta) / 0.16); sc = 1.30 - 0.30 * spring((t - ta) / 0.3); any_ = True
        x, y, rot = c.get("slot") or HEAD_SLOTS[k % len(HEAD_SLOTS)]
        im = clip_card(c["text"], c.get("src", "")).rotate(rot, expand=True, resample=Image.BICUBIC)
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
        im.putalpha(im.getchannel("A").point(lambda v, a=min(1, u * 1.6) * fade: int(v * a)))
        lay.alpha_composite(im, (int(W * x - (im.width - im.width / sc) / 2), max(0, int(H * y - (im.height - im.height / sc) / 2))))
    if not any_: return comp
    out = over(comp, to_np(lay))
    if m is not None and fx.get("behind", True): out = out * (1 - m) + fr * m          # the wall sits behind the person
    return out
def chart_comp(comp, t, fx, s, seg_end):
    t0, t1 = span(fx, s, seg_end)
    a = eq((t - t0) / 0.3) * ((1 - eq((t - (t1 - 0.18)) / 0.18) if t > t1 - 0.18 else 1) if "end" in fx else 1)
    bars = fx["bars"]; cw = S(fx.get("width", 820)); chh = S(fx.get("height", 330)); x0 = (W - cw) // 2; y1 = S(fx.get("bottom", 1510)); y0 = y1 - chh + int((1 - a) * S(30))
    comp = glass(comp, (x0, y0, x0 + cw, y0 + chh), S(30), a); RECTS.append(("圖表", x0, y0, x0 + cw, y0 + chh))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); A = lambda v: int(255 * max(0, min(1, v)) * a)
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + chh], S(30), outline=(255, 255, 255, A(0.14)), width=max(1, S(2)))
    if fx.get("title"): d.text((x0 + S(34), y0 + S(22)), fx["title"], font=F("sans", S(34)), fill=(225, 219, 208, A(1)))
    vmax = max(float(b["value"]) for b in bars) or 1; n = len(bars); gx0, gx1 = x0 + S(40), x0 + cw - S(40); base = y0 + chh - S(60); top = y0 + S(118)
    bw_ = (gx1 - gx0) / n * 0.56; hi = max(range(n), key=lambda i: float(bars[i]["value"]))
    for i, b in enumerate(bars):
        g = smooth((t - t0 - 0.15 - i * 0.12) / 0.6); v = float(b["value"]) * g; hpx = (base - top) * v / vmax
        cx = gx0 + (gx1 - gx0) * (i + 0.5) / n; col = EM if i == hi else (243, 238, 228)
        d.rounded_rectangle([cx - bw_ / 2, base - hpx, cx + bw_ / 2, base], S(8), fill=col + (A(0.92 if i == hi else 0.55),))
        lab = f"{v:,.0f}{fx.get('unit', '')}"; d.text((cx, base - hpx - S(10)), lab, font=F("mono", S(26)), fill=(IV if i == hi else (200, 195, 186)) + (A(g),), anchor="mb")
        d.text((cx, base + S(14)), b["label"], font=F("sans", S(28)), fill=(220, 214, 204, A(1)), anchor="mt")
    return over(comp, to_np(im))
def doodle_comp(comp, m, t, fx, s, seg_end):
    t0, t1 = span(fx, s, seg_end)
    if m is None: return comp
    a = min(1, (t - t0) / 0.15) * (1 - eq((t - (t1 - 0.2)) / 0.2) if t > t1 - 0.2 else 1)
    q = 4; mm = (cv2.resize(m[..., 0], (W // q, H // q)) > 0.5).astype(np.uint8)
    mm = cv2.dilate(mm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * S(fx.get("gap", 22)) // q + 1,) * 2))
    cs, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs: return comp
    c = max(cs, key=cv2.contourArea)[:, 0, :].astype(np.float32) * q
    c = c[c[:, 1] < H - S(16)]
    if len(c) < 8: return comp
    rng_ = np.random.default_rng(int(t * FPS) // 3)                       # "boil": the line re-draws every 3 frames
    step = max(1, len(c) // 160); c = c[::step] + rng_.normal(0, S(3.2), (len(c[::step]), 2))
    col = hex2rgb(fx.get("color", "#FFFFFF")); im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [tuple(p) for p in c]
    for k in range(len(pts) - 1):
        if abs(pts[k][0] - pts[k + 1][0]) + abs(pts[k][1] - pts[k + 1][1]) < S(140): d.line([pts[k], pts[k + 1]], fill=col + (int(255 * a),), width=S(7))
    if fx.get("doodles", True):
        ht = head_top(m); xs = c[:, 0]; L, R = float(xs.min()), float(xs.max())
        j = lambda: rng_.normal(0, S(3))
        hx, hy, r = L + S(30), max(S(220), ht - S(40)), S(46)               # heart, top-left of the head
        hp = [(hx + 16 * math.sin(th) ** 3 * r / 16 + j(), hy - (13 * math.cos(th) - 5 * math.cos(2 * th) - 2 * math.cos(3 * th) - math.cos(4 * th)) * r / 16 + j()) for th in np.linspace(0, 2 * math.pi, 28)]
        d.line(hp + [hp[0]], fill=col + (int(255 * a),), width=S(6))
        sx, sy, R_ = R - S(40), max(S(230), ht - S(10)), S(52)               # star, top-right (ember)
        sp = [(sx + (R_ if k % 2 == 0 else R_ * 0.42) * math.cos(-math.pi / 2 + k * math.pi / 5) + j(), sy + (R_ if k % 2 == 0 else R_ * 0.42) * math.sin(-math.pi / 2 + k * math.pi / 5) + j()) for k in range(10)]
        d.polygon(sp, fill=EM + (int(255 * a),))
    return over(comp, to_np(im))
def glass_word(comp, fr, word, n, size, top):
    def mk():
        im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
        fnt = lambda ch: F("lat_serif" if ch.isascii() and ch.strip() else "black", size * (0.92 if ch.isascii() else 1))
        ws = [d.textlength(ch, font=fnt(ch)) for ch in word]; x = (W - sum(ws)) / 2
        for j, ch in enumerate(word[:n]): d.text((x, top), ch, font=fnt(ch), fill=255); x += ws[j]
        Lm = np.asarray(im, np.float32) / 255; er = cv2.erode(Lm, np.ones((S(7), S(7)), np.uint8)); rim = np.clip(Lm - er, 0, 1)
        sh = cv2.GaussianBlur(np.roll(Lm, S(14), 0), (0, 0), S(16)) * 0.55
        return Lm[..., None], rim[..., None], sh[..., None]
    Lm, rim, sh = cached(("glass", word, n, size, top), mk)
    out = comp * (1 - sh * (1 - Lm))                                            # soft shadow lifts the glass off the background
    g = cv2.GaussianBlur(comp, (0, 0), S(22)) * 0.55 + 0.42                  # frosted: heavily blurred background, lifted toward white
    out = out * (1 - Lm) + g * Lm; return out * (1 - rim * 0.95) + rim * 0.95

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
    for bu in it.get("bubbles", []): events.append((to_out(s, bu["start"]), "pop", 0.75))
    if it.get("checklist"):
        events.append((to_out(s, it["checklist"]["start"]), "swish", 0.5))
        for row in it["checklist"].get("items", []): events.append((to_out(s, row["at"]), "tick", 0.9))
    if it.get("phone"):
        events.append((to_out(s, it["phone"]["start"]), "swish", 0.75))
    for c in (it.get("headlines") or {}).get("cards", []): events.append((to_out(s, c.get("at", it["headlines"]["start"])), "boom", 0.3))
    if it.get("chart"):
        events.append((to_out(s, it["chart"]["start"]), "swish", 0.5))
        for i in range(len(it["chart"]["bars"])): events.append((to_out(s, it["chart"]["start"]) + 0.15 + i * 0.12, "tick", 0.6))
    for key_ in ("sticker", "framebreak"):
        if it.get(key_): events.append((to_out(s, it[key_]["start"]), "pop", 0.85))
    if it.get("bg"): events.append((to_out(s, it["bg"]["start"]), "swish", 0.6))
    if it.get("ui"): events += UICARDS.UI.sfx(it["ui"], lambda x, s=s: to_out(s, x))
    if it.get("zoom_in") and s["start"] > 0: events.append((s["start"], "whoosh", 0.75))
    if it.get("_fast") is None and s["start"] > 0 and segs[segs.index(s) - 1]["item"].get("_fast"): events.append((s["start"], "swish", 0.6))
    C = it.get("cta")
    if C:
        events.append((to_out(s, C["show"]) - 0.04, "swish", 0.8))
        ts_ = to_out(s, C["show"]); ty = to_out(s, C["type_at"]) if "type_at" in C else ts_ + 0.9
        th_ = to_out(s, C["heart_at"]) if "heart_at" in C else ty + 0.45; tr = to_out(s, C["reply_at"]) if "reply_at" in C else th_ + 0.5
        for k in range(len(C.get("keyword", "EDIT"))): events.append((ty + k * 0.077, "click", 1.0))
        events += [(th_, "pop", 0.9), (tr, "pop", 0.8)]

UIC = UICARDS.UI(W, H, S, P, src_path, cache)
if HDR and HDR.get("kind") != "stamp": UIC.top_default = int(HDR.get("y", 205)) + 110      # cards sit under a header line, never on it
# ================= 3. overlay pass =================
VID = os.path.join(WORK, "video.mp4")
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", MASTER, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", VID], stdin=subprocess.PIPE)
whips = [s["start"] for s in segs if s["item"].get("whip_in") and s["start"] > 0]
zthru = [s["start"] for s in segs if s["item"].get("zoom_in") and s["start"] > 0]
impacts = sorted(set(round(t0, 3) for t0, name, g in events if name in ("boom", "scratch") or (name == "pop" and g >= 0.85)))
bigpos = {}; RECTS = []; COLL = []
def face_box(m):
    if m is None: return None
    ht = head_top(m); band = m[ht:ht + S(430), :, 0] > 0.5
    cols = np.where(band.mean(axis=0) > 0.25)[0]
    return (int(cols.min()), ht, int(cols.max()), ht + S(430)) if len(cols) else None
for n in range(TOTAL_N):
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    t = n / FPS; rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy(); s = seg_at(t); it = s["item"]; RECTS.clear()
    if s["kind"] == "clip":
        push = float(it.get("push", 0)); d0 = s["N"] / FPS
        if push: rgb = zoom(rgb, 1 + push * (0.5 - 0.5 * math.cos(math.pi * (t - s["start"]) / d0)), 0.4)
        for pz in it.get("punch", []):                                 # hard punch-in on a word (60 ms snap), held until `until` or the end of the clip
            p0 = to_out(s, pz["at"]); p1 = to_out(s, pz["until"]) if "until" in pz else s["start"] + d0 + 1
            if p0 <= t < p1:
                zz = 1 + (float(pz.get("scale", 1.18)) - 1) * eq((t - p0) / 0.07); yy_ = float(pz.get("y", 0.38))
                rgb = zoom(rgb, zz, yy_) if t - p0 > 0.07 else (sum(zoom(rgb, zz * f_, yy_).astype(np.float32) for f_ in (0.975, 1.0, 1.025)) / 3).astype(np.uint8)
        pb = it.get("pullback")
        if pb:                                                           # start tight on the face, then release to the wide shot
            q0 = to_out(s, pb.get("at", it["in"])); z0 = float(pb.get("from", 1.6)); u = smooth((t - q0) / float(pb.get("dur", 0.8)))
            rgb = zoom(rgb, 1 + (z0 - 1) * (1 - u), float(pb.get("y", 0.32)))
        if (push or it.get("punch") or pb) and it.get("bars", spec.get("bars", False)):   # zooming must not eat the letterbox bars
            bb = S(spec.get("bars_px", 200)); rgb[:bb] = 0; rgb[H - bb:] = 0
        fr = rgb.astype(np.float32) / 255
        if GRAIN: fr = np.clip(fr + _grain[n % 6] * GRAIN, 0, 1)
        comp = fr.copy(); low = False
        C = it.get("cta"); cta_on = C is not None and t >= to_out(s, C["show"])
        seg_end = s["start"] + d0; MK = {}
        def getm():
            if "m" not in MK: MK["m"] = smooth_mask(rgb, id(s))
            return MK["m"]
        on = lambda key_: it.get(key_) and span(it[key_], s, seg_end)[0] <= t < span(it[key_], s, seg_end)[1]
        if on("bg") and getm() is not None: comp = bg_comp(comp, getm(), t, it["bg"], s, seg_end)
        if on("sticker") and getm() is not None: comp = sticker_comp(comp, getm(), t, it["sticker"], s, seg_end)
        if on("framebreak") and getm() is not None: comp = framebreak_comp(comp, getm(), t, it["framebreak"], s, seg_end)
        base_person = comp.copy()
        if on("headlines"): comp = headlines_comp(comp, base_person, getm(), t, it["headlines"], s, seg_end)
        for bw in it.get("bigwords", []):
            t0, t1 = to_out(s, bw["start"]), to_out(s, bw["end"])
            if not (t0 <= t < t1): continue
            word = bw["word"]; nch = len(word); p = (t - t0) / 0.32; k = min(nch, int(p * nch) + 1); frac = min(1, p * nch - (k - 1))
            place = bw.get("place", "auto"); m = person_mask(rgb) if place != "low" else None
            key = (id(bw),)
            if key not in bigpos:
                ht = head_top(m) if m is not None else None
                ov = float(bw.get("overlap", 0.10))                   # share of the letters the head covers (0.10 subtle … 0.5 deep behind the head)
                size = int(max(S(170), min(S(bw.get("size", 300)), (ht + S(20) - S(120)) / max(0.6, 1.18 - ov), W * 0.9 / max(1, nch)))) if ht else 0
                if m is None or size <= S(170) or place == "low": bigpos[key] = ("low", int(min(S(bw.get("size", 300)), W * 0.9 / max(1, nch))), S(bw.get("low_y", 1150)))
                else: bigpos[key] = ("top", size, max(S(120) if not HDR or HDR.get("kind") == "stamp" else S(HDR.get("y", 205) + 70), int(ht + ov * size - size * 1.18)))
            mode, size, top = bigpos[key]
            if bw.get("style") == "glass": comp = glass_word(comp, fr, word, k, size, top)
            else:
                if ("col",) + key not in bigpos:                          # ivory on dark backgrounds, ink when the spot behind it is bright (a white shirt)
                    gm = bigword(word, nch, size, top)[..., 3:4]                # brightness measured under the letters themselves
                    lum = float((fr.mean(axis=2, keepdims=True) * gm).sum() / max(1.0, float(gm.sum())))
                    bigpos[("col",) + key] = INK if lum > 0.58 else IV
                bc = bigpos[("col",) + key]
                if k > 1: comp = over(comp, bigword(word, k - 1, size, top, bc))
                comp = over(comp, bigword(word, k, size, top, bc), frac)
            if mode == "top": comp = comp * (1 - m) + base_person * m
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
        if on("doodle"): comp = doodle_comp(comp, getm(), t, it["doodle"], s, seg_end)
        chart_on = bool(on("chart"))
        if chart_on: comp = chart_comp(comp, t, it["chart"], s, seg_end)
        if it.get("checklist"): comp = checklist_comp(comp, t, it["checklist"], s, seg_end)
        if it.get("bubbles"): comp = bubbles_comp(comp, t, it["bubbles"], s, seg_end)
        ph_on = False
        if it.get("phone"):
            comp = phone_comp(comp, t, it["phone"], s, seg_end)
            ph_on = to_out(s, it["phone"]["start"]) <= t < (to_out(s, it["phone"]["end"]) if "end" in it["phone"] else seg_end)
        if it.get("ui"): comp = UIC.draw(comp, t, it["ui"], s, lambda x, s=s: to_out(s, x), seg_end, RECTS, it["src"], float(it["in"]) + 0.4)   # app-style cards
        if it.get("_fast"): comp = over(comp, badge(f"▶▶ {it['_fast']:g}×", int(it.get("badge_y", 240))))
        if C is not None: comp = cta_comp(comp, t, C, s)
        bub_on = bool(it.get("bubbles")) and to_out(s, min(b_["start"] for b_ in it["bubbles"])) <= t and not it.get("captions_over")
        if not low and not cta_on and not bub_on and not (chart_on and not it["chart"].get("captions_over")) and not (ph_on and not it["phone"].get("captions_over")) and it.get("captions_on", True):
            for c in it.get("captions", []):
                t0, t1 = to_out(s, c["start"]), to_out(s, c["end"])
                if t0 <= t < t1:
                    text = c["text"]; nch = len(text); lit = nch if c.get("instant") else min(nch, 1 + int((t - t0) / max(1e-3, (t1 - t0) * 0.85) * nch))
                    look = c.get("look", CAP.get("look", "card"))
                    if look in CAPV2.LOOKS:
                        comp = CAPE.draw(comp, t, c, CHARS.get(os.path.basename(it["src"]), []), lambda x, s=s: to_out(s, x), RECTS, id(s)); break
                    pa = {"meme": 0.22, "bold": 0.10}.get(look, 0.08)
                    pop = round(1.0 + (pa * (1 - ease((t - t0) / 0.12)) if t - t0 < 0.12 else 0), 2)
                    kc = P.get(c.get("color", "accent"), EM) if isinstance(c.get("color", "accent"), str) else EM
                    comp = over(comp, caption(text, c.get("keys", []), lit, kc, pop, int(c.get("size", CAP["size"]) * float(CAP.get("scale", 1.0))), c.get("y", CAP["y"]) + float(CAP.get("dy", 0)), look)); break
    elif s["kind"] == "freeze":
        u = t - s["start"]; z = 1 + 0.035 * eq(u / 0.5)
        comp = freeze_comp(zoom(rgb, z, 0.4).astype(np.float32) / 255, u, it)
    else:
        comp = rgb.astype(np.float32) / 255
    if HDR and s["kind"] in ("clip", "freeze") and not (s["kind"] == "clip" and it.get("cta") and t >= to_out(s, it["cta"]["show"])):
        comp = over(comp, header_img(HDR), eq(t / 0.35))
    for b in impacts:
        dt = t - b
        if 0 <= dt < 0.17:
            amp = S(spec.get("shake_px", 9)) * (1 - dt / 0.17) ** 2; ox, oy = amp * math.sin(dt * 95), amp * 0.6 * math.cos(dt * 120)
            Mt = np.float32([[1.012, 0, ox - W * 0.006], [0, 1.012, oy - H * 0.006]])        # tiny overscan so edges never show
            comp = cv2.warpAffine(comp.astype(np.float32), Mt, (W, H), borderMode=cv2.BORDER_REPLICATE); break
    for b in zthru:
        dt = t - b
        if -0.22 < dt < 0.22:
            z = 1 + 1.6 * ((dt + 0.22) / 0.22) ** 2 if dt < 0 else 1 + 0.9 * (1 - eq(dt / 0.22))
            img = (np.clip(comp, 0, 1) * 255).astype(np.uint8)
            comp = sum(zoom(img, z * f_, 0.42).astype(np.float32) for f_ in (1.0, 1.035, 1.07)) / (3 * 255)
    for b in whips:
        dt = t - b
        if abs(dt) < 0.12:
            w = 1 - abs(dt) / 0.12; img = zoom((np.clip(comp, 0, 1) * 255).astype(np.uint8), 1 + 0.10 * w)
            L = max(3, int(S(90) * w)); ker = np.zeros((L, L), np.float32); ker[:, L // 2] = 1.0 / L
            comp = cv2.filter2D(img, -1, ker).astype(np.float32) / 255
    if RECTS and n % 10 == 0 and s["kind"] == "clip":
        fb = face_box(MK.get("m") if "m" in MK else person_mask(rgb))
        if fb:
            fx0, fy0, fx1, fy1 = fb; fa = max(1, (fx1 - fx0) * (fy1 - fy0))
            for nm, x0, y0, x1, y1 in RECTS:
                ov = max(0, min(x1, fx1) - max(x0, fx0)) * max(0, min(y1, fy1) - max(y0, fy0)) / fa
                if ov > 0.06: COLL.append(dict(t=round(t, 2), what=nm, face_cover=round(ov, 2)))
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
    if name == "scratch":                                             # record scratch: noise burst + falling pitch
        k = int(0.22 * SR); tt = np.arange(k) / SR; f0 = 1400 * np.exp(-tt * 9) + 180
        x = (0.35 * np.sign(np.sin(2 * np.pi * np.cumsum(f0) / SR)) + 0.5 * rng.standard_normal(k)) * np.exp(-tt * 14)
        x = np.convolve(x, np.ones(5) / 5, "same") * 0.45; return np.stack([x, x * 0.9], 1).astype(np.float32)
    if name.startswith("shimmer"):
        d = float(name.split(":")[1]); k = int(d * SR); tt = np.arange(k) / SR
        x = np.convolve(rng.standard_normal(k), np.ones(3) / 3, "same") * 0.022 + 0.018 * np.sin(2 * np.pi * (900 + 500 * tt / d) * tt) * np.sin(2 * np.pi * 2.5 * tt) ** 2
        x *= np.minimum(1, tt / 0.4) * np.minimum(1, (d - tt) / 0.25); return np.stack([x, x], 1).astype(np.float32)
    return sfx(name)
PEAKS = {}
for t0, name, g in events:
    x = gen(name)
    if name not in PEAKS:                                             # where this sound is loudest → line that up with the impact
        e = np.convolve(np.abs(x).mean(axis=1), np.ones(240) / 240, "same"); PEAKS[name] = int(e.argmax()) if name in ("whoosh", "swish", "whoosh_rev", "scratch") else 0
    i0 = max(0, int(t0 * SR) - PEAKS[name]); j = min(len(fx), i0 + len(x)); fx[i0:j] += x[:j - i0] * g * float(spec.get("sfx_gain", 1.0))
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
qa["face_collisions"] = COLL[:40]; qa["voice"] = VOICE_QA or "off"
try:
    import pacing as PACE; qa["dead_spots"] = PACE.analyze(resolve_words(json.load(open(args.spec)), SPEC_DIR))["dead_spots"]
except Exception as e: qa["dead_spots_error"] = str(e)
json.dump(qa, open(os.path.join(WORK, "qa.json"), "w"), indent=1, ensure_ascii=False); print(json.dumps(qa, ensure_ascii=False))
