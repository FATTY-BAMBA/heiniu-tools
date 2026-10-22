"""Dead-spot checker: finds stretches where the picture does not change for longer than `max_gap` seconds
(default 3.0 — on a Reel, a talking head that sits still for longer than that is where people swipe away).

usage: python3 pacing.py edit.json        → prints each dead spot with the beat it sits in and concrete fixes
Also imported by storyboard.py (warnings on the beat cards) and render.py (qa.json "dead_spots")."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hn_common import expand_timeline, resolve_words

QUOTE = ("說", "問", "回", "講", "叫", "AI", "它")
def analyze(spec, fps=None, max_gap=None):
    fps = int(fps or spec.get("output", {}).get("fps", 30)); max_gap = float(max_gap or spec.get("pacing", {}).get("max_gap", 3.0))
    pieces = expand_timeline(spec["timeline"], float(spec.get("speed", 1.0)))
    ev, beats, t, prev = [], {}, 0.0, None
    for it in pieces:
        kind = it.get("type", "clip"); bi = it["_beat"]
        if kind == "clip":
            a, b, k = float(it["in"]), float(it["out"]), float(it.get("speed", spec.get("speed", 1.0)))
            N = max(1, round((b - a) / k * fps)); dur = N / fps; keff = (b - a) / dur
            o = lambda x, t=t, a=a, keff=keff: t + (float(x) - a) / keff
            inside = lambda x, t=t, dur=dur: t - 1e-6 <= x <= t + dur + 1e-6
        else:
            dur = round(float(it.get("dur", 1.4 if kind == "cover" else 1.0 if kind == "freeze" else 2.625)) * fps) / fps
            o = None; inside = lambda x: False
        bb = beats.setdefault(bi, dict(start=t, end=t + dur, item=spec["timeline"][bi])); bb["end"] = t + dur
        # a cut counts as a picture change only when it really looks different
        if prev is not None:
            looks = lambda x: (x.get("type", "clip"), x.get("src"), x.get("crop", 1.0), bool(x.get("fit")))
            if kind != "clip" or it.get("whip_in") or it.get("zoom_in") or looks(it) != looks(prev) or it.get("_fast") != prev.get("_fast"): ev.append(t)
        if kind != "clip":
            x = t
            while x < t + dur: ev.append(x); x += 0.8                      # covers / compares / freezes animate throughout
        else:
            add = lambda x: ev.append(o(x)) if inside(o(x)) else None
            for bw in it.get("bigwords", []): add(bw["start"])
            for pr in it.get("prompts", []): add(pr["start"]); add(pr.get("send", pr["start"]))
            C = it.get("cta")
            if C:
                for kx in ("show", "type_at", "heart_at", "reply_at"):
                    if kx in C: add(C[kx])
            for bu in it.get("bubbles", []): add(bu["start"])
            ck = it.get("checklist")
            if ck:
                add(ck["start"])
                for row in ck.get("items", []): add(row["at"])
            for p in it.get("punch", []):
                add(p["at"])
                if "until" in p: add(p["until"])
            ph = it.get("phone")
            if ph: add(ph["start"]); add(ph.get("end", ph["start"]))
            for key in ("bg", "sticker", "framebreak", "doodle", "chart"):
                fx = it.get(key)
                if fx: add(fx["start"]); add(fx.get("end", fx["start"]))
            for c in it.get("ui", []):
                add(c["start"])
                for row in c.get("items", []): add(row["at"])
                if "click_at" in c: add(c["click_at"])
            hl = it.get("headlines")
            if hl:
                for c in hl.get("cards", []): add(c.get("at", hl["start"]))
            pb = it.get("pullback")
            if pb: add(pb.get("at", it["in"])); add(float(pb.get("at", it["in"])) + float(pb.get("dur", 0.8)) * float(it.get("speed", 1.0)))
        t += dur; prev = it
    total = t; ev = sorted(set([0.0] + [round(x, 3) for x in ev if 0 <= x <= total] + [round(total, 3)]))
    gaps = []
    for x0, x1 in zip(ev, ev[1:]):
        if x1 - x0 > max_gap:
            mid = (x0 + x1) / 2
            bi = next((k for k, v in beats.items() if v["start"] - 1e-6 <= mid < v["end"] + 1e-6), max(beats))
            gaps.append(dict(start=round(x0, 2), end=round(x1, 2), length=round(x1 - x0, 2), beat=bi + 1, fixes=fixes_for(beats[bi]["item"])))
    return dict(total=round(total, 2), max_gap=max_gap, events=len(ev), dead_spots=gaps)

def fixes_for(it):
    caps = it.get("captions", []); text = "".join(c.get("text", "") for c in caps)
    key = next((k for c in caps for k in c.get("keys", [])), "") or (caps[0]["text"][:3] if caps else "")
    f = []
    if key: f.append(f"在「{key}」那個字推近")
    if any(q in text for q in QUOTE): f.append("把這段對話做成對話泡泡")
    if any(ch.isdigit() for ch in text) or "、" in text: f.append("把重點做成清單，一項一項打勾")
    f.append("在這裡加一個暫停＋「等一下」")
    return f[:3]

if __name__ == "__main__":
    r = analyze(resolve_words(json.load(open(sys.argv[1])), os.path.dirname(os.path.abspath(sys.argv[1]))))
    if not r["dead_spots"]: print(f"✓ 沒有超過 {r['max_gap']:.0f} 秒不變的畫面（{r['total']} 秒，{r['events']} 個畫面變化）")
    for g in r["dead_spots"]:
        print(f"⚠ 第 {g['beat']:02d} 拍 {g['start']:.1f}–{g['end']:.1f}s：畫面 {g['length']:.1f} 秒沒變化 → " + "／".join(g["fixes"]))
