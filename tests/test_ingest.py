from src.ingest import split_markdown_by_headers

SAMPLE = """# Título del documento

## Primera sección

Contenido de la primera sección.

Segundo párrafo de la primera sección.

## Segunda sección

Contenido de la segunda sección.
"""


def test_splits_one_chunk_per_header():
    chunks = split_markdown_by_headers(SAMPLE, source_file="sample.md")
    assert [c.section_title for c in chunks] == ["Primera sección", "Segunda sección"]


def test_each_chunk_keeps_its_source_file():
    chunks = split_markdown_by_headers(SAMPLE, source_file="sample.md")
    assert all(c.source_file == "sample.md" for c in chunks)


def test_chunks_do_not_leak_content_across_sections():
    chunks = split_markdown_by_headers(SAMPLE, source_file="sample.md")
    assert "Segundo párrafo de la primera sección." not in chunks[1].content
    assert "Contenido de la segunda sección." in chunks[1].content


def test_first_chunk_is_exactly_its_own_section():
    chunks = split_markdown_by_headers(SAMPLE, source_file="sample.md")
    assert chunks[0].content == (
        "Contenido de la primera sección.\n\nSegundo párrafo de la primera sección."
    )


def test_chunk_id_is_stable_and_namespaced_by_file():
    chunks = split_markdown_by_headers(SAMPLE, source_file="sample.md")
    assert chunks[0].id == "sample.md::primera-seccion"


def test_document_without_headers_becomes_a_single_chunk():
    chunks = split_markdown_by_headers("Solo texto plano, sin encabezados.", source_file="plano.md")
    assert len(chunks) == 1
    assert chunks[0].content == "Solo texto plano, sin encabezados."
