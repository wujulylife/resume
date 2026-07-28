#!/usr/bin/env python3
"""Build B-onepage-cn.pdf as exactly 2 pages via chunked WeasyPrint renders.

WeasyPrint often clips CJK glyphs when fragmenting long flows across pages.
Rendering two single-page chunks and merging avoids mid-glyph cuts.
Spacing is expanded per page so both pages fill the sheet (little empty bottom).
"""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "B-onepage-cn.html"
PDF_PATH = ROOT / "B-onepage-cn.pdf"
TMP = Path("/tmp/resume-pages")

PRINT_OVERRIDES = """
html, body {
  margin: 0;
  background: #fff;
  font-size: 8.5pt;
  line-height: 1.4;
}
.sheet {
  width: auto;
  margin: 0;
  padding: 0;
  box-shadow: none;
  background: #fff;
}
.sheet::before { display: none; }
.sec-projects {
  break-before: auto;
  page-break-before: auto;
  padding-top: 0;
}
.sec-works { padding-bottom: 0; }
.strengths { gap: 5px; }
.strengths div { padding: 4px 6px 5px; font-size: 6.9pt; line-height: 1.32; }
.skills-wrap { padding: 4px 7px; gap: 3px 8px; }
@media print {
  @page { size: A4; margin: 8.5mm 10mm 11mm 10mm; }
  .sheet { width: auto; padding: 0; margin: 0; }
  body { line-height: 1.35; }
}
"""

# Expand vertical rhythm so a sparse page fills A4 (keeps readable, no empty tail).
FILL_STEPS = [
    "",  # 0: base
    """
.sec { margin-top: 7px; }
.entry, .edu-row { margin-bottom: 6px; }
.entry:not(:last-child) { padding-bottom: 5px; }
.sec-title { margin-bottom: 5px; }
li { margin: 1.8px 0; line-height: 1.42; }
.kw { margin-top: 3px; }
.skills-wrap { padding: 7px 9px; gap: 5px 10px; }
.strengths { gap: 7px; }
.strengths div { padding: 7px 8px 8px; line-height: 1.4; }
.bio { padding: 6px 9px; }
.header { margin-bottom: 7px; padding-bottom: 7px; }
""",
    """
.sec { margin-top: 9px; }
.entry, .edu-row { margin-bottom: 8px; }
.entry:not(:last-child) { padding-bottom: 6px; }
.sec-title { margin-bottom: 6px; }
li { margin: 2.4px 0; line-height: 1.48; }
.kw { margin-top: 4px; }
.skills-wrap { padding: 9px 10px; gap: 6px 12px; }
.skill-item { line-height: 1.48; }
.strengths { gap: 9px; }
.strengths div { padding: 9px 9px 10px; line-height: 1.45; font-size: 7.2pt; }
.bio { padding: 7px 10px; }
.bio p { margin: 2px 0; }
.header { margin-bottom: 9px; padding-bottom: 8px; }
""",
    """
.sec { margin-top: 10px; }
.entry, .edu-row { margin-bottom: 9px; }
.entry:not(:last-child) { padding-bottom: 7px; }
.sec-title { margin-bottom: 6.5px; }
li { margin: 2.7px 0; line-height: 1.5; }
.kw { margin-top: 4.5px; }
.skills-wrap { padding: 10px 11px; gap: 7px 12px; }
.skill-item { line-height: 1.5; }
.strengths { gap: 10px; }
.strengths div { padding: 10px 9px 11px; line-height: 1.48; font-size: 7.3pt; }
.bio { padding: 7.5px 10px; }
.bio p { margin: 2.5px 0; }
.header { margin-bottom: 9.5px; padding-bottom: 8.5px; }
""",
    """
.sec { margin-top: 11px; }
.entry, .edu-row { margin-bottom: 10px; }
.entry:not(:last-child) { padding-bottom: 8px; }
.sec-title { margin-bottom: 7px; }
li { margin: 3px 0; line-height: 1.52; }
.kw { margin-top: 5px; }
.kw span { margin-bottom: 3px; }
.skills-wrap { padding: 11px 11px; gap: 8px 12px; }
.skill-item { line-height: 1.52; }
.strengths { gap: 11px; }
.strengths div { padding: 11px 10px 12px; line-height: 1.5; font-size: 7.4pt; }
.bio { padding: 8px 10px; }
.bio p { margin: 3px 0; }
.header { margin-bottom: 10px; padding-bottom: 9px; }
.name { font-size: 20pt; }
""",
    """
.sec { margin-top: 13px; }
.entry, .edu-row { margin-bottom: 12px; }
.entry:not(:last-child) { padding-bottom: 9px; }
.sec-title { margin-bottom: 8px; }
li { margin: 3.5px 0; line-height: 1.55; }
.kw { margin-top: 6px; }
.skills-wrap { padding: 12px 12px; gap: 9px 12px; }
.strengths { gap: 12px; }
.strengths div { padding: 12px 10px 13px; line-height: 1.52; font-size: 7.5pt; }
.bio { padding: 9px 11px; }
.header { margin-bottom: 11px; padding-bottom: 10px; }
""",
]


def extract_entries(html: str) -> list[str]:
    entries: list[str] = []
    i = 0
    while True:
        start = html.find('<div class="entry"', i)
        if start < 0:
            break
        pos = start
        depth = 0
        while pos < len(html):
            next_open = html.find("<div", pos)
            next_close = html.find("</div>", pos)
            if next_close < 0:
                break
            if next_open >= 0 and next_open < next_close:
                depth += 1
                pos = next_open + 4
            else:
                depth -= 1
                pos = next_close + 6
                if depth == 0:
                    entries.append(html[start:pos])
                    i = pos
                    break
        else:
            break
    return entries


