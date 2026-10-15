"""Starter contract for the ecommerce search proof of concept.

Implement ``GET /search?query=...&page=...&page_size=...``.

``query`` is required. ``page`` and ``page_size`` are positive integers with
respective defaults of 1 and 5. Return a JSON object containing the requested
``page`` and ``page_size`` plus an ``items`` list. Each item contains ``sku``,
``name``, ``description``, ``category``, and numeric ``price`` values from the
catalog.
"""

# pyright: reportMissingImports=false

from fastapi import FastAPI

app = FastAPI(title="Ecommerce product search")
