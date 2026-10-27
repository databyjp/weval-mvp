Source: https://docs.weaviate.io/weaviate/manage-collections/collection-operations

# Basic collection operations

Every object in Weaviate belongs to exactly one collection. Use the examples on this page to manage your collections.

Terminology

Newer Weaviate documentation discuses "collections." Older Weaviate documentation refers to "classes" instead. Expect to see both terms throughout the documentation.

Python and JS/TS client - Vectorizer Configuration API Changes

Starting with Weaviate Python client `v4.16.0`, the [vectorizer configuration API has been updated](/weaviate/client-libraries/python#vectorizer-api-changes-v4160).
Starting with Weaviate JS/TS client `v3.8.0`, the [vectorizer configuration API has been updated](/weaviate/client-libraries/typescript#vectorizer-api-changes-v380).

Action required: **Update to the latest client version** and migrate your code to use the [new vectorizer configuration API](/weaviate/manage-collections/vector-config#specify-a-vectorizer).

## Create a collection

To create a collection, specify at least the collection name. If you don't specify any properties, [`auto-schema`](/weaviate/config-refs/collections#auto-schema) creates them.

From `v1.40`, a definition that sets only the name creates a [collection without a vector](/weaviate/config-refs/collections#no-vector).

Capitalization

Weaviate follows GraphQL naming conventions.

* Start collection names with an upper case letter.
* Start property names with a lower case letter.

If you use an initial upper case letter to define a property name, Weaviate changes it to a lower case letter internally.

```py
client.collections.create("Article")
```

```ts
  const newCollection = await client.collections.create({
    name: 'Article'
  })

  // The returned value is the full collection definition, showing all defaults
  console.log(JSON.stringify(newCollection, null, 2));
```

```go
className := "Article"

  emptyClass := &models.Class{
    Class: className,
  }

  // Create the collection (also called class)
  err := client.Schema().ClassCreator().
    WithClass(emptyClass).
    Do(ctx)
```

```go
_, err := client.Collections.Create(ctx, collections.Collection{
  Name: "Article",
})
if err != nil {
  // handle error
  panic(err)
}
```

```java
client.collections.create("Article");
```

```csharp
await client.Collections.Create(new CollectionCreateParams { Name = "Article" });
```

Production ready collections

* **Manually define you data schema**:
  Avoid using the [`auto-schema`](/weaviate/config-refs/collections#auto-schema) feature, instead, manually [define the properties for your collection](#create-a-collection-and-define-properties).
* **Avoid creating too many collections**:
  Using too many collections can lead to scalability issues like high memory usage and degraded query performance. Instead, consider [using multi-tenancy](/weaviate/manage-collections/multi-tenancy), where a single collection is subdivided into multiple tenants. For more details, see [Starter Guides: Scaling limits with collections](/weaviate/starter-guides/managing-collections/collections-scaling-limits).

## Create a collection and define properties

Properties are the data fields in your collection. Each property has a name and a data type.

Additional information

Use properties to configure additional parameters such as data type, index characteristics, or tokenization.

For details, see:

* [References: Configuration: Schema](/weaviate/config-refs/collections)
* [API References: REST: Schema](/weaviate/api/rest\#tag/schema)
* [Available data types](/weaviate/config-refs/datatypes)

```py
from weaviate.classes.config import Property, DataType

# Note that you can use `client.collections.create_from_dict()` to create a collection from a v3-client-style JSON object
client.collections.create(
    "Article",
    properties=[
        Property(name="title", data_type=DataType.TEXT),
        Property(name="body", data_type=DataType.TEXT),
    ],
)
```

```ts
import { dataType } from 'weaviate-client';

await client.collections.create({
  name: 'Article',
  properties: [
    {
      name: 'title',
      dataType: dataType.TEXT,
    },
    {
      name: 'body',
      dataType: dataType.TEXT,
    },
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
})
if err != nil {
  // handle error
  panic(err)
}
```

```java
client.collections.create("Article",
    col -> col.properties(Property.text("title"), Property.text("body")));
```

```csharp
await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "Article",
        Properties = [Property.Text("title"), Property.Text("body")],
    }
);
```

Or by using the fields from a class:

```csharp
// public class Article
// {
//     public string Title { get; set; }
//     public string Body { get; set; }
// }

await client.Collections.Create(
    new CollectionCreateParams
    {
        Name = "Article",
        Properties = [.. Property.FromClass<Article>()],
    }
);
```

## Create a collection with a vectorizer

Specify a `vectorizer` for a collection that will generate vector embeddings when creating objects and executing vector search queries.

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

Vectorizer configuration

Find out more about the vectorizer and vector index configuration in [Manage collections: Vectorizer and vector index](/weaviate/manage-collections/vector-config).

## Disable auto-schema

By default, Weaviate creates missing collections and missing properties. When you configure collections manually, you have more precise control of the collection settings.

To disable [`auto-schema`](/weaviate/config-refs/collections#auto-schema) set `AUTOSCHEMA_ENABLED: 'false'` in your system configuration file.

## Check if a collection exists

Get a boolean indicating whether a given collection exists.

```py
exists = client.collections.exists("Article")  # Returns a boolean
```

```ts
var exists = await client.collections.exists("Article")  // Returns a boolean
```

```go
exists, err := client.Collections.Exists(ctx, "Article")
if err != nil {
  // handle error
  panic(err)
}
fmt.Println(exists)
```

```java
client.collections.exists(collectionName);
```

```csharp
bool exists = await client.Collections.Exists("Article");
```

## Read a single collection definition

Retrieve a collection definition from the schema.

```py
articles = client.collections.use("Article")
articles_config = articles.config.get()

print(articles_config)
```

```ts
let articles = client.collections.use('Article')
const collectionConfig = await articles.config.get()
console.log(collectionConfig)
```

```go
className := "Article"

  class, err := client.Schema().ClassGetter().
    WithClassName(className).
    Do(ctx)

  b, err := json.MarshalIndent(class, "", "  ")
  fmt.Println(string(b))
```

```go
config, err := client.Collections.GetConfig(ctx, "Article")
if err != nil {
  // handle error
  panic(err)
}
fmt.Println(config.Name)
for _, p := range config.Properties {
  fmt.Printf("  %s (%s)\n", p.Name, p.DataType)
}
```

```java
CollectionHandle<Map<String, Object>> articles =
    client.collections.use("Article");
Optional<CollectionConfig> articlesConfig = articles.config.get();

System.out.println(articlesConfig);
```

```csharp
var articles = client.Collections.Use("Article");
var articlesConfig = await articles.Config.Get();

Console.WriteLine(articlesConfig);
```

Sample configuration: Text objects

This configuration for text objects defines the following:

* The collection name (`Article`)
* The vectorizer module (`text2vec-cohere`) and model (`embed-multilingual-v2.0`)
* A set of properties (`title`, `body`) with `text` data types.

```json
{
  "class": "Article",
  "vectorizer": "text2vec-cohere",
  "moduleConfig": {
    "text2vec-cohere": {
      "model": "embed-multilingual-v2.0"
    }
  },
  "properties": [
    {
      "name": "title",
      "dataType": ["text"]
    },
    {
      "name": "body",
      "dataType": ["text"]
    }
  ]
}
```

Sample configuration: Nested objects

This configuration for nested objects defines the following:

* The collection name (`Person`)
* The vectorizer module (`text2vec-huggingface`)
* A set of properties (`last_name`, `address`)

  + `last_name` has `text` data type
  + `address` has `object` data type
* The `address` property has two nested properties (`street` and `city`)

```json
{
  "class": "Person",
  "vectorizer": "text2vec-huggingface",
  "properties": [
    {
      "dataType": ["text"],
      "name": "last_name"
    },
    {
      "dataType": ["object"],
      "name": "address",
      "nestedProperties": [
        { "dataType": ["text"], "name": "street" },
        { "dataType": ["text"], "name": "city" }
      ]
    }
  ]
}
```

To filter on values inside nested objects, see [Filter on nested object properties](/weaviate/search/filters#filter-on-nested-object-properties).

Sample configuration: Generative search

This configuration for [retrieval augmented generation](/weaviate/search/generative) defines the following:

* The collection name (`Article`)
* The vectorizer (`text2vec-openai`)
* The generative module (`generative-openai`)
* A set of properties (`title`, `chunk`, `chunk_no` and `url`)
* The tokenization option for the `url` property
* The vectorization option (`skip` vectorization) for the `url` property

```json
{
  "class": "Article",
  "vectorizer": "text2vec-openai",
  "vectorIndexConfig": {
    "distance": "cosine"
  },
  "moduleConfig": {
    "generative-openai": {}
  },
  "properties": [
    {
      "name": "title",
      "dataType": ["text"]
    },
    {
      "name": "chunk",
      "dataType": ["text"]
    },
    {
      "name": "chunk_no",
      "dataType": ["int"]
    },
    {
      "name": "url",
      "dataType": ["text"],
      "tokenization": "field",
      "moduleConfig": {
        "text2vec-openai": {
          "skip": true
        }
      }
    }
  ]
}
```

Sample configuration: Images

This configuration for image search defines the following:

* The collection name (`Image`)
* The vectorizer module (`img2vec-neural`)

  + The `image` property configures collection to store image data.
* The vector index distance metric (`cosine`)
* A set of properties (`image`), with the `image` property set as `blob`.

For image searches, see [Image search](/weaviate/search/image).

```json
{
  "class": "Image",
  "vectorizer": "img2vec-neural",
  "vectorIndexConfig": {
    "distance": "cosine"
  },
  "moduleConfig": {
    "img2vec-neural": {
      "imageFields": ["image"]
    }
  },
  "properties": [
    {
      "name": "image",
      "dataType": ["blob"]
    }
  ]
}
```

## Read all collection definitions

Fetch the database schema to retrieve all of the collection definitions.

```py
response = client.collections.list_all(simple=False)

print(response)
```

```ts
const allCollections = await client.collections.listAll()
console.log(JSON.stringify(allCollections, null, 2));
```

```go
  schema, err := client.Schema().Getter().
    Do(ctx)

  b, err := json.MarshalIndent(schema, "", "  ")
  fmt.Println(string(b))
```

```go
configs, err := client.Collections.List(ctx)
if err != nil {
  // handle error
  panic(err)
}
for _, config := range configs {
  fmt.Println(config.Name)
}
```

```java
List<CollectionConfig> response = client.collections.list();

System.out.println(response);
```

```csharp
var response = new List<CollectionConfig>();
await foreach (var collection in client.Collections.List())
{
    response.Add(collection);
    Console.WriteLine(collection);
}
```

## Update a collection definition

Replication factor change

The replication factor of a collection cannot be updated by updating the collection's definition.

From `v1.32` by using [replica movement](/deploy/configuration/replica-movement), the [replication factor](/weaviate/config-refs/collections#replication) of a shard can be changed.

You can update a collection definition to change the [mutable collection settings](/weaviate/config-refs/collections#mutability).

```py
from weaviate.classes.config import (
    Reconfigure,
    VectorFilterStrategy,
    ReplicationDeletionStrategy,
)

articles = client.collections.use("Article")

# Update the collection definition
articles.config.update(
    description="An updated collection description.",
    property_descriptions={
        "title": "The updated title description for article",
    },  # Available from Weaviate v1.31.0
    inverted_index_config=Reconfigure.inverted_index(bm25_k1=1.5),
    vector_config=Reconfigure.Vectors.update(
        name="default",
        vector_index_config=Reconfigure.VectorIndex.hnsw(
            filter_strategy=VectorFilterStrategy.ACORN  # Available from Weaviate v1.27.0
        ),
    ),
    replication_config=Reconfigure.replication(
        deletion_strategy=ReplicationDeletionStrategy.TIME_BASED_RESOLUTION  # Available from Weaviate v1.28.0
    ),
)
articles = client.collections.use("Article")

article_shards = articles.config.update_shards(
    status="READY",
    shard_names=shard_names,  # The names (List[str]) of the shard to update (or a shard name)
)

print(article_shards)
```

```ts
import { reconfigure } from 'weaviate-client';

let articles = client.collections.use('Article')
await articles.config.update({
  invertedIndex: reconfigure.invertedIndex({
    bm25k1: 1.5 // Change the k1 parameter from 1.2
  }),
  vectorizers: reconfigure.vectors.update({
    vectorIndexConfig: reconfigure.vectorIndex.hnsw({
      quantizer: reconfigure.vectorIndex.quantizer.pq(),
      ef: 4,
      filterStrategy: 'acorn',  // Available from Weaviate v1.27.0
    }),

  })
})
```

```go
  updatedArticleClassConfig := &models.Class{
    // Note: The new collection config must be provided in full,
    // including the configuration that is not being updated.
    // We suggest using the original class config as a starting point.
    Class: "Article",
    InvertedIndexConfig: &models.InvertedIndexConfig{
      Bm25: &models.BM25Config{
        K1: 1.5,
      },
    },
    VectorIndexConfig: map[string]interface{}{
      "filterStrategy": "acorn",
    },
    ReplicationConfig: &models.ReplicationConfig{
      DeletionStrategy: models.ReplicationConfigDeletionStrategyTimeBasedResolution,
    },
  }
```

```go
// Coming soon
```

```java
CollectionHandle<Map<String, Object>> articles =
    client.collections.use("Article");

articles.config.update(col -> col
    .description("An updated collection description.")
    .invertedIndex(idx -> idx.bm25(bm25Builder -> bm25Builder.k1(1.5f))));
CollectionHandle<Map<String, Object>> articles =
    client.collections.use("Article");

List<Shard> articleShards =
    articles.config.updateShards(ShardStatus.READONLY, shardName);
System.out.println(articleShards);
```

```csharp
var articles = client.Collections.Use("Article");

await articles.Config.Update(c =>
{
    c.Description = "An updated collection description.";
    c.InvertedIndexConfig.Bm25.K1 = 1.5f;
});
    // Coming soon
```

## Delete a collection

You can delete any unwanted collection(s), along with the data that they contain.

Deleting a collection also deletes its objects

When you **delete a collection, you delete all associated objects**!

Be very careful with deletes on a production database and anywhere else that you have important data.

This code deletes a collection and its objects.

```py
# collection_name can be a string ("Article") or a list of strings (["Article", "Category"])
client.collections.delete(
    collection_name
)  # THIS WILL DELETE THE SPECIFIED COLLECTION(S) AND THEIR OBJECTS

# Note: you can also delete all collections in the Weaviate instance with:
# client.collections.delete_all()
```

```ts
// delete collection "Article" - THIS WILL DELETE THE COLLECTION AND ALL ITS DATA
await client.collections.delete('Article')

// you can also delete all collections of a cluster
// await client.collections.deleteAll()
```

```go
className := "YourClassName"

// delete the class
if err := client.Schema().ClassDeleter().WithClassName(className).Do(context.Background()); err != nil {
  // Weaviate will return a 400 if the class does not exist, so this is allowed, only return an error if it's not a 400
  if status, ok := err.(*fault.WeaviateClientError); ok && status.StatusCode != http.StatusBadRequest {
    panic(err)
  }
}
```

```java
client.collections.delete(collectionName);
```

```bash
curl \
  -X DELETE \
  https://WEAVIATE_INSTANCE_URL/v1/schema/YourClassName  # Replace WEAVIATE_INSTANCE_URL with your instance URL
```

```csharp
await client.Collections.Delete(collectionName);
```

## Add a property

You can add new properties to a collection, but you cannot change an existing one. See [Collection definition: Mutability](/weaviate/config-refs/collections#mutability) for the full list of what can change after creation.

Indexing limitations after data import

There are no index limitations when you add collection properties before you import data.

If you add a new property after you import data, there is an impact on indexing.

Property indexes are built at import time. If you add a new property after importing some data, pre-existing objects index aren't automatically updated to add the new property. This means pre-existing objects aren't added to the new property index. Queries may return unexpected results because the index only includes new objects.

To create an index that includes all of the objects in a collection, do one of the following:

* New collections: Add all of the collection's properties before importing objects.
* Existing collections: Export the existing data from the collection. Re-create it with the new property. Import the data into the updated collection.

We are working on a re-indexing API to allow you to re-index the data after adding a property. This will be available in a future release.

```py
from weaviate.classes.config import Property, DataType

articles = client.collections.use("Article")

articles.config.add_property(Property(name="onHomepage", data_type=DataType.BOOL))
```

```js
let articles = client.collections.use('Article')

articles.config.addProperty({
  name: "onHomepage",
  dataType: "boolean",
});
```

```go
package main

import (
  "context"

  "github.com/weaviate/weaviate-go-client/v5/weaviate"
  "github.com/weaviate/weaviate/entities/models"
)

func main() {
  cfg := weaviate.Config{
    Host:   "localhost:8080",
    Scheme: "http",
  }
  client, err := weaviate.NewClient(cfg)
  if err != nil {
    panic(err)
  }

  prop := &models.Property{
    DataType: []string{"boolean"},
    Name:     "onHomepage",
  }

  err := client.Schema().PropertyCreator().
    WithClassName("Article").
    WithProperty(prop).
    Do(context.Background())

  if err != nil {
    panic(err)
  }
}
```

```java
CollectionHandle<Map<String, Object>> articles =
    client.collections.use("Article");

articles.config.addProperty(Property.bool("onHomepage"));
```

```csharp
CollectionClient articles = client.Collections.Use("Article");
await articles.Config.AddProperty(Property.Text("description"));
```

## Further resources

* [Manage collections: Vectorizer and vector index](/weaviate/manage-collections/vector-config)
* [References: Collection definition](/weaviate/config-refs/collections)
* [Concepts: Data structure](/weaviate/concepts/data)
* [API References: REST: Schema](/weaviate/api/rest\#tag/schema/post/schema)

## Questions and feedback

Have a question or feedback? Here's how to reach us.

[Community Forum

Ask questions and connect with other developers on our Community forum.](https://forum.weaviate.io/c/support)[Support

Weaviate Cloud user or customer? Find the right channel on the Support page.](/support)
