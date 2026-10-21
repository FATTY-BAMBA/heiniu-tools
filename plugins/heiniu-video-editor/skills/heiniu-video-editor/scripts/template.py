"""Style templates (風格): one edit.json, five finished looks. A template sets the caption look, colour grade, accent colour,
SFX level and shake, and adds / removes effects to match the style. It is reversible: switching style restores the base
edit first (everything a template removed is kept in `_off`, everything it added is marked), so the person can try
another style at any time without losing the cut.

usage:
  python3 template.py edit.json --list                         # the styles, one line each
  python3 template.py edit.json --previews [--seconds 3.5]     # ~3 s of THEIR clip in every style → _render/styles/ (+ styles.json)
  python3 template.py edit.json --apply knowledge              # rewrite edit.json in that style (switching restores the base first)
  python3 template.py edit.json --reel [--out styles_reel.mp4] # demo reel: the same opening cycling through every style, with labels
"""
import sys, os, json, copy, argparse, subprocess, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hn_common import resolve_words, F, palette           # noqa: E402

# Five style families that top short-form editors and caption tools converge on (impact word-by-word, editorial serif,
# minimal, news strip, cinematic vlog) + a product style — rebuilt in our own look, never a copy of one creator's.
T = {
    "impact": dict(name="衝擊字", line="粗黑描邊大字・一次 2–5 字跟著嘴巴跳・重點字變色＋emoji", look="impact", grade="punchy", accent="#FFE14D",
                   shake=14, sfx=1.2, gap=2.5, strip=["headlines"], glass=False, punch=1.25, hold=0.5, freeze="蛤？"),
    "editorial": dict(name="雜誌", line="襯線字逐字浮現・重點字斜體上色・刊頭＋毛玻璃巨字", look="editorial", grade="soft", accent="#FF6A1A",
                      shake=6, sfx=0.85, gap=3.0, header="masthead", strip=[], glass=True, punch=1.12, keep_punch_only=True),
    "minimal": dict(name="極簡", line="低飽和＋單一重點色・小字從模糊浮現・安靜不吵", look="minimal", grade="muted", accent="#FFC233",
                    shake=0, sfx=0.35, gap=4.5, push=0.025, strip=["bigwords", "headlines", "framebreak", "sticker", "doodle", "bg", "zoom_in", "whip_in", "chart"],
                    drop=["freeze", "cover", "compare"], punch=1.07, keep_punch_only=True),
    "news": dict(name="新聞快報", line="紅色快報標題列・黑底字幕條・正在講的字變黃", look="news", grade="crisp", accent="#FFD43B",
                 shake=6, sfx=0.9, gap=3.0, header="news", low_words=True, strip=["sticker", "doodle", "framebreak", "bg"], glass=False,
                 punch=1.12, punch_digits_only=True),
    "vlog": dict(name="電影感 Vlog", line="電影黑邊＋底片顆粒・字小而淡・緩慢推近", look="vlog", grade="film", accent="#F2C98A",
                 shake=0, sfx=0.3, gap=5.0, push=0.03, header="stamp", bars=True, grain=0.035,
                 strip=["bigwords", "headlines", "framebreak", "sticker", "doodle", "punch", "pullback", "zoom_in", "whip_in", "chart", "bg"],
                 drop=["freeze", "cover", "compare"]),
    "product": dict(name="開箱／業配", line="一段一張標籤滑進來・明亮原色・留言拿連結", look="label", grade="clean", accent="#14A38B",
                    shake=4, sfx=0.7, gap=3.0, header="label", low_words=True, strip=["doodle", "framebreak", "headlines", "sticker"], glass=False,
                    punch=1.1, cta=True),
}
ORDER = ["impact", "editorial", "minimal", "news", "vlog", "product"]
GLOBALS = ["captions_style", "grade", "style", "shake_px", "sfx_gain", "header", "bars", "grain", "pacing"]

