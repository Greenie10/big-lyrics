# Larger, bolder Alto lyrics

`enlarge_alto_lyrics.py` saves a separate PDF with taller, darker Alto lyrics.
The original PDF is never overwritten. The notation, other voice parts, original
letter shapes, and horizontal syllable positions are preserved.

## Setup (once)

In Terminal, change to this folder, then run:

```sh
python3 -m venv .lyrics-venv
.lyrics-venv/bin/python -m pip install -r requirements.txt
```

## Use

Always start with the **original score**, not an already enlarged copy:

```sh
.lyrics-venv/bin/python enlarge_alto_lyrics.py "Santa Claus is Coming to Town.pdf"
```

This creates `Santa Claus is Coming to Town - Alto Lyrics Extra Large.pdf`.
The default makes letters **50% taller than the original** and thickens them.
It preserves their width to keep dense syllables from colliding or drifting
away from the notes. This is vertical enlargement, not a uniform font-size increase.
The top of each lyric line stays in place; extra height extends downwards.

For another score, replace the input filename. To change the enlargement:

```sh
.lyrics-venv/bin/python enlarge_alto_lyrics.py "another score.pdf" \
  --height 1.7 --weight 0.22 -o "another score - large alto lyrics.pdf"
```

- `--height`: 1 to 2, relative to the original; default 1.5.
- `--weight`: 0 to 0.5 points of horizontal thickening; default 0.22.
- `--label Alto --label A.`: staff labels to match (these are the defaults).
- `--expected-lines 15`: optional check against a known lyric-line count.
- `--highlight`: add a continuous pale bright-yellow highlighter band behind
  each whole lyric line, including gaps between words. It is embedded page
  content, so it displays and prints without enabling PDF annotations.
- Existing output files are not overwritten; choose a different output filename.

For the enlarged, bold, yellow-highlighted version:

```sh
.lyrics-venv/bin/python enlarge_alto_lyrics.py "Santa Claus is Coming to Town.pdf" \
  --highlight
```

This creates `Santa Claus is Coming to Town - Alto Lyrics Extra Large Highlighted.pdf`.

## Supported scores and checks

This is a reusable version of the process used for this score, **not a universal
music-layout detector**. It supports selectable-text/vector PDFs with a separately
labelled Alto staff in each system. It looks for a lyric baseline 18 to 40 PDF
points below each staff-label baseline. Scans, shared staves, missing repeated
labels, unusual spacing, or unfamiliar music fonts may need manual adaptation.
An error is reported if there are no matches or a labelled row is ambiguous.
A successful run does not prove that unlabelled systems were found.

**Visually check all pages before sharing or printing.** Larger lyrics can run
into the next staff in tightly spaced scores. Increase the height gradually;
for much larger, uniformly scaled type, the music needs reflowing from its
original notation source, or a larger paper size.

The script uses white-backed vector overlays, intended for black-on-white scores.
It does not rasterize the music or replace the original font. Covered original
text remains in the PDF, so this is a visual/print adaptation, not a tagged,
screen-reader-accessible PDF; text extraction can include repeated lyrics.

## Tests

```sh
.lyrics-venv/bin/python -m unittest -v test_enlarge_alto_lyrics.py
```
