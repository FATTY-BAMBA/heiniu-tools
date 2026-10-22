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
    f = block.get("finish") or {}
    if f:
        msg = []
        if "multicam" in f: spec["multicam"] = bool(f["multicam"]); msg.append("雙機位" + ("開" if f["multicam"] else "關"))
        if "teaser" in f:
            if f["teaser"]:
                if spec.get("teaser") is False: spec.pop("teaser")
                if spec.get("_teaser_off"): spec["teaser"] = spec.pop("_teaser_off")
                if not any(it.get("teaser") for it in spec["timeline"]) and not spec.get("teaser"): spec["teaser"] = True
            else:
                if isinstance(spec.get("teaser"), dict): spec["_teaser_off"] = spec["teaser"]
                spec["teaser"] = False
            msg.append("先看結果開頭" + ("開" if f["teaser"] else "關"))
        if "teaser_tr" in f and f["teaser_tr"] in ("vhs", "rewind", "whip", "card"):
            t_ = spec.get("teaser") if isinstance(spec.get("teaser"), dict) else ({} if spec.get("teaser") else None)
            if t_ is not None: t_["transition"] = f["teaser_tr"]; spec["teaser"] = t_
            msg.append("倒回開頭的方式：" + {"vhs": "VHS 倒帶", "rewind": "快速倒轉", "whip": "甩鏡", "card": "字卡"}[f["teaser_tr"]])
        if "ending" in f:
            e_ = f["ending"]
            if e_ in ("loop", "off") and spec.get("rewind"): spec["_rewind_off"] = spec.pop("rewind")
            if e_ == "rewind": spec["rewind"] = spec.pop("_rewind_off", None) or {"text": "再看一次"}
            spec["loop"] = e_ != "off"; msg.append({"loop": "結尾無縫接回開頭", "rewind": "結尾 VHS 倒帶", "off": "結尾不循環"}.get(e_, e_))
        if "kit" in f and f["kit"] in ("cinematic", "punchy", "subtle"): spec["sfx_kit"] = f["kit"]; msg.append("音效 " + {"cinematic": "電影感", "punchy": "俐落", "subtle": "安靜"}[f["kit"]])
        if "signature" in f:
            if f["signature"] and spec.get("_signature_off"): spec["signature"] = spec.pop("_signature_off")
            elif not f["signature"] and spec.get("signature"): spec["_signature_off"] = spec.pop("signature")
            msg.append("簽名" + ("開" if f["signature"] else "關"))
        if "credit" in f: spec["credit"] = bool(f["credit"]); msg.append("黑牛 AI 標記" + ("開" if f["credit"] else "關"))
        if msg: out[-1] = "成片質感：" + "、".join(msg)
    return spec, out, cut

def extract(text):
    m = re.search(r"<!--room-json\s*(\{.*?\})\s*-->", text, re.S); return json.loads(m.group(1)) if m else json.loads(text)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--json"); ap.add_argument("--file"); a = ap.parse_args()
    raw = a.json if a.json else open(a.file).read()
    spec = json.load(open(a.spec)); spec, out, cut = apply(spec, extract(raw))
    json.dump(spec, open(a.spec, "w"), ensure_ascii=False, indent=1)
    if cut: print(f"⚠ 刪掉了第 {', '.join(str(i + 1) for i in sorted(cut))} 拍：後面的拍號往前移，--change 用新的拍號")
    for k, v in sorted(out.items()): print(("--change \"%d=%s\"" % (k, v)) if k > 0 else v)
    if not out: print("（沒有直接修改）")
