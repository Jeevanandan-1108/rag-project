import os
from dotenv import load_dotenv

from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX")

client = SearchIndexClient(endpoint, AzureKeyCredential(key))

index = client.get_index(index_name)

print("FIELDS IN INDEX:\n")

for f in index.fields:
    print(f.name)