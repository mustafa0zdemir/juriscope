from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.contract import ContractListResponse, ContractResponse
from app.services.contract_service import delete_contract, get_contract, list_contracts

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=ContractListResponse)
def get_user_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_contracts(db=db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/{contract_id}", response_model=ContractResponse)
def get_single_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_contract(db=db, contract_id=contract_id, user_id=current_user.id)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_contract(db=db, contract_id=contract_id, user_id=current_user.id)
