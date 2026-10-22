"""Parte los documentos Markdown de data/kb/ en chunks por encabezado `##`,
los embebe con Ollama y los guarda en la colección local de Chroma."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import chromadb

from . import config
from .llm_client import OllamaClient

HEADER_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


@dataclass
class Chunk:
    source_file: str
    section_title: str
    content: str

    @property
    def id(self) -> str:
        return f"{self.source_file}::{_slugify(self.section_title)}"


def _last_paragraph(text: str) -> str:
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return paragraphs[-1] if paragraphs else ""


def split_markdown_by_headers(text: str, source_file: str) -> list[Chunk]:
    """Un chunk por sección `##`. Cada chunk (salvo el primero) lleva como
    overlap el último párrafo de la sección anterior, para no perder
    continuidad cuando el retrieval solo trae una sección aislada."""
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return [Chunk(source_file=source_file, section_title=source_file, content=text.strip())]

    sections: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((title, text[start:end].strip()))

    chunks: list[Chunk] = []
    previous_content = ""
    for title, content in sections:
        overlap = _last_paragraph(previous_content)
        chunk_content = f"{overlap}\n\n{content}" if overlap else content
        chunks.append(Chunk(source_file=source_file, section_title=title, content=chunk_content))
        previous_content = content
    return chunks


def load_kb_chunks(kb_dir: Path = config.KB_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        chunks.extend(split_markdown_by_headers(text, source_file=path.name))
    return chunks


def ingest(kb_dir: Path = config.KB_DIR) -> int:
    chunks = load_kb_chunks(kb_dir)
    if not chunks:
        return 0

    client = OllamaClient()
    embeddings = client.embed([c.content for c in chunks])

    chroma_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
    collection = chroma_client.get_or_create_collection(
        config.CHROMA_COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    collection.upsert(
        ids=[c.id for c in chunks],
        embeddings=embeddings,
        documents=[c.content for c in chunks],
        metadatas=[{"source_file": c.source_file, "section_title": c.section_title} for c in chunks],
    )
    return len(chunks)


if __name__ == "__main__":
    count = ingest()
    print(f"Ingeridos {count} chunks en la colección '{config.CHROMA_COLLECTION_NAME}'.")
