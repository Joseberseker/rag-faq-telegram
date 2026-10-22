from fastapi.testclient import TestClient

from src import api


class _FakeAnswer:
    def __init__(self, text, sources):
        self.text = text
        self.sources = sources


def test_health_endpoint():
    client = TestClient(api.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_returns_answer_and_sources(monkeypatch):
    monkeypatch.setattr(api.memory, "get_history", lambda session_id: [])
    recorded_turns = []
    monkeypatch.setattr(
        api.memory,
        "append_turn",
        lambda session_id, role, content: recorded_turns.append((session_id, role, content)),
    )
    monkeypatch.setattr(
        api.rag,
        "answer",
        lambda message, history=None, llm=None: _FakeAnswer("respuesta de prueba", ["Costos de envío"]),
    )

    client = TestClient(api.app)
    response = client.post("/chat", json={"session_id": "s1", "message": "¿cuánto cuesta el envío?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "respuesta de prueba", "sources": ["Costos de envío"]}
    assert recorded_turns == [
        ("s1", "user", "¿cuánto cuesta el envío?"),
        ("s1", "assistant", "respuesta de prueba"),
    ]


def test_chat_endpoint_rejects_missing_fields():
    client = TestClient(api.app)
    response = client.post("/chat", json={"session_id": "s1"})
    assert response.status_code == 422
