# app/embeddings.py

import os
import logging
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()

# ----------------------------------------
# Logger
# ----------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# ----------------------------------------
# Azure OpenAI client
# ----------------------------------------
client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-01"
)

# ----------------------------------------
# Single embedding (used for queries)
# ----------------------------------------
async def get_embedding(text: str):

    response = await client.embeddings.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBED"),
        input=[text]
    )

    return response.data[0].embedding


# ----------------------------------------
# Batch embeddings (used for document ingestion)
# ----------------------------------------
async def get_embeddings_batch(texts: list[str], batch_size: int = 32):

    all_vectors = []

    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):

        batch = texts[i:i + batch_size]
        batch_number = i // batch_size + 1

        logger.info(f"Embedding batch {batch_number}/{total_batches}")

        response = await client.embeddings.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBED"),
            input=batch
        )

        vectors = [item.embedding for item in response.data]

        all_vectors.extend(vectors)
        await asyncio.sleep(0.5)

    logger.info(f"Generated {len(all_vectors)} embeddings")

    return all_vectors