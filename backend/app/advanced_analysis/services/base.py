from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.contract import Contract
from app.repositories.contract_repository import ContractRepository


class ContractAnalysisAccess:
    @staticmethod
    def require_ready_contract(db: Session, contract_id: int, user_id: int) -> Contract:
        contract = ContractRepository(db).get_by_id(contract_id)
        if not contract:
            raise NotFoundException(detail="Sözleşme bulunamadı")
        if contract.user_id != user_id:
            raise ForbiddenException(detail="Bu sözleşmeye erişim yetkiniz yok")
        if contract.status != "embedded":
            raise BadRequestException(detail="Sözleşme analiz için henüz hazır değil")
        return contract
