
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "case_documents"

    # Paths
    data_dir: str = "./data/sample_documents"
    edits_dir: str = "./sample_edits"
    outputs_dir: str = "./outputs"

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 80

    class Config:
            env_file = ".env"

settings = Settings()
