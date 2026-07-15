from typing import Optional

from sqlalchemy.orm import Session

from app.models.document_content import DocumentContent


class DocumentContentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        contract_id: int,
        extracted_text: str,
        page_count: int,
        parser: str,
        language: str = "tr",
    ) -> DocumentContent:
        content = DocumentContent(
            contract_id=contract_id,
            extracted_text=extracted_text,
            page_count=page_count,
            parser=parser,
            language=language,
        )
        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)
        return content

    def get_by_contract_id(self, contract_id: int) -> Optional[DocumentContent]:
        return self.db.query(DocumentContent).filter(DocumentContent.contract_id == contract_id).first()
