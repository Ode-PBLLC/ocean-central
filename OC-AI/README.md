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
  - Uses `gpt-4o` to generate answers from combined snippet context in accessible language.
  - Combines both RAG and web search responses when snippets contain relevant information.
  - Falls back to web search only if snippets don't provide a clear answer.
  - Consolidates RAG and web search results using GPT-4o for comprehensive responses.
  - Includes filtering for reliable sources in web search results.

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
  "source_used": "rag + web_search"  // or "rag" or "web_search"
}
```

## Notes

- Only marine science and ocean-related questions will be answered. Others will be rejected.
- Responses include snippet metadata to help users trace the source of information.
- The app now combines RAG and web search results for more comprehensive answers with proper citations.
- Citations reference sources broadly (e.g., "leading marine scientists") or specifically (e.g., "research published in 2020") when direct links are unavailable.
- The app automatically filters unreliable sources during web search.

#### Disclaimer: Ocean Central’s chatbot draws from trusted sources, including IPCC reports, peer-reviewed research by Professor Carlos Duarte, and a leading oceanography textbook. If needed, it searches the web for credible information while excluding low-quality sources. Responses are AI-generated, may contain inaccuracies, and do not reflect the views of Wave. This tool is not a substitute for expert advice, and Wave disclaims any responsibility for actions taken based on this content.
