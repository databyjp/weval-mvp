"""One static page per packaged Task file, syntax-highlighted.

Pygments highlights at build time, so a page needs no JavaScript and opens
from ``file://``. Every line carries an ``L-<n>`` anchor, which lets the Task
page link a check to the line that defines it.
"""

from html import escape
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.util import ClassNotFound

from weval.report.assets import LOGO
from weval.report.pages import _Links, _page

# Larger files keep only their raw link: a page that size is no easier to read.
MAX_BYTES = 256 * 1024


def render_source(
    path: Path, *, label: str, page_dir: Path, task_page: Path, task_name: str
) -> str | None:
    """Return the page for the text file at ``path``, titled ``label`` (its
    path inside the Task package), or ``None`` when it is binary or larger
    than ``MAX_BYTES``. The page links back to ``task_page`` and to the raw
    file; links are relative to ``page_dir``."""
    if path.stat().st_size > MAX_BYTES:
        return None
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        return None
    try:
        lexer = get_lexer_for_filename(path.name, stripnl=False)
    except ClassNotFound:
        lexer = TextLexer(stripnl=False)
    # Pygments closes its spans at every line break, so each line can be its
    # own row: a long line then wraps under its own text, not its number.
    lines = highlight(text, lexer, HtmlFormatter(nowrap=True)).splitlines()
    code = "".join(
        f'<span class="line" id="L-{number}"><a class="linenos" '
        f'href="#L-{number}">{number}</a><span>{line}</span></span>'
        for number, line in enumerate(lines, start=1)
    )
    links = _Links(page_dir)
    body = (
        f'<div class="breadcrumb"><a href="{links.href(task_page)}">&larr; '
        f'{escape(task_name)}</a> <span class="muted">/ File</span></div>'
        f"<h1>{LOGO}{escape(label)}</h1>"
        f'<p class="intro">As the newest run packaged it. Raw file: '
        f"{links.link(path, path.name)}.</p>"
        f'<div class="card"><pre class="source">{code}</pre></div>'
    )
    return _page(label, body)
