from src.rag import MAX_CITED_SOURCES, MAX_RELEVANT_DISTANCE, RetrievedChunk, _top_sources, build_messages

RELEVANT_CHUNK = RetrievedChunk(
    section_title="Costos de envío",
    source_file="envios.md",
    content="El envío estándar cuesta $12.000 COP en ciudades principales.",
    distance=0.20,
)

IRRELEVANT_CHUNK = RetrievedChunk(
    section_title="Pagos en cuotas",
    source_file="pagos.md",
    content="Las tarjetas de crédito permiten diferir en cuotas.",
    distance=0.45,
)


def test_chunk_within_threshold_is_relevant():
    assert RELEVANT_CHUNK.is_relevant is True


def test_chunk_above_threshold_is_not_relevant():
    assert IRRELEVANT_CHUNK.is_relevant is False


def test_chunk_exactly_at_threshold_is_relevant():
    boundary = RetrievedChunk(
        section_title="x", source_file="x.md", content="x", distance=MAX_RELEVANT_DISTANCE
    )
    assert boundary.is_relevant is True


def test_build_messages_includes_relevant_context_and_question():
    messages = build_messages(
        "cuánto cuesta el envío", [RELEVANT_CHUNK, IRRELEVANT_CHUNK], history=[]
    )
    user_message = messages[-1]["content"]
    assert "Costos de envío" in user_message
    assert RELEVANT_CHUNK.content in user_message
    assert "cuánto cuesta el envío" in user_message


def test_build_messages_excludes_irrelevant_chunks_from_context():
    messages = build_messages("cuánto cuesta el envío", [IRRELEVANT_CHUNK], history=[])
    user_message = messages[-1]["content"]
    assert "sin contexto relevante encontrado" in user_message
    assert IRRELEVANT_CHUNK.content not in user_message


def test_build_messages_preserves_conversation_history():
    history = [{"role": "user", "content": "hola"}, {"role": "assistant", "content": "hola, ¿en qué te ayudo?"}]
    messages = build_messages("cuánto cuesta el envío", [RELEVANT_CHUNK], history=history)
    assert messages[0]["role"] == "system"
    assert messages[1:3] == history
    assert messages[-1]["role"] == "user"


def test_top_sources_orders_by_distance_not_alphabetically():
    far_but_relevant = RetrievedChunk(
        section_title="Zonas de cobertura", source_file="envios.md", content="x", distance=0.35
    )
    close = RetrievedChunk(
        section_title="Costos de envío", source_file="envios.md", content="x", distance=0.10
    )
    assert _top_sources([far_but_relevant, close]) == ["Costos de envío", "Zonas de cobertura"]


def test_top_sources_deduplicates_repeated_section_titles():
    chunk_a = RetrievedChunk(section_title="Costos de envío", source_file="envios.md", content="x", distance=0.10)
    chunk_b = RetrievedChunk(section_title="Costos de envío", source_file="envios.md", content="y", distance=0.20)
    assert _top_sources([chunk_a, chunk_b]) == ["Costos de envío"]


def test_top_sources_caps_at_max_cited_sources():
    chunks = [
        RetrievedChunk(section_title=f"Sección {i}", source_file="x.md", content="x", distance=0.1 * i)
        for i in range(MAX_CITED_SOURCES + 3)
    ]
    assert len(_top_sources(chunks)) == MAX_CITED_SOURCES
