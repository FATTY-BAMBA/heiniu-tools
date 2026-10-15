"""Quick before/after preview of only the beats that changed — so the person sees each one-sentence edit in seconds,
without waiting for (or re-watching) the full render.

usage:
  python3 preview.py edit.json --snapshot          # BEFORE applying edits: saves _versions/edit.vN.json
  python3 preview.py edit.json                     # AFTER editing: diff vs the latest snapshot → preview_vN.mp4
  python3 preview.py edit.json --beats 2,5 [--prev _versions/edit.v1.json] [--note "第 02 拍：字幕再大一點"]

Output: <name>_preview_vN.mp4 — 修改前 | 修改後 side by side (half resolution), one block per changed beat,
with the beat number and the request written on top. Typically 3–10 s and < 3 MB, renders in under a minute.
"""
import sys, os, json, glob, argparse, subprocess, shutil, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hn_common import F, palette                   # noqa: E402
from PIL import Image, ImageDraw                   # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--snapshot", action="store_true")
ap.add_argument("--beats"); ap.add_argument("--prev"); ap.add_argument("--note", action="append", default=[]); ap.add_argument("--out")
a = ap.parse_args()
D = os.path.dirname(os.path.abspath(a.spec)); VD = os.path.join(D, "_versions"); os.makedirs(VD, exist_ok=True)
spec = json.load(open(a.spec)); name = spec.get("name", "edit")
def vnum(p): m = re.search(r"\.v(\d+)\.json$", p); return int(m.group(1)) if m else 0
snaps = sorted(glob.glob(os.path.join(VD, "edit.v*.json")), key=vnum)

if a.snapshot:
    n = (vnum(snaps[-1]) + 1) if snaps else 1; dst = os.path.join(VD, f"edit.v{n}.json"); shutil.copy(a.spec, dst)
    print("snapshot →", dst); sys.exit(0)

prev_p = a.prev or (snaps[-1] if snaps else None)
if not prev_p: raise SystemExit("no snapshot to compare with — run with --snapshot before editing, or pass --prev")
prev = json.load(open(prev_p))
canon = lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False)
glob_changed = any(canon(spec.get(k)) != canon(prev.get(k)) for k in ("captions_style", "style", "grade", "speed", "bars"))
T1, T0 = spec["timeline"], prev["timeline"]
if a.beats:
    beats = [int(x) for x in a.beats.split(",")]
else:
    beats = [i + 1 for i in range(len(T1)) if i >= len(T0) or canon(T1[i]) != canon(T0[i])]
    if glob_changed and not beats: beats = list(range(1, min(3, len(T1)) + 1))   # global style change: show the first beats
if not beats: raise SystemExit("nothing changed vs " + os.path.basename(prev_p))
notes = {}
for s in a.note:                                     # "第 02 拍：…" or "2:…"
    m = re.match(r"\D*(\d+)\D*?[:：]\s*(.+)", s)
    if m: notes[int(m.group(1))] = m.group(2)

W = os.path.join(D, "_render", "preview"); os.makedirs(W, exist_ok=True)
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.py")
def render_one(src_spec, idx, tag):
    if idx - 1 >= len(src_spec["timeline"]): return None
    sub = dict(src_spec); sub["timeline"] = [src_spec["timeline"][idx - 1]]; sub["name"] = f"pv_{tag}_{idx}"
    sub.setdefault("output", {}); sub["output"] = dict(sub["output"], max_mb=4)
    sp = os.path.join(D, f".pv_{tag}_{idx}.json"); json.dump(sub, open(sp, "w"), ensure_ascii=False)
    out = os.path.join(W, f"{tag}_{idx:02d}.mp4")
    subprocess.run([sys.executable, R, sp, "--preview", "--work", os.path.join(W, f"w_{tag}_{idx}"), "--out", out], check=True, stdout=subprocess.DEVNULL)
    os.remove(sp); return out
def dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)

P = palette(spec.get("style")); EM = P["accent"]
def band(idx, note):                                  # 1080x200 header: beat number + the request
    im = Image.new("RGB", (1080, 200), P["ink"]); d = ImageDraw.Draw(im)
    f1, f2, f3 = F("sans", 30), F("sans", 40), F("sans_m", 26)
    d.text((40, 30), f"第 {idx:02d} 拍", font=f1, fill=EM)
    d.text((40, 74), (note or "已修改")[:24], font=f2, fill=P["ivory"])
    d.text((40 + 0, 150), "修改前", font=f3, fill=(150, 146, 138)); d.text((580, 150), "修改後", font=f3, fill=EM)
    p = os.path.join(W, f"band_{idx}.png"); im.save(p); return p

parts = []
for idx in beats:
    new = render_one(spec, idx, "new"); old = render_one(prev, idx, "old")
    hb = band(idx, notes.get(idx)); L = max(dur(new), dur(old) if old else 0)
    out = os.path.join(W, f"pair_{idx:02d}.mp4")
    if old:
        fc = (f"[0:v]tpad=stop_mode=clone:stop_duration={L:.3f},trim=0:{L:.3f},setpts=PTS-STARTPTS[o];"
              f"[1:v]tpad=stop_mode=clone:stop_duration={L:.3f},trim=0:{L:.3f},setpts=PTS-STARTPTS[n];"
              f"[o][n]hstack=inputs=2[s];[2:v][s]vstack=inputs=2,format=yuv420p[v];"
              f"[1:a]apad,atrim=0:{L:.3f}[a]")
        cmd = ["-i", old, "-i", new, "-loop", "1", "-i", hb]
    else:                                             # a newly added beat: show it alone, centred
        fc = f"[0:v]pad=1080:960:270:0:color=black[s];[1:v][s]vstack=inputs=2,format=yuv420p[v];[0:a]apad,atrim=0:{L:.3f}[a]"
        cmd = ["-i", new, "-loop", "1", "-i", hb]
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + cmd + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{L:.3f}", "-r", "30",
                    "-c:v", "libx264", "-crf", "24", "-preset", "fast", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", out], check=True)
    parts.append(out)
lst = os.path.join(W, "pairs.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
v = vnum(prev_p) + 1
OUT = a.out or os.path.join(D, f"{name}_preview_v{v}.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", OUT], check=True)
print(json.dumps(dict(output=OUT, beats=beats, compared_with=os.path.basename(prev_p), seconds=round(dur(OUT), 2),
                      size_mb=round(os.path.getsize(OUT) / 1048576, 2)), ensure_ascii=False))
