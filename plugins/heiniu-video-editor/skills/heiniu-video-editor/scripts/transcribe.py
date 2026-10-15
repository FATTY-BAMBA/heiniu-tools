"""Word-level transcript for one or more takes (Mandarin/English/Cantonese/Japanese/Korean).

usage:  python3 transcribe.py take1.mov take2.mov ... [--out words.json] [--lang zh|en|auto]
        python3 transcribe.py take1.mov --srt take1.srt      # no ASR available: use an SRT the user exported

Prints one line per phrase with source timestamps, e.g.
  take1.mov  [0.46 – 1.38]  這支影片
and writes words.json: [{file, phrases:[{text, start, end, chars:[[ch, t], ...]}]}]
Engine: sherpa-onnx SenseVoice (downloaded once to ~/.cache/heiniu). Output is converted to Traditional Chinese (Taiwan) when opencc is installed.
"""
import sys, os, json, re, argparse, subprocess, tarfile, urllib.request
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--out", default="words.json")
ap.add_argument("--lang", default="auto"); ap.add_argument("--srt"); ap.add_argument("--gap", type=float, default=0.38)
a = ap.parse_args()
CACHE = os.environ.get("HN_MODELS", os.path.expanduser("~/.cache/heiniu"))
MODEL = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
URL = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{MODEL}.tar.bz2"
try:
    import opencc; CC = opencc.OpenCC("s2twp")
    def tw(s): return CC.convert(s)
except Exception:
    def tw(s): return s
PUNCT = set("，。！？、,.!?；;：:")

def srt_phrases(path):
    txt = open(path, encoding="utf-8-sig").read(); out = []
    for blk in re.split(r"\n\s*\n", txt.strip()):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", blk)
        if not m: continue
        g = list(map(int, m.groups())); s = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000; e = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = tw(" ".join(l for l in blk.splitlines()[2:] if l.strip()).strip()); chars = [c for c in text if not c.isspace()]
        out.append(dict(text=text, start=round(s, 3), end=round(e, 3),
                        chars=[[c, round(s + (e - s) * i / max(1, len(chars)), 3)] for i, c in enumerate(chars)]))
    return out

def recognizer():
    import sherpa_onnx
    d = os.path.join(CACHE, MODEL)
    if not os.path.exists(os.path.join(d, "model.int8.onnx")):
        os.makedirs(CACHE, exist_ok=True); tb = os.path.join(CACHE, MODEL + ".tar.bz2")
        print("[asr] downloading SenseVoice model (~230 MB, once)…", flush=True); urllib.request.urlretrieve(URL, tb)
        with tarfile.open(tb) as t: t.extractall(CACHE)
        os.remove(tb)
    return sherpa_onnx.OfflineRecognizer.from_sense_voice(model=f"{d}/model.int8.onnx", tokens=f"{d}/tokens.txt",
                                                          language="" if a.lang == "auto" else a.lang, use_itn=True)
def asr_phrases(rec, path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    # decode in ~25 s windows cut at quiet points so long takes keep accurate timestamps
    win, out, i = 16000 * 25, [], 0
    while i < len(x):
        j = min(len(x), i + win)
        if j < len(x):
            e = np.convolve(np.abs(x[j - 16000 * 3:j]), np.ones(1600) / 1600, "same"); j = j - 16000 * 3 + int(np.argmin(e))
        s = rec.create_stream(); s.accept_waveform(16000, x[i:j]); rec.decode_stream(s); r = s.result
        toks = [(tw(tk), i / 16000 + ts) for tk, ts in zip(r.tokens, r.timestamps)]
        cur = []
        for k, (tk, ts) in enumerate(toks):
            gap = ts - toks[k - 1][1] if k else 0
            if cur and (gap > a.gap or cur[-1][0] in PUNCT):
                out.append(cur); cur = []
            cur.append((tk, ts))
        if cur: out.append(cur)
        i = j
    phrases = []
    for p in out:
        chars = [[c, round(t, 3)] for c, t in p if c not in PUNCT and c.strip()]
        if not chars: continue
        text = "".join(c for c, _ in p).strip("，。、, ")
        phrases.append(dict(text=text, start=chars[0][1], end=round(p[-1][1] + 0.24, 3), chars=chars))
    return phrases

res = []
if a.srt:
    res.append(dict(file=a.files[0], phrases=srt_phrases(a.srt)))
else:
    try: rec = recognizer()
    except Exception as e:
        sys.exit(f"[asr] speech recognition unavailable ({e}).\nAsk the user for an .srt (CapCut / phone auto-captions export) and rerun with --srt.")
    for f in a.files: res.append(dict(file=f, phrases=asr_phrases(rec, f)))
for r in res:
    for p in r["phrases"]: print(f"{os.path.basename(r['file'])}  [{p['start']:6.2f} – {p['end']:6.2f}]  {p['text']}")
json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1); print("→", a.out)