# ---------------- reversible edits ----------------
def _set(it, k, v):
    if k not in it.get("_off", {}) and k not in it.get("_tpl_keys", []):
        if k in it: it.setdefault("_off", {})[k] = copy.deepcopy(it[k])
        else: it.setdefault("_tpl_keys", []).append(k)
    it[k] = v
def _strip(it, k):
    if k in it:
        if k not in it.get("_off", {}) and k not in it.get("_tpl_keys", []): it.setdefault("_off", {})[k] = it[k]
        del it[k]
def restore(spec):
    """undo whatever template was applied → the base edit"""
    spec = copy.deepcopy(spec)
    base = spec.pop("_base_globals", None)
    if base is not None:
        for k in GLOBALS:
            if base.get(k) is None: spec.pop(k, None)
            else: spec[k] = base[k]
    tl = []
    for it in spec["timeline"]:
        if it.get("_tpl"): continue
        for k in it.pop("_tpl_keys", []): it.pop(k, None)
        for k, v in it.pop("_off", {}).items(): it[k] = v
        tl.append(it)
    spec["timeline"] = tl; spec.pop("template", None); return spec

# ---------------- word times for template-added effects ----------------
def key_times(spec, spec_dir, it, cap, key):
    """source time of `key` inside caption `cap` of clip `it`: word-locked when there is a transcript, else proportional"""
    if spec.get("words"):
        probe = {"words": spec["words"], "timeline": [dict(type="clip", src=it["src"], **{"in": it["in"], "out": it["out"]}, x={"at": "@" + key})]}
        try: return float(resolve_words(probe, spec_dir)["timeline"][0]["x"]["at"])
        except Exception: pass
    rc = resolve_words({"words": spec.get("words"), "timeline": [dict(it, captions=[cap])]}, spec_dir)["timeline"][0]["captions"][0] if spec.get("words") else cap
    c0, c1 = float(rc["start"]), float(rc["end"]); j = max(0, rc["text"].find(key))
    return c0 + (c1 - c0) * j / max(1, len(rc["text"]))

