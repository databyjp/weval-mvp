Source: https://docs.weaviate.io/weaviate/search

# Query and search

Use these **query and search** how-to guides to find the data you want.

[Query basics

Learn fundamental search syntax and how to retrieve specific object properties.](/weaviate/search/basics)[Query Agent (natural language)

Ask questions in plain English - automatically translates to optimized Weaviate queries.

![](/img/cloud-icon.svg)Cloud only](/weaviate/search/query-agent)[Vector similarity search

Find objects based on vector embedding similarity using `nearVector`, `nearObject`, etc.](/weaviate/search/similarity)[Image search

Perform vector similarity searches using images as the query input.](/weaviate/search/image)[Multimedia search

Search using audio or video files as query inputs with multimedia search.](/weaviate/search/near-media)[Keyword search (BM25F)

Execute keyword searches ranked relevance using the BM25F algorithm.](/weaviate/search/bm25)[Hybrid search

Combine keyword (BM25F) and vector similarity search results with fusion algorithms.](/weaviate/search/hybrid)[Retrieval Augmented Generation (RAG)

Use search results to provide context and augment prompts for Large Language Models.](/weaviate/search/generative)[Boost

Promote or demote matching results by recency, popularity or a filter, without removing them.](/weaviate/search/boost)[Reranking

Refine and re-order search results using integrated reranker modules.](/weaviate/search/rerank)[Multiple target vectors

Search several named vectors at once and combine their scores.](/weaviate/search/multi-vector)[Query profiling

Get per-shard timing breakdowns to find out where a slow query spends its time.](/weaviate/search/query-profile)[Aggregation

Perform aggregate operations like count, mean, sum, etc., on search result sets.](/weaviate/search/aggregate)[Filters

Apply conditional filters, such as `where` clauses, to narrow down search results.](/weaviate/search/filters)

## Which search type?

| Search type | What it matches | Use it when | Cost |
| --- | --- | --- | --- |
| [Vector](/weaviate/search/similarity) | Meaning, through vector distance | The wording of the query and the data differ, or the data is not text | One vector search per query |
| [Keyword (BM25)](/weaviate/search/bm25) | Exact terms, ranked by BM25F | Names, codes, error strings, or any term that must appear literally | Inverted index lookup |
| [Hybrid](/weaviate/search/hybrid) | Both, fused into one ranking | You want one query to handle both cases. A good default for text search | Both of the above, plus fusion |
| [Boost](/weaviate/search/boost) | The search above, re-scored | Ranking should also reflect recency, popularity or a category, without dropping anything | In-memory rescoring of the candidates |
| [Rerank](/weaviate/search/rerank) | The search above, re-ordered by a model | Precision at the top of the list matters more than latency | One model call per query |

Boost and rerank are second-stage operations: they reorder what the first search retrieved. Neither adds results, so if an object is not in the initial result set, neither can pull it in. Use a [filter](/weaviate/search/filters) when a condition must remove objects instead of demoting them.

## Questions and feedback

Have a question or feedback? Here's how to reach us.

[Community Forum

Ask questions and connect with other developers on our Community forum.](https://forum.weaviate.io/c/support)[Support

Weaviate Cloud user or customer? Find the right channel on the Support page.](/support)
