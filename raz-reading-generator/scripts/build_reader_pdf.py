#!/usr/bin/env python3
"""Render approved reader pages and their matching illustrations to a PDF."""
import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

from PIL import Image
from reportlab import __file__ as reportlab_file
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from content_gate import load_approved_book


PAGE_W, PAGE_H = 396, 612
MARGIN = 30
BODY_W = PAGE_W - 2 * MARGIN
FONT = "ReaderVera"
HEADER_TOP = 550
IMAGE_MIN_H = PAGE_H * 0.55
IMAGE_MAX_H = PAGE_H * 0.62
BODY_BOTTOM = 38
BODY_GAP = 12
LEADING_FACTOR = 1.2


def fail(message):
    raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def check_glyphs(value, label):
    widths = pdfmetrics.getFont(FONT).face.charWidths
    missing = sorted({char for char in value if char != "\n" and ord(char) not in widths})
    if missing:
        points = ", ".join(f"U+{ord(char):04X}" for char in missing)
        fail(f"{label} contains characters unsupported by the embedded font: {points}")


def wrap_text(text, font_size):
    if "\t" in text or "\r" in text or "  " in text:
        fail("Page text must use single spaces, LF line breaks, and no tabs")
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        if paragraph.startswith(" ") or paragraph.endswith(" "):
            fail("Page text lines cannot start or end with spaces")
        words = paragraph.split(" ")
        line = ""
        for word in words:
            if pdfmetrics.stringWidth(word, FONT, font_size) > BODY_W:
                return None
            candidate = word if not line else f"{line} {word}"
            if line and pdfmetrics.stringWidth(candidate, FONT, font_size) > BODY_W:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def page_layout(page, level):
    text = page["text"]
    check_glyphs(text, f"Page {page['page']} text")
    if wrap_text(text, 18) is None:
        fail(f"Page {page['page']} contains a word too wide to fit at 18 pt")
    start = 20 if str(level).upper() in {"F", "G", "H", "I", "J", "K", "L"} else 22
    for size in range(start, 17, -1):
        lines = wrap_text(text, size)
        if lines is None:
            continue
        text_h = len(lines) * size * LEADING_FACTOR
        image_h = min(IMAGE_MAX_H, HEADER_TOP - BODY_GAP - BODY_BOTTOM - text_h)
        if image_h >= IMAGE_MIN_H:
            return size, lines, image_h
    fail(f"Page {page['page']} text does not fit at the minimum 18 pt font")


def validate_book(book):
    if not isinstance(book, dict):
        fail("Approved book must be a JSON object")
    dialect = book.get("dialect")
    if not isinstance(dialect, str) or not dialect.strip().lower().startswith("en"):
        fail("Book dialect must identify an English variant, such as en-US or en-GB")
    pages = book.get("pages")
    if not isinstance(pages, list) or not pages:
        fail("Book must contain at least one body page")
    for number, page in enumerate(pages, 1):
        if not isinstance(page, dict) or type(page.get("page")) is not int or page["page"] != number:
            fail("Book page numbers must be consecutive and start at 1")
    return pages


def validate_images(manifest_path, manifest, pages, book_hash):
    if not isinstance(manifest, dict) or manifest.get("book_sha256") != book_hash:
        fail("images.json book_sha256 does not match the approved book bytes")
    entries = manifest.get("pages")
    if not isinstance(entries, list) or len(entries) != len(pages):
        fail("images.json must contain exactly one image for every book page")
    results, seen = [], set()
    for number, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or type(entry.get("page")) is not int or entry["page"] != number:
            fail("Image page numbers must exactly match the book pages")
        raw_path = entry.get("path")
        if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute():
            fail(f"Image for page {number} must have a relative path")
        path = (manifest_path.parent / raw_path).resolve()
        if not path.is_file():
            fail(f"Image for page {number} does not exist: {raw_path}")
        data = path.read_bytes()
        digest = sha256(data)
        if digest in seen:
            fail("Each page must use a distinct image file; duplicate image content found")
        seen.add(digest)
        try:
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size
                image.verify()
        except Exception as exc:
            fail(f"Image for page {number} is not a readable image: {exc}")
        if width < 1 or height < 1:
            fail(f"Image for page {number} has invalid dimensions")
        results.append({"page": number, "path": path, "width": width,
                        "height": height, "sha256": digest})
    return results


