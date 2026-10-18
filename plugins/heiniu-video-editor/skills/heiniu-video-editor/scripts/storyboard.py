"""Build the review room (剪輯室) from edit.json: a draft player with every beat playable on its own, an OK / 要改 verdict and a
one-sentence note per beat, a 'send to Claude' button (falls back to copy), a change log for each new version, and a
delivery panel once the final is out.

usage:
  python3 storyboard.py edit.json --version 1 --video _render/draft_v1.mp4
  python3 storyboard.py edit.json --version 2 --video _render/draft_v2.mp4 --prev _versions/edit.v1.json --change "2=字幕放大，幾千塊換紅色"
  python3 storyboard.py edit.json --version 3 --video _render/draft_v3.mp4 --delivered heiniu.mp4
Options:
  --video       the draft render (render.py --preview); re-encoded small and embedded so each beat can be played
  --prev        the previous edit.json: beats that differ get a 「已修改」 tag
  --change N=…  what was changed on beat N in this version (repeatable) — shown on the card and in the banner
  --delivered   the final master: switches the page to 已交片 with a 下載完整影片 button (the video is published next to the
                page with Artifact `files`; a ≤ 14 MB download copy is made when the master is bigger) plus cover / SRT downloads
Publish the HTML as an artifact with capabilities {"comments": {}, "downloads": true} and keep its URL: every later
version is republished to the SAME URL so the open page reloads itself (see SKILL.md, step 6).
"""
import sys, os, json, base64, html, argparse, io, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hn_common import grab, ASSETS, expand_timeline, resolve_words
import pacing as PACE
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--out"); ap.add_argument("--version", type=int, default=1)
ap.add_argument("--video"); ap.add_argument("--prev"); ap.add_argument("--change", action="append", default=[]); ap.add_argument("--delivered")
ap.add_argument("--max-mb", type=float, default=8.0, help="cap for the embedded review copy")
a = ap.parse_args()
D = os.path.dirname(os.path.abspath(a.spec)); spec = resolve_words(json.load(open(a.spec)), os.path.dirname(os.path.abspath(a.spec))); P = lambda p: p if os.path.isabs(p) else os.path.join(D, p)
FPS = int(spec.get("output", {}).get("fps", 30))
PREV = json.load(open(a.prev))["timeline"] if a.prev else None
canon = lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False)

def jpeg_uri(arr, q=78):
    b = io.BytesIO(); Image.fromarray(arr).save(b, "JPEG", quality=q); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
def fmt_srt(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000); return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ---- review copy of the draft (small, fast-start, embedded) ----
video_uri = ""
if a.video:
    src = P(a.video); tmp = tempfile.mkdtemp(); out = os.path.join(tmp, "review.mp4")
    for scale, crf in (("432:768", 28), ("360:640", 31), ("288:512", 34)):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"scale={scale}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", str(crf), "-profile:v", "main", "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", out], check=True)
        if os.path.getsize(out) <= a.max_mb * 1048576: break
    video_uri = "data:video/mp4;base64," + base64.b64encode(open(out, "rb").read()).decode()

# ---- beats on the OUTPUT timeline (same frame maths as render.py) ----
changes = {}
for c in a.change:
    k, _, v = c.partition("="); changes[int(k)] = v.strip()
# output-time span of every beat (speed-ramped beats are several clip pieces) + SRT from the pieces
spans, srt, t = {}, [], 0.0
for pc in expand_timeline(spec["timeline"], float(spec.get("speed", 1.0))):
    kind = pc.get("type", "clip"); bi = pc["_beat"]
    if kind == "clip":
        a0, b0, k = float(pc["in"]), float(pc["out"]), float(pc.get("speed", spec.get("speed", 1.0)))
        N = max(1, round((b0 - a0) / k * FPS)); dur = N / FPS; keff = (b0 - a0) / dur
        for c in pc.get("captions", []):
            c0, c1 = max(a0, float(c["start"])), min(b0, float(c["end"]))
            if c1 > c0: srt.append((t + (c0 - a0) / keff, t + (c1 - a0) / keff, c["text"]))
    else:
        dur = round(float(pc.get("dur", 1.4 if kind == "cover" else 1.0 if kind == "freeze" else 2.625)) * FPS) / FPS
    sp = spans.setdefault(bi, [t, t]); sp[1] = t + dur; t += dur
TOTAL = t
srt.sort()
pace = PACE.analyze(spec)
warn = {}
for g in pace["dead_spots"]:
    warn.setdefault(g["beat"], g)
