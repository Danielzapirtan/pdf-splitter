"""
PDF Chapter Splitter
A Flask app that splits PDF files into chapters based on the table of contents (bookmarks/outline).

How it works:
  1. Reads the PDF's built-in outline (bookmarks) to find top-level chapters.
  2. Splits the PDF at those chapter boundaries.
  3. Returns a ZIP with one PDF per chapter.

If a PDF has no outline, we fall back to splitting by detecting heading-like text
(e.g., lines matching "Chapter N", "CHAPTER N", numbered sections, etc.).

Run:
  pip install flask pypdf
  python app.py
  Open http://localhost:5000
"""

import io
import os
import re
import zipfile
from flask import Flask, render_template_string, request, send_file, flash, redirect, url_for
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)
app.secret_key = "change-me-in-production"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB upload limit


# ---------------------------------------------------------------------------
# Chapter detection
# ---------------------------------------------------------------------------

def get_chapters_from_outline(reader: PdfReader):
    """
    Return a list of (title, start_page_index) from the PDF's top-level outline.
    Returns [] if there is no outline.
    """
    try:
        outline = reader.outline
    except Exception:
        return []

    if not outline:
        return []

    chapters = []
    for item in outline:
        # Top-level items can be either a Destination (leaf) or a list (nested).
        if isinstance(item, list):
            # Nested list: descend once to grab its first entry as the chapter start.
            if item:
                first = item[0]
                title = getattr(first, "title", None)
                page_idx = _resolve_page_index(reader, first)
                if title and page_idx is not None:
                    chapters.append((title.strip(), page_idx))
        else:
            title = getattr(item, "title", None)
            page_idx = _resolve_page_index(reader, item)
            if title and page_idx is not None:
                chapters.append((title.strip(), page_idx))

    # Sort by page and drop duplicates on the same page.
    chapters.sort(key=lambda c: c[1])
    deduped = []
    seen_pages = set()
    for title, page in chapters:
        if page in seen_pages:
            continue
        seen_pages.add(page)
        deduped.append((title, page))
    return deduped


def _resolve_page_index(reader: PdfReader, dest):
    """Resolve a pypdf Destination to a 0-based page index, or None."""
    try:
        page_num = reader.get_destination_page_number(dest)
    except Exception:
        return None
    if page_num is None or page_num < 0:
        return None
    return page_num


# --- Fallback: detect chapter headings from text ----------------------------

# Matches common chapter/section heading patterns at the start of a line.
HEADING_PATTERNS = [
    re.compile(r"^\s*chapter\s+([0-9]+|[ivxlcdm]+)\b", re.IGNORECASE),
    re.compile(r"^\s*part\s+([0-9]+|[ivxlcdm]+)\b", re.IGNORECASE),
    re.compile(r"^\s*section\s+([0-9]+)\b", re.IGNORECASE),
    re.compile(r"^\s*([0-9]{1,2})\.\s+[A-Z][A-Za-z]"),  # "1. Introduction"
]


def _line_looks_like_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 80:
        return False
    return any(p.match(line) for p in HEADING_PATTERNS)


def get_chapters_from_text(reader: PdfReader):
    """
    Scan each page's text for heading-like lines. A chapter starts on the page
    where the first heading-like line is found, and subsequent headings start
    new chapters. This is heuristic and may miss things, but works for many
    textbooks.

    Returns list of (title, page_index). Returns [] if nothing found.
    """
    chapters = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        # Look only at first few lines: headings usually appear at the top.
        for line in text.splitlines()[:8]:
            if _line_looks_like_heading(line):
                title = line.strip()
                if not chapters or chapters[-1][1] != i:
                    chapters.append((title, i))
                break
    return chapters


# ---------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------

