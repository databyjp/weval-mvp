"""Write the Oracle's findings: the recommendations and code from the docs
pages cited with each answer. The code is the docs' own Python, TypeScript,
and Go (v6) examples."""

import json
from pathlib import Path

DOCS = "https://docs.weaviate.io"

CREATE_AND_IMPORT_PYTHON = """\
from weaviate.classes.config import Configure, Property, DataType

client.collections.create(
    "Article",
    vector_config=Configure.Vectors.text2vec_openai(),
    properties=[
        Property(name="title", data_type=DataType.TEXT),
        Property(name="body", data_type=DataType.TEXT),
    ],
)

collection = client.collections.use("Article")
with collection.batch.stream() as batch:
    for row in rows:
        batch.add_object(properties=row)
"""

CREATE_AND_IMPORT_TYPESCRIPT = """\
import { vectors, dataType } from 'weaviate-client';

await client.collections.create({
  name: 'Article',
  vectorizers: vectors.text2VecOpenAI(),
  properties: [
    { name: 'title', dataType: dataType.TEXT },
    { name: 'body', dataType: dataType.TEXT },
  ],
})

const articles = client.collections.use('Article')
const result = await articles.data.ingest(rows.map((properties) => ({ properties })))
"""

CREATE_AND_IMPORT_GO = """\
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Article",
  Properties: []collections.Property{
    {Name: "title", DataType: collections.DataTypeText},
    {Name: "body", DataType: collections.DataTypeText},
  },
  Vectors: map[string]collections.VectorConfig{
    "default": {Vectorizer: openai.Text2Vec{}},
  },
})

articles := client.Collections.Use("Article")
b := articles.Batch(ctx, batch.WithRetryTimes(1))
for _, row := range rows {
  if _, err := b.Object(ctx, &data.Object{Properties: row}); err != nil {
    panic(err)
  }
}
if err := b.Close(); err != nil {
  panic(err)
}
"""

HYBRID_PYTHON = """\
articles = client.collections.use("Article")
response = articles.query.hybrid(query="food", limit=3)
"""

HYBRID_TYPESCRIPT = """\
const articles = client.collections.use('Article');
const result = await articles.query.hybrid('food', { limit: 3 })
"""

HYBRID_GO = """\
articles := client.Collections.Use("Article")
response, err := articles.Query.Hybrid(ctx, query.Hybrid{
  Query: "food",
  Limit: 3,
})
"""

findings = {
    "deployment": {
        "answer": "Docker for local development; Kubernetes or Weaviate Cloud for production.",
        "sources": [f"{DOCS}/deploy"],
    },
    "config_ingestion": {
        "answer": "Define each collection with a named vector from Configure.Vectors "
        "(configure.vectors in TypeScript, the Vectors map in Go v6); import objects with "
        "server-side batching.",
        "sources": [
            f"{DOCS}/weaviate/manage-collections/vector-config",
            f"{DOCS}/weaviate/manage-objects/import",
        ],
        "code": {
            "python": CREATE_AND_IMPORT_PYTHON,
            "typescript": CREATE_AND_IMPORT_TYPESCRIPT,
            "go": CREATE_AND_IMPORT_GO,
        },
    },
    "search": {
        "answer": "Hybrid search as the starting point.",
        "sources": [
            f"{DOCS}/weaviate/concepts/search",
            f"{DOCS}/weaviate/search/hybrid",
        ],
        "code": {
            "python": HYBRID_PYTHON,
            "typescript": HYBRID_TYPESCRIPT,
            "go": HYBRID_GO,
        },
    },
}
Path("/app/findings.json").write_text(json.dumps(findings, indent=2))
