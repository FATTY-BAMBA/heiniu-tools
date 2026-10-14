"""Match one segment's brightness and colour to a reference shot so a different recording doesn't jump at the cut.
usage: python3 colormatch.py SEG.mov REF_SOURCE REF_TIME OUT.mov
Mean match in Lab (fixed parameters for the whole clip → no flicker), with slightly softer contrast/chroma."""
import sys, subprocess, numpy as np, cv2
sys.path.insert(0, __import__("os").path.dirname(__file__)); from hn_common import grab, probe
seg, refsrc, reft, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
st = [s for s in probe(seg)["streams"] if s["codec_type"] == "video"][0]; W, H = int(st["width"]), int(st["height"])
num, den = map(int, st["r_frame_rate"].split("/")); fps = num / den
lab = lambda im: cv2.cvtColor(im, cv2.COLOR_RGB2LAB).astype(np.float32)
y0, y1 = int(H * 0.13), int(H * 0.88)
ref = lab(grab(refsrc, reft, W, H))[y0:y1].reshape(-1, 3)
dur = float(probe(seg)["format"]["duration"]); samp = np.concatenate([lab(grab(seg, t, W, H, "null"))[y0:y1].reshape(-1, 3) for t in np.linspace(0.2, max(0.3, dur - 0.2), 5)])
mr, ms = ref.mean(0), samp.mean(0); SC = np.array([0.94, 0.90, 0.90], np.float32); K = 0.8
print("colormatch: source Lab", ms.round(1), "→ reference", mr.round(1))
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", seg, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-", "-i", seg,
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "copy", out], stdin=subprocess.PIPE)
while True:
    b = dec.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    x = lab(np.frombuffer(b, np.uint8).reshape(H, W, 3)); y = x * (1 - K) + ((x - ms) * SC + mr) * K
    enc.stdin.write(cv2.cvtColor(np.clip(y, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).tobytes())
enc.stdin.close(); enc.wait()
