from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from db.database import get_db
from models.query import QueryAskRequest, QueryAskResponse, QueryExample, QueryMetricMetadata
from rate_limiting import limiter, RATE_LIMIT_LLM_QUERY
from services.query_service import answer_query, get_query_examples, get_query_metrics

router = APIRouter()


@router.get("/examples", response_model=List[QueryExample])
def examples() -> list[dict]:
    return get_query_examples()


@router.get("/metrics", response_model=List[QueryMetricMetadata])
def metrics() -> list[dict]:
    return get_query_metrics()


@router.post("/ask", response_model=QueryAskResponse)
@limiter.limit(RATE_LIMIT_LLM_QUERY)
def ask(
    request: Request,
    payload: QueryAskRequest,
    db: Session = Depends(get_db),
) -> QueryAskResponse:
    """Sprint 98 C3 — rate-limited to 10/min/IP (or 10000/min when disabled).

    Heaviest endpoint on the platform: LLM call + DB query synthesis. The
    Cloudflare 100/10min WAF rule isn't fine-grained enough for this one;
    a single IP could spend the budget here in 10s without slowapi.
    """
    return answer_query(db, payload)