def apply(spec, name, spec_dir, preview=False):
    if name not in T: raise SystemExit(f"unknown style {name!r} — one of: {', '.join(ORDER)}")
    t = T[name]; spec = restore(spec)
    spec["_base_globals"] = {k: copy.deepcopy(spec.get(k)) for k in GLOBALS}
    cs = {k: v for k, v in (spec.get("captions_style") or {}).items() if k not in ("size", "y")}; cs["look"] = t["look"]; spec["captions_style"] = cs   # size / y come from the look
    spec["grade"] = t["grade"]; st = dict(spec.get("style") or {}); st["accent"] = t["accent"]; spec["style"] = st
    spec["shake_px"] = t["shake"]; spec["sfx_gain"] = t["sfx"]; spec["template"] = name
    if t.get("bars"): spec["bars"] = True
    if t.get("grain"): spec["grain"] = t["grain"]
    spec["pacing"] = dict(spec.get("pacing") or {}, max_gap=t["gap"])
    if t.get("header"):                                                   # topic line: spec "topic" (Claude writes it), else the first caption
        first = next((c["text"] for it in spec["timeline"] for c in it.get("captions", [])), spec.get("name", ""))
        topic = spec.get("topic") or first
        if t["header"] == "stamp":
            import datetime; spec["header"] = dict(kind="stamp", text=spec.get("place_stamp") or datetime.date.today().strftime("%Y.%m.%d") + "  ·  " + spec.get("place", "TAIPEI"))
        elif t["header"] == "bar": spec["header"] = dict(kind="bar", text=topic, badge=spec.get("episode", "#01"))
        elif t["header"] == "masthead": spec["header"] = dict(kind="masthead", text=topic, badge=spec.get("issue", "N°01"))
        elif t["header"] == "news": spec["header"] = dict(kind="news", text=topic, badge=spec.get("badge", "快報"))
        else: spec["header"] = dict(kind="label", text=topic, badge=spec.get("badge", "開箱"))
    tl = []
    for it in spec["timeline"]:
        if it.get("type", "clip") in t.get("drop", []): it["_tpl_dropped"] = True
        tl.append(it)
    # dropped items (covers / freezes for vlog) leave the timeline but come back on restore: keep them as hidden stash items
    spec["timeline"] = [it for it in tl if not it.get("_tpl_dropped")]
    spec["_dropped"] = [dict(at=i, item={k: v for k, v in it.items() if k != "_tpl_dropped"}) for i, it in enumerate(tl) if it.get("_tpl_dropped")]
    clips = [it for it in spec["timeline"] if it.get("type", "clip") == "clip"]
    for n, it in enumerate(clips):
        for k in t["strip"]: _strip(it, k)
        for c in it.get("captions", []):                                  # per-caption size overrides would fight the template
            if "size" in c: c["_size"] = c.pop("size")
        if t.get("push") and not it.get("push"): _set(it, "push", t["push"])
        if ("glass" in t or t.get("low_words")) and it.get("bigwords"):
            def bw_(bw):
                bw = dict(bw, style="glass") if t.get("glass") else {k: v for k, v in bw.items() if k != "style"}
                if t.get("low_words"): bw["place"] = "low"; bw["size"] = min(int(bw.get("size", 300)), 280); bw["low_y"] = 1240   # infographic number in the lower third
                return bw
            _set(it, "bigwords", [bw_(bw) for bw in it["bigwords"]])
        if t.get("punch") and "punch" not in t["strip"] and it.get("punch"):     # keep the editor's word-locked punches, restyle them
            ats = resolve_words({"words": spec.get("words"), "timeline": [dict(it)]}, spec_dir)["timeline"][0]["punch"] if spec.get("words") else it["punch"]
            new = []
            for p, rp in zip(it["punch"], ats):
                q = dict(p, scale=t["punch"])
                if t.get("hold") and "until" not in p: q["until"] = round(min(float(it["out"]) - 0.05, float(rp["at"]) + t["hold"]), 3)
                new.append(q)
            _set(it, "punch", new)
        elif t.get("punch") and "punch" not in t["strip"] and not t.get("keep_punch_only"):
            pz = []
            for c in it.get("captions", []):
                for key in c.get("keys", [])[:1]:
                    if t.get("punch_digits_only") and not any(ch.isdigit() for ch in key) and not any(ch in "萬千百億塊元%" for ch in key): continue
                    at = key_times(spec, spec_dir, it, c, key); p = dict(at=round(at - 0.067, 3), scale=t["punch"])
                    if t.get("hold"): p["until"] = round(min(float(it["out"]) - 0.05, at + t["hold"]), 3)
                    pz.append(p)
            if pz and not it.get("pullback"): _set(it, "punch", pz)
        if t.get("zoom_cuts") and n > 0 and not it.get("whip_in"): _set(it, "zoom_in", True)
    if t.get("freeze") and not any(it.get("type") == "freeze" for it in spec["timeline"]) and clips:
        tgt = next((it for it in clips if any(c.get("color") == "red" for c in it.get("captions", []))), clips[min(1, len(clips) - 1)])
        k = spec["timeline"].index(tgt)
        spec["timeline"].insert(k + 1, dict(type="freeze", src=tgt["src"], at=round(float(tgt["out"]) - 0.04, 3), dur=0.9, text=t["freeze"], _tpl=True, shot="定格・蛤？"))
    if t.get("cta") and not preview and clips and not any(it.get("cta") for it in clips):
        last = clips[-1]; a, b = float(last["in"]), float(last["out"])
        _set(last, "cta", dict(show=round(max(a, b - 2.6), 3), keyword="LINK", sub="拿連結", reply="連結傳給你了"))
    return spec

