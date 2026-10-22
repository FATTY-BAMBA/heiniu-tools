"""App-style UI cards — the graphics that make a tool demo look like a real product.

A clip's `ui` list holds cards that slide in at the top of the frame (above the head, under the Reels top bar):
  {kind: "file",    start, end?, files: [{name, meta, badge?, thumb?: {src, t} | "image.png"}]}
        a file chip per take — thumbnail, badge (PHONE / 4K CAMERA), file name, "1080×1920 · 1:06 · 136 MB"
  {kind: "steps",   start, end?, file?: {name, meta, thumb?}, items: [{text, at}]}
        the pipeline as a checklist: each item ticks at its word, the current one spins, a counter n/N and a bar fill
  {kind: "install", start, end?, name, sub?, icon?: "icon.png", button?: "Install", done?: "Installed", click_at}
        an app card; a cursor glides in and clicks the button at `click_at`, the button fills and turns to ✓
Common: `x`: "left" | "center" (default) | "right", `top` (1080×1920 units, default 230), `width` (default 700).
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from hn_common import F, eq, spring, shadow, to_np, grab

CARD = (247, 243, 234); LINE = (226, 219, 205); MUTED = (138, 130, 116); INKT = (26, 26, 28)

class UI:
    def __init__(self, W, H, S, P, src_path, cache):
        self.W, self.H, self.S, self.P, self.src_path, self.cache = W, H, S, P, src_path, cache; self.default_thumb = None
        self.top_default = 230                                              # render.py moves it below a style's header line
    # ---------- helpers ----------
    def geom(self, c, h):
        S, W = self.S, self.W; w = S(c.get("width", 700)); y = S(c.get("top", self.top_default))
        x = {"left": S(56), "right": W - S(56) - w}.get(c.get("x", "center"), (W - w) // 2)
        return x, y, w, h
    def thumb(self, spec, w, h):
        key = ("uithumb", str(spec), w, h)
        if key not in self.cache:
            try:
                if isinstance(spec, str): im = Image.open(self.src_path(spec)).convert("RGB")
                else: im = Image.fromarray(grab(self.src_path(spec["src"]), float(spec.get("t", 0.5)), 540, 960))
                sc = max(w / im.width, h / im.height); im = im.resize((int(im.width * sc) + 1, int(im.height * sc) + 1), Image.LANCZOS)
                im = im.crop(((im.width - w) // 2, (im.height - h) // 2, (im.width - w) // 2 + w, (im.height - h) // 2 + h))
            except Exception: im = Image.new("RGB", (w, h), (60, 60, 64))
            m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], self.S(12), fill=255)
            out = Image.new("RGBA", (w, h)); out.paste(im, (0, 0), m); self.cache[key] = out
        return self.cache[key]
    def card(self, w, h, r=None):
        """ivory card with a soft drop shadow, as an RGBA image (cached)"""
        S = self.S; r = r or S(30); key = ("uicard", w, h, r)
        if key not in self.cache:
            pad = S(40); im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.rounded_rectangle([pad, pad, pad + w, pad + h], r, fill=CARD + (252,), outline=(255, 255, 255, 200), width=max(1, S(2)))
            self.cache[key] = (shadow(im, (0, S(14)), S(22), 0.42), pad)
        return self.cache[key]
    def place(self, comp, im, x, y, a=1.0, sc=1.0, rects=None, name="卡片"):
        if sc != 1.0: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
        if a < 0.999: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        W, H = self.W, self.H; x, y = int(x), int(y); x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + im.width), min(H, y + im.height)
        if x1 <= x0 or y1 <= y0: return comp
        arr = np.asarray(im.crop((x0 - x, y0 - y, x1 - x, y1 - y)), np.float32) / 255; al = arr[..., 3:4]
        out = comp.copy(); out[y0:y1, x0:x1] = comp[y0:y1, x0:x1] * (1 - al) + arr[..., :3] * al
        if rects is not None: rects.append((name, x0 + self.S(30), y0 + self.S(30), x1 - self.S(30), y1 - self.S(30)))
        return out
    def envelope(self, t, t0, t1, has_end):
        """entrance (drop + spring) and exit (lift + fade) progress"""
        u = eq(min(1, (t - t0) / 0.42)); sc = 0.94 + 0.06 * spring(min(1, (t - t0) / 0.5)); dy = (1 - u) * -self.S(46); a = min(1, (t - t0) / 0.16)
        if has_end and t > t1 - 0.25: q = eq((t - (t1 - 0.25)) / 0.25); a *= 1 - q; dy -= q * self.S(30)
        return a, sc, dy
    # ---------- file chip(s) ----------
    def file_row(self, d, im, f, x, y, w, S):
        th_w, th_h = S(84), S(112); th = f.get("thumb") or self.default_thumb
        im.alpha_composite(self.thumb(th, th_w, th_h) if th else Image.new("RGBA", (th_w, th_h), (70, 70, 76, 255)), (x, y))
        tx = x + th_w + S(26); ty = y + S(6)
        if f.get("badge"):
            fb = F("mono", S(20)); bw = d.textlength(f["badge"], font=fb) + S(22)
            d.rounded_rectangle([tx, ty, tx + bw, ty + S(34)], S(8), fill=INKT); d.text((tx + S(11), ty + S(17)), f["badge"], font=fb, fill=(243, 238, 228), anchor="lm"); ty += S(44)
        d.text((tx, ty), f.get("name", "IMG_0001.MOV"), font=F("mono", S(40)), fill=INKT); ty += S(52)
        d.text((tx, ty), f.get("meta", ""), font=F("mono", S(24)), fill=MUTED)
    def draw_file(self, comp, t, c, t0, t1, has_end, rects):
        S = self.S; files = c.get("files") or [c]; rh = S(148); n = len(files)
        out = comp
        for k, f in enumerate(files):                                      # each take its own chip, staggered
            tk = t0 + k * 0.22
            if t < tk: continue
            w = S(c.get("width", 700)); h = rh; x, y, _, _ = self.geom(c, h); y += k * (h + S(18))
            key = ("uifile", id(c), k)
            if key not in self.cache:
                base, pad = self.card(w, h); im = base.copy(); d = ImageDraw.Draw(im); self.file_row(d, im, f, pad + S(20), pad + S(18), w, S); self.cache[key] = (im, pad)
            im, pad = self.cache[key]; a, sc, dy = self.envelope(t, tk, t1, has_end)
            out = self.place(out, im, x - pad, y - pad + dy, a, 1.0, rects, "檔案卡")
        return out
    # ---------- steps (pipeline checklist) ----------
    def draw_steps(self, comp, t, c, t0, t1, has_end, rects, to_out):
        S = self.S; items = c["items"]; n = len(items); w = S(c.get("width", 640)); head = S(132) if c.get("file") else S(92); rowh = S(54)
        h = head + rowh * n + S(26); x, y, _, _ = self.geom(dict(c, width=c.get("width", 640)), h)
        base, pad = self.card(w, h); im = base.copy(); d = ImageDraw.Draw(im); ox, oy = pad, pad
        ats = [to_out(it_["at"]) for it_ in items]; done = sum(1 for a_ in ats if t >= a_)
        if c.get("file"):
            f = c["file"]; tsp = f.get("thumb") or self.default_thumb; th = self.thumb(tsp, S(64), S(86)) if tsp else Image.new("RGBA", (S(64), S(86)), (70, 70, 76, 255))
            im.alpha_composite(th, (ox + S(26), oy + S(26))); d.text((ox + S(110), oy + S(34)), f.get("name", ""), font=F("mono", S(30)), fill=INKT)
            d.text((ox + S(110), oy + S(78)), f.get("meta", ""), font=F("mono", S(22)), fill=MUTED)
        else: d.text((ox + S(30), oy + S(30)), c.get("title", "AI 剪輯中"), font=F("sans", S(34)), fill=INKT)
        cnt = f"{done}/{n}"; fc = F("mono", S(46)); d.text((ox + w - S(30), oy + S(30)), cnt, font=fc, fill=INKT, anchor="ra")
        by = oy + head - S(22); prog = done / n
        if done < n and t >= t0:                                           # the bar creeps toward the next tick
            nxt = ats[done]; prv = ats[done - 1] if done else t0; prog += min(1, max(0, (t - prv) / max(0.2, nxt - prv))) * 0.8 / n
        d.rounded_rectangle([ox + S(30), by, ox + w - S(30), by + S(8)], S(4), fill=LINE)
        d.rounded_rectangle([ox + S(30), by, ox + S(30) + (w - S(60)) * min(1, prog), by + S(8)], S(4), fill=tuple(self.P["accent"]))
        for k, it_ in enumerate(items):
            cy = oy + head + S(10) + rowh * k + rowh // 2; cx = ox + S(46); ta = ats[k]; r = S(15)
            if t >= ta:
                q = spring(min(1, (t - ta) / 0.3)); rr = r * (0.6 + 0.4 * q)
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=tuple(self.P["accent"]))
                d.line([(cx - S(8), cy), (cx - S(2), cy + S(7)), (cx + S(9), cy - S(7))], fill=(255, 255, 255), width=max(2, S(4)))
                col = INKT
            elif k == done:                                                # the step being worked on spins
                ang = (t * 360 * 1.6) % 360; d.arc([cx - r, cy - r, cx + r, cy + r], ang, ang + 270, fill=tuple(self.P["accent"]), width=max(2, S(4))); col = INKT
            else: d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LINE, width=max(2, S(3))); col = MUTED
            d.text((cx + S(34), cy), it_["text"], font=F("sans", S(31)), fill=col, anchor="lm")
        a, sc, dy = self.envelope(t, t0, t1, has_end)
        return self.place(comp, im, x - pad, y - pad + dy, a, 1.0, rects, "步驟卡")
    # ---------- install card + cursor ----------
    def icon(self, c, sz):
        key = ("uiicon", c.get("icon"), sz)
        if key not in self.cache:
            try: im = Image.open(self.src_path(c["icon"])).convert("RGBA").resize((sz, sz), Image.LANCZOS)
            except Exception:
                im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.rounded_rectangle([0, 0, sz - 1, sz - 1], sz // 4, fill=INKT)
                d.polygon([(sz * 0.4, sz * 0.3), (sz * 0.72, sz * 0.5), (sz * 0.4, sz * 0.7)], fill=tuple(self.P["accent"]))
            m = Image.new("L", (sz, sz), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, sz - 1, sz - 1], sz // 4, fill=255)
            out = Image.new("RGBA", (sz, sz)); out.paste(im, (0, 0), m); self.cache[key] = out
        return self.cache[key]
    def cursor(self, sz):
        key = ("uicursor", sz)
        if key not in self.cache:
            s = sz / 24; pts = [(0, 0), (0, 17), (4.2, 13.2), (7, 19.5), (9.6, 18.4), (6.9, 12.2), (12.4, 12.2)]
            im = Image.new("RGBA", (int(sz * 0.8), sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im); P_ = [(1 + x * s, 1 + y * s) for x, y in pts]
            d.polygon(P_, fill=(255, 255, 255, 255)); d.line(P_ + [P_[0]], fill=(10, 10, 12, 255), width=max(2, int(s * 1.3)), joint="curve")
            self.cache[key] = shadow(im, (self.S(3), self.S(5)), self.S(5), 0.45)
        return self.cache[key]
    def draw_install(self, comp, t, c, t0, t1, has_end, rects, to_out, events=None):
        S = self.S; w = S(c.get("width", 700)); h = S(250); x, y, _, _ = self.geom(c, h); tc = to_out(c["click_at"]); dur = 0.55
        base, pad = self.card(w, h); im = base.copy(); d = ImageDraw.Draw(im); ox, oy = pad, pad
        im.alpha_composite(self.icon(c, S(88)), (ox + S(30), oy + S(28)))
        d.text((ox + S(140), oy + S(36)), c.get("name", "黑牛 AI 剪輯"), font=F("sans", S(40)), fill=INKT)
        d.text((ox + S(140), oy + S(90)), c.get("sub", "Claude 外掛"), font=F("sans_m", S(26)), fill=MUTED)
        bx0, by0, bx1, by1 = ox + S(30), oy + S(148), ox + w - S(30), oy + S(222); press = 1.0
        if tc <= t < tc + 0.1: press = 0.96
        cxm, cym = (bx0 + bx1) / 2, (by0 + by1) / 2; hw, hh = (bx1 - bx0) / 2 * press, (by1 - by0) / 2 * press
        fill = INKT; label = c.get("button", "Install"); txtc = (243, 238, 228)
        if t >= tc:
            q = min(1, (t - tc) / dur)
            d.rounded_rectangle([cxm - hw, cym - hh, cxm + hw, cym + hh], S(37), fill=INKT)
            if q < 1:
                d.rounded_rectangle([cxm - hw, cym - hh, cxm - hw + 2 * hw * smoothq(q), cym + hh], S(37), fill=tuple(self.P["accent"])); label = c.get("busy", "安裝中…")
            else:
                d.rounded_rectangle([cxm - hw, cym - hh, cxm + hw, cym + hh], S(37), fill=tuple(self.P["accent"])); label = "✓ " + c.get("done", "Installed"); txtc = (255, 255, 255)
        else: d.rounded_rectangle([cxm - hw, cym - hh, cxm + hw, cym + hh], S(37), fill=fill)
        fl = F("sans", S(36)); d.text((cxm, cym), label, font=fl, fill=txtc, anchor="mm")
        if tc <= t < tc + 0.45:                                            # click ripple
            q = (t - tc) / 0.45; rr = S(20) + S(90) * eq(q)
            d.ellipse([cxm + S(40) - rr, cym + S(10) - rr, cxm + S(40) + rr, cym + S(10) + rr], outline=tuple(self.P["accent"]) + (int(200 * (1 - q)),), width=max(2, S(5)))
        a, sc, dy = self.envelope(t, t0, t1, has_end)
        comp = self.place(comp, im, x - pad, y - pad + dy, a, 1.0, rects, "安裝卡")
        # the cursor: glides in from the lower right along a curve, lands on the button just before the click, then rests
        ta = tc - 0.75
        if t >= ta and a > 0.05:
            px1, py1 = x + (cxm - pad) + S(40), y + (cym - pad) + S(10) + dy
            px0, py0 = self.W + S(40), y + h + S(380)
            q = eq(min(1, (t - ta) / 0.7)); mx, my = (px0 + px1) / 2 + S(120), (py0 + py1) / 2 + S(60)
            cx_ = (1 - q) ** 2 * px0 + 2 * (1 - q) * q * mx + q * q * px1; cy_ = (1 - q) ** 2 * py0 + 2 * (1 - q) * q * my + q * q * py1
            s = 0.86 if tc <= t < tc + 0.12 else 1.0
            comp = self.place(comp, self.cursor(S(64)), cx_, cy_, a, s)
        return comp
    # ---------- entry ----------
    def draw(self, comp, t, cards, s, to_out, seg_end, rects, src=None, src_t=0.5):
        self.default_thumb = {"src": src, "t": src_t} if src else None
        for c in cards:
            t0 = to_out(c["start"]); has_end = "end" in c; t1 = to_out(c["end"]) if has_end else seg_end
            if not (t0 <= t < t1): continue
            k = c.get("kind", "file")
            if k == "file": comp = self.draw_file(comp, t, c, t0, t1, has_end, rects)
            elif k == "steps": comp = self.draw_steps(comp, t, c, t0, t1, has_end, rects, to_out)
            elif k == "install": comp = self.draw_install(comp, t, c, t0, t1, has_end, rects, to_out)
        return comp
    @staticmethod
    def sfx(cards, to_out):
        ev = []
        for c in cards:
            k = c.get("kind", "file"); t0 = to_out(c["start"]); ev.append((t0, "swish", 0.55))
            if k == "file": ev += [(t0 + 0.22 * i + 0.05, "pop", 0.6) for i in range(len(c.get("files") or [c]))]
            if k == "steps": ev += [(to_out(it_["at"]), "tick", 0.9) for it_ in c["items"]]
            if k == "install": tc = to_out(c["click_at"]); ev += [(tc, "click", 1.0), (tc + 0.02, "tick", 0.7), (tc + 0.57, "pop", 0.8)]
        return ev

def smoothq(p): p = min(max(p, 0.0), 1.0); return p * p * (3 - 2 * p)
