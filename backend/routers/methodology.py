from fastapi import APIRouter

from models.methodology import MethodologyDetailResponse, MethodologyRegistryResponse
from services.methodology_registry_service import get_methodology_detail, list_methodologies


router = APIRouter()


@router.get("", response_model=MethodologyRegistryResponse)
def methodology_registry():
    return list_methodologies()


@router.get("/{domain}", response_model=MethodologyDetailResponse)
def methodology_detail(domain: str):
    return get_methodology_detail(domain)
