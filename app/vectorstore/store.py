import logging

from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)


def get_vector_store(collection_name="ledger_chunks"):
    try:
        embeddings = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
        return PGVector(
            embeddings=embeddings,
            collection_name=collection_name,
            connection=settings.database_url,
            engine_args={"connect_args": {"connect_timeout": 5}},
        )
    except Exception as e:
        logger.error(f"Could not connect to Postgres: {e}")
        raise RuntimeError(
            "Could not connect to Postgres. Is your Docker container running? "
            "Check with: docker ps --filter name=ledger-postgres"
        ) from e