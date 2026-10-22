from src import config, memory


def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MEMORY_DB_PATH", str(tmp_path / "memory.db"))


def test_history_empty_for_new_session(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    assert memory.get_history("new-session") == []


def test_append_and_retrieve_preserves_order(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    memory.append_turn("chat-1", "user", "hola")
    memory.append_turn("chat-1", "assistant", "hola, ¿en qué te ayudo?")

    assert memory.get_history("chat-1") == [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "hola, ¿en qué te ayudo?"},
    ]


def test_sessions_are_isolated(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    memory.append_turn("chat-a", "user", "mensaje de a")
    memory.append_turn("chat-b", "user", "mensaje de b")

    assert memory.get_history("chat-a") == [{"role": "user", "content": "mensaje de a"}]
    assert memory.get_history("chat-b") == [{"role": "user", "content": "mensaje de b"}]


def test_history_is_truncated_to_limit(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    for i in range(20):
        memory.append_turn("chat-1", "user", f"mensaje {i}")

    history = memory.get_history("chat-1", limit=4)

    assert len(history) == 4
    assert history[-1]["content"] == "mensaje 19"


def test_history_survives_a_new_connection(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    memory.append_turn("chat-1", "user", "¿siguen ahí?")

    # Simula un reinicio del proceso: no hay estado en memoria del proceso,
    # solo lo que persiste en el archivo SQLite.
    assert memory.get_history("chat-1") == [{"role": "user", "content": "¿siguen ahí?"}]
