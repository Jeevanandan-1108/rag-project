from dotenv import load_dotenv
import os
from typing import List, Dict

load_dotenv()

from openai import AsyncAzureOpenAI
from app.embeddings import get_embedding
from app.search import hybrid_search
score_multiplier = 3000
CONFIDENCE_THRESHOLD = 60
MIN_RETRIEVAL_SCORE = 0.03
# ---------------------------------------------------
# Azure OpenAI Client
# ---------------------------------------------------
client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-01"
)


# ---------------------------------------------------
# In-memory chat history
# ---------------------------------------------------
_store: Dict[str, List[Dict[str, str]]] = {}


def get_session_history(session_id: str):
    if session_id not in _store:
        _store[session_id] = []
    return _store[session_id]


# ---------------------------------------------------
# Main Chat Function
# ---------------------------------------------------
async def chat(message: str, session_id: str, document_id: str | None = None):

    history = get_session_history(session_id)

    # =================================================
    # 1️⃣ Generate query embedding
    # =================================================
    query_embedding = await get_embedding(message)

    if not query_embedding:
        return {
            "answer": "I don't know.",
            "sources": [],
            "retrieval_debug": []
        }

    # =================================================
    # 2️⃣ Hybrid Search
    # =================================================
    results = await hybrid_search(message, query_embedding, document_id=document_id)

    use_retrieval = False
    top_score = 0
    confidence = 0

    if results and len(results) > 0:

        # raw score from Azure AI Search
        top_score = results[0].get("score", 0)

        

        print(f"Top retrieval raw score: {top_score}")
        print(f"Top retrieval confidence: {confidence}")

        # threshold based on UI score
        

        use_retrieval= top_score>MIN_RETRIEVAL_SCORE

    print(f"Retrieval enabled: {use_retrieval}")


    # =================================================
    # 3️⃣ Normal conversation (NO sources)
    # =================================================
    if not use_retrieval:

        response = await client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_CHAT"),
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                *history,
                {"role": "user", "content": message}
            ],
            temperature=0.4
        )

        answer = response.choices[0].message.content

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": answer})

        return {
            "answer": answer,
            "sources": [],
            "retrieval_debug": []
        }


    # =================================================
    # 4️⃣ Apply MMR (diverse chunks)
    # =================================================
    filtered_results = []

    for doc in results:

        score = doc.get("score", 0)
        confidence = round(min(100, score * score_multiplier), 2)
        print(f"Chunk score: {score:.5f} → {confidence}%")

        # only keep strong chunks
        if confidence > CONFIDENCE_THRESHOLD:            
            doc["confidence"] = confidence
            filtered_results.append(doc)

        
    # If nothing passes threshold
    if not filtered_results:
        return {
            "answer": "I cannot find this information in the uploaded documents.",
            "sources": [],
            "retrieval_debug": []
        }


    mmr_docs = filtered_results[:5]

    # =================================================
    # 5️⃣ Build Context
    # =================================================
    context_parts = []
    sources = []
    retrieval_debug = []

    for doc in mmr_docs:

        content = doc.get("content", "")
        file_name = doc.get("file_name", "Unknown File")
        page_number = doc.get("page_number", "Unknown Page")
        score = doc.get("score", 0)
        score_percent = doc.get("confidence",0)

        context_parts.append(
f"""
Document: {file_name}
Page: {page_number}
Score: {score}

{content}
"""
        )

        source_text = f"{file_name} - Page {page_number}"

        sources.append(source_text)

        retrieval_debug.append({
            "source": source_text,
            "file_name": file_name,
            "page_number": page_number,
            "score": score_percent,
            "content": content
        })


    context_text = "\n\n".join(context_parts)

    print("\n----- CONTEXT SENT TO LLM -----\n")
    print(context_text[:2000])
    print("\n--------------------------------\n")


    # =================================================
    # 6️⃣ LLM Generation
    # =================================================
    system_prompt = """
You are a document-based assistant.

You must answer ONLY using the provided document context.

Rules:
- Use only the information found in the context.
- If the context contains the answer, summarize it clearly.
- If the context contains partial information, explain only what is available.
- If the answer cannot be found in the context, respond exactly with:

NOT_FOUND

Do NOT use external knowledge.
Do NOT guess or invent information.
"""

    response = await client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_CHAT"),
        messages=[
            {"role": "system", "content": system_prompt},
            *history,
            {
                "role": "user",
                "content": f"Context:\n{context_text}\n\nQuestion:\n{message}"
            }
        ],
        temperature=0.2
    )

    answer = response.choices[0].message.content.strip()

    if "NOT_FOUND" in answer:
        return {
            "answer": "I cannot find this information in the uploaded documents.",
            "sources": [],
            "retrieval_debug": []
        }
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})


    return {
        "answer": answer,
        "sources": list(dict.fromkeys(sources)),  # remove duplicates
        "retrieval_debug": retrieval_debug
    }