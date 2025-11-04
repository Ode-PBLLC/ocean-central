import openai
import hashlib
import pickle
import os

from flask import Flask, request, jsonify
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh import scoring
from openai import OpenAI
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# Load OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# Load vector stores
vector_store_oceanography = Chroma(
    persist_directory="./data/oceanography_rag_db",
    embedding_function=OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=OPENAI_API_KEY)
)

vector_store_ipcc = Chroma(
    persist_directory="./data/oceans_rag_db",
    embedding_function=OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=OPENAI_API_KEY)
)

vector_store_duarte = Chroma(
    persist_directory="./data/duarte_rag_db",
    embedding_function=OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=OPENAI_API_KEY)
)

# Load Whoosh index
WHOOSH_INDEX_DIR = 'index'
ix = open_dir(WHOOSH_INDEX_DIR)

# Simple local cache
CACHE_FILE = "/tmp/query_cache.pkl"
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "rb") as f:
        query_cache = pickle.load(f)
else:
    query_cache = {}

STOPWORDS = {"how", "does", "is", "the", "a", "an", "to", "of", "on", "in", "for", "with", "at", "by", "about"}

def preprocess_query(query):
    words = query.lower().split()
    filtered_words = [word for word in words if word not in STOPWORDS]
    return " ".join(filtered_words)

def cache_query(query, response):
    query_hash = hashlib.md5(query.encode()).hexdigest()
    
    # Add timestamp and search type
    response_with_metadata = {
        "response": response,
        "timestamp": datetime.utcnow().isoformat(),
        "source_used": response["source_used"]
    }

    query_cache[query_hash] = response_with_metadata # Replaces any old versions of the query
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(query_cache, f)
    except Exception as e:
        print(f"Warning: Failed to write cache - {e}")

def get_cached_response(query):
    query_hash = hashlib.md5(query.encode()).hexdigest()
    cached = query_cache.get(query_hash)
    return cached

def search_whoosh(query, top_n=5, snippet_length=300):
    query = preprocess_query(query)
    with ix.searcher(weighting=scoring.BM25F()) as searcher:
        parser = MultifieldParser(["title", "content"], ix.schema, group=OrGroup)
        parsed_query = parser.parse(query)
        results = searcher.search(parsed_query, limit=top_n)
        search_results = []
        for result in results:
            full_content = result["content"]
            snippet = full_content[:snippet_length]
            if len(full_content) > snippet_length:
                last_period = snippet.rfind(". ")
                if last_period != -1:
                    snippet = snippet[:last_period + 1]
            search_results.append({
                "url": result["url"],
                "title": result["title"],
                "snippet": snippet.strip() + "..." if len(full_content) > snippet_length else snippet.strip()
            })
    return search_results

