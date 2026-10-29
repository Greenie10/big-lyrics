#!/usr/bin/env python3
"""Enlarge and darken Alto lyrics in text/vector choir PDFs; see README.md."""

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class LyricRegion:
    page_number: int
    clip: pymupdf.Rect

    def destination(self, height: float) -> pymupdf.Rect:
        # Keep the top fixed so enlarged letters do not grow into the notes above.
        return pymupdf.Rect(
            self.clip.x0, self.clip.y0,
            self.clip.x1, self.clip.y0 + self.clip.height * height,
        )


def find_lyric_regions(
    document: pymupdf.Document, labels: set[str]
) -> list[LyricRegion]:
    regions = []
    for page_number, page in enumerate(document):
        if page.rotation:
            raise ValueError(f"Page {page_number + 1} is rotated; normalize it first.")
        spans = [
            span
            for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
        ]
        staff_labels = [
            span for span in spans
            if span["text"].strip().casefold() in labels
            and span["origin"][0] < page.rect.width * 0.18
        ]
        for label in staff_labels:
            label_x, label_y = label["origin"]
            lyrics = [
                span for span in spans
                if span["text"].strip()
                and span["origin"][0] > label_x + 25
                and 18 <= span["origin"][1] - label_y <= 40
                and not any(
                    name in span["font"].casefold()
                    for name in ("opus", "music", "bravura", "maestro")
                )
            ]
            baselines = [span["origin"][1] for span in lyrics]
            if not lyrics or max(baselines) - min(baselines) > 1.5:
                raise ValueError(
                    f"Page {page_number + 1}, staff at y={label_y:.1f}: "
                    "could not identify exactly one lyric line. "
                    "This PDF needs its layout checked manually."
                )
            clip = pymupdf.Rect(lyrics[0]["bbox"])
            for span in lyrics[1:]:
                clip.include_rect(pymupdf.Rect(span["bbox"]))
            clip = clip + (-0.3, -0.3, 0.3, 0.3)
            regions.append(LyricRegion(page_number, clip))
    if not regions:
        raise ValueError(
            "No labelled Alto lyric lines found. Scanned PDFs and scores without "
            "repeated Alto/A. staff labels are not supported automatically."
        )
    return regions


def enlarge(
    input_path: Path,
    output_path: Path,
    *,
    height: float = 1.5,
    weight: float = 0.22,
    labels: set[str] | None = None,
    expected_lines: int | None = None,
    highlight: bool = False,
) -> list[LyricRegion]:
    if input_path.resolve() == output_path.resolve():
        raise ValueError("The output must not overwrite the input.")
    if output_path.exists():
        raise FileExistsError(f"Output already exists: {output_path}")
    if not math.isfinite(height) or not 1 <= height <= 2:
        raise ValueError("Height must be between 1 and 2.")
    if not math.isfinite(weight) or not 0 <= weight <= 0.5:
        raise ValueError("Weight must be between 0 and 0.5 points.")
    selected_labels = (
        {"alto", "a."} if labels is None
        else {label.strip().casefold() for label in labels}
    )
    with pymupdf.open(input_path) as source:
        if source.needs_pass:
            raise ValueError("Unlock the password-protected PDF first.")
        regions = find_lyric_regions(source, selected_labels)
        if expected_lines is not None and len(regions) != expected_lines:
            raise ValueError(
                f"Expected {expected_lines} lyric lines, found {len(regions)}."
            )
        with pymupdf.open(input_path) as output:
            for region in regions:
                page = output[region.page_number]
                destination = region.destination(height)
                if not page.rect.contains(destination):
                    raise ValueError(
                        f"Enlarged lyrics would leave page {region.page_number + 1}."
                    )
                page.draw_rect(region.clip, color=None, fill=(1, 1, 1))
                if highlight:
                    band = destination + (-2, -0.5, 2, 0.5)
                    band.intersect(page.rect)
                    page.draw_rect(band, color=None, fill=(1, 1, 0.6))
                # Reuse the original vector letters, including syllable alignment.
                for shift in (-weight, 0, weight):
                    target = destination + (shift, 0, shift, 0)
                    page.show_pdf_page(
                        target, source, region.page_number,
                        clip=region.clip, keep_proportion=False, overlay=True,
                    )
            output.save(output_path, garbage=4, deflate=True)
    with pymupdf.open(output_path) as result:
        for page in result:
            if not page.get_text().strip():
                raise RuntimeError(f"Output page {page.number + 1} has no text.")
    return regions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Original, unmodified PDF")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument(
        "--height", type=float, default=1.5,
        help="Letter height relative to original (1 to 2; default: 1.5)",
    )
    parser.add_argument(
        "--weight", type=float, default=0.22,
        help="Horizontal boldening in points (0 to 0.5; default: 0.22)",
    )
    parser.add_argument(
        "--label", action="append",
        help="Repeated staff label to match; repeat for abbreviations (default: Alto, A.)",
    )
    parser.add_argument("--expected-lines", type=int, help="Fail if line count differs")
    parser.add_argument(
        "--highlight", action="store_true",
        help="Add a continuous pale bright-yellow band behind each lyric line",
    )
    args = parser.parse_args()
    output_path = args.output or args.input.with_name(
        f"{args.input.stem} - Alto Lyrics Extra Large"
        f"{' Highlighted' if args.highlight else ''}.pdf"
    )
    try:
        regions = enlarge(
            args.input, output_path, height=args.height, weight=args.weight,
            labels=set(args.label) if args.label else None,
            expected_lines=args.expected_lines,
            highlight=args.highlight,
        )
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Saved: {output_path}")
    for page_number in sorted({region.page_number for region in regions}):
        count = sum(region.page_number == page_number for region in regions)
        print(f"  Page {page_number + 1}: {count} lyric lines")
    print("Visually check every page before printing, especially tightly spaced systems.")


if __name__ == "__main__":
    main()
