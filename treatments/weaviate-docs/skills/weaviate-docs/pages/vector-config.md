Source: https://docs.weaviate.io/weaviate/manage-collections/vector-config

# Vectorizer and vector index config

Python and JS/TS client - Vectorizer Configuration API Changes

Starting with Weaviate Python client `v4.16.0`, the [vectorizer configuration API has been updated](/weaviate/client-libraries/python#vectorizer-api-changes-v4160).
Starting with Weaviate JS/TS client `v3.8.0`, the [vectorizer configuration API has been updated](/weaviate/client-libraries/typescript#vectorizer-api-changes-v380).

Action required: **Update to the latest client version** and migrate your code to use the [new vectorizer configuration API](/weaviate/manage-collections/vector-config#specify-a-vectorizer).

## Specify a vectorizer

Specify a `vectorizer` for a collection.

Additional information

Collection level settings override default values and general configuration parameters such as [environment variables](/deploy/configuration/env-vars).

* [Available model integrations](/weaviate/model-providers)
* [Vectorizer configuration references](/weaviate/config-refs/collections#vector-configuration)

```py
from weaviate.classes.config import Configure, Property, DataType

client.collections.create(
    "Article",
    vector_config=Configure.Vectors.text2vec_openai(),
    properties=[
        Property(name="title", data_type=DataType.TEXT),
        Property(name="body", data_type=DataType.TEXT),
    ],
)
```

```ts
import { vectors, dataType } from 'weaviate-client';

await client.collections.create({
  name: 'Article',
  vectorizers: vectors.text2VecOpenAI(),
  properties: [
    { name: 'title', dataType: dataType.TEXT },
    { name: 'body', dataType: dataType.TEXT },
  ],
})
```

```go
  articleClass := &models.Class{
    Class:       "Article",
    Description: "Collection of articles",
    Vectorizer:  "text2vec-openai",
    Properties: []*models.Property{
      {
        Name:     "title",
        DataType: schema.DataTypeText.PropString(),
      },
      {
        Name:     "body",
        DataType: schema.DataTypeText.PropString(),
      },
    },
  }
```

```go
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
if err != nil {
  // handle error
  panic(err)
}
```

```java
client.collections.create("Article",
    col -> col.vectorConfig(VectorConfig.text2vecTransformers())
        .properties(Property.text("title"), Property.text("body")));
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "Article",
        VectorConfig = new VectorConfigList
        {
            Configure.Vector("default", v => v.Text2VecTransformers()),
        },
        Properties = [Property.Text("title"), Property.Text("body")],
    }
);
```

## Specify vectorizer settings

.Vectors.text2vec\_xxx with AutoSchema

Defining a collection with `Configure.Vectors.text2vec_xxx()` with Python client library `4.16.0`-`4.16.3` will throw an error if no properties are defined and `vectorize_collection_name` is not set to `True`.

This is addressed in `4.16.4` of the Weaviate Python client. See this FAQ entry for more details: [Invalid properties error in Python client versions 4.16.0 to 4.16.3](/weaviate/more-resources/faq#q-invalid-properties-error-when-creating-a-collection-python-client-versions-4160-to-4163).

To configure how a vectorizer works (i.e. what model to use) with a specific collection, set the vectorizer parameters.

```py
from weaviate.classes.config import Configure

client.collections.create(
    "Article",
    vector_config=Configure.Vectors.text2vec_cohere(
        model="embed-multilingual-v2.0", vectorize_collection_name=True
    ),
)
```

```ts
import { vectors } from 'weaviate-client';

await client.collections.create({
  name: 'Article',
  vectorizers: vectors.text2VecCohere({
    model: 'embed-multilingual-v2.0',
  }),
})
```

```go
  articleClass := &models.Class{
    Class:       "Article",
    Description: "Collection of articles",
    Vectorizer:  "text2vec-cohere",
    ModuleConfig: map[string]interface{}{
      "text2vec-cohere": map[string]interface{}{
        "model":              "embed-multilingual-v2.0",
        "vectorizeClassName": true,
      },
    },
  }
```

```go
// Point the vectorizer at a remote inference service and embed only the
// listed properties.
vectorizer := model2vec.Text2Vec{
  URL:        "http://text2vec-model2vec:8080",
  Properties: []string{"title"},
}
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Article",
  Properties: []collections.Property{
    {Name: "title", DataType: collections.DataTypeText},
    {Name: "body", DataType: collections.DataTypeText},
  },
  Vectors: map[string]collections.VectorConfig{
    "default": {Vectorizer: vectorizer},
  },
})
if err != nil {
  // handle error
  panic(err)
}
```

```java
client.collections.create("Article", col -> col.vectorConfig(
    VectorConfig.text2vecCohere(c -> c.model("embed-multilingual-v2.0"))));
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "Article",
        VectorConfig = new VectorConfigList
        {
            Configure.Vector(
                "default",
                v =>
                    v.Text2VecTransformers(
                    // The available settings depend on the module
                    // inferenceUrl: "http://custom-inference:8080",
                    // vectorizeCollectionName: false
                    )
            ),
        },
        Properties = [Property.Text("title"), Property.Text("body")],
    }
);
```

## Define named vectors

You can define multiple [named vectors](/weaviate/concepts/data#multiple-vector-embeddings-named-vectors) per collection. This allows each object to be represented by multiple vector embeddings, each with its own vector index.

As such, each named vector configuration can include its own vectorizer and vector index settings.

```py
from weaviate.classes.config import Configure, Property, DataType

client.collections.create(
    "ArticleNV",
    vector_config=[
        # Set a named vector with the "text2vec-cohere" vectorizer
        Configure.Vectors.text2vec_cohere(
            name="title",
            source_properties=["title"],  # (Optional) Set the source property(ies)
            vector_index_config=Configure.VectorIndex.hnsw(),  # (Optional) Set vector index options
        ),
        # Set another named vector with the "text2vec-openai" vectorizer
        Configure.Vectors.text2vec_openai(
            name="title_country",
            source_properties=[
                "title",
                "country",
            ],  # (Optional) Set the source property(ies)
            vector_index_config=Configure.VectorIndex.hnsw(),  # (Optional) Set vector index options
        ),
        # Set a named vector for your own uploaded vectors
        Configure.Vectors.self_provided(
            name="custom_vector",
            vector_index_config=Configure.VectorIndex.hnsw(),  # (Optional) Set vector index options
        ),
    ],
    properties=[  # Define properties
        Property(name="title", data_type=DataType.TEXT),
        Property(name="country", data_type=DataType.TEXT),
    ],
)
```

```ts
import { vectors, dataType } from 'weaviate-client';

await client.collections.create({
  name: 'ArticleNV',

  vectorizers: [
    // Set a named vector with the "text2vec-cohere" vectorizer
    vectors.text2VecCohere({
      name: 'title',
      sourceProperties: ['title'],                      // (Optional) Set the source property(ies)
      vectorIndexConfig: configure.vectorIndex.hnsw()   // (Optional) Set the vector index configuration
    }),
    // Set a named vector with the "text2vec-openai" vectorizer
    vectors.text2VecOpenAI({
      name: 'title_country',
      sourceProperties: ['title', 'country'],            // (Optional) Set the source property(ies)
      vectorIndexConfig: configure.vectorIndex.hnsw()   // (Optional) Set the vector index configuration
    }),
    // Set a named vector for your own uploaded vectors
    vectors.selfProvided({
      name: 'custom_vector',
      vectorIndexConfig: configure.vectorIndex.hnsw()   // (Optional) Set the vector index configuration
    })
  ],

  properties: [
    { name: 'title', dataType: dataType.TEXT },
    { name: 'country', dataType: dataType.TEXT },
  ],
})
```

```go
  articleClass := &models.Class{
    Class:       "ArticleNV",
    Description: "Collection of articles with named vectors",
    Properties: []*models.Property{
      {
        Name:     "title",
        DataType: schema.DataTypeText.PropString(),
      },
      {
        Name:     "country",
        DataType: schema.DataTypeText.PropString(),
      },
    },
    VectorConfig: map[string]models.VectorConfig{
      "title": {
        Vectorizer: map[string]interface{}{
          "text2vec-openai": map[string]interface{}{
            "properties": []string{"title"},
          },
        },
        VectorIndexType: "hnsw",
      },
      "title_country": {
        Vectorizer: map[string]interface{}{
          "text2vec-openai": map[string]interface{}{
            "properties": []string{"title", "country"},
          },
        },
        VectorIndexType: "hnsw",
      },
      "custom_vector": {
        Vectorizer: map[string]interface{}{
          "none": map[string]interface{}{},
        },
        VectorIndexType: "hnsw",
      },
    },
  }
```

```go
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Article",
  Properties: []collections.Property{
    {Name: "title", DataType: collections.DataTypeText},
    {Name: "body", DataType: collections.DataTypeText},
  },
  Vectors: map[string]collections.VectorConfig{
    // A vector generated from the title only.
    "title": {Vectorizer: model2vec.Text2Vec{Properties: []string{"title"}}},
    // A vector you supply yourself at import time.
    "custom": {Vectorizer: selfprovided.Vectorizer},
  },
})
if err != nil {
  // handle error
  panic(err)
}
```

```java
// Weaviate
client.collections
    .create("ArticleNV",
        col -> col
            .vectorConfig(
                VectorConfig.text2vecTransformers("title",
                    c -> c.sourceProperties("title")
                        .vectorIndex(Hnsw.of())),
                VectorConfig.text2vecTransformers("title_country",
                    c -> c.sourceProperties("title", "country")
                        .vectorIndex(Hnsw.of())),
                VectorConfig.selfProvided("custom_vector",
                    c -> c.vectorIndex(Hnsw.of()).vectorIndex(Hnsw.of())))
            .properties(Property.text("title"), Property.text("country")));
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "ArticleNV",
        VectorConfig = new VectorConfigList
        {
            Configure.Vector(
                "title",
                v => v.Text2VecTransformers(),
                sourceProperties: ["title"],
                index: new VectorIndex.HNSW()
            ),
            Configure.Vector(
                "title_country",
                v => v.Text2VecTransformers(),
                sourceProperties: ["title", "country"],
                index: new VectorIndex.HNSW()
            ),
            Configure.Vector(
                "custom_vector",
                v => v.SelfProvided(),
                index: new VectorIndex.HNSW()
            ),
        },
        Properties = [Property.Text("title"), Property.Text("country")],
    }
);
```

## Add new named vectors

Added in `v1.31`

Named vectors can be added to a collection that already has named vectors, to a [collection created without a vector](/weaviate/config-refs/collections#no-vector), and to a [single vector collection](/weaviate/config-refs/collections#single-vector-collections). In a single vector collection you cannot add one called `default`. See [The `default` vector name](/weaviate/config-refs/collections#default-vector-name).

```py
from weaviate.classes.config import Configure

articles = client.collections.use("Article")

articles.config.add_vector(
    vector_config=Configure.Vectors.text2vec_cohere(
        name="body_vector",
        source_properties=["body"],
    )
)
```

```ts
await articles.config.addVector(
    vectors.text2VecCohere({
        name: "body_vector",
        sourceProperties: ["body"],
    })
)
```

```go
// Coming soon
```

```java
CollectionHandle<Map<String, Object>> collection =
    client.collections.use("ArticleNV");

collection.config.update(
    u -> u.vectorConfig(VectorConfig.text2vecTransformers("title_country",
        c -> c.sourceProperties("title", "country")
            .vectorIndex(Hnsw.of()))));
```

```csharp
await articles.Config.AddVector(
    Configure.Vector("body_vector", v => v.Text2VecCohere(), sourceProperties: "body")
);
```

Objects aren't automatically revectorized

Adding a new vector to the collection definition [won't trigger vectorization for existing objects](/weaviate/concepts/data#adding-a-named-vector-after-collection-creation). Only objects created after the vector addition will receive these new vector embeddings.

## Define multi-vector embeddings (e.g. ColBERT, ColPali)

Added in `v1.30`

Multi-vector embeddings, also known as multi-vectors, represent a single object with multiple vectors, i.e. a 2-dimensional matrix. Multi-vectors are available for named vectors on `hnsw` indexes. From `v1.40`, they are also available on `hfresh` indexes [with MUVERA encoding only](/weaviate/config-refs/indexing/vector-index#hfresh-multi-vector). To use multi-vectors, enable it for the appropriate named vector.

```py
from weaviate.classes.config import Configure, Property, DataType

client.collections.create(
    "DemoCollection",
    vector_config=[
        # Example 1 - Use a model integration
        # The factory function will automatically enable multi-vector support for the HNSW index
        Configure.MultiVectors.text2vec_jinaai(
            name="jina_colbert",
            source_properties=["text"],
        ),
        # Example 2 - User-provided multi-vector representations
        # Must explicitly enable multi-vector support for the HNSW index
        Configure.MultiVectors.self_provided(
            name="custom_multi_vector",
        ),
    ],
    properties=[Property(name="text", data_type=DataType.TEXT)],
    # Additional parameters not shown
)
```

```ts
await client.collections.create({
  name: "DemoCollection",
  vectorizers: [
    // Example 1 - Use a model integration
    // The factory function will automatically enable multi-vector support for the HNSW index
    configure.multiVectors.text2VecJinaAI({
      name: "jina_colbert",
      sourceProperties: ["text"],
    }),
    // Example 2 - User-provided multi-vector representations
    // Must explicitly enable multi-vector support for the HNSW index
    configure.multiVectors.selfProvided({
      name: "custom_multi_vector",
    }),
  ],
  properties: [{ name: "text", dataType: dataType.TEXT }],
  // Additional parameters not shown
})
```

```java
client.collections.create("DemoCollection", col -> col.vectorConfig(
    // Example 1 - Use a model integration
    // The factory function will automatically enable multi-vector support for the HNSW index
    VectorConfig.text2multivecJinaAi("jina_colbert",
        vc -> vc.sourceProperties("text")
            // In Java, explicitly configure the HNSW index for multi-vector
            .vectorIndex(Hnsw.of(h -> h.multiVector(MultiVector.of())))),
    // Example 2 - User-provided multi-vector representations
    // Must explicitly enable multi-vector support for the HNSW index
    VectorConfig.selfProvided("custom_multi_vector",
        vc -> vc.vectorIndex(Hnsw.of(h -> h.multiVector(MultiVector.of()))))
).properties(Property.text("text"))
// Additional parameters not shown
);
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "DemoCollection",
        VectorConfig =
        [
            // Example 1 - Use a model integration
            Configure.MultiVector("jina_colbert", v => v.Text2MultiVecJinaAI()),
            // Example 2 - User-provided multi-vector representations
            Configure.MultiVector("custom_multi_vector", v => v.SelfProvided()),
        ],
        Properties = [Property.Text("text")],
    }
);
```

Use quantization and encoding to compress your vectors

Multi-vector embeddings use up more memory than single vector embeddings. You can use [vector quantization](/weaviate/configuration/compression) and [encoding](/weaviate/configuration/compression/multi-vectors#muvera-encoding) to compress them and reduce memory usage.

## Set vector index type

The [vector index type](/weaviate/config-refs/indexing/vector-index) can be set for each collection at creation time, between `hnsw`, `flat`, `dynamic`, and `hfresh` index types.

```py
from weaviate.classes.config import Configure, Property, DataType

client.collections.create(
    "Article",
    vector_config=Configure.Vectors.text2vec_openai(
        name="default",
        vector_index_config=Configure.VectorIndex.hnsw(),  # Use the HNSW index
        # vector_index_config=Configure.VectorIndex.flat(),  # Use the FLAT index
        # vector_index_config=Configure.VectorIndex.dynamic(),  # Use the DYNAMIC index
        # vector_index_config=Configure.VectorIndex.hfresh(),  # Use the HFRESH index
    ),
    properties=[
        Property(name="title", data_type=DataType.TEXT),
        Property(name="body", data_type=DataType.TEXT),
    ],
)
```

```ts
import { vectors, dataType, configure } from 'weaviate-client';

await client.collections.create({
  name: 'Article',
  vectorizers: vectors.text2VecOpenAI({
    vectorIndexConfig: configure.vectorIndex.hnsw(),  // Use HNSW
    // vectorIndexConfig: configure.vectorIndex.flat(),  // Use Flat
    // vectorIndexConfig: configure.vectorIndex.dynamic(),  // Use Dynamic
    // vectorIndexConfig: configure.vectorIndex.hfresh(),  // Use HFresh
  }),
  properties: [
    { name: 'title', dataType: dataType.TEXT },
    { name: 'body', dataType: dataType.TEXT },
  ],
})
```

```go
  articleClass := &models.Class{
    Class:       "Article",
    Description: "Collection of articles",
    Properties: []*models.Property{
      {
        Name:     "title",
        DataType: schema.DataTypeText.PropString(),
      },
      {
        Name:     "country",
        DataType: schema.DataTypeText.PropString(),
      },
    },
    Vectorizer:      "text2vec-openai",
    VectorIndexType: "hnsw", // Or "flat", "dynamic", "hfresh"
  }
```

```go
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Article",
  Properties: []collections.Property{
    {Name: "title", DataType: collections.DataTypeText},
    {Name: "body", DataType: collections.DataTypeText},
  },
  Vectors: map[string]collections.VectorConfig{
    "default": {
      Vectorizer: openai.Text2Vec{},
      Index: vectorindex.HNSW{}, // Use the HNSW index
      // Index: vectorindex.Flat{}, // Use the flat index
      // Index: vectorindex.Dynamic{Threshold: 10000}, // Use the dynamic index
      // Index: vectorindex.HFresh{MaxPostingSizeKB: 8}, // Use the HFresh index
    },
  },
})
if err != nil {
  // handle error
  panic(err)
}
```

```java
client.collections.create("Article",
    col -> col
        .vectorConfig(VectorConfig
            .text2vecTransformers(vec -> vec.vectorIndex(Hnsw.of())))
        .properties(Property.text("title"), Property.text("body")));
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "Article",
        VectorConfig = new VectorConfigList
        {
            Configure.Vector(
                "default",
                v => v.Text2VecTransformers(),
                index: new VectorIndex.HNSW()
            ),
        },
        Properties = [Property.Text("title"), Property.Text("body")],
    }
);
```

Additional information

Read more about index types & compression in:

* [References: Vector index](/weaviate/config-refs/indexing/vector-index)
* [Concepts: Vector index](/weaviate/concepts/vector-index)

## Set vector index parameters

Set [vector index parameters](/weaviate/config-refs/indexing/vector-index) such as [compression](/weaviate/configuration/compression) and [filter strategy](/weaviate/concepts/filtering#filter-strategy) through collection configuration. Some parameters can be [updated later](/weaviate/manage-collections/collection-operations#update-a-collection-definition) after collection creation.

```py
from weaviate.classes.config import (
    Configure,
    Property,
    DataType,
    VectorDistances,
    VectorFilterStrategy,
)

client.collections.create(
    "Article",
    vector_config=Configure.Vectors.text2vec_openai(
        name="default",
        vector_index_config=Configure.VectorIndex.hnsw(
            ef_construction=300,
            distance_metric=VectorDistances.COSINE,
            filter_strategy=VectorFilterStrategy.ACORN,
        ),
    ),
)
```

```ts
import { configure, vectors } from 'weaviate-client';

await client.collections.create({
  name: 'Article',
  // Additional configuration not shown
  vectorizers: vectors.text2VecCohere({
    vectorIndexConfig: configure.vectorIndex.flat({
      quantizer: configure.vectorIndex.quantizer.bq({
        rescoreLimit: 200,
        cache: true
      }),
      vectorCacheMaxObjects: 100000
    })
  })
})
```

```go
  articleClass := &models.Class{
    Class:       "Article",
    Description: "Collection of articles",
    Properties: []*models.Property{
      {
        Name:     "title",
        DataType: schema.DataTypeText.PropString(),
      },
      {
        Name:     "country",
        DataType: schema.DataTypeText.PropString(),
      },
    },
    Vectorizer:      "text2vec-openai",
    VectorIndexType: "hnsw",
    VectorIndexConfig: map[string]interface{}{
      "bq": map[string]interface{}{
        "enabled": true,
      },
      "efConstruction": 300,
      "distance":       "cosine",
      "filterStrategy": "acorn",
    },
  }
```

```go
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Article",
  Vectors: map[string]collections.VectorConfig{
    "default": {
      Vectorizer: openai.Text2Vec{},
      Index: vectorindex.HNSW{
        EfConstruction: 300,
        Distance:       vectorindex.DistanceCosine,
        FilterStrategy: vectorindex.FilterStrategyACORN,
      },
    },
  },
})
if err != nil {
  // handle error
  panic(err)
}
```

```java
client.collections.create("Article", col -> col
    .vectorConfig(
        VectorConfig.text2vecTransformers(vec -> vec.vectorIndex(Hnsw.of(
            hnsw -> hnsw.efConstruction(300).distance(Distance.COSINE)))))
    .properties(Property.text("title")));
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "Article",
        VectorConfig = new[]
        {
            Configure.Vector(
                "default",
                v => v.Text2VecTransformers(),
                index: new VectorIndex.HNSW()
                {
                    EfConstruction = 300,
                    Distance = VectorDistance.Cosine,
                }
            ),
        },
        Properties = [Property.Text("title")],
    }
);
```

Additional information

Read more about index types & compression in:

* [References: Vector index](/weaviate/config-refs/indexing/vector-index)
* [Concepts: Vector index](/weaviate/concepts/vector-index)

## Property-level settings

Configure individual properties in a collection. Each property can have it's own configuration. Here are some common settings:

* Vectorize the property
* Vectorize the property name
* Set a [tokenization type](/weaviate/config-refs/collections#tokenization)

```py
from weaviate.classes.config import Configure, Property, DataType, Tokenization

client.collections.create(
    "Article",
    vector_config=Configure.Vectors.text2vec_cohere(),
    properties=[
        Property(
            name="title",
            data_type=DataType.TEXT,
            vectorize_property_name=True,  # Use "title" as part of the value to vectorize
            tokenization=Tokenization.LOWERCASE,  # Use "lowercase" tokenization
            description="The title of the article.",  # Optional description
        ),
        Property(
            name="body",
            data_type=DataType.TEXT,
            skip_vectorization=True,  # Don't vectorize this property
            tokenization=Tokenization.WHITESPACE,  # Use "whitespace" tokenization
        ),
    ],
)
```

```ts
import { vectors, dataType, tokenization } from 'weaviate-client';

  const newCollection = await client.collections.create({
    name: 'Article',
    vectorizers: vectors.text2VecHuggingFace(),
    properties: [
      {
        name: 'title',
        dataType: dataType.TEXT,
        vectorizePropertyName: true,
        tokenization: tokenization.LOWERCASE // or 'lowercase'
      },
      {
        name: 'body',
        dataType: dataType.TEXT,
        skipVectorization: true,
        tokenization: tokenization.WHITESPACE // or 'whitespace'
      },
    ],
  })
```

```go
  vTrue := true
  vFalse := false

  articleClass := &models.Class{
    Class:       "Article",
    Description: "Collection of articles",
    Properties: []*models.Property{
      {
        Name:            "title",
        DataType:        schema.DataTypeText.PropString(),
        Tokenization:    "lowercase",
        IndexFilterable: &vTrue,
        IndexSearchable: &vFalse,
        ModuleConfig: map[string]interface{}{
          "text2vec-cohere": map[string]interface{}{
            "vectorizePropertyName": true,
          },
        },
      },
      {
        Name:            "body",
        DataType:        schema.DataTypeText.PropString(),
        Tokenization:    "whitespace",
        IndexFilterable: &vTrue,
        IndexSearchable: &vTrue,
        ModuleConfig: map[string]interface{}{
          "text2vec-cohere": map[string]interface{}{
            "vectorizePropertyName": false,
          },
        },
      },
    },
    Vectorizer: "text2vec-cohere",
  }
```

```go
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Article",
  Properties: []collections.Property{
    {
      Name:     "title",
      DataType: collections.DataTypeText,
      Tokenization: collections.TokenizationLowercase, // Use "lowercase" tokenization
      Description:  "The title of the article.",       // Optional description
    },
    {
      Name:     "body",
      DataType: collections.DataTypeText,
      Tokenization: collections.TokenizationWhitespace, // Use "whitespace" tokenization
    },
  },
  Vectors: map[string]collections.VectorConfig{
    // Vectorize the title only. The body is left out of the vector.
    "default": {Vectorizer: model2vec.Text2Vec{Properties: []string{"title"}}},
  },
})
if err != nil {
  // handle error
  panic(err)
}
```

```java
client.collections.create("Article",
    col -> col.properties(
        Property.text("title",
            p -> p.description("The title of the article.")
                .tokenization(Tokenization.LOWERCASE)
                .vectorizePropertyName(false)),
        Property.text("body", p -> p.skipVectorization(true)
            .tokenization(Tokenization.WHITESPACE))));
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "Article",
        Properties =
        [
            Property.Text("title", tokenization: PropertyTokenization.Lowercase),
            Property.Text("body", tokenization: PropertyTokenization.Whitespace),
        ],
    }
);
```

## Specify a distance metric

If you choose to bring your own vectors, you should specify the `distance metric`.

```py
from weaviate.classes.config import Configure, VectorDistances

client.collections.create(
    "Article",
    vector_config=Configure.Vectors.text2vec_openai(
        vector_index_config=Configure.VectorIndex.hnsw(
            distance_metric=VectorDistances.COSINE
        ),
    ),
)
```

```ts
import { configure, vectors, vectorDistances } from 'weaviate-client';

await client.collections.create({
  name: 'Article',
  vectorizers: vectors.text2VecOllama({
    vectorIndexConfig: configure.vectorIndex.hnsw({
      distanceMetric: vectorDistances.COSINE // or 'cosine'
    })
  })
})
```

```go
  articleClass := &models.Class{
    Class:       "Article",
    Description: "Collection of articles",
    VectorIndexConfig: map[string]interface{}{
      "distance": "cosine",
    },
  }
```

```go
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Article",
  Vectors: map[string]collections.VectorConfig{
    "default": {
      Vectorizer: selfprovided.Vectorizer,
      Index: vectorindex.HNSW{Distance: vectorindex.DistanceCosine},
    },
  },
})
if err != nil {
  // handle error
  panic(err)
}
```

```java
client.collections.create("Article",
    col -> col
        .vectorConfig(VectorConfig.text2vecTransformers(vec -> vec
            .vectorIndex(Hnsw.of(hnsw -> hnsw.distance(Distance.COSINE)))))
        .properties(Property.text("title")));
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "Article",
        VectorConfig = new[]
        {
            Configure.Vector(
                "default",
                v => v.Text2VecTransformers(),
                index: new VectorIndex.HNSW() { Distance = VectorDistance.Cosine }
            ),
        },
        Properties = [Property.Text("title")],
    }
);
```

Additional information

For details on the configuration parameters, see the following:

* [Distances](/weaviate/config-refs/distances)
* [Vector indexes](/weaviate/config-refs/indexing/vector-index)

## Further resources

* [API References: REST: Schema](/weaviate/api/rest#tag/schema/post/schema)
* [References: Configuration: Schema](/weaviate/config-refs/collections)
* [Concepts: Data structure](/weaviate/concepts/data)

## Questions and feedback

Have a question or feedback? Here's how to reach us.

[Community Forum

Ask questions and connect with other developers on our Community forum.](https://forum.weaviate.io/c/support)[Support

Weaviate Cloud user or customer? Find the right channel on the Support page.](/support)