def generate_openai_response(context, user_query, model="gpt-4o", max_tokens=500):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": """
                    You are a helpful assistant answering user questions using context snippets from three sources:
                    1. Ocean Studies -- Introduction to Oceanography by Segar et al.
                    2. IPCC reports.
                    3. Carlos Duarte scientific papers.

                    If the snippets clearly contain the answer to the user's question, answer it directly and concisely using language that's accessible to a broad audience. Reference the relevant snippet numbers to support your answer (e.g., "As stated in Snippet 2...").

                    If the answer is not explicitly found in the snippets, respond with "The snippets do not provide a clear answer to your question."

                    Never hallucinate facts from the snippets that are not supported by the content. Prioritize snippet-supported answers when available. 
                    
                    If the prompt is unrelated to marine science or oceanography, respond with:
                    "This question is outside of my scope. Please ask something related to marine science or ocean-related topics."
                """
            },
            {
                "role": "user",
                "content": f"""
                    User Question:
                    {user_query}

                    Snippets:
                    {context}
                """
            }
        ],
        temperature=0.8,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()

def generate_openai_response_with_web_search(user_query, model="gpt-4o-mini-search-preview", max_tokens=500):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": """
                    You are a helpful assistant with access to real-time web search. Answer user questions using the most current and reliable web information available.
                    Please only use trusted sources, such as government websites, academic institutions, or reputable news agencies.
                    Exclude claims sourced from unverified sources like personal blogs, tourism blogs, Wikipedia, or Wordpress sites, for example.            
                    Be concise and cite web results when relevant (e.g., "According to web results..."). Do not make any claims that are not cited.
                    Only answer marine science and oceanography-related questions. For other topics, respond with:
                    "This question is outside of my scope. Please ask something related to marine science or ocean-related topics."
                """
            },
            {
                "role": "user",
                "content": user_query
            }
        ],
        web_search_options={} 
    )
    return response.choices[0].message.content.strip()

def review_web_search_response(openai_response, model="gpt-4o-mini-search-preview", max_tokens=500):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": """
                     You are a helpful and discerning assistant with access to web search that reviews AI-generated responses for source quality. 
                     Your task is to check the previous response for any low-quality or untrustworthy sources (such as blogs, Wordpress sites, Wikipedia, unverified sites, user-generated content, or content farms). 
                     Revise the answer to only include claims supported by reputable, high-quality sources such as peer-reviewed articles, government institutions, academic publishers, or established news organizations. 
                     If a claim cannot be verified with and cited from a trustworthy source, omit the claim. Do not make any claims that are not cited.
                     If the response is the "question is outside of my scope", don't change it.
                """
            },
            {
                "role": "user",
                "content": f"Here is the previous answer: \n\n{openai_response}\n\n Please check for low-quality sources. Revise the answer accordingly, citing only reputable sources and excluding any from the specified domains. If any claims are unverifiable, remove it."
            }
        ],
        web_search_options={} 
    )
    return response.choices[0].message.content.strip()


@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    user_query = data.get('query', '').strip()
    if not user_query:
        return jsonify({"error": "Query is required."}), 400

    cached_response = get_cached_response(user_query)
    if cached_response:
        # Check for web search and date
        if cached_response["timestamp"]:
            if cached_response["source_used"] == "web_search":
                cached_time = datetime.fromisoformat(cached_response["timestamp"])
                if cached_time.date() == datetime.utcnow().date():
                # If web search and from today, return cached response
                    return jsonify(cached_response["response"])
                else:
                    pass
            else:
                return jsonify(cached_response["response"])
        else:
            return jsonify(cached_response["response"])
        

    # === 1. Search Whoosh index ===
    whoosh_results = search_whoosh(user_query)
    oc_links = []
    whoosh_summary = "**Ocean Central Results:**\n"
    for res in whoosh_results:
        oc_links.append({"title": res['title'], "url": res['url']})
        whoosh_summary += f"- [{res['title']}]({res['url']})\n  Snippet: {res['snippet']}\n"

    # === 2. Search vector stores
    retriever_oceanography = vector_store_oceanography.as_retriever(search_kwargs={"k": 5})
    retriever_ipcc = vector_store_ipcc.as_retriever(search_kwargs={"k": 5})
    retriever_duarte = vector_store_duarte.as_retriever(search_kwargs={"k": 5})

    oceanography_results = retriever_oceanography.get_relevant_documents(user_query)
    ipcc_results = retriever_ipcc.get_relevant_documents(user_query)
    duarte_results = retriever_duarte.get_relevant_documents(user_query)

    combined_results = oceanography_results + ipcc_results + duarte_results

    combined_summary = "**Oceanography, IPCC, and Duarte Paper Results:**\n"
    structured_snippets = []
    for i, doc in enumerate(combined_results, 1):
        snippet = doc.page_content.strip()
        source = (
            "Segar et al. (2018)" if doc in oceanography_results else
            "IPCC" if doc in ipcc_results else
            "Duarte"
        )
        if doc in oceanography_results:
            doc.metadata["source"] = "Segar et al. (2018)"
            doc.metadata["title"] = "Ocean Studies - Introduction to Oceanography Fourth Edition"
        
        combined_summary += f"- Snippet {i} ({source}): {snippet[:300]}{'...' if len(snippet) > 300 else ''}\n"
        structured_snippets.append({
            "snippet_number": i,
            "source": f"{doc.metadata.get('source', '')}, {doc.metadata.get('title', '')}, Page {doc.metadata.get('page', 'N/A')}"
        })

    # === 3. Try RAG response ===
    openai_response = generate_openai_response(combined_summary, user_query)

    if "the snippets do not provide a clear answer to your question" in openai_response.lower():
        # Fallback: Use web search only
        web_response_raw = generate_openai_response_with_web_search(user_query)
        openai_response = review_web_search_response(web_response_raw)
        source_used = "web_search"
    else:
        # Combine: Use both RAG and web search responses
        web_response_raw = generate_openai_response_with_web_search(user_query)
        web_response_clean = review_web_search_response(web_response_raw)

        # Consolidate RAG and web search answers using GPT
        consolidation_prompt = f"""
        You are a marine science assistant. The user asked: "{user_query}"

        You have two answers:
        1. From retrieved documents (RAG): {openai_response}
        2. From a real-time web search: {web_response_clean}

        Keep the citations from both the RAG and web search answers. 
        Instead of saying “According to retrieved documents,” reference the sources, either broadly (e.g., “According to leading marine scientists”) or specifically (e.g., “According to research published in 2020”). 
        When a link to a reference is unavailable, refer to the name of the study or the publication in which it was published. When referring to an author for the first time, use their full name. 
        Still include snippet numbers from the RAG response (e.g., "As stated in Snippet 2...").

        """

        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for ocean and marine science."},
                {"role": "user", "content": consolidation_prompt}
            ],
            temperature=0.7,
            max_tokens=700
        )

        openai_response = final_response.choices[0].message.content.strip()
        source_used = "rag + web_search"

    # === 4. Build response ===
    structured_response = {
        "answer": openai_response,
        "links": oc_links,
        "snippets": structured_snippets,
        "source_used": source_used
    }

    # === 5. Cache it ===
    cache_query(user_query, structured_response)

    return jsonify(structured_response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
