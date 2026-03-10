import os
import hashlib
import tempfile
import time
import logging

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.search import upload_documents_batch
from app.embeddings import get_embeddings_batch


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def generate_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


# ------------------------------------------------
# Recursive text splitter
# ------------------------------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=120,
    separators=["\n\n", "\n", ".", " ", ""]
)


def chunk_text(text):
    return text_splitter.split_text(text)


# ------------------------------------------------
# PDF ingestion pipeline
# ------------------------------------------------
async def ingest_uploaded_pdf(content: bytes, file_name: str, document_id: str, blob_url: str):

    start_time = time.time()

    logger.info("====================================")
    logger.info("PDF INGESTION STARTED")
    logger.info(f"File Name: {file_name}")
    logger.info(f"Document ID: {document_id}")
    logger.info("====================================")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        temp_path = tmp.name

    parse_start = time.time()

    reader = PdfReader(temp_path)

    logger.info(f"PDF parsed in {time.time() - parse_start:.2f} sec")
    logger.info(f"Total pages: {len(reader.pages)}")

    all_chunks = []

    for page_number, page in enumerate(reader.pages):

        page_text = page.extract_text() or ""

        if not page_text.strip():
            continue

        chunks = chunk_text(page_text)

        logger.info(f"Page {page_number + 1} → {len(chunks)} chunks")

        for chunk in chunks:
            all_chunks.append({
                "content": chunk,
                "page_number": page_number + 1
            })

    logger.info(f"Total chunks created: {len(all_chunks)}")

    embed_start = time.time()

    texts = [c["content"] for c in all_chunks]

    embeddings = await get_embeddings_batch(texts)

    logger.info(
        f"Embeddings generated for {len(embeddings)} chunks "
        f"in {time.time() - embed_start:.2f} sec"
    )

    documents_batch = []
    batch_size = 50
    total_chunks = 0

    for i, (chunk_data, embedding) in enumerate(zip(all_chunks, embeddings)):

        documents_batch.append({
            "id": f"{document_id}_{chunk_data['page_number']}_{i}",
            "document_id": document_id,
            "content": chunk_data["content"],
            "file_name": file_name,
            "page_number": chunk_data["page_number"],
            "blob_url": blob_url,
            "embedding": embedding
        })

        total_chunks += 1

        if len(documents_batch) >= batch_size:

            batch_start = time.time()

            await upload_documents_batch(documents_batch)

            logger.info(
                f"Uploaded batch of {len(documents_batch)} chunks "
                f"in {time.time() - batch_start:.2f} sec"
            )

            documents_batch = []

    if documents_batch:

        batch_start = time.time()

        await upload_documents_batch(documents_batch)

        logger.info(
            f"Uploaded final batch of {len(documents_batch)} chunks "
            f"in {time.time() - batch_start:.2f} sec"
        )

    os.remove(temp_path)

    total_time = time.time() - start_time

    logger.info("====================================")
    logger.info("UPLOAD COMPLETE")
    logger.info(f"Total chunks indexed: {total_chunks}")
    logger.info(f"Total ingestion time: {total_time:.2f} sec")
    logger.info("====================================")

    return {
        "status": "added",
        "message": f"{file_name} uploaded successfully.",
        "chunks_added": total_chunks,
        "document_id": document_id,
        "ingestion_time_seconds": round(total_time, 2)
    }