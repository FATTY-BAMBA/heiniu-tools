"""Apply the review room's DIRECT edits (caption text typed in, effects switched off, beats cut, caption size / position)
exactly as the person made them — no interpretation, so a typo fix never becomes a different edit.

The room's send message ends with a block like
  <!--room-json {"v": 2, "edits": [{"beat": 2, "caps": {"0": "少了幾千塊"}, "off": ["punch"], "cut": false}], "global": {"scale": 1.1, "dy": -40}}-->
usage:
  python3 room_apply.py edit.json --json '<the {...} inside room-json>'      (or --file block.json)
prints one line per beat for storyboard.py --change, and leaves free-text notes to you.
"""
import sys, os, json, argparse, re

LABEL = {"bigwords": "巨字", "prompts": "指令框", "punch": "推近", "bubbles": "對話泡泡", "checklist": "清單", "phone": "手機畫面", "headlines": "標題牆",
         "chart": "長條圖", "bg": "換背景", "sticker": "貼紙", "framebreak": "出框", "doodle": "手繪描邊", "pullback": "拉開", "zoom_in": "穿越轉場",
         "whip_in": "甩鏡轉場", "push": "慢推", "cta": "留言結尾", "ramp": "加速", "ui": "介面卡片"}
FX = list(LABEL)

def apply(spec, block):
    tl = spec["timeline"]; out = {}; cut = []
    for e in block.get("edits", []):
        i = int(e["beat"]) - 1
        if not (0 <= i < len(tl)): continue
        it = tl[i]; done = []
        for k, txt in (e.get("caps") or {}).items():
            caps = it.get("captions", []); j = int(k)
            if j < len(caps) and isinstance(txt, str) and txt.strip() and txt.strip() != caps[j]["text"]:
                old = caps[j]["text"]; caps[j]["text"] = txt.strip()
                caps[j]["keys"] = [kw for kw in caps[j].get("keys", []) if kw in caps[j]["text"]]
                done.append(f"字幕「{old}」→「{caps[j]['text']}」")
        for key in e.get("off") or []:
            if key in it and key in FX:
                it.setdefault("_off_room", {})[key] = it.pop(key); done.append(f"拿掉{LABEL[key]}")
        if e.get("cut"): cut.append(i); done.append("整拍刪掉")
        if done: out[i + 1] = "；".join(done)
    for i in sorted(cut, reverse=True): tl.pop(i)
    out = {(k - sum(1 for c in cut if c < k - 1)): v for k, v in out.items() if k - 1 not in cut}     # beat numbers after the cuts
    g = block.get("global") or {}
    if g:
        cs = dict(spec.get("captions_style") or {}); msg = []
        if "scale" in g: cs["scale"] = round(max(0.7, min(1.5, float(g["scale"]))), 2); msg.append(f"字幕大小 ×{cs['scale']:g}")
        if "dy" in g: cs["dy"] = int(max(-300, min(200, float(g["dy"])))); msg.append(("字幕往上" if cs["dy"] < 0 else "字幕往下") + f" {abs(cs['dy'])}")
        spec["captions_style"] = cs
        if msg: out[0] = "全片：" + "、".join(msg)
    return spec, out, cut

def extract(text):
    m = re.search(r"<!--room-json\s*(\{.*?\})\s*-->", text, re.S); return json.loads(m.group(1)) if m else json.loads(text)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--json"); ap.add_argument("--file"); a = ap.parse_args()
    raw = a.json if a.json else open(a.file).read()
    spec = json.load(open(a.spec)); spec, out, cut = apply(spec, extract(raw))
    json.dump(spec, open(a.spec, "w"), ensure_ascii=False, indent=1)
    if cut: print(f"⚠ 刪掉了第 {', '.join(str(i + 1) for i in sorted(cut))} 拍：後面的拍號往前移，--change 用新的拍號")
    for k, v in sorted(out.items()): print(("--change \"%d=%s\"" % (k, v)) if k else v)
    if not out: print("（沒有直接修改）")
