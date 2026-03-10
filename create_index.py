import os
from dotenv import load_dotenv

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration
)

from azure.core.credentials import AzureKeyCredential

load_dotenv()

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX")

credential = AzureKeyCredential(key)

client = SearchIndexClient(endpoint, credential)

# -----------------------------
# Index fields
# -----------------------------
fields = [

    # unique chunk id
    SimpleField(
        name="id",
        type=SearchFieldDataType.String,
        key=True
    ),

    # UUID for the whole PDF
    SimpleField(
        name="document_id",
        type=SearchFieldDataType.String,
        filterable=True
    ),

    # text content
    SearchableField(
        name="content",
        type=SearchFieldDataType.String
    ),

    # original file name
    SimpleField(
        name="file_name",
        type=SearchFieldDataType.String,
        filterable=True
    ),

    # page number
    SimpleField(
        name="page_number",
        type=SearchFieldDataType.Int32,
        filterable=True
    ),

    # NEW FIELD (important)
    SimpleField(
        name="blob_url",
        type=SearchFieldDataType.String,
        retrievable=True
    ),

    # vector embedding
    SearchField(
        name="embedding",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        vector_search_dimensions=1536,
        vector_search_profile_name="vector-profile"
    )
]

# -----------------------------
# Vector Search Config
# -----------------------------
vector_search = VectorSearch(
    profiles=[
        VectorSearchProfile(
            name="vector-profile",
            algorithm_configuration_name="hnsw-config"
        )
    ],
    algorithms=[
        HnswAlgorithmConfiguration(
            name="hnsw-config"
        )
    ]
)

# -----------------------------
# Create index
# -----------------------------
index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search
)

client.create_or_update_index(index)

print("Index with UUID + blob_url metadata created successfully")