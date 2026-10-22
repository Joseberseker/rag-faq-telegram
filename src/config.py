import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "data" / "kb"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.environ.get("OLLAMA_CHAT_MODEL", "qwen2.5:3b-instruct")
OLLAMA_EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_data"))
CHROMA_COLLECTION_NAME = "kb-faq"

MEMORY_DB_PATH = os.environ.get("MEMORY_DB_PATH", str(BASE_DIR / "memory.db"))

RETRIEVAL_TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", "4"))
