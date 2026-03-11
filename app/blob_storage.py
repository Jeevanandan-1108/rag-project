import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

def get_container_client():

    connection_string = os.getenv("BLOB_CONNECTION_STRING")
    container_name = os.getenv("BLOB_CONTAINER")

    if not connection_string:
        raise ValueError("BLOB_CONNECTION_STRING is missing")

    if not container_name:
        raise ValueError("BLOB_CONTAINER is missing")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    return blob_service_client.get_container_client(container_name)


def upload_pdf_to_blob(file_bytes, filename):

    container_client = get_container_client()

    blob_client = container_client.get_blob_client(filename)

    blob_client.upload_blob(
        file_bytes,
        overwrite=True,
        content_type="application/pdf"
    )

    return blob_client.url