import requests

from . import config


class OllamaClient:
    """Wrapper delgado sobre la API HTTP de Ollama (embeddings por ahora;
    el chat se agrega en la rama de retrieval)."""

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
