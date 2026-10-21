"""Demo reel for the style templates: the same opening in every style, one after another, each with a style label,
then a grid of all of them with 「你選哪一個？留言 1–N」. Called by `template.py edit.json --reel`."""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hn_common import F, hex2rgb                                                   # noqa: E402
from PIL import Image, ImageDraw, ImageFilter                                     # noqa: E402

W, H = 1080, 1920
def chip(i, n, name, accent, path):
    """compact one-line label on the right, below the style's own header line: [2/5] 知識乾貨"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fb, fn = F("mono", 30), F("sans", 44); lab = f"{i}/{n}"
    bw = d.textlength(lab, font=fb) + 30; w = bw + d.textlength(name, font=fn) + 54; x1, y0, h = W - 56, 318, 88; x0 = x1 - w
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + 10, x1, y0 + h + 10], 44, fill=(0, 0, 0, 110))
    im = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), im); d = ImageDraw.Draw(im)
    d.rounded_rectangle([x0, y0, x1, y0 + h], 44, fill=(20, 20, 22, 230), outline=(255, 255, 255, 40), width=2)
    d.rounded_rectangle([x0 + 12, y0 + 12, x0 + 12 + bw, y0 + h - 12], 32, fill=hex2rgb(accent) + (255,))
    d.text((x0 + 12 + bw / 2, y0 + h / 2), lab, font=fb, fill=(20, 20, 22, 255), anchor="mm")
    d.text((x0 + 12 + bw + 20, y0 + h / 2), name, font=fn, fill=(243, 238, 228, 255), anchor="lm")
    im.save(path)
COLS, CW, CH = 3, 360, 640                                                      # 2 rows of 3 styles + a question band
def grid_card(meta, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); n = len(meta)
    for k, m in enumerate(meta):
        x, y = (k % COLS) * CW, (k // COLS) * CH
        d.rounded_rectangle([x + 16, y + 16, x + 84, y + 84], 18, fill=hex2rgb(m["accent"]) + (255,))
        d.text((x + 50, y + 50), str(k + 1), font=F("mono", 44), fill=(20, 20, 22, 255), anchor="mm")
        fw = d.textlength(m["name"], font=F("sans", 34))
        d.rounded_rectangle([x + 16, y + CH - 78, x + 40 + fw, y + CH - 22], 12, fill=(20, 20, 22, 225))
        d.text((x + 28, y + CH - 50), m["name"], font=F("sans", 34), fill=(243, 238, 228, 255), anchor="lm")
    y = ((n + COLS - 1) // COLS) * CH
    d.rectangle([0, y, W, H], fill=(20, 20, 22, 255))
    d.text((W / 2, y + 200), "同一支影片，你選哪一個？", font=F("serif", 72), fill=(243, 238, 228, 255), anchor="mm")
    d.text((W / 2, y + 320), f"留言 1–{n}", font=F("serif", 84), fill=(255, 106, 26, 255), anchor="mm")
    d.text((W / 2, y + 440), "全部都是 AI 剪的 · 我一秒都沒剪", font=F("sans", 34), fill=(170, 165, 156, 255), anchor="mm")
    im.save(path)
def build(meta, out, wd):
    wd, out = os.path.abspath(wd), os.path.abspath(out)
    parts = []
    for i, m in enumerate(meta, 1):
        png = os.path.join(wd, f"chip_{m['id']}.png"); chip(i, len(meta), m["name"], m["accent"], png); p = os.path.join(wd, f"part_{i}.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", m["file"], "-loop", "1", "-i", png, "-filter_complex",
                        "[0:v]scale=1080:1920,setsar=1[b];[1:v]format=rgba,fade=t=in:st=0:d=0.15:alpha=1[c];[b][c]overlay=0:0:shortest=1,format=yuv420p[v]",
                        "-map", "[v]", "-map", "0:a", "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", p], check=True)
        parts.append(p)
    gpng = os.path.join(wd, "grid.png"); grid_card(meta, gpng); g = os.path.join(wd, "part_grid.mp4"); n = len(meta)
    ins = sum([["-i", m["file"]] for m in meta], []) + ["-i", gpng]
    fc = "".join(f"[{k}:v]scale={CW}:{CH},setsar=1,trim=0:3.5,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=3.5[g{k}];" for k in range(n))
    fc += f"color=c=0x141416:s=1080x1920:d=3.5[bg];" + "".join(f"[{'bg' if k == 0 else f'o{k - 1}'}][g{k}]overlay={(k % COLS) * CW}:{(k // COLS) * CH}[o{k}];" for k in range(n))
    fc += f"[{n}:v]format=rgba[gc];[o{n - 1}][gc]overlay=0:0,trim=0:3.5,format=yuv420p[v];anullsrc=r=48000:cl=stereo,atrim=0:3.5[a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-crf", "18",
                    "-preset", "fast", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", g], check=True)
    parts.append(g); lst = os.path.join(wd, "reel.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-crf", "19", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)
    print("→", out)