beats = []
for i, it in enumerate(spec["timeline"]):
    kind = it.get("type", "clip"); n = f"{i + 1:02d}"; st, en = spans[i]
    if kind == "clip":
        a0, b0, k = float(it["in"]), float(it["out"]), float(it.get("speed", spec.get("speed", 1.0)))
        line = " ".join(c["text"] for c in it.get("captions", [])) or "（無口白）"
        acts = []
        for bw in it.get("bigwords", []): acts.append(f"巨字「{bw['word']}」逐字打出" + ("，放在頭頂上方、頭部壓在字前" if bw.get("place", "auto") != "low" else "，放畫面下方"))
        for pr in it.get("prompts", []): acts.append(f"指令框打出「{pr['text']}」，按下送出 ✓")
        for pz in it.get("punch", []): acts.append(f"推近 {float(pz.get('scale', 1.18)) * 100 - 100:.0f}%（punch-in）")
        if it.get("bubbles"): acts.append("對話泡泡：" + " → ".join(("我：" if b_.get("who") == "me" else "AI：") + b_["text"] for b_ in it["bubbles"]))
        if it.get("checklist"): acts.append("清單逐項打勾：" + "、".join(r["text"] for r in it["checklist"].get("items", [])))
        if it.get("phone"): acts.append("手機畫面從下方滑上來（" + os.path.basename(it["phone"]["src"]) + "）")
        for r in it.get("ramp", []): acts.append(f"{float(r['from']):.1f}–{float(r['to']):.1f}s 加速 {float(r.get('speed', 3)):g}×（畫面標示「▶▶」）")
        if it.get("fit"): acts.append("螢幕錄影完整呈現，背景模糊")
        if it.get("headlines"): acts.append("新聞標題牆（在頭後面）：" + "、".join(c["text"] for c in it["headlines"].get("cards", [])))
        if it.get("chart"): acts.append("長條圖長出來：" + "、".join(f"{b['label']} {b['value']}" for b in it["chart"]["bars"]))
        if it.get("bg"): acts.append("換背景（綠幕效果）：" + os.path.basename(it["bg"]["src"]))
        if it.get("sticker"): acts.append("人物剪成貼紙（白邊＋紙張背景）")
        if it.get("framebreak"): acts.append("相框效果：頭從相框裡衝出來")
        if it.get("doodle"): acts.append("手繪描邊＋小塗鴉（會抖動）")
        if it.get("pullback"): acts.append(f"從臉部特寫拉開到全景（{float(it['pullback'].get('from', 1.6)):g}× → 1×）")
        if it.get("zoom_in"): acts.append("穿越式放大轉場進來")
        for bw in it.get("bigwords", []):
            if bw.get("style") == "glass": acts.append(f"「{bw['word']}」是毛玻璃字")
        if it.get("cta"): acts.append(f"留言卡片滑入，逐字打出 {it['cta'].get('keyword', 'EDIT')}，愛心＋作者回覆「{it['cta'].get('reply', '')}」")
        if it.get("push"): acts.append(f"畫面緩慢推近 {float(it['push']) * 100:.1f}%")
        if k != 1 and not it.get("ramp"): acts.append(f"語速 {k:g}×")
        if it.get("captions"): acts.append("卡拉 OK 字幕逐字亮起（墨色字卡、橘色重點字）")
        if it.get("whip_in"): acts.append("甩鏡模糊轉場進來")
        shot = it.get("shot", "特寫")
        key = next((k_ for c in it.get("captions", []) for k_ in c.get("keys", [])), "")
        frame_src, frame_t = it["src"], a0 + (b0 - a0) * 0.5
    elif kind == "cover":
        line = "（封面開場）"; key = ""
        acts = [f"雜誌封面：刊頭「{it.get('masthead', '黑牛')}」藏在頭後", "封面標題：" + "".join(it.get("headline", [])), "最後快速甩鏡進入開場句"]
        shot = "封面・冷開場"; frame_src, frame_t = it["src"], float(it.get("at", 0))
    elif kind == "freeze":
        line = "（定格）"; key = ""
        acts = [f"畫面定格 {float(it.get('dur', 1.0)):.1f} 秒，蓋上紅色「{it.get('text', '等一下')}」印章" + ("，紅圈畫出重點" if it.get("circle") else ""), "刮唱片音效"]
        shot = "定格・暫停"; frame_src, frame_t = it["src"], float(it.get("at", 0))
    else:
        line = "（前後對比）"; key = ""
        acts = [f"斜線由左往右慢慢掃過：左「{it.get('label_after', 'AI 調色')}」右「{it.get('label_before', '原始')}」"]
        shot = "定格・前後對比"; frame_src, frame_t = it["src"], float(it.get("at", 0))
    acts += it.get("notes", [])
    changed = PREV is not None and (i >= len(PREV) or canon(PREV[i]) != canon(it))
    w = warn.get(i + 1)
    beats.append(dict(n=n, start=round(st, 3), end=round(en, 3), shot=shot, line=line, acts=acts, key=key,
                      changed=bool(changed or (i + 1) in changes), applied=changes.get(i + 1, ""), _src=frame_src, _t=frame_t,
                      warn=(dict(text=f"畫面 {w['length']:.1f} 秒沒變化（{w['start']:.1f}–{w['end']:.1f}s）", fixes=w["fixes"]) if w else None)))

