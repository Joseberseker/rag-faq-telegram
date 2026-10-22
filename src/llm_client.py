import requests

from . import config


class OllamaClient:
    """Wrapper delgado sobre la API HTTP de Ollama (embeddings + chat)."""

    def __init__(self, host: str | None = None):
        self.host = host or config.OLLAMA_HOST

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model = model or config.OLLAMA_EMBED_MODEL
        response = requests.post(
            f"{self.host}/api/embed",
            json={"model": model, "input": texts},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    def chat(self, messages: list[dict], model: str | None = None) -> str:
        model = model or config.OLLAMA_CHAT_MODEL
        response = requests.post(
            f"{self.host}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
