from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.query import QueryAskRequest, QueryAskResponse, QueryExample, QueryMetricMetadata
from services.query_service import answer_query, get_query_examples, get_query_metrics

router = APIRouter()


@router.get("/examples", response_model=List[QueryExample])
def examples() -> list[dict]:
    return get_query_examples()


@router.get("/metrics", response_model=List[QueryMetricMetadata])
def metrics() -> list[dict]:
    return get_query_metrics()


@router.post("/ask", response_model=QueryAskResponse)
def ask(payload: QueryAskRequest, db: Session = Depends(get_db)) -> QueryAskResponse:
    return answer_query(db, payload)
