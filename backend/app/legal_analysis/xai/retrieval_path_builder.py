from app.legal_analysis.xai.schemas import RetrievalPathStep
from app.retrieval.base import SearchResult


class RetrievalPathBuilder:
    def build(self, chunks: list[SearchResult]) -> list[RetrievalPathStep]:
        contract_count = sum(chunk.source_type == "contract" for chunk in chunks)
        legal_count = sum(
            chunk.source_type == "legal"
            and chunk.metadata.get("document_type") not in {"SUPREME_COURT", "COUNCIL_OF_STATE", "CONSTITUTIONAL_COURT"}
            for chunk in chunks
        )
        case_count = sum(
            chunk.metadata.get("document_type") in {"SUPREME_COURT", "COUNCIL_OF_STATE", "CONSTITUTIONAL_COURT"}
            for chunk in chunks
        )
        return [
            RetrievalPathStep(stage="Question", status="completed", detail="Hukuki analiz sorgusu oluşturuldu."),
            RetrievalPathStep(stage="Contract Retrieval", status="completed", detail="Yetkili sözleşme chunk'ları arandı.", hit_count=contract_count),
            RetrievalPathStep(stage="Law Retrieval", status="completed", detail="Merkezi mevzuat bilgi tabanı arandı.", hit_count=legal_count),
            RetrievalPathStep(stage="Case Retrieval", status="completed", detail="Emsal karar kaynakları arandı.", hit_count=case_count),
            RetrievalPathStep(stage="Hybrid Merge", status="completed", detail="Semantic ve BM25 sonuçları birleştirildi.", hit_count=len(chunks)),
            RetrievalPathStep(stage="Re-ranking", status="completed", detail="Kaynaklar Cross Encoder ile yeniden sıralandı.", hit_count=len(chunks)),
            RetrievalPathStep(stage="Gemini", status="completed", detail="Kaynaklandırılmış analiz üretildi."),
            RetrievalPathStep(stage="Answer", status="completed", detail="Açıklanabilir analiz çıktısı hazırlandı."),
        ]
