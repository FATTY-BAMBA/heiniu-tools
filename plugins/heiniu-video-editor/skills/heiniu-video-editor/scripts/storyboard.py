"""Build the reviewable storyboard page from edit.json (one card per beat, thumbnail, line, what happens on screen,
plus a one-sentence comment box under every beat and a 'copy all' button).

usage: python3 storyboard.py edit.json [--out storyboard.html] [--version 2] [--prev _versions/edit.v1.json]
--prev marks every beat that changed since that version with a 「已修改」 badge (and the beats list at the top).
Publish the HTML as an artifact (or send the file) and ask the person to write changes in the boxes."""
import sys, os, json, base64, html, argparse, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hn_common import grab, ASSETS
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--out"); ap.add_argument("--version", default="1"); ap.add_argument("--prev"); a = ap.parse_args()
D = os.path.dirname(os.path.abspath(a.spec)); spec = json.load(open(a.spec)); P = lambda p: p if os.path.isabs(p) else os.path.join(D, p)
def thumb(src, t):
    im = Image.fromarray(grab(P(src), t, 216, 384)); b = io.BytesIO(); im.save(b, "JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
_c = lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False)
PREV = json.load(open(a.prev))["timeline"] if a.prev else None
def changed(i, it): return PREV is not None and (i >= len(PREV) or _c(PREV[i]) != _c(it))
def fmt(x): return f"{int(x // 60)}:{x % 60:04.1f}"
cards, strip, t = [], [], 0.0
for i, it in enumerate(spec["timeline"]):
    kind = it.get("type", "clip"); n = f"{i + 1:02d}"
    if kind == "clip":
        a0, b0, k = float(it["in"]), float(it["out"]), float(it.get("speed", spec.get("speed", 1.0))); dur = (b0 - a0) / k
        line = " ".join(c["text"] for c in it.get("captions", [])) or "（無口白）"
        th = [thumb(it["src"], a0 + (b0 - a0) * f) for f in ((0.5,) if dur < 2.5 else (0.25, 0.75))]
        acts = []
        for bw in it.get("bigwords", []): acts.append(f"巨字「{bw['word']}」逐字打出" + ("，放在頭頂上方、頭部壓在字前" if bw.get("place", "auto") != "low" else "，放畫面下方"))
        for pr in it.get("prompts", []): acts.append(f"指令框打出「{pr['text']}」，按下送出 ✓")
        if it.get("cta"): acts.append(f"留言卡片滑入，逐字打出 {it['cta'].get('keyword', 'EDIT')}，愛心＋作者回覆「{it['cta'].get('reply', '')}」")
        if it.get("push"): acts.append(f"畫面緩慢推近 {float(it['push']) * 100:.1f}%")
        if k != 1: acts.append(f"語速 {k:g}×")
        if it.get("captions"): acts.append("卡拉 OK 字幕逐字亮起（墨色字卡、橘色重點字）")
        shot = it.get("shot", "特寫"); trans = it.get("transition", "甩鏡模糊轉場" if it.get("whip_in") else "接續")
    elif kind == "cover":
        dur = float(it.get("dur", 1.4)); line = "（封面開場）"; th = [thumb(it["src"], float(it.get("at", 0)))]
        acts = [f"雜誌封面：刊頭「{it.get('masthead', '黑牛')}」藏在頭後", "封面標題：" + "".join(it.get("headline", [])), "最後快速甩鏡進入開場句"]
        shot, trans = "封面・冷開場", "暗場亮起"
    else:
        dur = float(it.get("dur", 2.625)); line = "（前後對比）"; th = [thumb(it["src"], float(it.get("at", 0)))]
        acts = [f"斜線由左往右慢慢掃過：左「{it.get('label_after', 'AI 調色')}」右「{it.get('label_before', '原始')}」"]
        shot, trans = "定格・前後對比", "定格"
    acts += it.get("notes", [])
    strip.append(f'<a class="seg" href="#b{n}" style="flex:{dur:.2f}" title="{n}"><span>{n}</span></a>')
    figs = "".join(f'<figure><img src="{s}" alt="第 {n} 拍畫面" width="108" height="192"></figure>' for s in th)
    keys = "、".join(k_ for c in it.get("captions", []) for k_ in c.get("keys", [])) or "—"
    ch = changed(i, it)
    cards.append(f'''<article class="beat{' changed' if ch else ''}" id="b{n}">
  <div class="thumbs">{figs}</div>
  <div class="info">
    <div class="meta"><span class="num">{n}</span><span>{fmt(t)}–{fmt(t + dur)}</span><span>{dur:.1f}s</span><span class="shot">{html.escape(shot)}</span>{'<span class="badge">已修改</span>' if ch else ''}</div>
    <blockquote>「{html.escape(line)}」</blockquote>
    <ul>{"".join(f"<li>{html.escape(x)}</li>" for x in acts)}</ul>
    <dl><dt>EMPHASIS</dt><dd>{html.escape(keys)}</dd><dt>TRANSITION</dt><dd>{html.escape(trans)}</dd><dt>SOUND</dt><dd>{html.escape(it.get("sound", "自動配音效"))}</dd></dl>
    <label class="note" for="note-{n}">一句話修改</label>
    <textarea id="note-{n}" data-beat="{n}" rows="2" placeholder="例如：這拍字幕再大一點"></textarea>
  </div>
</article>''')
    t += dur
tpl = open(os.path.join(ASSETS, "storyboard_template.html")).read()
brand = spec.get("style", {}).get("brand", "黑牛")
out = (tpl.replace("{{TITLE}}", f"{brand} AI 剪輯分鏡").replace("{{PATH}}", spec.get("name", "edit")).replace("{{VER}}", str(a.version))
          .replace("{{COUNT}}", str(len(cards))).replace("{{DUR}}", f"{t:.1f}").replace("{{MID}}", fmt(t / 2)).replace("{{END}}", fmt(t))
          .replace("{{KEY}}", f"hn-sb-{spec.get('name', 'edit')}-v{a.version}").replace("{{STRIP}}", "".join(strip)).replace("{{CARDS}}", "\n".join(cards)))
dst = a.out or os.path.join(D, "storyboard.html"); open(dst, "w").write(out); print("→", dst, f"{len(out) // 1024} KB, {len(cards)} beats, {t:.1f}s")