def split_pdf_by_chapters(pdf_bytes: bytes):
    """
    Split the given PDF bytes into chapter PDFs.
    Returns (chapters, mode) where:
      chapters = list of (title, pdf_bytes)
      mode = "outline" | "text" | "none"
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)

    chapters = get_chapters_from_outline(reader)
    mode = "outline"

    if not chapters:
        chapters = get_chapters_from_text(reader)
        mode = "text"

    if not chapters:
        # No chapters found; return the whole thing as one file.
        return [("document", pdf_bytes)], "none"

    # Ensure a chapter starting at page 0 exists; otherwise prepend one.
    if chapters[0][1] != 0:
        chapters.insert(0, ("Front Matter", 0))

    # Build (start, end) boundaries.
    boundaries = []
    for idx, (title, start) in enumerate(chapters):
        end = chapters[idx + 1][1] if idx + 1 < len(chapters) else total_pages
        if start < end:
            boundaries.append((title, start, end))

    # Extract each chapter.
    out_chapters = []
    for title, start, end in boundaries:
        writer = PdfWriter()
        for p in range(start, end):
            writer.add_page(reader.pages[p])
        buf = io.BytesIO()
        writer.write(buf)
        out_chapters.append((title, buf.getvalue()))

    return out_chapters, mode


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

_SAFE = re.compile(r"[^A-Za-z0-9._ -]+")


def safe_filename(name: str, max_len: int = 80) -> str:
    name = _SAFE.sub("_", name).strip(" ._")
    if not name:
        name = "chapter"
    return name[:max_len]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

PAGE = """
<!doctype html>
<html>
<head>
  <title>PDF Chapter Splitter</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 3em auto; padding: 0 1em; }
    h1 { margin-bottom: 0.2em; }
    p.lead { color: #555; margin-top: 0; }
    form { margin-top: 1.5em; padding: 1.5em; border: 1px solid #ddd; border-radius: 8px; }
    input[type=file] { display: block; margin-bottom: 1em; }
    button { padding: 0.6em 1.2em; font-size: 1em; cursor: pointer; }
    .flash { padding: 0.75em 1em; background: #fee; border: 1px solid #fbb; border-radius: 6px; margin-bottom: 1em; }
    .info { background: #eef; border: 1px solid #bbd; padding: 0.75em 1em; border-radius: 6px; margin-top: 1em; }
    code { background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 3px; }
  </style>
</head>
<body>
  <h1>PDF Chapter Splitter</h1>
  <p class="lead">Upload a PDF. The app splits it into chapters using the PDF's
  bookmarks/outline. If there are none, it falls back to heading detection
  (e.g. <code>Chapter 1</code>, <code>1. Introduction</code>).</p>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
    {% endif %}
  {% endwith %}

  <form method="post" enctype="multipart/form-data" action="{{ url_for('split') }}">
    <input type="file" name="pdf" accept="application/pdf" required>
    <button type="submit">Split PDF</button>
  </form>

  <div class="info">
    <strong>How it works:</strong> no AI, no cloud — the PDF is parsed locally
    with <code>pypdf</code>.
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/split", methods=["POST"])
def split():
    file = request.files.get("pdf")
    if not file or not file.filename:
        flash("Please choose a PDF file.")
        return redirect(url_for("index"))

    data = file.read()
    if not data:
        flash("Uploaded file is empty.")
        return redirect(url_for("index"))

    try:
        chapters, mode = split_pdf_by_chapters(data)
    except Exception as e:
        flash(f"Could not process PDF: {e}")
        return redirect(url_for("index"))

    base = os.path.splitext(os.path.basename(file.filename))[0]

    # Single-chapter result: just send the PDF directly.
    if len(chapters) == 1:
        title, pdf_bytes = chapters[0]
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{safe_filename(base)}.pdf",
        )

    # Multiple chapters: zip them up.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, (title, pdf_bytes) in enumerate(chapters, 1):
            name = f"{i:02d}_{safe_filename(title)}.pdf"
            zf.writestr(name, pdf_bytes)
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{safe_filename(base)}_chapters.zip",
    )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5009)
