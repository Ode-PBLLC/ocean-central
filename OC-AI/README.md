# Ocean Central RAG API (`OC_app.py`)

This is a Flask-based API application designed to answer user questions related to marine science and oceanography using a **retrieval-augmented generation (RAG)** approach. It integrates vector search, keyword-based search, and OpenAI’s GPT models to provide reliable, source-cited responses. It uses a combination of structured document retrieval and fallback web search for high-quality answers.

## Features

- **Hybrid Search Pipeline**:
  - **Whoosh Index**: Keyword-based search over scraped content from the Ocean Central website.
  - **Chroma Vector Stores**: Embedding-based retrieval from three sources:
    - *Oceanography textbook* (Segar et al.)
    - *IPCC ocean reports*
    - *Carlos Duarte’s scientific papers*

- **Query Answering**:
  - Uses `gpt-4o` to generate an answer from combined snippet context.
  - Falls back to `gpt-4o-mini-search-preview` with web search if no snippet-based answer is available.
  - Includes filtering for reliable sources in the web fallback.

- **Response Caching**:
  - Stores query results (including timestamp and source used) to avoid recomputation.
  - Caches daily for web search and indefinitely for RAG results.

## API Endpoint

### `POST /query`

#### Request JSON:
```json
{
  "query": "What is the impact of ocean acidification on coral reefs?"
}
```

#### Response JSON:
```json
{
  "answer": "As stated in Snippet 2 (IPCC)...",
  "links": [
    {"title": "Ocean Central Article", "url": "https://..."}
  ],
  "snippets": [
    {
      "snippet_number": 1,
      "source": "Segar et al. (2018), Ocean Studies..., Page 123"
    },
    ...
  ],
  "source_used": "rag"  // or "web_search"
}
```

## Notes

- Only marine science and ocean-related questions will be answered. Others will be rejected.
- Responses include snippet metadata to help users trace the source of information.
- The app automatically filters unreliable sources during web search fallback.
