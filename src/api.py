"""Adaptador HTTP (FastAPI): expone el mismo núcleo de rag.py/memory.py que
usa el bot de Telegram, para que el widget web (u otro cliente) lo consuma."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import memory, rag
from .llm_client import OllamaClient

_llm = OllamaClient()

app = FastAPI(title="RAG FAQ Telegram — API")

# CORS abierto a propósito: en este MVP el widget se sirve como archivo
# estático local (file:// o http://localhost) durante el desarrollo. Si se
# despliega públicamente (ver sección de despliegue del README), restringir
# allow_origins al dominio real del frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    history = memory.get_history(request.session_id)
    result = rag.answer(request.message, history=history, llm=_llm)

    memory.append_turn(request.session_id, "user", request.message)
    memory.append_turn(request.session_id, "assistant", result.text)

    return ChatResponse(answer=result.text, sources=result.sources)
