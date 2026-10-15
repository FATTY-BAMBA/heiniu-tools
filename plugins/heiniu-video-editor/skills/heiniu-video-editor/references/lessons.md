# Lessons from the first real edit (read before changing the engine)

These came from a long round of real feedback; each one cost a re-render to discover.

**Lip-sync drift.** Cutting video to whole frames but audio to exact samples loses ~20 ms per cut; over 9–20 cuts the voice visibly trails the mouth by the end. The engine snaps every cut so each segment is an exact frame count, then nudges tempo so audio is exactly the same length (`keff`), and pads/trims audio per segment. If you write new segment code, keep that invariant: `video frames / fps == audio samples / 48000` for every segment, checked in `qa.json` (`av_gap_ms` must be < 40).

**loudnorm shifts timestamps.** ffmpeg's `loudnorm` can start its output at a non-zero PTS; `atrim` after it then silently drops audio. Always `asetpts=N/SR/TB` right after loudnorm/atempo.

**Freeze timing.** A freeze or before/after that interrupts a sentence feels broken. Put it after the sentence ends.

**Before/after must be slow.** Start on the full original, slide the line across over ~1.9 s with ease-in-out, rest briefly on the full result. Fast wipes are not perceived.

**Head-room.** Giant words above the head only work when there is ≥ ~250 px above the hair; otherwise use `place:"low"`. Captions sit at y≈1330 — below the chin, above the bottom UI zone.

**Platform safe zone.** Instagram Reels / TikTok draw the caption, username and audio over the bottom ~420 px and the like/comment/share buttons over the right ~150 px (y≈1000–1800), and their header over the top ~200 px. Keep text, cards and chips inside x 48–930, y 200–1500 (1080×1920 units). Captions at y≈1330 are fine.

**Typography.** Serif (Noto Serif TC Bold) for captions and big words reads premium; sans for UI. Ink box (26,26,28 @ ~200 alpha) with a faint white rim and an ember left bar — not a solid black or a copied colour from another creator.

**Text on busy clothing.** White/orange type over a plaid or white shirt disappears. Put type on a dark gradient scrim (cover) or on the ink card (captions/CTA).

**First frame.** Players and feeds use frame 0 as the thumbnail — never start on a white flash.

**Different recordings.** A take shot later in warmer light looks "high contrast" next to the others; mean-match its colour to the neighbouring clip instead of grading harder.

**Music.** Synthesised background music sounded cheap and was rejected. Use a real royalty-free track (ducked) or let the creator add a trending sound in the app.

**Memory.** Don't cache full-frame float layers without a bound — 1080×1920×4 float32 is 33 MB each.

**Honesty.** If the video claims "AI edited this", the workflow must actually be what produced it. Name the real tool.
