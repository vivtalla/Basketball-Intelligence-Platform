from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.methodology import (
    MethodologyDetailResponse,
    MethodologyRegistryResponse,
    MethodologyValidationResponse,
)
from services.methodology_registry_service import get_methodology_detail, list_methodologies
from services.methodology_validation_service import methodology_validation_report


router = APIRouter()


@router.get("", response_model=MethodologyRegistryResponse)
def methodology_registry(db: Session = Depends(get_db)):
    return list_methodologies(db=db)


@router.get("/validation", response_model=MethodologyValidationResponse)
def methodology_validation():
    return methodology_validation_report()


@router.get("/{domain}", response_model=MethodologyDetailResponse)
def methodology_detail(domain: str, db: Session = Depends(get_db)):
    return get_methodology_detail(domain, db=db)