def wrap_page(style: str, inner: str, fill_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<style>
{style}
{PRINT_OVERRIDES}
{fill_css}
</style>
</head>
<body>
<article class="sheet">
{inner}
</article>
</body>
</html>
"""


def page_bottom_slack_px(pdf_path: Path, scale: float = 2.0) -> float:
    """Distance from last ink to physical page bottom (points*scale)."""
    import pypdfium2 as pdfium

    pil = pdfium.PdfDocument(str(pdf_path))[0].render(scale=scale).to_pil()
    g = pil.convert("L")
    w, h = g.size
    last = 0
    for y in range(h - 1, -1, -1):
        if any(g.getpixel((x, y)) < 210 for x in range(24, w - 24)):
            last = y
            break
    return h - 1 - last


def render_chunk(html: str, out_pdf: Path) -> int:
    HTML(string=html, base_url=str(ROOT) + "/").write_pdf(str(out_pdf))
    return len(PdfReader(str(out_pdf)).pages)


def render_filled(style: str, inner: str, out_pdf: Path, min_slack: float, max_slack: float) -> tuple[int, float, int]:
    """Expand spacing until the page is full, without overflowing to 2 pages."""
    candidates: list[tuple[int, float]] = []
    for fill_idx, fill_css in enumerate(FILL_STEPS):
        html = wrap_page(style, inner, fill_css)
        n = render_chunk(html, out_pdf)
        if n != 1:
            break
        slack = page_bottom_slack_px(out_pdf)
        print(f"  fill={fill_idx} pages=1 slack≈{slack:.0f}px")
        candidates.append((fill_idx, slack))
        if slack <= max_slack:
            break

    if not candidates:
        html = wrap_page(style, inner, "")
        n = render_chunk(html, out_pdf)
        slack = page_bottom_slack_px(out_pdf) if n == 1 else -1
        return (-1, slack, n)

    # Prefer the fullest page that still keeps a safe bottom margin.
    valid = [c for c in candidates if c[1] >= min_slack]
    if not valid:
        fill_idx, slack = candidates[0]  # densest that still fit
    else:
        fill_idx, slack = min(valid, key=lambda c: c[1])

    html = wrap_page(style, inner, FILL_STEPS[fill_idx])
    n = render_chunk(html, out_pdf)
    slack = page_bottom_slack_px(out_pdf)
    return fill_idx, slack, n


def main() -> None:
    source = HTML_PATH.read_text()
    style = re.search(r"<style>(.*?)</style>", source, re.S).group(1)
    body = re.search(r'<article class="sheet">(.*?)</article>', source, re.S).group(1)

    proj_idx = body.find("sec-projects")
    proj_sec = body.rfind("<section", 0, proj_idx)
    skills_idx = body.find("sec-skills")
    skills_sec = body.rfind("<section", 0, skills_idx)

    pre_body = body[:proj_sec].rstrip()
    projects_body = body[proj_sec:skills_sec].rstrip()
    tail_body = body[skills_sec:].rstrip()

    entries = extract_entries(projects_body)
    if len(entries) < 6:
        raise SystemExit(f"expected >=6 project entries, got {len(entries)}")

    proj_header = projects_body[: projects_body.find("</h2>") + len("</h2>")]
    TMP.mkdir(exist_ok=True)

    min_slack_px = 85
    max_slack_px = 140  # keep pages visually full
    candidate_splits = [3, 2, 4, 1]
    chosen: list[Path] | None = None

    for split_at in candidate_splits:
        page1_inner = (
            pre_body
            + f'\n<section class="sec sec-projects">\n{proj_header}\n'
            + '<div class="proj-rail">\n'
            + "\n".join(entries[:split_at])
            + "\n</div>\n</section>"
        )
        page2_inner = (
            '<section class="sec sec-projects">\n'
            + '<div class="proj-rail">\n'
            + "\n".join(entries[split_at:])
            + f"\n</div>\n</section>\n{tail_body}"
        )
        print(f"try split_at={split_at}")
        pdfs: list[Path] = []
        ok = True
        for i, inner in enumerate((page1_inner, page2_inner), 1):
            out = TMP / f"p{i}.pdf"
            print(f" chunk{i}:")
            fill_idx, slack, n = render_filled(
                style, inner, out, min_slack_px, max_slack_px
            )
            print(f"  -> pages={n} fill={fill_idx} slack≈{slack:.0f}px")
            if n != 1 or slack < min_slack_px:
                ok = False
            pdfs.append(out)
        if ok:
            chosen = pdfs
            print(f"using split_at={split_at}")
            break

    if chosen is None:
        raise SystemExit("could not find a 2-page split; tighten content or CSS")

    writer = PdfWriter()
    for pdf in chosen:
        for page in PdfReader(str(pdf)).pages:
            writer.add_page(page)
    with open(PDF_PATH, "wb") as f:
        writer.write(f)
    n_pages = len(PdfReader(str(PDF_PATH)).pages)
    print(f"wrote {PDF_PATH} ({n_pages} pages)")
    if n_pages != 2:
        raise SystemExit(f"expected 2 pages, got {n_pages}")


if __name__ == "__main__":
    main()
