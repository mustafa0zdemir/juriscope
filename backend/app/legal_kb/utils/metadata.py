import re

from app.legal_kb.models.legal_document import LegalDocument, LegalDocumentType


def extract_article(text: str) -> str | None:
    match = re.search(r"\b(?:madde|m\.)\s*(\d+[A-Za-z]?)", text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def court_name(document_type: LegalDocumentType) -> str | None:
    names = {
        LegalDocumentType.SUPREME_COURT: "Yargıtay",
        LegalDocumentType.COUNCIL_OF_STATE: "Danıştay",
        LegalDocumentType.CONSTITUTIONAL_COURT: "Anayasa Mahkemesi",
    }
    return names.get(document_type)


def build_legal_metadata(document: LegalDocument, text: str) -> dict:
    court = court_name(document.document_type)
    return {
        "source_type": "legal",
        "document_id": document.id,
        "document_type": document.document_type.value,
        "title": document.title,
        "source": document.source,
        "official_number": document.official_number,
        "publication_date": document.publication_date.isoformat() if document.publication_date else None,
        "article": extract_article(text),
        "court": court,
        "decision_number": document.official_number if court else None,
    }
