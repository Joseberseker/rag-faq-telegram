"""Retrieval-augmented generation: recupera los chunks relevantes de Chroma
y arma la respuesta citando sus fuentes, con un guardrail anti-alucinación
cuando no hay contexto suficiente."""

from dataclasses import dataclass

import chromadb

from . import config
from .llm_client import OllamaClient

# Distancia coseno de Chroma (0 = idéntico, ~1 = sin relación). Calibrado
# manualmente contra la KB de NovaShop: preguntas del dominio caen entre
# ~0.19 y ~0.40; preguntas claramente fuera de dominio ("capital de Francia",
# "quién ganó el mundial") caen entre ~0.40 y ~0.46. 0.38 separa ambos grupos.
MAX_RELEVANT_DISTANCE = 0.38

# Con top_k=6 pueden pasar el umbral varias secciones relacionadas; mostrar
# las 6 como "fuente" es ruido para el usuario del chat. Se citan solo las
# más cercanas.
MAX_CITED_SOURCES = 3

SYSTEM_PROMPT = (
    "Eres el asistente de soporte de NovaShop, una tienda en línea. "
    "Responde SOLO con base en el contexto recuperado que se te entrega a "
    "continuación. Si el contexto no contiene la respuesta, dilo explícitamente "
    "y sugiere contactar a soporte humano — nunca inventes políticas, precios "
    "ni plazos que no estén en el contexto. Responde en español, de forma "
    "breve y directa."
)

FALLBACK_MESSAGE = (
    "No tengo información sobre eso en mi base de conocimiento. "
    "Te recomiendo contactar a soporte humano para que te ayude."
)


@dataclass
class RetrievedChunk:
    section_title: str
    source_file: str
    content: str
    distance: float

    @property
    def is_relevant(self) -> bool:
        return self.distance <= MAX_RELEVANT_DISTANCE


@dataclass
class RagAnswer:
    text: str
    sources: list[str]


def _get_collection():
    client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(
        config.CHROMA_COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def retrieve(query: str, llm: OllamaClient, top_k: int | None = None) -> list[RetrievedChunk]:
    top_k = top_k or config.RETRIEVAL_TOP_K
    collection = _get_collection()
    query_embedding = llm.embed([query])[0]
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    if not results["documents"][0]:
        return []

    return [
        RetrievedChunk(
            section_title=meta["section_title"],
            source_file=meta["source_file"],
            content=doc,
            distance=distance,
        )
        for doc, meta, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
    ]


def _format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = [f"[Fuente: {chunk.section_title}]\n{chunk.content}" for chunk in chunks]
    return "\n\n---\n\n".join(blocks)


def build_messages(query: str, chunks: list[RetrievedChunk], history: list[dict]) -> list[dict]:
    relevant = [c for c in chunks if c.is_relevant]
    context = _format_context(relevant) if relevant else "(sin contexto relevante encontrado)"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history]
    messages.append(
        {
            "role": "user",
            "content": f"Contexto recuperado:\n\n{context}\n\nPregunta del cliente: {query}",
        }
    )
    return messages


def answer(query: str, history: list[dict] | None = None, llm: OllamaClient | None = None) -> RagAnswer:
    llm = llm or OllamaClient()
    history = history or []

    chunks = retrieve(query, llm)
    relevant = [c for c in chunks if c.is_relevant]

    # Corte determinístico: en pruebas, el modelo chico local (qwen2.5:3b)
    # a veces ignora la instrucción del system prompt y responde de todos
    # modos cuando no hay contexto relevante (ej. "cuál es la capital de
    # Francia" → "París"). No confiamos solo en el prompt para el guardrail:
    # si no hay chunks relevantes, respondemos el fallback sin llamar al LLM.
    if not relevant:
        return RagAnswer(text=FALLBACK_MESSAGE, sources=[])

    messages = build_messages(query, chunks, history)
    text = llm.chat(messages)

    sources = _top_sources(relevant)
    return RagAnswer(text=text, sources=sources)


def _top_sources(relevant: list[RetrievedChunk]) -> list[str]:
    ordered = sorted(relevant, key=lambda c: c.distance)
    seen: set[str] = set()
    sources: list[str] = []
    for chunk in ordered:
        if chunk.section_title in seen:
            continue
        seen.add(chunk.section_title)
        sources.append(chunk.section_title)
        if len(sources) == MAX_CITED_SOURCES:
            break
    return sources
