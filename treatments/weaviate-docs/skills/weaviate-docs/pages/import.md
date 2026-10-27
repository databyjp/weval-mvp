Source: https://docs.weaviate.io/weaviate/manage-objects/import

# Batch import

[Batch imports](/weaviate/tutorials/import) are an efficient way to add multiple data objects and cross-references. For most use cases, we recommend **server-side batching** as the starting point: the server tells the client how much data to send next, so you don't have to tune batch parameters yourself. When you need manual control over the batch size and concurrency, or you are using a client that does not yet support server-side batching, use [manual batching](#manual-batching) instead.

## Server-side batching

Added in `v1.36`

With [server-side batch imports](/weaviate/concepts/data-import#server-side-batching) (also called "automatic" batching), the client sends data in batch sizes determined by feedback from the server. This simplifies your code and helps the server manage its own load. Server-side batching offers two entry points:

* **Stream from a data source** (recommended for large datasets): Add objects to the import one at a time as you read them from the source, so the full dataset never has to fit in memory.
* **[Ingest an in-memory list](#ingest-an-in-memory-list)**: Import a list of objects that you already hold in memory with a single call.

Server-side batching uses the [gRPC API](/weaviate/api), which current client versions enable by default.

The following example adds objects to a collection named `MyCollection`.

Open the `batch.stream()` context manager and add objects one at a time; the client sends them at the pace the server requests. The [async Python client](/weaviate/client-libraries/python/async#bulk-data-insertion) also supports server-side batching through the `stream()` method and the one-shot `ingest()` method.

```py
data_rows = [{"title": f"Object {i + 1}"} for i in range(5)]

collection = client.collections.use("MyCollection")

# Use `stream` for server-side batching. The client will send data
# in batches at a rate specified by the server.
with collection.batch.stream() as batch:
    for data_row in data_rows:
        batch.add_object(
            properties=data_row,
        )
        if batch.number_errors > 10:
            print("Batch import stopped due to excessive errors.")
            break

failed_objects = collection.batch.failed_objects
if failed_objects:
    print(f"Number of failed imports: {len(failed_objects)}")
    print(f"First failed object: {failed_objects[0]}")
```

You can also stream from a data source with `data.ingest()`. It accepts any iterable, so you can pass a generator that reads a source file record by record. Objects go to the server as the generator produces them, so the source never has to fit in memory. To import objects that you already hold in a list, see [Ingest an in-memory list](#ingest-an-in-memory-list).

```py
import json


# Each line of the source file holds one JSON object
def read_objects(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:  # Skip blank lines
                continue
            record = json.loads(line)
            yield {"title": record["title"]}


collection = client.collections.use("MyCollection")

# `ingest` pulls objects from the generator as it goes
result = collection.data.ingest(read_objects("my-data.jsonl"))

if result.errors:
    print(f"Number of failed imports: {len(result.errors)}")
```

In TypeScript, `data.ingest()` is the server-side batching API, with no separate streaming context. It accepts any `Iterable`, so passing a generator streams objects to the server without building the full list in memory.

```ts
const myCollection = client.collections.use('MyCollection')

// `ingest` is the TypeScript server-side batching API. It accepts any
// Iterable, so passing a generator streams objects to the server
// without building the full list in memory.
function* generateData(): Generator<{ properties: { title: string } }> {
  for (let i = 1; i <= 5; i++) {
    yield { properties: { title: `Object ${i}` } }
  }
}

const result = await myCollection.data.ingest(generateData())

console.log(result)
```

This client does not support server-side batching. Use [manual batching](#manual-batching) instead.

```go
dataRows := make([]map[string]any, 0, 5)
for i := range 5 {
  dataRows = append(dataRows, map[string]any{"title": fmt.Sprintf("Object %d", i+1)})
}

collection := client.Collections.Use("MyCollection")

// Open a server-side batch stream. The client sends objects
// at the rate the server requests.
b := collection.Batch(ctx, batch.WithRetryTimes(1))

tasks := make([]*batch.Task, 0, len(dataRows))
for _, row := range dataRows {
  task, err := b.Object(ctx, &data.Object{Properties: row})
  if err != nil {
    // handle error
    panic(err)
  }
  tasks = append(tasks, task)
}

// Close blocks until every task has completed.
if err := b.Close(); err != nil {
  // handle error
  panic(err)
}

// Wait returns the error of a task that failed.
failed := 0
for _, task := range tasks {
  if err := task.Wait(); err != nil {
    failed++
    fmt.Printf("Failed to import %s: %v\n", task.ID(), err)
  }
}
if failed > 0 {
  fmt.Printf("Number of failed imports: %d\n", failed)
}
```

Open a streaming context with `collection.batch.start()` and add objects one at a time. The batch is flushed and closed automatically when the try-with-resources block exits.

```java
List<Map<String, Object>> dataRows = new ArrayList<>();
for (int i = 0; i < 5; i++) {
  dataRows.add(Map.of("title", "Object " + (i + 1)));
}

var collection = client.collections.use("MyCollection");

// Use `batch.start()` for server-side batching. The client sends data
// in batches at a rate controlled by the server. The batch is flushed
// and closed automatically when the try-with-resources block exits.
BatchContext<Map<String, Object>> batch = collection.batch.start();
try (batch) {
  for (Map<String, Object> dataRow : dataRows) {
    batch.add(WeaviateObject.<Map<String, Object>>of(
        obj -> obj.properties(dataRow)));
  }
} catch (InterruptedException e) {
  Thread.currentThread().interrupt();
}

// numberOfErrors() reports objects that could not be imported.
if (batch.numberOfErrors() > 0) {
  System.err
      .println("Number of failed imports: " + batch.numberOfErrors());
}
```

Open a streaming batch with `collection.Batch.StartBatch()` and add objects one at a time with `Add`. Call `Close` to flush the batch.

```csharp
var dataRows = Enumerable
    .Range(0, 5)
    .Select(i => new { title = $"Object {i + 1}" })
    .ToList();

var collection = client.Collections.Use("MyCollection");

// Use `Batch.StartBatch` for server-side batching. The client streams
// objects to the server, which paces the import based on its own load.
await using var batch = await collection.Batch.StartBatch();

var handles = new List<TaskHandle>();
foreach (var dataRow in dataRows)
{
    handles.Add(await batch.Add(dataRow));
}

await batch.Close();

var results = await Task.WhenAll(handles.Select(h => h.Result));
var failedObjects = results.Where(r => !r.Success).ToList();
if (failedObjects.Any())
{
    Console.WriteLine($"Number of failed imports: {failedObjects.Count}");
}
```

### Ingest an in-memory list

If your objects are already in memory, you can import the whole list with a single call. The client sends the list using server-side batching, so the import is safe for large lists that would exceed the server's [`GRPC_MAX_MESSAGE_SIZE`](/deploy/configuration/env-vars#GRPC_MAX_MESSAGE_SIZE) limit if sent as one request.

`data.ingest()` is the safe replacement for passing a large list to `insert_many`, which sends all objects in a single request. `ingest` accepts plain property dicts or `DataObject` instances (to set object IDs, vectors, or references) and returns the same return object as `insert_many`.

```py
data_rows = [{"title": f"Object {i + 1}"} for i in range(5)]

collection = client.collections.use("MyCollection")

# `ingest` imports the whole list with server-side batching in a single call
result = collection.data.ingest(data_rows)

# The return object is the same as for `insert_many`
if result.errors:
    print(f"Number of failed imports: {len(result.errors)}")
    # `errors` is a dict keyed by the index of the failed object
    for index, error in result.errors.items():
        print(f"Failed object at index {index}: {error.message}")
```

When your objects are already in an array, pass the array directly to `data.ingest()` to import the whole list in a single call.

```ts
const dataObjects = [
  { properties: { title: 'Object 1' } },
  { properties: { title: 'Object 2' } },
  { properties: { title: 'Object 3' } },
  { properties: { title: 'Object 4' } },
  { properties: { title: 'Object 5' } },
]

const myCollection = client.collections.use('MyCollection')

// `ingest` imports the whole list with server-side batching in a single call
const result = await myCollection.data.ingest(dataObjects)

console.log(result)
```

The Go client does not support server-side batching; use [manual batching](#manual-batching) instead.

The Java client does not provide a one-shot ingest method. Use the streaming context `collection.batch.start()` shown in the [server-side batching example](#server-side-batching) above. Note that `collection.data.insertMany(...)` sends all objects in a single request and does not use server-side batching.

In the C# client, `Batch.InsertMany` uses server-side batching under the hood.

```csharp
var dataRows = Enumerable
    .Range(0, 5)
    .Select(i => new { title = $"Object {i + 1}" })
    .ToList();

var collection = client.Collections.Use("MyCollection");

// `Batch.InsertMany` is the one-shot server-side ingest of an
// in-memory list. The client streams the list to the server
// using server-side batching under the hood.
var response = await collection.Batch.InsertMany(dataRows);

var failedObjects = response.Where(r => r.Error != null).ToList();
if (failedObjects.Any())
{
    Console.WriteLine($"Number of failed imports: {failedObjects.Count}");
    Console.WriteLine($"First failed object: {failedObjects.First().Error}");
}
```

## Manual batching

Use manual (client-side) batching when you want to control the batch size and concurrency yourself, or when using a client that does not yet support server-side batching. The following example adds objects to the `MyCollection` collection.

```py
data_rows = [{"title": f"Object {i + 1}"} for i in range(5)]

collection = client.collections.use("MyCollection")

with collection.batch.fixed_size(batch_size=200) as batch:
    for data_row in data_rows:
        batch.add_object(
            properties=data_row,
        )
        if batch.number_errors > 10:
            print("Batch import stopped due to excessive errors.")
            break

failed_objects = collection.batch.failed_objects
if failed_objects:
    print(f"Number of failed imports: {len(failed_objects)}")
    print(f"First failed object: {failed_objects[0]}")
```

```ts
let dataObjects = [
  { title: 'Object 1' },
  { title: 'Object 2' },
  { title: 'Object 3' }
]

const myCollection = client.collections.use('MyCollection')
const response = await myCollection.data.insertMany(dataObjects);

console.log(response);
```

Configure the Go client's gRPC connection parameters as described on the [connection configuration](/weaviate/connections/connect-custom) page.

```go
className := "MyCollection" // Replace with your class name
dataObjs := []models.PropertySchema{}
for i := 0; i < 5; i++ {
  dataObjs = append(dataObjs, map[string]interface{}{
  	"title": fmt.Sprintf("Object %v", i), // Replace with your actual objects
  })
}

batcher := client.Batch().ObjectsBatcher()
for _, dataObj := range dataObjs {
  batcher.WithObjects(&models.Object{
  	Class:      className,
  	Properties: dataObj,
  	// Tenant: "tenantA", // If multi-tenancy is enabled, specify the tenant to which the object will be added.
  })
}

// Flush
batcher.Do(ctx)
```

```java
List<Map<String, Object>> dataRows = new ArrayList<>();
for (int i = 0; i < 5; i++) {
  dataRows.add(Map.of("title", "Object " + (i + 1)));
}

var collection = client.collections.use("MyCollection");

// The Java client uses insertMany for batching.
// There is no direct equivalent of the Python client's stateful batch manager.
// You collect objects and send them in a single request.
var response = collection.data.insertMany(dataRows.toArray(new Map[0]));

if (!response.errors().isEmpty()) {
  System.err
      .println("Number of failed imports: " + response.errors().size());
  System.err.println("First failed object: " + response.errors().get(0));
}
```

```csharp
var dataRows = Enumerable
    .Range(0, 5)
    .Select(i => new { title = $"Object {i + 1}" })
    .ToList();

var collection = client.Collections.Use("MyCollection");

var response = await collection.Data.InsertMany(dataRows);

var failedObjects = response.Where(r => r.Error != null).ToList();
if (failedObjects.Any())
{
    Console.WriteLine($"Number of failed imports: {failedObjects.Count}");
    Console.WriteLine($"First failed object: {failedObjects.First().Error}");
}
```

## Error handling

Batch imports report failures per object: a problem with one object does not abort the rest of the import. Errors are reported the same way in server-side and manual batching. Inspect the failed items during and after the import to catch data issues early.

* Within a batching context manager, `batch.number_errors` holds a running count of failed objects and references. You can use this counter to stop the import process and investigate the failures.
* After the context closes, `collection.batch.failed_objects` and `collection.batch.failed_references` contain the failed items.
* The one-shot `data.ingest()` method returns the same result object as `insert_many`: its `errors` dict maps the original index of each failed object to its error.

Find out more about error handling on the Python client [reference page](/weaviate/client-libraries/python).

`data.ingest()` returns a result object. Inspect its `errors` field for the objects that failed to import.

Inspect the per-object errors on the result returned by the batcher.

Within a `batch.start()` streaming context, `batch.numberOfErrors()` reports the number of objects that could not be imported. The response returned by `insertMany` exposes the failed objects through its `errors()` method.

The response returned by `Batch.InsertMany` is a collection of per-object entries. Filter for entries where `Error` is not null to find the failed objects. With `Batch.StartBatch()`, each `Add` returns a handle whose result reports whether the object succeeded.

## Customize imported objects

Batch-imported objects support the same parameters as individually created objects, such as custom IDs, vectors, and cross-references. These parameters work the same way in server-side and manual batching.

### Specify an ID value

Weaviate generates an UUID for each object. Object IDs must be unique. If you set object IDs, use one of these deterministic UUID methods to prevent duplicate IDs:

* `generate_uuid5` (Python)
* `generateUuid5` (TypeScript)

```py
from weaviate.util import generate_uuid5  # Generate a deterministic ID
from weaviate.classes.data import DataObject

data_rows = [{"title": f"Object {i + 1}"} for i in range(5)]

collection = client.collections.use("MyCollection")

data_objects = [
    DataObject(properties=data_row, uuid=generate_uuid5(data_row))
    for data_row in data_rows
]

result = collection.data.ingest(data_objects)

if result.errors:
    print(f"Number of failed imports: {len(result.errors)}")
```

```ts
import { generateUuid5 } from 'weaviate-client';  // requires v1.3.2+

let dataObjects = [
  {
    properties: { title: 'Object 1' },
    id: generateUuid5('MyCollection', 'Object 1'), // generate uuid from collection name and the unique value(s)
  },
  {
    properties: { title: 'Object 2' },
    id: generateUuid5('MyCollection', 'Object 2'), // generate uuid from collection name and the unique value(s)
  },
  // ...
]

const myCollection = client.collections.use('MyCollection')
// `ingest` imports the list using server-side batching
await myCollection.data.ingest(dataObjects)
```

```go
generateUUID := func(input string) strfmt.UUID {
  input = strings.ToLower(input)
  hash := md5.Sum([]byte(input))
  uuid := fmt.Sprintf("%x-%x-%x-%x-%x", hash[0:4], hash[4:6], hash[6:8], hash[8:10], hash[10:])
  return strfmt.UUID(uuid)
}

className := "MyCollection" // Replace with your class name
dataObjs := []models.PropertySchema{}
for i := 0; i < 5; i++ {
  dataObjs = append(dataObjs, map[string]interface{}{
  	"title": fmt.Sprintf("Object %v", i), // Replace with your actual objects
  })
}

batcher := client.Batch().ObjectsBatcher()
for _, dataObj := range dataObjs {
  batcher.WithObjects(&models.Object{
  	Class:      className,
  	Properties: dataObj,
  	ID: generateUUID((dataObj.(map[string]interface{}))["title"].(string)),
  })
}

// Flush
batcher.Do(ctx)
```

```java
var collection = client.collections.use("MyCollection");

// Add objects with custom IDs to a server-side batch import.
BatchContext<Map<String, Object>> batch = collection.batch.start();
try (batch) {
  for (int i = 0; i < 5; i++) {
    Map<String, Object> dataRow = Map.of("title", "Object " + (i + 1));
    UUID objUuid = generateUuid5(dataRow.toString());

    batch.add(WeaviateObject.<Map<String, Object>>of(
        obj -> obj.properties(dataRow).uuid(objUuid.toString())));
  }
} catch (InterruptedException e) {
  Thread.currentThread().interrupt();
}

if (batch.numberOfErrors() > 0) {
  System.err
      .println("Number of failed imports: " + batch.numberOfErrors());
}
```

```csharp
var dataToInsert = new List<BatchInsertRequest>();
var vectorData = Enumerable.Repeat(0.1f, 10).ToArray();

for (int i = 0; i < 5; i++)
{
    var dataRow = new { title = $"Object {i + 1}" };
    var objUuid = GenerateUuid5(JsonSerializer.Serialize(dataRow));

    var vectors = new Vectors { { "default", vectorData } };

    dataToInsert.Add(
        BatchInsertRequest.Create(data: dataRow, uuid: objUuid, vectors: vectors)
    );
}

var collection = client.Collections.Use("MyCollection");

// `Batch.InsertMany` imports the list using server-side batching.
var response = await collection.Batch.InsertMany(dataToInsert);

var failedObjects = response.Where(r => r.Error != null).ToList();
if (failedObjects.Any())
{
    Console.WriteLine($"Number of failed imports: {failedObjects.Count}");
    Console.WriteLine($"First failed object: {failedObjects.First().Error}");
}
```

### Specify a vector

Use the `vector` property to specify a vector for each object.

```py
from weaviate.classes.data import DataObject

data_rows = [{"title": f"Object {i + 1}"} for i in range(5)]
vectors = [[0.1] * 1536 for i in range(5)]

collection = client.collections.use("MyCollection")

data_objects = [
    DataObject(properties=data_row, vector=vectors[i])
    for i, data_row in enumerate(data_rows)
]

result = collection.data.ingest(data_objects)

if result.errors:
    print(f"Number of failed imports: {len(result.errors)}")
```

```ts
const myCollection = client.collections.use('MyCollection')

let dataObjects = [
  {
    properties: { title: 'Object 1' },
    vectors: Array(100).fill(0.1111), // provide the vector here
  },
  {
    properties: { title: 'Object 2' },
    vectors: Array(100).fill(0.2222), // provide the vector here
  },
  // ...
]

// `ingest` imports the list using server-side batching
await myCollection.data.ingest(dataObjects)
```

```go
className := "MyCollection" // Replace with your class name
dataObjs := []models.PropertySchema{}
for i := 0; i < 5; i++ {
  dataObjs = append(dataObjs, map[string]interface{}{
  	"title": fmt.Sprintf("Object %v", i), // Replace with your actual objects
  })
}
vectors := [][]float32{}
for i := 0; i < 5; i++ {
  vector := make([]float32, 10)
  for j := range vector {
  	vector[j] = 0.25 + float32(j/100) // Replace with your actual vectors
  }
  vectors = append(vectors, vector)
}

batcher := client.Batch().ObjectsBatcher()
for i, dataObj := range dataObjs {
  batcher.WithObjects(&models.Object{
  	Class:      className,
  	Properties: dataObj,
  	Vector: vectors[i],
  })
}

// Flush
batcher.Do(ctx)
```

```java
float[] vector = new float[10]; // Using a small vector for demonstration
Arrays.fill(vector, 0.1f);

var collection = client.collections.use("MyCollection");

// Add objects with custom vectors to a server-side batch import.
BatchContext<Map<String, Object>> batch = collection.batch.start();
try (batch) {
  for (int i = 0; i < 5; i++) {
    Map<String, Object> dataRow = Map.of("title", "Object " + (i + 1));

    batch.add(WeaviateObject.<Map<String, Object>>of(
        obj -> obj.properties(dataRow).vectors(Vectors.of(vector))));
  }
} catch (InterruptedException e) {
  Thread.currentThread().interrupt();
}

if (batch.numberOfErrors() > 0) {
  System.err
      .println("Number of failed imports: " + batch.numberOfErrors());
}
```

```csharp
var dataToInsert = new List<BatchInsertRequest>();
var vectorData = Enumerable.Repeat(0.1f, 10).ToArray();

for (int i = 0; i < 5; i++)
{
    var dataRow = new { title = $"Object {i + 1}" };
    var objUuid = GenerateUuid5(JsonSerializer.Serialize(dataRow));

    var vectors = new Vectors { { "default", vectorData } };

    dataToInsert.Add(
        BatchInsertRequest.Create(data: dataRow, uuid: objUuid, vectors: vectors)
    );
}

var collection = client.Collections.Use("MyCollection");

// `Batch.InsertMany` imports the list using server-side batching.
var response = await collection.Batch.InsertMany(dataToInsert);

// Handle errors
var failedObjects = response.Where(r => r.Error != null).ToList();
if (failedObjects.Any())
{
    Console.WriteLine($"Number of failed imports: {failedObjects.Count}");
    Console.WriteLine($"First failed object: {failedObjects.First().Error}");
}
```

### Specify named vectors

When you create an object, you can specify named vectors (if [configured in your collection](/weaviate/manage-collections/vector-config#define-named-vectors)).

```py
from weaviate.classes.data import DataObject

data_rows = [{"title": f"Object {i + 1}", "body": f"Body {i + 1}"} for i in range(5)]

title_vectors = [[0.12] * 1536 for _ in range(5)]
body_vectors = [[0.34] * 1536 for _ in range(5)]

collection = client.collections.use("MyCollection")

data_objects = [
    DataObject(
        properties=data_row,
        vector={
            "title": title_vectors[i],
            "body": body_vectors[i],
        },
    )
    for i, data_row in enumerate(data_rows)
]

result = collection.data.ingest(data_objects)

if result.errors:
    print(f"Number of failed imports: {len(result.errors)}")
```

```ts
const myCollection = client.collections.use("MyCollection")
let dataObjects = [
  {
    properties: { title: 'Object 1' },
    vectors: {
      title: Array(100).fill(0.1111), // provide the vector here
      body: Array(100).fill(0.9999),  // provide the vector here
    }
  },
  {
    properties: { title: 'Object 2' },
    vectors: {
      title: Array(100).fill(0.2222), // provide the vector here
      body: Array(100).fill(0.8888),  // provide the vector here
    }
  },
  // ...
]

// `ingest` imports the list using server-side batching
await myCollection.data.ingest(dataObjects)
}
```

```java
// Prepare the data and vectors
List<Map<String, Object>> dataRows = new ArrayList<>();
List<float[]> titleVectors = new ArrayList<>();
List<float[]> bodyVectors = new ArrayList<>();

for (int i = 0; i < 5; i++) {
  dataRows
      .add(Map.of("title", "Object " + (i + 1), "body", "Body " + (i + 1)));

  float[] titleVector = new float[1536];
  Arrays.fill(titleVector, 0.12f);
  titleVectors.add(titleVector);

  float[] bodyVector = new float[1536];
  Arrays.fill(bodyVector, 0.34f);
  bodyVectors.add(bodyVector);
}

CollectionHandle<Map<String, Object>> collection =
    client.collections.use("MyCollection");

// Add objects with named vectors to a server-side batch import.
BatchContext<Map<String, Object>> batch = collection.batch.start();
try (batch) {
  for (int i = 0; i < dataRows.size(); i++) {
    int index = i;
    batch.add(WeaviateObject
        .<Map<String, Object>>of(v -> v.properties(dataRows.get(index))
            .vectors(Vectors.of("title", titleVectors.get(index)))
            .vectors(Vectors.of("body", bodyVectors.get(index)))));
  }
} catch (InterruptedException e) {
  Thread.currentThread().interrupt();
}

// Check for errors
if (batch.numberOfErrors() > 0) {
  System.err.printf("Number of failed imports: %d\n",
      batch.numberOfErrors());
}
```

```csharp
var dataToInsert = new List<BatchInsertRequest>();

for (int i = 0; i < 5; i++)
{
    var dataRow = new { title = $"Object {i + 1}", body = $"Body {i + 1}" };
    var titleVector = Enumerable.Repeat(0.12f, 1536).ToArray();
    var bodyVector = Enumerable.Repeat(0.34f, 1536).ToArray();

    var namedVectors = new Vectors { { "title", titleVector }, { "body", bodyVector } };

    dataToInsert.Add(BatchInsertRequest.Create(dataRow, vectors: namedVectors));
}

var collection = client.Collections.Use("MyCollection");

// `Batch.InsertMany` imports the list using server-side batching.
var response = await collection.Batch.InsertMany(dataToInsert);

// Handle errors
var failedObjects = response.Where(r => r.Error != null).ToList();
if (failedObjects.Any())
{
    Console.WriteLine($"Number of failed imports: {failedObjects.Count}");
    Console.WriteLine($"First failed object error: {failedObjects.First().Error}");
}
```

### Import with references

You can batch create links from an object to another object through cross-references.

```py
from weaviate.classes.data import DataObject

collection = client.collections.use("Author")

data_objects = [
    DataObject(
        properties={"name": "Jane Austen"},
        references={"writesFor": target_uuid},
    ),
]

result = collection.data.ingest(data_objects)

if result.errors:
    print(f"Number of failed imports: {len(result.errors)}")
```

```java
var collection = client.collections.use("Author");

var response = collection.data
    .referenceAddMany(BatchReference.uuids(from, "writesFor", targetUuid));

if (!response.errors().isEmpty()) {
  System.err
      .println("Number of failed imports: " + response.errors().size());
  System.err.println("First failed object: " + response.errors().get(0));
}
```

```csharp
var collection = client.Collections.Use("Author");

var response = await collection.Data.ReferenceAddMany([
    new DataReference(fromUuid, "writesFor", targetUuid),
]);

if (response.HasErrors)
{
    Console.WriteLine($"Number of failed imports: {response.Errors.Count}");
    Console.WriteLine($"First failed object: {response.Errors.First()}");
}
```

## Stream data from large files

If your dataset does not fit in memory, do not load it all at once. Instead, read the source file lazily and add objects to the import as you go:

* With the [server-side streaming context](#server-side-batching), add each object as you read it from the file. The client sends data at the pace the server requests, so memory usage stays flat.
* In Python and TypeScript, the [one-shot import method](#server-side-batching) accepts any iterable, so you can pass a lazy source, such as a generator that reads the file record by record, instead of a fully loaded list.
* With manual batching, apply the same pattern: add objects to the batch as you read them.

For JSON files, use a streaming parser that yields one object at a time (such as `ijson` in Python). For CSV files, read the file in chunks (such as `pandas` with the `chunksize` parameter) rather than loading it whole.

## Batch vectorization

Some [model providers](/weaviate/model-providers) provide batch vectorization APIs, where each request can include multiple objects.

From Weaviate `v1.25.0`, a batch import automatically makes use of the model providers' batch vectorization APIs where available. This reduces the number of requests to the model provider, improving throughput.

## Model provider configurations

You can configure the batch vectorization settings for each model provider, such as the requests per minute or tokens per minute. The following examples sets rate limits for Cohere and OpenAI integrations, and provides API keys for both.

Note that each provider exposes different configuration options.

```py
from weaviate.classes.config import Integrations

integrations = [
    # Each model provider may expose different parameters
    Integrations.cohere(
        api_key=cohere_key,
        requests_per_minute_embeddings=rpm_embeddings,
    ),
    Integrations.openai(
        api_key=openai_key,
        requests_per_minute_embeddings=rpm_embeddings,
        tokens_per_minute_embeddings=tpm_embeddings,  # e.g. OpenAI also exposes tokens per minute for embeddings
    ),
]
client.integrations.configure(integrations)
```

## Additional considerations

Data imports can be resource intensive. Consider the following when you import large amounts of data.

### Asynchronous imports

To maximize import speed, enable [asynchronous indexing](/weaviate/config-refs/indexing/vector-index#asynchronous-indexing) by setting the `ASYNC_INDEXING` environment variable to `true` in your Weaviate configuration. This decouples vector index construction from object creation, so imports are not slowed down by index building.

### Automatically add new tenants

By default, Weaviate returns an error if you try to insert an object into a non-existent tenant. To change this behavior so Weaviate creates a new tenant, set `autoTenantCreation` to `true` in the collection definition.

The auto-tenant feature is available from `v1.25.0` for batch imports, and from `v1.25.2` for single object insertions as well.

Set `autoTenantCreation` when you create the collection, or reconfigure the collection to update the setting as needed.

Automatic tenant creation is useful when you import a large number of objects. Be cautious if your data is likely to have small inconsistencies or typos. For example, the names `TenantOne`, `tenantOne`, and `TenntOne` will create three different tenants.

For details, see [auto-tenant](/weaviate/manage-collections/multi-tenancy#automatically-add-new-tenants).

## Further resources

* [Connect to Weaviate](/weaviate/connections)
* [How-to: Create objects](/weaviate/manage-objects/create)
* [Python client: batch import notes and best practices](/weaviate/client-libraries/python/notes-best-practices)
* [Blog: Data import best practices](https://weaviate.io/blog/data-import-best-practices)
* [References: REST - /v1/batch](/weaviate/api/rest#tag/batch)
* [Configuration: Indexes](/weaviate/config-refs/indexing/vector-index#asynchronous-indexing)

## Questions and feedback

Have a question or feedback? Here's how to reach us.

[Community Forum

Ask questions and connect with other developers on our Community forum.](https://forum.weaviate.io/c/support)[Support

Weaviate Cloud user or customer? Find the right channel on the Support page.](/support)
