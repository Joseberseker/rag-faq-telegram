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


def split_markdown_by_headers(text: str, source_file: str) -> list[Chunk]:
    """Un chunk por sección `##`, sin overlap entre secciones.

    La primera versión agregaba como overlap el último párrafo de la
    sección anterior, pensado para no perder continuidad. En la práctica
    causó dos bugs reales al probar el bot:
    1. Un párrafo largo de una sección podía dominar el embedding de la
       siguiente y hacer que el retrieval citara la sección equivocada
       ("¿puedo pagar en cuotas?" citaba "Facturación electrónica").
    2. Acotar el overlap a N palabras (el primer intento de arreglo) podía
       cortar la oración justo donde empezaba una negación — "No tiene
       costo adicional" se volvía "tiene costo adicional" al perder la
       primera palabra, invirtiendo el significado de una política real.
    Las secciones de esta KB ya son respuestas autocontenidas por
    diseño (una pregunta de FAQ por sección), así que el beneficio del
    overlap no compensaba el riesgo. Se prefirió simplicidad correcta
    sobre una heurística que seguía fallando."""
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return [Chunk(source_file=source_file, section_title=source_file, content=text.strip())]

    chunks: list[Chunk] = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        chunks.append(Chunk(source_file=source_file, section_title=title, content=content))
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
