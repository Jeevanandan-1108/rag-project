from azure.search.documents.models import VectorizedQuery
import os
from dotenv import load_dotenv
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_INDEX"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)


# -----------------------------
# Batch upload documents
# -----------------------------
async def upload_documents_batch(documents):

    if not documents:
        return

    await search_client.upload_documents(documents)


# -----------------------------
# hybrid Search
# -----------------------------

async def hybrid_search(query, embedding, document_id=None):

    vector_query = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=10,
        fields="embedding"
    )

    filter_query = None
    if document_id:
        filter_query = f"document_id eq '{document_id}'"

    results = await search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=filter_query,
        select=["content", "file_name", "page_number", "blob_url"],
        top=10
    )

    docs = []

    print("\n--- VECTOR SEARCH RESULTS ---")

    async for doc in results:

        print(
            doc.get("file_name"),
            doc.get("page_number"),
            doc.get("@search.score")
        )

        docs.append({
            "content": doc.get("content"),
            "file_name": doc.get("file_name"),
            "page_number": doc.get("page_number"),
            "blob_url": doc.get("blob_url"),
            "embedding": doc.get("embedding"),
            "score": doc.get("@search.score")
        })

    print("-----------------------------\n")

    return docs