# ---- thumbnails: from the draft when we have it (shows captions/effects), else from the source ----
for b in beats:
    uri = ""
    if a.video:
        mid = (b["start"] + b["end"]) / 2
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{mid:.3f}", "-i", P(a.video), "-frames:v", "1", "-vf", "scale=216:384", "-q:v", "4",
                            "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True)
        if r.stdout: uri = "data:image/jpeg;base64," + base64.b64encode(r.stdout).decode()
    b["thumb"] = uri or jpeg_uri(grab(P(b["_src"]), b["_t"], 216, 384))
    del b["_src"], b["_t"]

data = dict(name=spec.get("name", "edit"), version=a.version, duration=round(TOTAL, 3), beats=beats, pace=dict(max_gap=pace["max_gap"], count=len(pace["dead_spots"])),
            changes=[dict(beat=f"{k:02d}", note=v) for k, v in sorted(changes.items())],
            srt="\n".join(f"{i + 1}\n{fmt_srt(s0)} --> {fmt_srt(s1)}\n{txt}\n" for i, (s0, s1, txt) in enumerate(srt)))
if a.delivered:
    fp = P(a.delivered); mb = os.path.getsize(fp) / 1048576
    # the page carries the video as a supporting file (Artifact `files`, ≤ 15 MB per file): use the master when it fits,
    # otherwise make a download copy at Instagram-level bitrate that fits; the full master is always also sent in chat.
    dl = fp; note = ""
    if mb > 14.5:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", fp], capture_output=True, text=True).stdout or 1)
        vbr = int(max(1.2e6, (14.0 * 8 * 1048576) / dur - 160_000)); dl = os.path.splitext(fp)[0] + "_download.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", fp, "-c:v", "libx264", "-b:v", str(vbr), "-maxrate", str(int(vbr * 1.15)), "-bufsize", str(vbr * 2),
                        "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", dl], check=True)
        note = f"下載版 {vbr / 1e6:.1f} Mbps（IG 上傳後的畫質相同）；{mb:.0f} MB 的最高畫質原檔在對話裡"
    dmb = os.path.getsize(dl) / 1048576
    data["delivered"] = dict(file=os.path.basename(dl), url=os.path.basename(dl), size=f"{dmb:.1f} MB", master=f"{mb:.1f} MB", spec="1080×1920 · 30fps · H.264 / AAC", note=note)
    print(f"   publish with files: {{\"{os.path.basename(dl)}\": \"{dl}\"}}")
    cov = os.path.join(D, "_render", "cover.jpg"); os.makedirs(os.path.dirname(cov), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.6", "-i", fp, "-frames:v", "1", "-q:v", "3", cov], check=True)
    data["cover"] = "data:image/jpeg;base64," + base64.b64encode(open(cov, "rb").read()).decode()

def fmt(x): return f"{int(x // 60)}:{x % 60:04.1f}"
tpl = open(os.path.join(ASSETS, "storyboard_template.html")).read()
brand = spec.get("style", {}).get("brand", "黑牛")
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
out = (tpl.replace("{{TITLE}}", f"{brand} AI 剪輯室").replace("{{PATH}}", html.escape(spec.get("name", "edit"))).replace("{{VER}}", str(a.version))
          .replace("{{COUNT}}", str(len(beats))).replace("{{DUR}}", f"{TOTAL:.1f}").replace("{{END}}", fmt(TOTAL))
          .replace("{{VIDEO}}", video_uri).replace("{{POSTER}}", beats[0]["thumb"] if beats else "").replace("{{DATA}}", payload))
dst = a.out or os.path.join(D, "storyboard.html"); open(dst, "w").write(out)
print("→", dst, f"{len(out) / 1048576:.2f} MB, {len(beats)} beats, {TOTAL:.1f}s, video {'embedded' if video_uri else 'none'}")
