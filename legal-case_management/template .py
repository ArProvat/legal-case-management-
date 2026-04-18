import os

# Base project structure
PROJECT_STRUCTURE = {
    "ai_case_pipeline": {
        "app": {
            "__init__.py": "",
            "main.py": "# FastAPI app + demo endpoint\n",
            "config.py": "# Settings (env vars)\n",
            "models.py": "# Pydantic models\n",
            "processing": {
                "__init__.py": "",
                "ocr_cleaner.py": "# OCR noise correction (regex)\n",
                "extractors.py": "# LLM structured extraction\n",
                "document_processor.py": "# Orchestrator\n",
            },
            "retrieval": {
                "__init__.py": "",
                "indexer.py": "# ChromaDB chunking + indexing\n",
                "retriever.py": "# Semantic search + citations\n",
            },
            "generation": {
                "__init__.py": "",
                "prompts.py": "# Base + improved prompt templates\n",
                "drafts.py": "# Draft generation with evidence\n",
            },
            "improvement": {
                "__init__.py": "",
                "diff_engine.py": "# Structured diff analysis\n",
                "learner.py": "# LLM pattern extraction\n",
            },
            "routers": {
                "__init__.py": "",
                "documents.py": "# /documents/* endpoints\n",
                "drafts.py": "# /drafts/* endpoints\n",
                "improvements.py": "# /improvements/* endpoints\n",
                "retrieval.py": "# /retrieval/* endpoints\n",
            },
        },
        "data": {
            "sample_documents": {}
        },
        "sample_edits": {},
        "Dockerfile": "# Docker configuration\n",
        "docker-compose.yml": "# Docker Compose setup\n",
        "requirements.txt": "# Python dependencies\n",
        "APPROACH.md": "# Project approach\n",
        "README.md": "# Project documentation\n",
    }
}


def create_structure(base_path, structure):
    for name, content in structure.items():
        path = os.path.join(base_path, name)

        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


if __name__ == "__main__":
    create_structure(".", PROJECT_STRUCTURE)
    print("✅ Project structure created successfully!")