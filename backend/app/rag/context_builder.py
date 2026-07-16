from app.retrieval.base import SearchResult


class ContextBuilder:
    def __init__(self, max_context_chars: int = 12000) -> None:
        if max_context_chars < 1:
            raise ValueError("max_context_chars must be greater than zero")
        self.max_context_chars = max_context_chars

    def build(self, chunks: list[SearchResult]) -> str:
        sections: list[str] = []
        remaining = self.max_context_chars

        for index, chunk in enumerate(chunks, start=1):
            header = (
                f"[Kaynak {index} | contract_id={chunk.contract_id} "
                f"chunk_id={chunk.chunk_id} chunk_index={chunk.chunk_index}]"
            )
            separator = "\n\n---\n\n"
            available = remaining - len(header) - len(separator)
            if available <= 0:
                break

            text = chunk.text[:available]
            sections.append(f"{header}\n{text}")
            remaining -= len(header) + len(separator) + len(text)

            if len(text) < len(chunk.text):
                break

        return separator.join(sections)
