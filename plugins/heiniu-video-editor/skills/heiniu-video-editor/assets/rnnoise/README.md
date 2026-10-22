RNNoise model "somnolent-hogwash" (recording noise / speech) from https://github.com/GregorR/rnnoise-models — the model
files are not creative work and not subject to copyright, per that repository. It is plain text, split into parts under
256 KiB (`sh.rnnn.part1`, `sh.rnnn.part2`, …) so every file can be read and checked; render.py joins them into one
`sh.rnnn` in its work folder and passes that to ffmpeg's `arnndn` filter for voice clean-up.
