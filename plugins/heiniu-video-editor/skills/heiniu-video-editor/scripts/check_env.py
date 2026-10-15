"""Check what this machine can do and print the mode to use: FULL (everything) or LITE (no ASR / no person cut-out)."""
import shutil, importlib.util, subprocess, os, sys
ok = lambda m: importlib.util.find_spec(m) is not None
rows = [("ffmpeg", bool(shutil.which("ffmpeg"))), ("ffprobe", bool(shutil.which("ffprobe"))), ("fc-match (fonts)", bool(shutil.which("fc-match"))),
        ("numpy", ok("numpy")), ("opencv (cv2)", ok("cv2")), ("Pillow", ok("PIL")), ("soundfile", ok("soundfile")),
        ("sherpa_onnx (speech-to-text)", ok("sherpa_onnx")), ("onnxruntime (person cut-out)", ok("onnxruntime")), ("opencc (繁體轉換)", ok("opencc"))]
cjk = False
if shutil.which("fc-list"):
    cjk = "CJK" in subprocess.run(["fc-list", ":lang=zh-tw"], capture_output=True, text=True).stdout or "TC" in subprocess.run(["fc-list", ":lang=zh-tw"], capture_output=True, text=True).stdout
rows.append(("Traditional Chinese font", cjk))
for k, v in rows: print(f"  {'✓' if v else '✗'} {k}")
core = all(v for k, v in rows[:7]) and cjk
full = core and rows[7][1] and rows[8][1]
print("\nMODE:", "FULL" if full else ("LITE" if core else "MISSING-CORE"))
if not core:
    print("Install core:  apt-get install -y ffmpeg fonts-noto-cjk fontconfig && pip install numpy opencv-python-headless pillow soundfile")
if core and not full:
    print("Optional for FULL: pip install sherpa-onnx onnxruntime opencc-python-reimplemented  (models download on first use from GitHub)")