def draw_reader(pdf_path, book, pages, images):
    pdf = canvas.Canvas(str(pdf_path), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    pdf.setTitle(book["title"])
    report = []
    for page, image in zip(pages, images):
        size, lines, image_h = page_layout(page, book["level"])
        image_box = {"x": MARGIN, "y": HEADER_TOP - image_h,
                     "width": BODY_W, "height": image_h}
        text_box = {"x": MARGIN, "y": BODY_BOTTOM, "width": BODY_W,
                    "height": image_box["y"] - BODY_GAP - BODY_BOTTOM}
        scale = min(BODY_W / image["width"], image_h / image["height"])
        actual_w, actual_h = image["width"] * scale, image["height"] * scale
        actual = {"x": MARGIN + (BODY_W - actual_w) / 2,
                  "y": image_box["y"] + (image_h - actual_h) / 2,
                  "width": actual_w, "height": actual_h}
        if actual_w < PAGE_W * 0.5 or actual_h < PAGE_H * 0.5:
            fail(f"Image for page {page['page']} is too wide or tall for this layout; "
                 "use a portrait or near-square composition so the contained image "
                 "covers at least half the page in both dimensions")

        title = book["title"]
        check_glyphs(title, "Book title")
        title_size = 17
        while title_size > 12 and pdfmetrics.stringWidth(title, FONT, title_size) > BODY_W:
            title_size -= 1
        if pdfmetrics.stringWidth(title, FONT, title_size) > BODY_W:
            fail("Book title is too long to fit on the page")
        metadata = f"Level {book['level']} | {book['dialect']}"
        check_glyphs(metadata, "Book metadata")

        pdf.setFillColor(HexColor("#1B1B1B"))
        pdf.setFont(FONT, title_size)
        pdf.drawString(MARGIN, 583, title)
        pdf.setFillColor(HexColor("#707070"))
        pdf.setFont(FONT, 9)
        pdf.drawString(MARGIN, 565, metadata)

        raw = image["path"].read_bytes()
        if sha256(raw) != image["sha256"]:
            fail(f"Image for page {image['page']} changed during PDF generation")
        pdf.drawImage(ImageReader(io.BytesIO(raw)), actual["x"], actual["y"],
                      width=actual_w, height=actual_h, mask="auto")

        pdf.setFillColor(HexColor("#202020"))
        pdf.setFont(FONT, size)
        leading = size * LEADING_FACTOR
        first_baseline = text_box["y"] + text_box["height"] - size
        if len(lines) * leading > text_box["height"] + 0.01:
            fail(f"Page {page['page']} text exceeds its measured text box")
        for index, line in enumerate(lines):
            pdf.drawString(MARGIN, first_baseline - index * leading, line)
        pdf.setFillColor(HexColor("#707070"))
        pdf.setFont(FONT, 8)
        pdf.drawRightString(PAGE_W - MARGIN, 19, str(page["page"]))
        pdf.showPage()
        report.append({"page": page["page"], "text_font_size": size,
                       "text_box": text_box, "image_box": image_box,
                       "actual_image_rect": actual})
    pdf.save()
    return report


def write_outputs(output_path, book, pages, images, book_hash):
    layout_path = Path(str(output_path) + ".layout.json")
    parent = output_path.parent
    if not parent.is_dir():
        fail(f"Output directory does not exist: {parent}")
    if output_path.exists() or layout_path.exists():
        fail("Refusing to overwrite an existing PDF or layout report")
    pdf_tmp = layout_tmp = None
    try:
        fd, pdf_tmp = tempfile.mkstemp(prefix=".reader-", suffix=".pdf", dir=parent)
        os.close(fd)
        fd, layout_tmp = tempfile.mkstemp(prefix=".reader-", suffix=".json", dir=parent)
        os.close(fd)
        report = draw_reader(pdf_tmp, book, pages, images)
        layout = {"book_sha256": book_hash,
                  "image_hashes": [{"page": img["page"], "sha256": img["sha256"]}
                                   for img in images],
                  "pages": report}
        with open(layout_tmp, "w", encoding="utf-8") as stream:
            json.dump(layout, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.link(layout_tmp, layout_path)
        try:
            os.link(pdf_tmp, output_path)
        except Exception:
            layout_path.unlink(missing_ok=True)
            raise
    finally:
        for path in (pdf_tmp, layout_tmp):
            if path:
                Path(path).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", type=Path)
    parser.add_argument("images", type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        book_path, approval_path = args.book, args.approval
        original_hash = sha256(book_path.read_bytes())
        book = load_approved_book(book_path, approval_path)
        if sha256(book_path.read_bytes()) != original_hash:
            fail("Book changed while its approval was being checked")
        pages = validate_book(book)
        manifest_path = args.images.resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        images = validate_images(manifest_path, manifest, pages, original_hash)

        font_path = Path(reportlab_file).parent / "fonts" / "Vera.ttf"
        pdfmetrics.registerFont(TTFont(FONT, str(font_path)))
        for value, label in ((book["title"], "Book title"),
                             (f"Level {book['level']} | {book['dialect']}", "Book metadata")):
            check_glyphs(value, label)
        write_outputs(args.output, book, pages, images, original_hash)
        print(f"Created {args.output} and {args.output}.layout.json")
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f"PDF generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
