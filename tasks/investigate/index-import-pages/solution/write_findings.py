"""Write the Oracle's findings: the recommendations from the concepts pages and
code adapted from the how-to pages' Python, TypeScript, and Go (v6) examples."""

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

CREATE_TYPESCRIPT = """\
import weaviate, { configure } from 'weaviate-client';

// HNSW is the default index; 8-bit RQ is the default rq() quantizer.
await client.collections.create({
  name: 'Product',
  vectorizers: configure.vectors.text2VecOpenAI({
    model: 'text-embedding-3-small',
    quantizer: configure.vectorIndex.quantizer.rq(),
  }),
  properties: [
    { name: 'title', dataType: weaviate.configure.dataType.TEXT },
    { name: 'description', dataType: weaviate.configure.dataType.TEXT },
  ],
});
"""

CREATE_GO = """\
// Imports: github.com/weaviate/weaviate-go-client/v6/collections,
// .../collections/compression, .../collections/vectorindex, .../modules/openai
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Product",
  Properties: []collections.Property{
    {Name: "title", DataType: collections.DataTypeText},
    {Name: "description", DataType: collections.DataTypeText},
  },
  Vectors: map[string]collections.VectorConfig{
    "default": {
      Vectorizer: openai.Text2Vec{},
      // Set the index explicitly. The client sends compression only with it.
      Index:       vectorindex.HNSW{},
      Compression: compression.RQ{Bits: 8},
    },
  },
})
if err != nil {
  panic(err)
}
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

IMPORT_TYPESCRIPT = """\
import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';

async function readProducts(path: string) {
  const products = [];
  for await (const line of createInterface({ input: createReadStream(path) })) {
    if (!line.trim()) continue;
    const { title, description } = JSON.parse(line);
    products.push({ properties: { title, description } });
  }
  return products;
}

const products = client.collections.use('Product');

// `ingest` is the TypeScript server-side batching API.
const result = await products.data.ingest(await readProducts('products.jsonl'));
console.log(result);
"""

IMPORT_GO = """\
// Imports: bufio, encoding/json, fmt, os,
// github.com/weaviate/weaviate-go-client/v6/batch, .../data
file, err := os.Open("products.jsonl")
if err != nil {
  panic(err)
}
defer file.Close()

products := client.Collections.Use("Product")

// Open a server-side batch stream. The client sends objects
// at the rate the server requests.
b := products.Batch(ctx, batch.WithRetryTimes(1))

var tasks []*batch.Task
scanner := bufio.NewScanner(file)
for scanner.Scan() {
  var row map[string]any
  if err := json.Unmarshal(scanner.Bytes(), &row); err != nil {
    continue
  }
  task, err := b.Object(ctx, &data.Object{Properties: map[string]any{
    "title": row["title"], "description": row["description"],
  }})
  if err != nil {
    panic(err)
  }
  tasks = append(tasks, task)
}

// Close blocks until every task has completed.
if err := b.Close(); err != nil {
  panic(err)
}
failed := 0
for _, task := range tasks {
  if err := task.Wait(); err != nil {
    failed++
  }
}
fmt.Printf("Number of failed imports: %d\\n", failed)
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
            "typescript": CREATE_TYPESCRIPT,
            "go": CREATE_GO,
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
        "client sends at, so there are no batch sizes to tune. Python and TypeScript use "
        "data.ingest() with a generator or list; Go v6 uses collection.Batch(ctx, ...). The Go "
        "v5 client does not support it.",
        "sources": [DATA_IMPORT, IMPORT],
        "code": {
            "python": IMPORT_PYTHON,
            "typescript": IMPORT_TYPESCRIPT,
            "go": IMPORT_GO,
        },
    },
}

Path("/app/findings.json").write_text(json.dumps(findings, indent=2))
