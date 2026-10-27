# /// script
# dependencies = ["beautifulsoup4", "html5lib", "markdownify"]
# ///
"""Regenerate skills/weaviate-docs/pages/ from the live docs site.

    uv run treatments/weaviate-docs/fetch_pages.py

docs.weaviate.io serves no Markdown, so each page is the rendered HTML's
<article> converted with markdownify, first line ``Source: <url>``. Code
blocks keep their language (``py``, ``ts``, ...) but lose the tab labels.
"""

import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify

SITE = "https://docs.weaviate.io/"
PAGES = {
    "release-notes": "weaviate/release-notes",
    "client-libraries": "weaviate/client-libraries",
    "client-libraries-python": "weaviate/client-libraries/python",
    "deploy": "deploy",
    "docker-installation": "deploy/installation-guides/docker-installation",
    "k8s-installation": "deploy/installation-guides/k8s-installation",
    "collection-operations": "weaviate/manage-collections/collection-operations",
    "vector-config": "weaviate/manage-collections/vector-config",
    "import": "weaviate/manage-objects/import",
    "search": "weaviate/search",
    "hybrid": "weaviate/search/hybrid",
    "similarity": "weaviate/search/similarity",
}
# Page chrome with no content: heading anchors, the code-language selector,
# breadcrumbs, and footer navigation.
CHROME = ("a.hash-link, [class^=codeDropdownHeader], nav, button, .theme-doc-footer, "
          ".pagination-nav, .theme-doc-breadcrumbs, svg, script, style")


def code_language(element) -> str:
    return next((c.removeprefix("language-") for c in element.get("class") or []
                 if c.startswith("language-")), "")


def page_markdown(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(request, timeout=30).read()
    # html5lib, because the site's HTML omits closing tags in tables.
    soup = BeautifulSoup(html, "html5lib")
    article = soup.find("article")
    for tag in article.select(CHROME):
        tag.decompose()
    # Prose tabs: write each label above its panel, which hidden tabs keep.
    # Code blocks are tab panels too, switched by a select, so pair labels
    # only with the panels in their own tablist's container.
    for tablist in article.select('[role="tablist"]'):
        labels = [tab.get_text(strip=True) for tab in tablist.select('[role="tab"]')]
        panels = tablist.parent.select('[role="tabpanel"]', limit=len(labels))
        tablist.decompose()
        for label, panel in zip(labels, panels):
            marker = soup.new_tag("p")
            marker.string = f"Tab: {label}"
            panel.insert_before(marker)
    text = markdownify(str(article), heading_style="ATX", code_language_callback=code_language)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return f"Source: {url}\n\n{text.strip()}\n"


if __name__ == "__main__":
    pages = Path(__file__).parent / "skills/weaviate-docs/pages"
    for name, path in PAGES.items():
        (pages / f"{name}.md").write_text(page_markdown(SITE + path))
