from typing import Optional

from sqlalchemy.orm import Session

from app.models.contract import Contract


class ContractRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        user_id: int,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        mime_type: str,
        file_size: int,
    ) -> Contract:
        contract = Contract(
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            mime_type=mime_type,
            file_size=file_size,
        )
        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        return contract

    def get_by_id(self, contract_id: int) -> Optional[Contract]:
        return self.db.get(Contract, contract_id)

    def list_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> list[Contract]:
        return (
            self.db.query(Contract)
            .filter(Contract.user_id == user_id)
            .order_by(Contract.uploaded_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_status(self, contract: Contract, status: str) -> Contract:
        contract.status = status
        self.db.commit()
        self.db.refresh(contract)
        return contract

    def delete(self, contract: Contract) -> None:
        self.db.delete(contract)
        self.db.commit()
