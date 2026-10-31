"""Write the Oracle's findings: the recommendations from the concepts pages and
code adapted from the how-to pages' Python examples."""

import json
from pathlib import Path

DOCS = "https://docs.weaviate.io/weaviate"
VECTOR_INDEX = f"{DOCS}/concepts/vector-index"
QUANTIZATION = f"{DOCS}/concepts/vector-quantization"
DATA_IMPORT = f"{DOCS}/concepts/data-import"
RQ = f"{DOCS}/configuration/compression/rq-compression"
IMPORT = f"{DOCS}/manage-objects/import"

CREATE_PYTHON = """\
from weaviate.classes.config import Configure, Property, DataType

# HNSW is the default index; 8-bit RQ is the default rq() quantizer.
client.collections.create(
    name="Product",
    vector_config=Configure.Vectors.text2vec_openai(
        model="text-embedding-3-small",
        quantizer=Configure.VectorIndex.Quantizer.rq(),
    ),
    properties=[
        Property(name="title", data_type=DataType.TEXT),
        Property(name="description", data_type=DataType.TEXT),
    ],
)
"""



IMPORT_PYTHON = """\
import json

def read_products(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            yield {"title": record["title"], "description": record["description"]}

products = client.collections.use("Product")

# `ingest` uses server-side batching and pulls objects from the generator.
result = products.data.ingest(read_products("products.jsonl"))
if result.errors:
    print(f"Number of failed imports: {len(result.errors)}")
"""



findings = {
    "vector_index": {
        "answer": "HNSW: the docs recommend it for large collections that need high query "
        "throughput and low latency, which 5 million products at high QPS are. Keep the "
        "defaults, including dynamic ef (ef = -1), and reduce memory with compression rather "
        "than a flat or dynamic index.",
        "sources": [VECTOR_INDEX, RQ],
        "code": {
            "python": CREATE_PYTHON,
        },
    },
    "compression": {
        "answer": "8-bit rotational quantization (RQ): recommended for most use cases, about "
        "4x compression with 98-99% recall, and no training step, so it is enabled when the "
        "collection is created.",
        "sources": [QUANTIZATION, RQ],
    },
    "batch_import": {
        "answer": "Server-side batching, the recommended import: the server sets the rate the "
        "client sends at, so there are no batch sizes to tune. The Python client's "
        "data.ingest() takes a generator, so the file is read one line at a time.",
        "sources": [DATA_IMPORT, IMPORT],
        "code": {
            "python": IMPORT_PYTHON,
        },
    },
}

Path("/app/findings.json").write_text(json.dumps(findings, indent=2))
