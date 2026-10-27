Source: https://docs.weaviate.io/weaviate/search/similarity

# Vector similarity search

Vector search returns the objects with most similar vectors to that of the query.

Prefer natural language queries?

The [Query Agent](/weaviate/search/query-agent) translates plain English questions into optimized Weaviate queries automatically - no manual query construction needed.

![](/img/cloud-icon.svg)Cloud only

## Search with text

Use the [`Near Text`](/weaviate/api/graphql/search-operators#neartext) operator to find objects with the nearest vector to an input text.

```python
from weaviate.classes.query import MetadataQuery

jeopardy = client.collections.use("JeopardyQuestion")
response = jeopardy.query.near_text(
    query="animals in movies", limit=2, return_metadata=MetadataQuery(distance=True)
)

for o in response.objects:
    print(o.properties)
    print(o.metadata.distance)
```

```ts
const jeopardy = client.collections.use('JeopardyQuestion');

const result = await jeopardy.query.nearText('animals in movies', {
  limit: 2,
  returnMetadata: ['distance']
})

result.objects.forEach(item => {
  console.log(JSON.stringify(item.properties, null, 2))
  console.log(item.metadata?.distance)
})
```

```go
response, err := client.GraphQL().Get().
  WithClassName("JeopardyQuestion").
  WithFields(
    graphql.Field{Name: "question"},
    graphql.Field{Name: "answer"},
    graphql.Field{
      Name: "_additional",
      Fields: []graphql.Field{
        {Name: "distance"},
      },
    },
  ).
  WithNearText(client.GraphQL().NearTextArgBuilder().
    WithConcepts([]string{"animals in movies"})).
  WithLimit(2).
  Do(ctx)
```

```go
jeopardy := client.Collections.Use("JeopardyQuestion")
response, err := jeopardy.Query.NearText(ctx, query.NearText{
  Concepts: []string{"animals in movies"},
  Limit:    2,
  ReturnMetadata: query.ReturnMetadata{
    Distance: true,
  },
})
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.Properties)
  if obj.Metadata.Distance != nil {
    fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
  }
}
```

```java
CollectionHandle<Map<String, Object>> jeopardy =
    client.collections.use("JeopardyQuestion");
var response = jeopardy.query.nearText(
    "animals in movies",
    q -> q.limit(2).returnMetadata(Metadata.DISTANCE));

for (var o : response.objects()) {
  System.out.println(o.properties());
  System.out.println(o.queryMetadata().distance());
}
```

```graphql
{
  Get {
    JeopardyQuestion(
      limit: 2
      nearText: {
        concepts: ["animals in movies"]
      }
    ) {
      question
      answer
      _additional {
        distance
      }
    }
  }
}
```

```csharp
var jeopardy = client.Collections.Use("JeopardyQuestion");
var response = await jeopardy.Query.NearText(
    "animals in movies",
    limit: 2,
    returnMetadata: MetadataOptions.Distance
);

foreach (var o in response.Objects)
{
    Console.WriteLine(JsonSerializer.Serialize(o.Properties));
    Console.WriteLine(o.Metadata.Distance);
}
```

Example response

The output is like this:

```json
{
  "data": {
    "Get": {
      "JeopardyQuestion": [
        {
          "answer": "meerkats",
          "question": "Group of mammals seen <a href=\"http://www.j-archive.com/media/1998-06-01_J_28.jpg\" target=\"_blank\">here</a>:  [like Timon in <i>The Lion King</i>]",
          "_additional": { "distance": 0.17602634 }
        },
        {
          "answer": "dogs",
          "question": "Scooby-Doo, Goofy & Pluto are cartoon versions",
          "_additional": { "distance": 0.17842108 }
        }
      ]
    }
  }
}
```

## Search with image

Use the [`Near Image`](/weaviate/api/graphql/search-operators) operator to find objects with the nearest vector to an image.
This example uses a base64 representation of an image.

```py
base64_string = "SOME_BASE_64_REPRESENTATION"

# Get the collection containing images
dogs = client.collections.use("Dog")

# Perform query
response = dogs.query.near_image(
    near_image=base64_string,
    return_properties=["breed"],
    limit=1,
    # targetVector: "vector_name" # required when using multiple named vectors
)

print(response.objects[0])

client.close()
```

```ts
  import { toBase64FromMedia } from 'weaviate-client';

  const myCollection = client.collections.use('Dog');
  const filePath = './images/search-image.jpg'
  const base64String = await toBase64FromMedia(file.path)

  // Perform query
  const result = await myCollection.query.nearImage(base64String, {
    returnProperties: ['breed'],
    limit: 1,
    // targetVector: 'vector_name' // required when using multiple named vectors
  })

  console.log(JSON.stringify(result.objects, null, 2));
```

```java
String base64String = fileToBase64(QUERY_IMAGE_PATH); // This would be a real base64 string

// Get the collection containing images
CollectionHandle<Map<String, Object>> dogs = client.collections.use("Dog");

// Perform query
var response = dogs.query.nearImage(base64String,
    q -> q.returnProperties("breed").limit(1)
// targetVector: "vector_name" // required when using multiple named vectors
);

if (!response.objects().isEmpty()) {
  System.out.println(response.objects().get(0));
}
```

```csharp
// The C# client's NearImage method takes a byte array directly.
var imageBytes = await FileToByteArray(QUERY_IMAGE_PATH);

// Get the collection containing images
var dogs = client.Collections.Use("Dog");

// Perform query
var response = await dogs.Query.NearMedia(
    query => query.Image(imageBytes).Build(),
    returnProperties: ["breed"],
    limit: 1
);

if (response.Objects.Any())
{
    Console.WriteLine(JsonSerializer.Serialize(response.Objects.First()));
}
```

See [Image search](/weaviate/search/image) for more information.

## Search with an existing object

If you have an object ID, use the [`Near Object`](/weaviate/api/graphql/search-operators#nearobject) operator to find similar objects to that object.

```python
from weaviate.classes.query import MetadataQuery

jeopardy = client.collections.use("JeopardyQuestion")
response = jeopardy.query.near_object(
    near_object=uuid,  # A UUID of an object (e.g. "56b9449e-65db-5df4-887b-0a4773f52aa7")
    limit=2,
    return_metadata=MetadataQuery(distance=True),
)

for o in response.objects:
    print(o.properties)
    print(o.metadata.distance)
```

```ts
const jeopardy = client.collections.use('JeopardyQuestion');

const result = await jeopardy.query.nearObject('56b9449e-65db-5df4-887b-0a4773f52aa7', {
  limit: 2,
  returnMetadata: ['distance']
})

for (let object of result.objects) {
  console.log(JSON.stringify(object.properties, null, 2));
  console.log(JSON.stringify(object.metadata?.distance, null, 2));
}
```

```go
response, err := client.GraphQL().Get().
  WithClassName("JeopardyQuestion").
  WithFields(
    graphql.Field{Name: "question"},
    graphql.Field{Name: "answer"},
    graphql.Field{
      Name: "_additional",
      Fields: []graphql.Field{
        {Name: "distance"},
      },
    },
  ).
  WithNearObject(client.GraphQL().NearObjectArgBuilder().
    WithID("56b9449e-65db-5df4-887b-0a4773f52aa7")).
  WithLimit(2).
  Do(ctx)
```

```go
// A UUID of an object in the collection.
id := uuid.MustParse("5a6b7c8d-9e0f-4a1b-8c2d-1a2b3c4d5e6f")

jeopardy := client.Collections.Use("JeopardyQuestion")
response, err := jeopardy.Query.NearObject(ctx, query.NearObject{
  UUID:  id,
  Limit: 2,
  ReturnMetadata: query.ReturnMetadata{
    Distance: true,
  },
})
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.Properties)
  if obj.Metadata.Distance != nil {
    fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
  }
}
```

```java
var response = jeopardy.query.nearObject(uuid, // A UUID of an object (e.g. "56b9449e-65db-5df4-887b-0a4773f52aa7")
    q -> q.limit(2).returnMetadata(Metadata.DISTANCE));

for (var o : response.objects()) {
  System.out.println(o.properties());
  System.out.println(o.queryMetadata().distance());
}
```

```csharp
var response = await jeopardy.Query.NearObject(
    uuid, // A UUID of an object
    limit: 2,
    returnMetadata: MetadataOptions.Distance
);

foreach (var o in response.Objects)
{
    Console.WriteLine(JsonSerializer.Serialize(o.Properties));
    Console.WriteLine(o.Metadata.Distance);
}
```

```graphql

```

Additional information

To get the object ID, see [Retrieve the object ID](/weaviate/search/basics#retrieve-the-object-id).

## Search with a vector

If you have an input vector, use the [`Near Vector`](/weaviate/api/graphql/search-operators#nearvector) operator to find objects with similar vectors

```python
from weaviate.classes.query import MetadataQuery

jeopardy = client.collections.use("JeopardyQuestion")
response = jeopardy.query.near_vector(
    near_vector=query_vector,  # your query vector goes here
    limit=2,
    return_metadata=MetadataQuery(distance=True),
)

for o in response.objects:
    print(o.properties)
    print(o.metadata.distance)
```

```ts
const jeopardy = client.collections.use('JeopardyQuestion');

const result = await jeopardy.query.nearVector(queryVector, {
  limit: 2,
  returnMetadata: ['distance']
})

for (let object of result.objects) {
  console.log(JSON.stringify(object.properties, null, 2));
  console.log(JSON.stringify(object.metadata?.distance, null, 2));
}
```

```go
// Edit the vector variable to add a vector of length 384
// vector := ADD_A_VECTOR_HERE

response, err := client.GraphQL().Get().
  WithClassName("JeopardyQuestion").
  WithFields(
    graphql.Field{Name: "question"},
    graphql.Field{Name: "answer"},
    graphql.Field{
      Name: "_additional",
      Fields: []graphql.Field{
        {Name: "distance"},
      },
    },
  ).
  WithNearVector(client.GraphQL().NearVectorArgBuilder().
    WithVector(vector)).
  WithLimit(2).
  Do(ctx)
```

To run the example, paste the sample test vector into the code sample.

Sample test vector

vector := []float320.630052995

```go
// A query vector, for example an embedding produced by your model.
vector := []float32{0.12, 0.20, 0.33}

jeopardy := client.Collections.Use("JeopardyQuestion")
response, err := jeopardy.Query.NearVector(ctx, query.NearVector{
  Target: &types.Vector{Single: vector},
  Limit:  2,
  ReturnMetadata: query.ReturnMetadata{
    Distance: true,
  },
})
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.Properties)
  if obj.Metadata.Distance != nil {
    fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
  }
}
```

```java
var response = jeopardy.query.nearVector(queryVector, // your query vector goes here
    q -> q.limit(2).returnMetadata(Metadata.DISTANCE));

for (var o : response.objects()) {
  System.out.println(o.properties());
  System.out.println(o.queryMetadata().distance());
}
```

```csharp
var response = await jeopardy.Query.NearVector(
    vectors: queryVector, // your query vector goes here
    limit: 2,
    returnMetadata: MetadataOptions.Distance
);

foreach (var o in response.Objects)
{
    Console.WriteLine(JsonSerializer.Serialize(o.Properties));
    Console.WriteLine(o.Metadata.Distance);
}
```

```graphql
{
  Get {
    JeopardyQuestion (
      limit: 2
      nearVector: {
        vector: [-0.0125526935, -0.021168863, -0.01076519, -0.02589537, -0.0070362035, 0.019870078, -0.010001986, -0.019120263, 0.00090044655, -0.017393013, 0.021302758, 0.010055545, 0.02937665, -0.003816019, 0.007692291, 0.012385325, 0.032750815, 0.020847514, 0.020311933, -0.022159688, -0.0009924996, 0.009399457, 0.0022226637, -0.029510546, 0.014393755, -0.007223657, 0.018276723, -0.03639277, -0.010001986, -0.022842556, 0.010363504, -0.020927852, -0.006929087, -0.022521207, -0.007652122, -0.011126708, 0.0279038, -0.01721895, 0.016482525, 0.002281243, -0.00169294, 0.009191919, -0.019655844, -0.022869334, -0.012412104, 0.0031967526, -0.0033457114, -0.01483561, -0.03173321, 0.004746592, 0.010095714, 0.007973471, -0.032134898, -0.023739655, -0.008040419, 0.018290112, -0.013637247, -0.008488968, 0.024623364, -0.039365247, -0.0032586793, 0.0009606995, -0.029510546, 0.0063265576, -0.019602288, 0.003081268, 0.013463182, -0.006601043, 0.019910246, -0.01542475, 0.0367409, -0.01193008, 0.012961075, -0.015625594, 0.0062462203, -0.0058646183, -0.0059248717, 0.01889264, 0.008127451, 0.0037155973, 0.037142586, -0.025373178, -0.005503101, 0.014982895, 0.035053816, -0.012432188, -0.017285896, 0.022936283, 0.0024620018, 0.016937768, -0.0062127467, 0.02154377, 0.0066378643, 0.029698, 0.0013071538, 0.0043850746, -0.008040419, 0.024797428, -0.012452273, -0.025132166, -0.0031900578, 0.0000019433794, -0.002378317, -0.008629559, 0.0126732, -0.0022494427, 0.0009623732, 0.0035582704, 0.017312676, -0.024569806, -0.008890655, 0.023056788, 0.014902558, -0.047104403, -0.009011161, -0.030447815, 0.017982153, -0.0042009684, -0.00654079, 0.00069249026, 0.011936775, 0.023378137, 0.025105387, -0.009245478, 0.030929837, 0.00394322, 0.02123581, -0.0042545265, 0.0022578111, -0.017259117, 0.047157962, -0.00022029977, 0.03497348, -0.00072094303, -0.023605758, 0.036499888, -0.015384582, 0.011099929, -0.0139519, -0.03408977, 0.013155223, 0.030501373, -0.026698742, 0.004311432, -0.010236303, 0.011361024, 0.023793213, -0.00014874942, 0.0020352101, 0.0026829292, 0.00989487, 0.0074780583, 0.02734144, 0.003826061, 0.011722542, 0.00712993, -0.013992069, 0.0009406152, 0.010785274, -0.012325072, 0.01692438, 0.010617905, 0.016750315, -0.0070295087, 0.017687583, 0.038320865, 0.020485997, 0.005054551, -0.018812304, 0.0007201062, 0.0015381235, 0.0349467, 0.014728494, 0.050773136, -0.017901815, 0.0027716348, 0.0064704954, 0.026671965, -0.015063233, -0.013536825, 0.016696757, 0.008127451, 0.026966535, 0.029912233, -0.0031431946, 0.015156959, 0.012412104, -0.047907773, 0.022012403, -0.027006702, -0.0069491714, 0.010718327, 0.011976943, -0.008127451, -0.65212417, 0.00024289463, 0.0051214993, -0.013007938, 0.022373922, 0.0337952, -0.0026829292, -0.0110463705, -0.013034717, -0.0012167745, 0.010062239, -0.0023013272, 0.024409132, -0.009118277, -0.020191427, -0.01597372, 0.010115798, -0.030929837, -0.010932559, 0.010912475, -0.0009841312, 0.010571042, -0.008348378, -0.009104887, 0.02711382, 0.0036553445, -0.018263333, -0.030876279, 0.014594599, 0.037704945, -0.030126465, 0.014366977, 0.0055533117, 0.003487975, 0.044988856, 0.009881481, -0.012699978, 0.041132666, 0.01744657, 0.05417408, -0.004686339, 0.016121006, 0.0070495927, 0.015478308, -0.020593112, 0.0012376956, 0.027127208, -0.0051248465, 0.0005979267, 0.0063366, -0.008616169, 0.027877023, -0.00042679158, 0.008442105, 0.00069751136, 0.023806602, 0.029296314, -0.0047332025, 0.027877023, 0.0033005215, 0.014996285, -0.0061424514, 0.00451897, 0.015531867, -0.015317634, 0.044185482, 0.010196134, 0.007504837, 0.012405409, -0.030126465, 0.03821375, 0.0256008, -0.016710145, 0.0032804373, -0.013884953, 0.022775607, 0.030608488, -0.023431696, -0.008502358, 0.008683117, -0.0045490963, -0.0030143203, -0.024074392, 0.00874337, 0.009466405, -0.0072370465, -0.021383096, 0.001360712, 0.020298542, 0.0040168623, 0.008201093, 0.011106623, -0.03202778, 0.0046461704, -0.00088370964, -0.008957602, 0.0057575023, 0.00037407028, 0.017259117, -0.0482559, -0.0049507823, -0.024235068, -0.0014418861, 0.004425243, 0.023244241, 0.0107919695, -0.017058274, 0.0183035, 0.033339955, -0.009091497, 0.000118936776, 0.0031900578, -0.000044483608, -0.017058274, 0.001529755, -0.027984139, 0.02740839, -0.015344413, 0.015264076, -0.01719217, 0.010463926, -0.0067048124, 0.014942727, -0.00026653553, 0.02677908, -0.00036570182, -0.043194655, -0.022855945, -0.011294077, 0.005764197, 0.004910614, -0.0029724778, 0.0056637754, -0.01425986, -0.000008708432, 0.01866502, 0.031626094, 0.0050378144, 0.015451529, 0.009406152, -0.030742384, -0.0024318753, -0.029751558, -0.008348378, 0.0028519721, -0.008388547, -0.010611211, 0.0139519, -0.0006895613, -0.001230164, -0.0062462203, -0.013510046, 0.010617905, -0.010229609, 0.022213247, -0.00610563, -0.00568386, -0.0056503857, 0.02416812, -0.0076253433, 0.015183738, -0.005188447, -0.016080838, 0.013516741, 0.0062897364, -0.0068520973, 0.021396484, 0.007799407, -0.01721895, -0.025266062, 0.013791226, -0.017205559, -0.002068684, 0.032938268, 0.014661547, 0.023552202, -0.005827797, -0.008442105, -0.0074914475, 0.009111582, 0.016817262, -0.0050244248, -0.005871313, -0.008368462, 0.040329296, 0.008683117, 0.031518977, 0.026109602, -0.025815032, 0.011006202, -0.0034310697, 0.019575508, -0.013831395, -0.008676422, -0.008770149, -0.019990584, 0.008750064, 0.02851972, 0.0337952, 0.012666505, 0.021383096, -0.027448557, 0.0035448808, -0.016214734, 0.015197128, -0.027582452, -0.0138046155, -0.03899034, 0.008261346, 0.015478308, 0.017888425, 0.0153979715, 0.010658074, -0.011581952, 0.02530623, 0.017982153, -0.0059449556, 0.0054294583, 0.0022879376, -0.018758746, -0.0076119537, -0.027689569, 0.013463182, 0.011186961, -0.0063165156, 0.028412605, 0.011347636, 0.008709895, -0.003374164, -0.007919913, -0.025828423, 0.0033875536, -0.013831395, -0.0035716598, 0.010450536, -0.025172336, 0.003990083, -0.00093224674, 0.024047613, 0.008027029, -0.0029440252, 0.023458473, 0.016643198, -0.0326437, 0.019147042, 0.01925416, -0.0020151257, 0.0038628823, -0.026738912, 0.0008753412, -0.025105387, 0.0069491714, -0.02623011, 0.027033482, -0.0040737675, -0.021034967, 0.019468391, 0.0026042655, 0.03467891, 0.016107617, -0.0057139862, -0.011735932, 0.017687583, 0.011628816, 0.015090012, -0.006678033, -0.011715848, -0.01833028, 0.008040419, -0.01921399, -0.03267048, -0.005914829, 0.0014435598, -0.0030662047, 0.005479669, 0.01597372, -0.01454104, 0.023257632, 0.019722793, 0.0344379, 0.006929087, -0.043248214, 0.015853215, 0.012766927, -0.007417805, -0.018316891, -0.01163551, -0.017352844, -0.01978974, 0.015304244, -0.00005920687, 0.033580966, -0.0022343795, 0.0047800657, -0.007357552, 0.00033536615, 0.00887057, -0.025654359, 0.016388796, -0.011361024, 0.00019090556, 0.0060119033, -0.010075629, -0.0131485285, 0.01604067, -0.015531867, 0.0035616176, -0.017259117, 0.0035415334, 0.009265562, -0.0043348637, -0.005867966, -0.03283115, -0.004773371, -0.018410617, -0.0095400475, -0.006520706, -0.00414741, 0.031197628, 0.013690805, -0.008984381, -0.022320364, -0.012492441, -0.005724028, 0.09806499, 0.017272506, -0.00007704216, 0.00858939, 0.0030126465, -0.002835235, -0.023753043, -0.025587412, 0.016067449, 0.0024536331, 0.004719813, -0.02908208, 0.027743127, 0.0023414958, 0.0152908545, 0.00552988, -0.031974223, 0.0019582203, 0.010812053, -0.01952195, -0.00006171741, -0.02241409, 0.025252672, 0.013737668, 0.002356559, -0.03719614, 0.021637497, 0.033580966, 0.0044453274, -0.0074378895, -0.014715104, -0.01741979, -0.013489962, -0.003221858, 0.0038561875, -0.013121749, -0.012974464, 0.012619642, 0.053424265, -0.020459218, 0.011581952, 0.041962817, -0.00087032013, -0.0036988605, -0.0010025419, -0.020392269, 0.014902558, 0.021409875, 0.01771436, -0.006483885, 0.036633782, -0.00028808432, 0.011983639, 0.014326808, 0.024931323, 0.002629371, -0.01223804, -0.010972728, -0.011253908, 0.013831395, -0.01748674, -0.013777837, -0.0043449057, -0.009292341, -0.0015849868, -0.019455003, -0.031170849, -0.014393755, -0.03778528, -0.0028335615, -0.00785966, -0.027528895, -0.021008188, -0.03786562, -0.0008226199, -0.005539922, 0.011970249, -0.016937768, -0.0044553694, 0.015839826, -0.014929337, -0.011166876, 0.0031448682, -0.032402687, -0.011207045, -0.009432931, 0.0034059642, -0.00089124124, -0.009439626, -0.012840569, 0.013610467, 0.008877265, 0.006108978, 0.0021289368, 0.039124236, 0.0025557284, -0.004277958, 0.02822515, 0.022373922, -0.00888396, 0.032777593, -0.021610718, -0.010490704, -0.0017222296, -0.011113319, -0.024569806, 0.0024703701, 0.021155473, -0.004555791, -0.0060353354, 0.008241262, -0.03234913, -0.00048076818, -0.0069960346, 0.02910886, 0.013315897, -0.014728494, 0.01454104, -0.00567047, -0.0012602905, 0.0001736456, 0.005302258, -0.0000424961, 0.035589397, -0.01570593, 0.0107919695, 0.0051348885, -0.015331023, -0.0034193539, 0.003625218, -0.010477315, 0.024583196, -0.0030226887, -0.011776101, -0.040115062, -0.009091497, -0.003886314, 0.017888425, -0.03143864, -0.008629559, -0.005533227, -0.017138612, 0.01338954, -0.02681925, -0.006688075, -0.026538068, 0.0050210776, 0.011401193, 0.0076655117, 0.008576, -0.028171593, -0.0022025793, 0.005911482, 0.017205559, -0.02066006, -0.0413469, -0.016910989, 0.0097944485, 0.020807344, 0.030742384, 0.026738912, -0.011628816, 0.03350063, 0.011146792, -0.024556417, 0.019709403, -0.00712993, 0.012110839, -0.044694286, 0.02795736, 0.016777094, -0.0054729744, 0.025975708, 0.0109191695, 0.009821228, 0.012485746, 0.01571932, 0.0018661672, -0.014567819, -0.010972728, 0.0022394005, 0.01626829, 0.0014820547, -0.0030026045, 0.004120631, -0.023699487, 0.040918436, 0.0011640531, -0.0092856465, -0.0180491, 0.03459857, -0.013161918, -0.0036151758, -0.0073910262, 0.0028737301, -0.017968763, -0.016549472, -0.01355691, 0.0031616052, 0.0067516756, 0.0023096956, -0.0076789013, -0.009955123, 0.011233824, -0.0072906045, 0.016402187, 0.009727501, -0.0153979715, 0.020445827, -0.0042980425, -0.024556417, -0.048496913, -0.026886197, -0.047693543, 0.0007615301, -0.013925122, -0.010437147, 0.01483561, -0.0050277724, -0.022266805, 0.02793058, -0.015264076, 0.032563362, 0.00472316, 0.017526908, 0.021061746, -0.013818005, -0.021945456, 0.028573278, -0.0313583, 0.016469134, 0.00013180329, -0.000116426236, -0.0018477566, -0.03722292, -0.002868709, 0.001186648, -0.037463933, -0.046568822, 0.0128004, 0.015197128, 0.013054801, -0.017821478, -0.022320364, -0.022012403, 0.013289118, -0.0043516005, -0.0029808464, -0.01660303, -0.03786562, -0.024877766, -0.013356066, -0.006825318, 0.027582452, -0.0042545265, -0.0017063295, 0.024891155, -0.0049240035, -0.014500872, -0.016803874, 0.008127451, 0.022855945, -0.0014284966, -0.006339947, 0.01604067, 0.0026092867, 0.012057281, -0.008569306, 0.00007374708, 0.02766279, -0.025774864, 0.0047064233, -0.024676923, 0.013938512, -0.002286264, -0.011166876, -0.024074392, -0.018450785, -0.0049842563, 0.0035080595, 0.028305488, 0.033286396, -0.003054489, -0.003272069, -0.024502859, 0.021302758, -0.015558646, -0.006798539, 0.005667123, -0.01716539, 0.003325627, 0.00885718, -0.0047767186, -0.0073843314, -0.0038193662, -0.009352594, 0.0209948, 0.041507576, -0.036526665, -0.0022661798, -0.035401944, 0.012204566, -0.034759246, -0.008850486, -0.0009975208, -0.00022176426, -0.008629559, -0.015357803, -0.01455443, -0.0059416085, -0.01687082, 0.014487483, -0.0008845465, -0.0010284841, 0.02708704, 0.028653616, 0.0033189321, -0.025373178, 0.0036620393, 0.018772135, -0.0031130682, 0.0070495927, -0.00006830758, -0.017674193, 0.000969068, -0.018290112, -0.005546617, 0.0037658082, -0.00016872912, -0.024784038, -0.020860903, 0.02070023, 0.0029138986, -0.036285654, -0.041159447, -0.022106132, -0.018651629, 0.03435756, -0.008194398, -0.020485997, 0.01660303, 0.026270278, 0.0079065235, 0.0015649025, -0.005807713, -0.012733453, -0.0042377897, -0.021891898, -0.0180491, -0.008783538, -0.017111832, 0.005493059, 0.011501615, -0.0025657706, -0.018946199, 0.006052072, -0.0120438915, 0.010644685, -0.005165015, 0.009881481, 0.02677908, -0.0035716598, 0.005449543, 0.021758003, -0.0072035724, 0.010745106, -0.012130924, -0.0011799532, 0.0036620393, -0.0034411119, 0.013028023, 0.045095973, -0.021396484, -0.01895959, 0.016281681, 0.0020050837, 0.008214483, 0.004632781, -0.030501373, -0.019709403, -0.021075137, -0.0027230978, -0.015183738, 0.0008828728, 0.015304244, -0.0034578487, -0.02940343, 0.015344413, 0.00785966, -0.0026260235, -0.008529137, 0.00442859, 0.0013900016, 0.0001500047, -0.024368962, -0.005580091, -0.017205559, -0.0285465, 0.0054729744, -0.0009422889, -0.0076722065, 0.02475726, -0.02241409, -0.016469134, -0.0064370213, 0.00018034037, 0.009044634, -0.0044486746, 0.000060462142, -0.014942727, 0.026658574, -0.0043181265, 0.030046128, -0.042043157, 0.016616419, -0.007170099, 0.02040566, -0.008227873, 0.025975708, -0.027877023, -0.022668492, 0.0051181517, -0.007116541, 0.016522693, -0.0025373178, -0.0018259985, -0.015906774, 0.013858174, -0.019843299, 0.0029942358, -0.01632185, -0.029831896, -0.024007445, -0.0045022327, -0.015946941, 0.030662047, 0.18091947, -0.016576251, 0.003936525, 0.039659817, -0.008160925, 0.021168863, 0.026002487, -0.0043248213, -0.008488968, 0.0125526935, -0.007839575, 0.024020836, -0.014500872, 0.008529137, 0.0011925059, -0.015652372, -0.00050880254, -0.0032017739, -0.006353337, -0.03438434, -0.013208781, -0.0023113694, -0.011608731, -0.015411361, 0.022842556, 0.0013423014, -0.0017356192, -0.005104762, 0.0062395255, 0.0056403438, 0.0061960095, -0.033018608, 0.0053591635, -0.02067345, -0.001453602, -0.013289118, -0.02851972, 0.028118035, 0.0052687842, 0.01338954, -0.0035314912, 0.009673943, 0.009191919, 0.01281379, -0.013992069, 0.008134145, -0.004575875, 0.0015013022, -0.00028620142, 0.03550906, -0.0512016, 0.010477315, 0.008897349, 0.03347385, -0.02471709, 0.0011297425, 0.005851229, -0.019588897, 0.012037196, 0.010182745, 0.0065776114, 0.030233582, -0.01309497, 0.018839084, -0.024623364, 0.0072370465, -0.02241409, 0.03400943, -0.00069207186, -0.014674936, -0.0031833632, -0.024784038, -0.02645773, -0.012793706, -0.0008506542, -0.03583041, -0.012325072, 0.026966535, 0.01018944, 0.013356066, -0.02474387, -0.014326808, -0.007658817, 0.012827179, -0.02740839, -0.015277465, 0.021784782, -0.0015858236, -0.0018460829, 0.0004573365, -0.0057072914, -0.019588897, 0.0058411867, -0.002308022, -0.00066278223, 0.006460453, -0.00038369402, 0.018705187, -0.009078108, -0.020298542, -0.035991084, -0.047211517, 0.018571293, -0.0041775363, -0.008676422, -0.002138979, -0.007504837, -0.00078579865, 0.014621378, -0.0043850746, -0.01455443, -0.015906774, 0.0010176051, 0.006935782, 0.025199115, -0.0038093242, 0.013690805, -0.022253416, 0.036874793, -0.019053316, -0.0044821487, 0.0042377897, 0.005998514, 0.0064102425, 0.008080588, -0.028064476, -0.025239283, 0.0070295087, 0.023083568, -0.028653616, -0.010771885, -0.019280938, -0.005563354, -0.012579473, -0.005258742, 0.0012109166, 0.015531867, -0.017339455, 0.016241511, 0.0069424766, 0.015652372, 0.014380367, 0.006791844, -0.0023967277, 0.037945956, -0.0285465, 0.02128937, 0.0049942983, -0.029831896, -0.023819992, -0.016281681, -0.0031850368, 0.0029691304, -0.0038227136, 0.023645928, -0.036473107, -0.02153038, -0.025279451, -0.010242999, 0.018156216, -0.025413347, 0.0036218707, 0.005111457, -0.014487483, -0.0059784297, -0.013690805, -0.171279, -0.0037222921, 0.01626829, -0.010417062, -0.0007322405, -0.001834367, 0.008776844, -0.012867348, -0.005884703, -0.0027147292, 0.022306973, 0.0042244, -0.049300287, -0.0157461, 0.016054058, 0.002781677, 0.00197161, 0.007980166, -0.014366977, -0.0071834885, 0.021048358, -0.024971493, 0.017955374, -0.007692291, 0.0043683373, 0.018557902, 0.01570593, 0.0027063608, 0.0011791164, -0.03698191, -0.014875779, 0.008455494, 0.016536081, 0.009486489, -0.001415107, 0.002960762, -0.008368462, -0.021878509, -0.022454258, 0.004686339, 0.012392019, 0.04394447, 0.016121006, -0.0068085813, 0.014085797, -0.0022946324, 0.008509053, -0.0063868104, 0.022333752, -0.026591627, 0.006497274, -0.01454104, 0.0080337245, -0.0059014396, 0.01602728, 0.02651129, -0.010738411, 0.014567819, -0.010303251, -0.031010175, -0.03821375, -0.0056403438, -0.00006835988, -0.0011732584, -0.021945456, -0.011146792, -0.023498643, 0.021409875, -0.026712133, -0.004190926, 0.002542339, 0.0062462203, -0.004522317, -0.02967122, 0.008334989, 0.00029415145, -0.018544514, 0.022240026, -0.024261847, -0.021811562, -0.020566333, 0.0390439, -0.025466906, 0.014059017, 0.013476572, -0.007451279, -0.0101760505, -0.021918677, 0.004093852, -0.003772503, 0.034304, -0.029483767, -0.025574021, -0.015893385, -0.003407638, 0.030233582, 0.007799407, 0.00002280406, 0.021838339, -0.01633524, -0.006875529, -0.010229609, 0.0053256894, 0.02011109, -0.010885696, 0.04016862, 0.028760733, 0.015183738, 0.013061496, -0.0073307734, 0.0077324593, 0.007739154, 0.015344413, 0.03783884, -0.012124228, 0.0145276515, -0.00086027797, 0.0006744981, 0.035375167, -0.0044620642, 0.030903058, 0.01567915, -0.0053189946, -0.014045628, -0.018852472, 0.0035683124, -0.09554776, -0.013791226, -0.015116791, 0.0013891648, -0.026377395, 0.019147042, -0.008254652, 0.040623866, -0.01656286, 0.01948178, 0.01310836, -0.006025293, 0.005971735, -0.0051348885, 0.019843299, 0.02007092, -0.027421778, 0.00007709446, 0.0038896615, 0.005737418, 0.010095714, -0.0044988855, 0.011294077, -0.001899641, -0.01567915, 0.007216962, -0.02095463, 0.024797428, -0.0064805374, 0.010691548, 0.01208406, -0.012867348, -0.0057775867, -0.023110347, -0.019588897, 0.0060821986, -0.019374665, -0.0061391043, 0.031331524, -0.018490955, 0.004043641, 0.0032017739, -0.003973346, -0.014982895, 0.008696507, -0.025989097, 0.007156709, 0.013523435, -0.0041139363, -0.03055493, -0.02793058, -0.011106623, -0.02851972, 0.023753043, 0.04689017, 0.0035850494, 0.009834617, 0.0096003, 0.016147785, 0.019856688, 0.0031582578, 0.004666255, -0.00829482, 0.0395527, -0.01077858, -0.020512775, -0.020512775, 0.012057281, 0.027006702, -0.021999015, -0.009633774, 0.02878751, -0.026645185, -0.005057899, -0.016964547, 0.003315585, -0.02910886, -0.008107367, 0.0138046155, -0.023538811, -0.0028804247, -0.03491992, 0.0076789013, -0.03781206, 0.014032238, 0.019642456, 0.021798171, -0.0074780583, -0.01602728, -0.011909996, -0.015183738, 0.0031063734, 0.0016686714, -0.036553446, -0.0018594724, 0.015906774, -0.009225393, 0.006755023, 0.0065776114, 0.0139117325, -0.0045524435, 0.0051583205, -0.049166393, 0.018477565, -0.010182745, 0.0031398472, 0.022614934, 0.0048905294, 0.027234325, -0.005191794, 0.026966535, -0.0012477378, -0.029483767, 0.010303251, -0.0072370465, 0.015505088, -0.015183738, -0.009948429, 0.00054185797, -0.016844042, 0.0015339392, -0.008495663, 0.01105976, 0.008375158, 0.013992069, 0.00698934, 0.0035448808, 0.01427325, 0.0080538085, 0.005382595, -0.021677665, 0.004900572, 0.008977687, -0.034812804, 0.005998514, 0.024984881, 0.0032687215, -0.02795736, 0.009124972, 0.0022778956, 0.0038126716, 0.012646421, 0.0019180516, -0.0128004, 0.013034717, -0.046033237, -0.00021506949, -0.005104762, -0.010309946, 0.0054093744, 0.01632185, -0.005737418, 0.016937768, 0.010945949, -0.018129438, 0.0039532618, -0.0047432445, -0.04051675, 0.03703547, 0.007551701, 0.0031264576, 0.00073935365, 0.012887432, 0.00020000625, 0.003869577, -0.012961075, -0.010443841, 0.038481537, 0.0037089025, -0.013643941, 0.03639277, -0.040329296, -0.022293584, 0.004087157, 0.011709153, 0.014902558, -0.006122367, 0.007852965, 0.003081268, 0.018571293, -0.0077190697, 0.020927852, 0.021195643, -0.00010554723, -0.029055303, 0.006269652, 0.029885454, 0.0060554193, -0.0075583956, 0.0008188541, 0.013041412, -0.006453758, -0.03467891, 0.005814408, 0.015090012, 0.010383588, 0.013818005, 0.018504344, -0.025761476, -0.011856438, 0.0052219206, 0.021423263, 0.00829482, -0.009881481, -0.01326234, -0.0038093242, -0.016951159, -0.005590133, -0.0067115068, -0.03483958, -0.010838833, 0.01717878, 0.038053073, -0.015612204, -0.004231095, 0.008027029, -0.008040419, 0.025667747, -0.005677165, -0.016455745, -0.028010918, 0.024342183, 0.010095714, 0.014219692, 0.016910989, -0.00083266204, 0.010182745, 0.021516992, 0.011950164, -0.03055493, -0.012104144, 0.004468759, -0.006969256, -0.014393755, -0.021342928, 0.0085626105, -0.015665762, 0.0021841687, -0.004234442, 0.030715605, -0.017138612, 0.042712633, 0.0062462203, 0.020057531, 0.008073892, -0.0326437, 0.01250583, 0.024342183, 0.04747931, -0.027020091, 0.0019414834, 0.015170349, -0.016362019, 0.02825193, -0.009566827, -0.039954387, -0.00697595, -0.023927107, -0.0285465, -0.000100316945, -0.024850987, 0.022963062, 0.002122242, 0.027877023, 0.0012870695, -0.018182995, -0.0079266075, 0.016174564, -0.010068934, -0.015090012, -0.0054227635, 0.0051516257, -0.013235561, -0.0075583956, -0.0131485285, 0.039365247, 0.0065575275, -0.011474836, 0.0028268667, -0.004425243, -0.0020703576, -0.010631295, -0.011702458, -0.0038394507, 0.0059784297, 0.032268792, 0.02244087, -0.023458473, -0.0053859423, -0.01925416]
      }
    ) {
      question
      answer
      _additional {
        distance
      }
    }
  }
}
```

## Named vectors

To search a collection that has [named vectors](/weaviate/config-refs/collections#named-vectors), use the `target vector` field to specify which named vector to search.

```python
from weaviate.classes.query import MetadataQuery

reviews = client.collections.use("WineReviewNV")
response = reviews.query.near_text(
    query="a sweet German white wine",
    limit=2,
    target_vector="title_country",  # Specify the target vector for named vector collections
    return_metadata=MetadataQuery(distance=True),
)

for o in response.objects:
    print(o.properties)
    print(o.metadata.distance)
```

```ts
const myNVCollection = client.collections.use('WineReviewNV');

const result = await myNVCollection.query.nearText('a sweet German white wine', {
  targetVector: 'title_country',
  returnMetadata: ['distance'],
  limit: 2,
})

for (let object of result.objects) {
  console.log(JSON.stringify(object.properties, null, 2));
  console.log(JSON.stringify(object.metadata?.distance, null, 2));
}
```

```go
className := "WineReviewNV"
targetVector := "title_country"
limit := 2

response, err := client.GraphQL().Get().
  WithClassName(className).
  WithFields(
    graphql.Field{Name: "_additional",
      Fields: []graphql.Field{{Name: "distance"}}},
  ).
  WithNearText((&graphql.NearTextArgumentBuilder{}).
    WithConcepts([]string{"a sweet German white wine"}).
    WithTargetVectors(targetVector),
  ).
  WithLimit(limit).
  Do(ctx)
```

```go
reviews := client.Collections.Use("WineReviewNV")
response, err := reviews.Query.NearText(ctx, query.NearText{
  Concepts: []string{"a sweet German white wine"},
  // Select the named vector to search against.
  Target: query.VectorName("title_country"),
  Limit: 2,
  ReturnMetadata: query.ReturnMetadata{
    Distance: true,
  },
})
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.Properties)
  fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
}
```

```java
CollectionHandle<Map<String, Object>> reviews =
    client.collections.use("WineReviewNV");
var response = reviews.query.nearText(
    Target.text("title_country", "a sweet German white wine"),
    q -> q.limit(2).returnMetadata(Metadata.DISTANCE));

for (var o : response.objects()) {
  System.out.println(o.properties());
  System.out.println(o.queryMetadata().distance());
}
```

```csharp
var reviews = client.Collections.Use("WineReviewNV");
var response = await reviews.Query.NearText(
    query =>
        query(["a sweet German white wine"])
            .TargetVectorsMinimum("title_country"),
    limit: 2,
    returnMetadata: MetadataOptions.Distance
);

foreach (var o in response.Objects)
{
    Console.WriteLine(JsonSerializer.Serialize(o.Properties));
    Console.WriteLine(o.Metadata.Distance);
}
```

```graphql
{
  Get {
    WineReviewNV(
      limit: 2
      nearText: {
        targetVectors: ["title_country"]
        concepts: ["a sweet German white wine"]
      }
    ) {
      title
      review_body
      country
    }
  }
}
```

Example response

The output is like this:

```json
{
  "WineReviewNV": [
    {
      "country": "Austria",
      "review_body": "With notions of cherry and cinnamon on the nose and just slight fizz, this is a refreshing, fruit-driven sparkling ros\u00e9 that's full of strawberry and cherry notes\u2014it might just be the very definition of easy summer wine. It ends dry, yet refreshing.",
      "title": "Gebeshuber 2013 Frizzante Ros\u00e9 Pinot Noir (\u00d6sterreichischer Perlwein)"
    },
    {
      "country": "Austria",
      "review_body": "Beautifully perfumed, with acidity, white fruits and a mineral context. The wine is layered with citrus and lime, hints of fresh pineapple acidity. Screw cap.",
      "title": "Stadt Krems 2009 Steinterrassen Riesling (Kremstal)"
    }
  ]
}
```

## Set a similarity threshold

To set a similarity threshold between the search and target vectors, define a maximum `distance` (or `certainty`).

```python
from weaviate.classes.query import MetadataQuery

jeopardy = client.collections.use("JeopardyQuestion")
response = jeopardy.query.near_text(
    query="animals in movies",
    distance=0.25,  # max accepted distance
    return_metadata=MetadataQuery(distance=True),
)

for o in response.objects:
    print(o.properties)
    print(o.metadata.distance)
```

```ts
const jeopardy = client.collections.use('JeopardyQuestion');
const maxDistance = 0.18;

const result = await jeopardy.query.nearText('animals in movies', {
  distance: maxDistance,
  returnMetadata: ['distance'],
})

result.objects.forEach(item => {
  console.log(JSON.stringify(item.properties, null, 2))
  console.log(item.metadata?.distance)
})
```

```go
maxDistance := float32(0.18)
response, err := client.GraphQL().Get().
  WithClassName("JeopardyQuestion").
  WithFields(
    graphql.Field{Name: "question"},
    graphql.Field{Name: "answer"},
    graphql.Field{
      Name: "_additional",
      Fields: []graphql.Field{
        {Name: "distance"},
      },
    },
  ).
  WithNearText(client.GraphQL().NearTextArgBuilder().
    WithConcepts([]string{"animals in movies"}).
    WithDistance(maxDistance)).
  Do(ctx)
```

```go
jeopardy := client.Collections.Use("JeopardyQuestion")
response, err := jeopardy.Query.NearText(ctx, query.NearText{
  Concepts: []string{"animals in movies"},
  Similarity: query.Distance(0.25),
  ReturnMetadata: query.ReturnMetadata{
    Distance: true,
  },
})
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.Properties)
  fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
}
```

```java
CollectionHandle<Map<String, Object>> jeopardy =
    client.collections.use("JeopardyQuestion");
var response = jeopardy.query.nearText("animals in movies", q -> q
    .distance(0.25f) // max accepted distance
    .returnMetadata(Metadata.DISTANCE));

for (var o : response.objects()) {
  System.out.println(o.properties());
  System.out.println(o.queryMetadata().distance());
}
```

```csharp
var jeopardy = client.Collections.Use("JeopardyQuestion");
var response = await jeopardy.Query.NearText(
    "animals in movies",
    distance: 0.25f, // max accepted distance
    returnMetadata: MetadataOptions.Distance
);

foreach (var o in response.Objects)
{
    Console.WriteLine(JsonSerializer.Serialize(o.Properties));
    Console.WriteLine(o.Metadata.Distance);
}
```

```graphql
{
  Get {
    JeopardyQuestion(
      nearText: {
        concepts: ["animals in movies"]
        distance: 0.18
      }
    ) {
      question
      answer
      _additional {
        distance
      }
    }
  }
}
```

Additional information

* The distance value depends on many factors, including the vectorization model you use. Experiment with your data to find a value that works for you.
* [`certainty`](/weaviate/config-refs/distances#distance-vs-certainty) is only available with `cosine` distance.
* To find the least similar objects, use the negative cosine distance with `nearVector` search.

## `limit` & `offset`

Use `limit` to set a fixed maximum number of objects to return.

Optionally, use `offset` to paginate the results.

`offset` + `limit` cannot exceed [`QUERY_MAXIMUM_RESULTS`](/deploy/configuration/env-vars#QUERY_MAXIMUM_RESULTS) (default `10000`). A query past that ceiling returns an error rather than a truncated result set, and for a ranked search the ceiling is hard: narrow the query with filters, or raise `QUERY_MAXIMUM_RESULTS` (a higher value costs memory and query time). To iterate over every object without ranking, use a [cursor](/weaviate/manage-objects/read-all-objects) instead, as cursors do not work with ranked searches.

```python
from weaviate.classes.query import MetadataQuery

jeopardy = client.collections.use("JeopardyQuestion")
response = jeopardy.query.near_text(
    query="animals in movies",
    limit=2,  # return 2 objects
    offset=1,  # With an offset of 1
    return_metadata=MetadataQuery(distance=True),
)

for o in response.objects:
    print(o.properties)
    print(o.metadata.distance)
```

```ts
const jeopardy = client.collections.use('JeopardyQuestion');

const result = await jeopardy.query.nearText('animals in movies', {
  limit: 2,
  offset: 1,
  returnMetadata: ['distance']
})

console.log(JSON.stringify(result.objects, null, 2));
```

```go
response, err := client.GraphQL().Get().
  WithClassName("JeopardyQuestion").
  WithFields(
    graphql.Field{Name: "question"},
    graphql.Field{Name: "answer"},
    graphql.Field{
      Name: "_additional",
      Fields: []graphql.Field{
        {Name: "distance"},
      },
    },
  ).
  WithNearText(client.GraphQL().NearTextArgBuilder().
    WithConcepts([]string{"animals in movies"})).
  WithLimit(2).
  WithOffset(1).
  Do(ctx)
```

```go
jeopardy := client.Collections.Use("JeopardyQuestion")
response, err := jeopardy.Query.NearText(ctx, query.NearText{
  Concepts: []string{"animals in movies"},
  Limit:  2,
  Offset: 1,
  ReturnMetadata: query.ReturnMetadata{
    Distance: true,
  },
})
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.Properties)
  fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
}
```

```java
CollectionHandle<Map<String, Object>> jeopardy =
    client.collections.use("JeopardyQuestion");
var response = jeopardy.query.nearText("animals in movies", q -> q
    .limit(2) // return 2 objects
    .offset(1) // With an offset of 1
    .returnMetadata(Metadata.DISTANCE));

for (var o : response.objects()) {
  System.out.println(o.properties());
  System.out.println(o.queryMetadata().distance());
}
```

```csharp
var jeopardy = client.Collections.Use("JeopardyQuestion");
var response = await jeopardy.Query.NearText(
    "animals in movies",
    limit: 2, // return 2 objects
    offset: 1, // With an offset of 1
    returnMetadata: MetadataOptions.Distance
);

foreach (var o in response.Objects)
{
    Console.WriteLine(JsonSerializer.Serialize(o.Properties));
    Console.WriteLine(o.Metadata.Distance);
}
```

```graphql
{
  Get {
    JeopardyQuestion(
      nearText: {
        concepts: ["animals in movies"]
      }
      limit: 2
      offset: 1
    ) {
      question
      answer
      _additional {
        distance
      }
    }
  }
}
```

## Limit result groups

To limit results to groups of similar distances to the query, use the [`autocut`](/weaviate/api/graphql/additional-operators#autocut) filter to set the number of groups to return.

```py
from weaviate.classes.query import MetadataQuery

jeopardy = client.collections.use("JeopardyQuestion")
response = jeopardy.query.near_text(
    query="animals in movies",
    auto_limit=1,  # number of close groups
    return_metadata=MetadataQuery(distance=True),
)

for o in response.objects:
    print(o.properties)
    print(o.metadata.distance)
```

```ts
const jeopardy = client.collections.use('JeopardyQuestion');

const result = await jeopardy.query.nearText('animals in movies', {
  autoLimit: 1,
  returnMetadata: ['distance'],
})

result.objects.forEach(item => {
  console.log(JSON.stringify(item.properties, null, 2))
  console.log(item.metadata?.distance)
})
```

```go
response, err := client.GraphQL().Get().
  WithClassName("JeopardyQuestion").
  WithFields(
    graphql.Field{Name: "question"},
    graphql.Field{Name: "answer"},
    graphql.Field{
      Name: "_additional",
      Fields: []graphql.Field{
        {Name: "distance"},
      },
    },
  ).
  WithNearText(client.GraphQL().NearTextArgBuilder().
    WithConcepts([]string{"animals in movies"})).
  WithAutocut(1).
  Do(ctx)
```

```go
jeopardy := client.Collections.Use("JeopardyQuestion")
response, err := jeopardy.Query.NearText(ctx, query.NearText{
  Concepts: []string{"animals in movies"},
  AutoLimit: 1, // number of close groups
  ReturnMetadata: query.ReturnMetadata{
    Distance: true,
  },
})
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.Properties)
  fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
}
```

```java
CollectionHandle<Map<String, Object>> jeopardy =
    client.collections.use("JeopardyQuestion");
var response = jeopardy.query.nearText("animals in movies", q -> q
    .autolimit(1) // number of close groups
    .returnMetadata(Metadata.DISTANCE));

for (var o : response.objects()) {
  System.out.println(o.properties());
  System.out.println(o.queryMetadata().distance());
}
```

```csharp
var jeopardy = client.Collections.Use("JeopardyQuestion");
var response = await jeopardy.Query.NearText(
    "animals in movies",
    autoLimit: 1, // number of close groups
    returnMetadata: MetadataOptions.Distance
);

foreach (var o in response.Objects)
{
    Console.WriteLine(JsonSerializer.Serialize(o.Properties));
    Console.WriteLine(o.Metadata.Distance);
}
```

```graphql
{
  Get {
    JeopardyQuestion(
      nearText: {
        concepts: ["animals in movies"]
      }
      autocut: 1
    ) {
      question
      answer
      _additional {
        distance
      }
    }
  }
}
```

Example response

The output is like this:

```json
{
  "data": {
    "Get": {
      "JeopardyQuestion": [
        {
          "answer": "meerkats",
          "question": "Group of mammals seen <a href=\"http://www.j-archive.com/media/1998-06-01_J_28.jpg\" target=\"_blank\">here</a>:  [like Timon in <i>The Lion King</i>]",
          "_additional": { "distance": 0.17602634 }
        },
        {
          "answer": "dogs",
          "question": "Scooby-Doo, Goofy & Pluto are cartoon versions",
          "_additional": { "distance": 0.17842108 }
        }
      ]
    }
  }
}
```

## Group results

Use a property or a cross-reference to group results. To group returned objects, the query must include a `Near` search operator, such as `Near Text` or `Near Object`.

```python
from weaviate.classes.query import MetadataQuery, GroupBy

jeopardy = client.collections.use("JeopardyQuestion")

group_by = GroupBy(
    prop="round",  # group by this property
    objects_per_group=2,  # maximum objects per group
    number_of_groups=2,  # maximum number of groups
)

response = jeopardy.query.near_text(
    query="animals in movies",  # find object based on this query
    limit=10,  # maximum total objects
    return_metadata=MetadataQuery(distance=True),
    group_by=group_by,
)

for o in response.objects:
    print(o.uuid)
    print(o.belongs_to_group)
    print(o.metadata.distance)

for grp, grp_items in response.groups.items():
    print("=" * 10 + grp_items.name + "=" * 10)
    print(grp_items.number_of_objects)
    for o in grp_items.objects:
        print(o.properties)
        print(o.metadata)
```

```ts
const jeopardy = client.collections.use('JeopardyQuestion');

const result = await jeopardy.query.nearText('animals in movies', {
  limit: 10,
  returnMetadata: ['distance'],
  groupBy: {
    property: 'round',
    objectsPerGroup: 2,
    numberOfGroups: 2
  }
})

for (let group of result.objects) {
  console.log(group.uuid);
  console.log(JSON.stringify(group.belongsToGroup, null, 2));
  console.log(group.metadata?.distance);
}
```

```go
maxGroups := 2
maxObjectsPerGroup := 2
response, err := client.GraphQL().Get().
  WithClassName("JeopardyQuestion").
  WithNearText(client.GraphQL().NearTextArgBuilder().
    WithConcepts([]string{"animals in movies"})).
  WithLimit(10).
  WithGroupBy(client.GraphQL().GroupByArgBuilder().
    WithPath([]string{"round"}).
    WithGroups(maxGroups).
    WithObjectsPerGroup(maxObjectsPerGroup)).
  WithFields(graphql.Field{
    Name: "_additional",
    Fields: []graphql.Field{
      {Name: "group",
        Fields: []graphql.Field{
          {Name: "id"},
          {Name: "groupedBy",
            Fields: []graphql.Field{
              {Name: "path"},
              {Name: "value"},
            },
          },
          {Name: "count"},
          {Name: "minDistance"},
          {Name: "maxDistance"},
          {Name: "hits",
            Fields: []graphql.Field{
              {Name: "question"},
              {Name: "answer"},
            },
          },
        },
      },
    },
  }).
  Do(ctx)
```

```go
jeopardy := client.Collections.Use("JeopardyQuestion")
response, err := jeopardy.Query.NearText.GroupBy(ctx,
  query.NearText{
    Concepts: []string{"animals in movies"},
    Limit:    10, // maximum total objects
    ReturnMetadata: query.ReturnMetadata{
      Distance: true,
    },
  },
  query.GroupBy{
    Property:       "round", // group by this property
    ObjectLimit:    2,       // maximum objects per group
    NumberOfGroups: 2,       // maximum number of groups
  },
)
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.UUID)
  fmt.Printf("%v\n", obj.BelongsToGroup)
  fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
}
for name, group := range response.Groups {
  fmt.Printf("========== %s ==========\n", name)
  fmt.Printf("%d\n", group.Size)
  for _, obj := range group.Objects {
    fmt.Printf("%v\n", obj.Properties)
  }
}
```

```java
CollectionHandle<Map<String, Object>> jeopardy =
    client.collections.use("JeopardyQuestion");
var response = jeopardy.query.nearText("animals in movies", // find object based on this query
    q -> q.limit(10) // maximum total objects
        .returnMetadata(Metadata.DISTANCE),
    GroupBy.property("round", // group by this property
        2, // maximum number of groups
        2 // maximum objects per group
    ));
// response.objects().getFirst().vectors().getSingle("default");
for (var o : response.objects()) {
  // System.out.println(o.uuid());
  System.out.println(o.belongsToGroup());
  System.out.println(o.metadata().distance());
}

response.groups().forEach((groupName, group) -> {
  System.out
      .println("=" + "=".repeat(10) + group.name() + "=" + "=".repeat(10));
  System.out.println(group.numberOfObjects());
  for (var o : group.objects()) {
    System.out.println(o.properties());
    System.out.println(o.metadata());
  }
});
```

```csharp
var jeopardy = client.Collections.Use("JeopardyQuestion");

var response = await jeopardy.Query.NearText(
    "animals in movies", // find object based on this query
    limit: 10, // maximum total objects
    returnMetadata: MetadataOptions.Distance,
    groupBy: new GroupByRequest("round") // group by this property
    {
        NumberOfGroups = 2, // maximum number of groups
        ObjectsPerGroup = 2, // maximum objects per group
    }
);

foreach (var o in response.Objects)
{
    Console.WriteLine(o.UUID);
    Console.WriteLine(o.BelongsToGroup);
    Console.WriteLine(o.Metadata.Distance);
}

foreach (var group in response.Groups.Values)
{
    Console.WriteLine($"=========={group.Name}==========");
    Console.WriteLine(group.Objects.Count());
    foreach (var o in group.Objects)
    {
        Console.WriteLine(JsonSerializer.Serialize(o.Properties));
        Console.WriteLine(JsonSerializer.Serialize(o.Metadata));
    }
}
```

```graphql
{
  Get {
    JeopardyQuestion(
      nearText: {
        concepts: ["animals in movies"],
      }
      limit: 10
      groupBy: {
        path: ["round"],
        groups: 2,
        objectsPerGroup: 2
      }
    ) {
      _additional {
        group {
          id
          groupedBy {
            path
            value
          }
          count
          minDistance
          maxDistance
          hits {
            question
            answer
          }
        }
      }
    }
  }
}
```

Example response

The output is like this:

```json
{
  "data": {
    "Get": {
      "JeopardyQuestion": [
        {
          "_additional": {
            "group": {
              "count": 2,
              "groupedBy": {
                "path": [
                  "round"
                ],
                "value": "Jeopardy!"
              },
              "hits": [
                {
                  "answer": "meerkats",
                  "question": "Group of mammals seen <a href=\"http://www.j-archive.com/media/1998-06-01_J_28.jpg\" target=\"_blank\">here</a>:  [like Timon in <i>The Lion King</i>]"
                },
                {
                  "answer": "dogs",
                  "question": "Scooby-Doo, Goofy & Pluto are cartoon versions"
                }
              ],
              "id": 0,
              "maxDistance": 0.17842054,
              "minDistance": 0.17602539
            }
          }
        },
        {
          "_additional": {
            "group": {
              "count": 1,
              "groupedBy": {
                "path": [
                  "round"
                ],
                "value": "Double Jeopardy!"
              },
              "hits": [
                {
                  "answer": "fox",
                  "question": "In titles, animal associated with both Volpone and Reynard"
                }
              ],
              "id": 1,
              "maxDistance": 0.18770188,
              "minDistance": 0.18770188
            }
          }
        }
      ]
    }
  }
}
```

## Filter results

For more specific results, use a [`filter`](/weaviate/api/graphql/filters) to narrow your search.

```python
from weaviate.classes.query import MetadataQuery, Filter

jeopardy = client.collections.use("JeopardyQuestion")
response = jeopardy.query.near_text(
    query="animals in movies",
    filters=Filter.by_property("round").equal("Double Jeopardy!"),
    limit=2,
    return_metadata=MetadataQuery(distance=True),
)

for o in response.objects:
    print(o.properties)
    print(o.metadata.distance)
```

```ts
const jeopardy = client.collections.use('JeopardyQuestion');

const result = await jeopardy.query.nearText('animals in movies', {
  limit: 2,
  returnMetadata: ['distance'],
  filters: jeopardy.filter.byProperty('round').equal('Double Jeopardy!')
})

result.objects.forEach(item => {
  console.log(JSON.stringify(item.properties, null, 2))
  console.log(item.metadata?.distance)
})
```

```go
// Add "github.com/weaviate/weaviate-go-client/v5/weaviate/filters" to import

response, err := client.GraphQL().Get().
  WithClassName("JeopardyQuestion").
  WithFields(
    graphql.Field{Name: "question"},
    graphql.Field{Name: "answer"},
    graphql.Field{Name: "round"},
    graphql.Field{
      Name: "_additional",
      Fields: []graphql.Field{
        {Name: "distance"},
      },
    },
  ).
  WithNearText(client.GraphQL().NearTextArgBuilder().
    WithConcepts([]string{"animals in movies"})).
  WithLimit(2).
  WithWhere(filters.Where().
    WithPath([]string{"round"}).
    WithOperator(filters.Equal).
    WithValueString("Double Jeopardy!")).
  Do(ctx)
```

```go
jeopardy := client.Collections.Use("JeopardyQuestion")
response, err := jeopardy.Query.NearText(ctx, query.NearText{
  Concepts: []string{"animals in movies"},
  Filter: &filter.Cond{
    Target:   "round",
    Operator: filter.Equal,
    Value:    "Double Jeopardy!",
  },
  Limit: 2,
  ReturnMetadata: query.ReturnMetadata{
    Distance: true,
  },
})
if err != nil {
  // handle error
  panic(err)
}
for _, obj := range response.Objects {
  fmt.Printf("%v\n", obj.Properties)
  fmt.Printf("distance: %v\n", *obj.Metadata.Distance)
}
```

```java
CollectionHandle<Map<String, Object>> jeopardy =
    client.collections.use("JeopardyQuestion");
var response = jeopardy.query.nearText("animals in movies", q -> q
    .filters(Filter.property("round").eq("Double Jeopardy!"))
    .limit(2)
    .returnMetadata(Metadata.DISTANCE));

for (var o : response.objects()) {
  System.out.println(o.properties());
  System.out.println(o.queryMetadata().distance());
}
```

```csharp
var jeopardy = client.Collections.Use("JeopardyQuestion");
var response = await jeopardy.Query.NearText(
    "animals in movies",
    filters: Filter.Property("round").IsEqual("Double Jeopardy!"),
    limit: 2,
    returnMetadata: MetadataOptions.Distance
);

foreach (var o in response.Objects)
{
    Console.WriteLine(JsonSerializer.Serialize(o.Properties));
    Console.WriteLine(o.Metadata.Distance);
}
```

```graphql
{
  Get {
    JeopardyQuestion(
      limit: 2
      nearText: {
        concepts: ["animals in movies"]
      }
      where: {
        path: ["round"]
        operator: Equal
        valueText: "Double Jeopardy!"
      }
    ) {
      question
      answer
      _additional {
        distance
      }
    }
  }
}
```

Example response

The output is like this:

```json
{
  "data": {
    "Get": {
      "JeopardyQuestion": [
        {
          "_additional": {
            "distance": 0.18759078
          },
          "answer": "fox",
          "question": "In titles, animal associated with both Volpone and Reynard",
          "round": "Double Jeopardy!"
        },
        {
          "_additional": {
            "distance": 0.19532347
          },
          "answer": "Swan",
          "question": "In a Tchaikovsky ballet, Prince Siegfried goes hunting for these animals & falls in love with 1 of them",
          "round": "Double Jeopardy!"
        }
      ]
    }
  }
}
```

## Diversity selection (MMR)

Added in `v1.37.3` and `v1.38.6`

**Diversity selection (MMR)** for vector search was added in **`v1.37.3`**.
**Diversity selection (MMR)** for hybrid search was added in **`v1.38.6`**.

Standard vector search returns the closest matches to the query, which often means a cluster of near-duplicate results. **Maximal Marginal Relevance (MMR)** reranks results to balance relevance with diversity: each selected result must add something new to the result set.

Add the `diversity_selection` parameter to any vector search query:

```python
from weaviate.classes.query import Diversity

collection = client.collections.get("MMRDemo")

# Retrieve 20 candidates, then rerank to select 5 diverse results
response = collection.query.near_vector(
    near_vector=base_vec,
    limit=20,
    diversity_selection=Diversity.mmr(
        limit=5,
        balance=0.5,
    ),
)

for o in response.objects:
    print(o.properties["question"])
```

#### How it works

1. Weaviate runs a regular vector search to retrieve a candidate set (controlled by the query's `limit`)
2. The most relevant candidate is selected first
3. For each remaining candidate, MMR computes a score that balances query similarity against maximum similarity to already-selected results, weighted by `balance`
4. The candidate with the highest MMR score is selected next
5. Steps 3–4 repeat until the `Diversity.mmr(limit)` is reached

#### Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `limit` | int | Number of results to return after MMR reranking. Must be at least `1` and no larger than the query's top-level `limit` (the candidate set size). Weaviate returns an error if it is omitted or out of range. |
| `balance` | float | Controls the relevance-diversity trade-off (0.0–1.0). `0.0` = pure diversity, `0.5` = balanced, `1.0` = pure relevance (equivalent to standard search). |

```python
from weaviate.classes.query import Diversity

collection = client.collections.get("MMRDemo")

# Pure diversity — maximize difference between results
response_diverse = collection.query.near_vector(
    near_vector=base_vec,
    limit=20,
    diversity_selection=Diversity.mmr(limit=5, balance=0.0),
)

# Balanced — equal weight on relevance and diversity
response_balanced = collection.query.near_vector(
    near_vector=base_vec,
    limit=20,
    diversity_selection=Diversity.mmr(limit=5, balance=0.5),
)

# Pure relevance — equivalent to standard vector search
response_relevant = collection.query.near_vector(
    near_vector=base_vec,
    limit=20,
    diversity_selection=Diversity.mmr(limit=5, balance=1.0),
)
```

Important notes:

* **Result ordering**: Results are ordered by MMR score, not query similarity. The first result is the most relevant, but subsequent results may have lower query similarity because they were chosen for diversity.
* **No reindexing needed**: MMR is applied at query time. You can use it on any existing collection without schema changes.
* **Supported queries**: `near_text`, `near_vector`, `near_object`, `near_image`, and `near_media`. Hybrid search is also supported, from `v1.38.6`. See [Diversity selection with hybrid search](/weaviate/search/hybrid#diversity-selection-mmr).
* **Not supported**: multi-vector collections. Weaviate rejects these queries with an error instead of ignoring the diversity settings.

tip

A larger candidate set (higher top-level `limit`) gives MMR more results to choose from, improving diversity at the cost of slightly more computation. A good starting point is setting the candidate `limit` to 2–4x the MMR `limit`.

#### Pagination

Diversity selection changes what `offset` means. `offset` moves the candidate window rather than the page, so it must advance by the query's top-level `limit`, not by the page size or the number of objects returned. Weaviate does not validate the relationship between `offset` and `limit`, so a wrong `offset` produces no error and no warning. The only symptoms are objects that repeat across pages and objects that are never returned at all.

Candidate window, worked example, and deep pages

A diversified query works with two limits:

* the query's top-level `limit` is the **candidate window** that gets diversified, and
* the diversity `limit` is the **page size**, or how many objects come back.

Each page is taken from the slice `[offset, offset + limit)` of the relevance-ranked results, so `offset` must advance by the query `limit`:

```python
from weaviate.classes.query import Diversity

collection = client.collections.get("MMRDemo")

# The query limit is the size of the window that gets diversified.
# The diversity limit is the page size.
query_limit = 10
page_size = 3

# Advance offset by the query limit, NOT by the number of returned objects
for offset in range(0, 30, query_limit):
    page = collection.query.near_vector(
        near_vector=base_vec,
        limit=query_limit,
        offset=offset,
        diversity_selection=Diversity.mmr(limit=page_size, balance=0.5),
    )

    for o in page.objects:
        print(offset, o.properties["question"])
```

The usual pagination idiom, adding the number of returned objects to `offset`, is the failing case here. The page size is always smaller than or equal to the candidate window, so consecutive windows overlap. With a query `limit` of `10` and a diversity `limit` of `3`, advancing `offset` by `3` reads the windows `[0:10]`, `[3:13]`, and `[6:16]`, which is how objects come back twice while others are skipped.

When diversity selection is combined with a boost or with hybrid search, deep pages are also not stable slices of one fixed ranking. Both the boost pool and the two hybrid search legs fetch more candidates as `offset` grows, so which objects can reach a given page depends on how deep you have paged.

## Soft-rank with Boost

Added in `v1.38`

Vector search queries accept an optional `boost` argument that promotes or demotes matching documents without removing them. This is useful for biasing results by recency, popularity, a soft filter, or another property. Matching documents move up. Everything else stays in the results but ranks lower.

See [Boost](/weaviate/search/boost) for the supported condition types (filter, property value, time decay, numeric decay), curve choices, blending semantics, and depth tuning.

## Related pages

* [Connect to Weaviate](/weaviate/connections)
* For image search, see [Image search](/weaviate/search/image).
* For search using the GraphQL API, see [GraphQL API](/weaviate/api).

## Questions and feedback

Have a question or feedback? Here's how to reach us.

[Community Forum

Ask questions and connect with other developers on our Community forum.](https://forum.weaviate.io/c/support)[Support

Weaviate Cloud user or customer? Find the right channel on the Support page.](/support)
