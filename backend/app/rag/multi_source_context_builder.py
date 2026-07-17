from app.retrieval.base import SearchResult


class MultiSourceContextBuilder:
    def __init__(self, max_context_chars: int = 16000) -> None:
        self.max_context_chars = max_context_chars

    def build(self, chunks: list[SearchResult]) -> str:
        contracts = [chunk for chunk in chunks if chunk.source_type == "contract"]
        laws = [
            chunk
            for chunk in chunks
            if chunk.metadata.get("document_type") in {"LAW", "REGULATION", "COMMUNIQUE", "OTHER"}
        ]
        cases = [
            chunk
            for chunk in chunks
            if chunk.metadata.get("document_type")
            in {"SUPREME_COURT", "COUNCIL_OF_STATE", "CONSTITUTIONAL_COURT"}
        ]
        indexed = {id(chunk): index for index, chunk in enumerate(chunks, start=1)}
        sections = [
            self._section("KULLANICI SÖZLEŞMESİ", contracts, indexed),
            self._section("KANUNLAR", laws, indexed),
            self._section("EMSAL KARARLAR", cases, indexed),
        ]
        context = "\n\n".join(section for section in sections if section)
        return context[: self.max_context_chars]

    @staticmethod
    def _section(title: str, chunks: list[SearchResult], indexed: dict[int, int]) -> str:
        if not chunks:
            return ""
        entries: list[str] = []
        for chunk in chunks:
            source_number = indexed[id(chunk)]
            if chunk.source_type == "contract":
                source = f"contract_id={chunk.contract_id} chunk_id={chunk.chunk_id}"
            else:
                source = (
                    f"document_id={chunk.document_id} title={chunk.metadata.get('title')} "
                    f"official_number={chunk.metadata.get('official_number')}"
                )
            entries.append(f"[Kaynak {source_number} | {source}]\n{chunk.text}")
        divider = "=" * 20
        return f"{divider}\n{title}\n{divider}\n" + "\n\n---\n\n".join(entries)
