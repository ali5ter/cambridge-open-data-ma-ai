#!/usr/bin/env python3
"""report_to_pdf.py - Render a docs/reports/*/report.md as a PDF alongside it.

Converts a Markdown report to standalone HTML, then prints it to PDF with
headless Chrome -- the same pipeline (Skia/PDF via HeadlessChrome) already used
for docs/reports/2026-08-09-publicly-accessible-private-spaces/report.pdf, just
codified instead of done by hand. Relative image references (e.g. chart.png)
resolve against the report's own directory, so the PDF is self-contained the
same way the report directory is.

Author: Alister Lewis-Bowen <alister@lewis-bowen.org>
Version: 1.0.0
Date: 2026-08-10
License: MIT

Usage:
    uv run scripts/report_to_pdf.py docs/reports/<date>-<slug>/report.md

Dependencies:
    markdown, rich -- a Chrome/Chromium binary on PATH or in a standard
    install location

Exit codes:
    0 - Success
    1 - Input file not found
    2 - No Chrome/Chromium binary found
    3 - Chrome print-to-PDF failed
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import markdown
from rich.console import Console

console = Console()
error_console = Console(stderr=True)

_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
_CHROME_ON_PATH = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]

_CSS = """
@page { size: Letter; margin: 0.75in; }
body {
    font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #1a1a1a;
    max-width: 100%;
}
h1, h2, h3 { line-height: 1.25; margin-top: 1.4em; margin-bottom: 0.5em; }
h1 { font-size: 20pt; margin-top: 0; }
h2 { font-size: 15pt; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; }
h3 { font-size: 12.5pt; }
p, li { orphans: 3; widows: 3; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 9.5pt; }
th, td { border: 1px solid #ccc; padding: 4px 8px; text-align: left; vertical-align: top; }
th { background: #f2f2f0; font-weight: 600; }
code { background: #f2f2f0; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }
pre { background: #f2f2f0; padding: 0.8em; border-radius: 4px; overflow-x: auto; }
pre code { background: none; padding: 0; }
img { max-width: 100%; page-break-inside: avoid; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; color: #555; }
"""

_HTML_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def find_chrome() -> str | None:
    """Locate a Chrome or Chromium binary usable for headless PDF printing.

    Returns:
        Absolute path to the binary, or None if none was found.
    """
    for candidate in _CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    for name in _CHROME_ON_PATH:
        found = shutil.which(name)
        if found:
            return found
    return None


def render_html(markdown_path: Path) -> str:
    """Convert a Markdown file to standalone HTML with report styling.

    Args:
        markdown_path: Path to the source Markdown file.

    Returns:
        A complete HTML document as a string.
    """
    text = markdown_path.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    title = markdown_path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return _HTML_TEMPLATE.format(title=title, css=_CSS, body=body)


def convert(markdown_path: Path, output_path: Path, chrome_binary: str) -> None:
    """Render a Markdown report to PDF via an HTML intermediate.

    Writes the HTML intermediate into the report's own directory (so
    relative image references resolve), prints it with headless Chrome,
    then removes the intermediate file.

    Args:
        markdown_path: Path to the source Markdown file.
        output_path: Path to write the resulting PDF to.
        chrome_binary: Path to the Chrome/Chromium executable to use.

    Raises:
        subprocess.CalledProcessError: If Chrome exits non-zero.
    """
    html = render_html(markdown_path)
    html_path = markdown_path.with_name(f".{markdown_path.stem}.report_to_pdf.html")
    html_path.write_text(html, encoding="utf-8")
    try:
        subprocess.run(
            [
                chrome_binary,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={output_path}",
                html_path.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        html_path.unlink(missing_ok=True)


def main() -> int:
    """CLI entry point.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown_path", type=Path, help="Path to the report's report.md")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path (default: report.pdf next to the input file)",
    )
    args = parser.parse_args()

    if not args.markdown_path.is_file():
        error_console.print(f"[red]✗[/red] Not found: {args.markdown_path}")
        return 1

    chrome_binary = find_chrome()
    if chrome_binary is None:
        error_console.print(
            "[red]✗[/red] No Chrome/Chromium binary found. Install Google Chrome or "
            "Chromium, or add one to PATH."
        )
        return 2

    output_path = args.output or args.markdown_path.with_name("report.pdf")
    console.print(f"[bold cyan]Rendering[/bold cyan] {args.markdown_path} -> {output_path}")
    try:
        convert(args.markdown_path, output_path, chrome_binary)
    except subprocess.CalledProcessError as exc:
        error_console.print(f"[red]✗[/red] Chrome print-to-PDF failed: {exc.stderr}")
        return 3

    console.print(f"[green]✔[/green] Wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