def restore_full(spec):
    """restore() plus putting dropped items back where they were"""
    drops = spec.get("_dropped", []); base = restore(spec); base.pop("_dropped", None)
    for d in sorted(drops, key=lambda d: d["at"]): base["timeline"].insert(min(d["at"], len(base["timeline"])), d["item"])
    for it in base["timeline"]:
        for c in it.get("captions", []):
            if "_size" in c: c["size"] = c.pop("_size")
    return base

# ---------------- previews / reel ----------------
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.py")
def opening(spec, seconds):
    """the first beats covering ~`seconds` of output (clips only, so every style starts from the same picture)"""
    out, t = [], 0.0; k_ = float(spec.get("speed", 1.0))
    rs = resolve_words(spec, D)
    for it, ri in zip(spec["timeline"], rs["timeline"]):
        if it.get("type", "clip") != "clip": continue
        out.append(it); t += (float(ri["out"]) - float(ri["in"])) / float(ri.get("speed", k_))
        if t >= seconds: break
    return out
def render(sub, tag, wd, preview=True):
    sp = os.path.join(D, f".tpl_{tag}.json"); json.dump(sub, open(sp, "w"), ensure_ascii=False)
    out = os.path.join(wd, f"{tag}.mp4"); log = open(os.path.join(wd, f"{tag}.log"), "w")
    subprocess.run([sys.executable, R, sp] + (["--preview"] if preview else []) + ["--work", os.path.join(wd, "w_" + tag), "--out", out], check=True, stdout=log, stderr=log)
    os.remove(sp); return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--list", action="store_true"); ap.add_argument("--apply")
    ap.add_argument("--previews", action="store_true"); ap.add_argument("--reel", action="store_true"); ap.add_argument("--seconds", type=float, default=3.5)
    ap.add_argument("--styles", default=",".join(ORDER)); ap.add_argument("--out")
    a = ap.parse_args(); D = os.path.dirname(os.path.abspath(a.spec)); spec = json.load(open(a.spec)); names = a.styles.split(",")
    if a.list:
        for k in ORDER: print(f"{k:10s} {T[k]['name']} — {T[k]['line']}")
    elif a.apply:
        base = restore_full(spec) if spec.get("template") else spec
        new = apply(base, a.apply, D); json.dump(new, open(a.spec, "w"), ensure_ascii=False, indent=1)
        print(f"✓ {os.path.basename(a.spec)} → {T[a.apply]['name']}（{a.apply}）. Switch any time with --apply <style>; the base cut is kept.")
    elif a.previews or a.reel:
        base = restore_full(spec) if spec.get("template") else spec
        sub = dict(base, timeline=opening(base, a.seconds), name="style"); sub.pop("music", None)
        wd = os.path.join(D, "_render", "styles"); os.makedirs(wd, exist_ok=True)
        jobs = {n: apply(sub, n, D, preview=True) for n in names}
        with cf.ThreadPoolExecutor(max_workers=1 if a.reel else min(2, len(jobs))) as ex:      # full-res renders use ~2–3 GB each
            outs = dict(zip(jobs, ex.map(lambda kv: render(kv[1], kv[0], wd, preview=not a.reel), jobs.items())))
        mp = os.path.join(wd, "styles.json"); old = {m["id"]: m for m in (json.load(open(mp)) if os.path.exists(mp) else []) if os.path.exists(m.get("file", ""))}
        old.update({n: dict(id=n, name=T[n]["name"], line=T[n]["line"], accent=T[n]["accent"], file=outs[n]) for n in names})   # re-rendering a few keeps the rest
        meta = [old[n] for n in ORDER if n in old]
        json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
        print(json.dumps(meta, ensure_ascii=False, indent=1))
        if a.reel:
            sys.argv = [sys.argv[0]]; import style_reel; style_reel.build(meta, a.out or os.path.join(D, "styles_reel.mp4"), wd)
