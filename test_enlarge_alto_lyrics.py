import tempfile
import unittest
from pathlib import Path

import pymupdf

from enlarge_alto_lyrics import enlarge, find_lyric_regions


class EnlargeLyricsTests(unittest.TestCase):
    def make_score(self, path: Path, label: str = "Alto") -> None:
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((40, 100), label, fontsize=12)
            page.insert_text((100, 126), "Test lyrics", fontsize=11)
            page.insert_text((100, 200), "Other voice unchanged", fontsize=11)
            document.save(path)

    def test_enlargement_preserves_other_content_and_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "original.pdf"
            target = Path(directory) / "larger.pdf"
            self.make_score(source)
            original_bytes = source.read_bytes()
            regions = enlarge(source, target, height=1.5, expected_lines=1)
            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertEqual(len(regions), 1)
            region = regions[0]
            self.assertAlmostEqual(region.destination(1.5).height / region.clip.height, 1.5)
            self.assertEqual(region.destination(1.5).width, region.clip.width)
            with pymupdf.open(source) as before, pymupdf.open(target) as after:
                self.assertEqual(len(before), len(after))
                other_voice = pymupdf.Rect(80, 175, 300, 210)
                self.assertEqual(
                    before[0].get_pixmap(clip=other_voice).samples,
                    after[0].get_pixmap(clip=other_voice).samples,
                )
                crop = region.destination(1.5) + (-1, -1, 1, 1)
                self.assertNotEqual(
                    before[0].get_pixmap(clip=crop).samples,
                    after[0].get_pixmap(clip=crop).samples,
                )
                ink_heights = []
                for page in (before[0], after[0]):
                    pixmap = page.get_pixmap(
                        clip=crop, matrix=pymupdf.Matrix(4, 4),
                        colorspace=pymupdf.csGRAY,
                    )
                    samples = pixmap.samples
                    ink_rows = [
                        row for row in range(pixmap.height)
                        if min(samples[row * pixmap.stride:
                                       row * pixmap.stride + pixmap.width]) < 128
                    ]
                    ink_heights.append(ink_rows[-1] - ink_rows[0] + 1)
                self.assertAlmostEqual(ink_heights[1] / ink_heights[0], 1.5, delta=0.1)

    def test_abbreviated_label(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "score.pdf"
            self.make_score(source, "A.")
            with pymupdf.open(source) as document:
                self.assertEqual(len(find_lyric_regions(document, {"a."})), 1)

    def test_highlight_is_behind_text_and_spans_word_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "score.pdf"
            plain = Path(directory) / "plain.pdf"
            highlighted = Path(directory) / "highlighted.pdf"
            self.make_score(source)
            enlarge(source, plain)
            regions = enlarge(source, highlighted, highlight=True)
            region = regions[0]
            with pymupdf.open(plain) as before, pymupdf.open(highlighted) as after:
                crop = region.destination(1.5)
                a = before[0].get_pixmap(clip=crop, matrix=pymupdf.Matrix(3, 3))
                b = after[0].get_pixmap(clip=crop, matrix=pymupdf.Matrix(3, 3))
                plain_pixels = list(zip(*[iter(a.samples)] * 3))
                highlighted_pixels = list(zip(*[iter(b.samples)] * 3))
                yellow_pixels = 0
                black_pixels = 0
                for original, changed in zip(plain_pixels, highlighted_pixels):
                    if original == (255, 255, 255):
                        self.assertEqual(changed[:2], (255, 255))
                        self.assertLessEqual(changed[2], 154)
                        yellow_pixels += 1
                    elif original == (0, 0, 0):
                        self.assertEqual(original, changed)
                        black_pixels += 1
                self.assertGreater(yellow_pixels, 100)
                self.assertGreater(black_pixels, 20)
                other_voice = pymupdf.Rect(80, 175, 300, 210)
                self.assertEqual(
                    before[0].get_pixmap(clip=other_voice).samples,
                    after[0].get_pixmap(clip=other_voice).samples,
                )
                self.assertEqual(len(list(after[0].annots())), 0)

    def test_missing_label_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "score.pdf"
            self.make_score(source, "Soprano")
            with pymupdf.open(source) as document:
                with self.assertRaisesRegex(ValueError, "No labelled Alto"):
                    find_lyric_regions(document, {"alto", "a."})

    def test_ambiguous_row_reports_error(self) -> None:
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((40, 100), "Alto", fontsize=12)
            page.insert_text((100, 122), "First lyric line", fontsize=11)
            page.insert_text((100, 136), "Second lyric line", fontsize=11)
            with self.assertRaisesRegex(ValueError, "exactly one lyric line"):
                find_lyric_regions(document, {"alto"})

    def test_safety_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "score.pdf"
            self.make_score(source)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                enlarge(source, source)
            target = Path(directory) / "output.pdf"
            for height in (0, 3, float("nan")):
                with self.subTest(height=height), self.assertRaises(ValueError):
                    enlarge(source, target, height=height)
            with self.assertRaisesRegex(ValueError, "Expected 2"):
                enlarge(source, target, expected_lines=2)
            self.assertFalse(target.exists())
            target.write_bytes(b"existing file")
            with self.assertRaises(FileExistsError):
                enlarge(source, target)
            self.assertEqual(target.read_bytes(), b"existing file")


if __name__ == "__main__":
    unittest.main()
