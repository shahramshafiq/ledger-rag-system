from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings

from app.config import settings

def get_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=settings.openai_api_key)
    return PGVector(
        embeddings=embeddings,
        collection_name="ledger_chunks",
        connection=settings.database_url,
    )