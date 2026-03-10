import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
load_dotenv()

connection_string = os.getenv("BLOB_CONNECTION_STRING")
container_name = os.getenv("BLOB_CONTAINER")

blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(container_name)


def upload_pdf_to_blob(file_bytes, filename):

    blob_client = container_client.get_blob_client(filename)

    blob_client.upload_blob(
    file_bytes,
    overwrite=True,
    content_type="application/pdf"
)

    return blob_client.url