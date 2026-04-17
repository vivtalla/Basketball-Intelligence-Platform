from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class QueryAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    season: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=1, le=50)


class QueryMetricMetadata(BaseModel):
    key: str
    label: str
    description: str
    format: Literal["number", "integer", "percent", "record"]
    category: str
    aliases: List[str]
    entity_types: List[Literal["player", "team"]]
    higher_is_better: bool
    source: str


class QueryExample(BaseModel):
    category: str
    prompt: str
    description: str


class QueryFilter(BaseModel):
    metric_key: str
    label: str
    operator: Literal["gte", "lte"]
    value: float
    formatted_value: str


class QueryIntent(BaseModel):
    intent_type: str
    entity_type: Optional[Literal["player", "team"]] = None
    metric_key: Optional[str] = None
    metric_label: Optional[str] = None
    season: Optional[str] = None
    sort_direction: Optional[Literal["asc", "desc"]] = None
    limit: int = 10
    confidence: float = 0.0
    normalized_question: str
    filters: List[QueryFilter] = []


class QueryResultRow(BaseModel):
    rank: int
    entity_type: Literal["player", "team", "game", "link"]
    entity_id: Optional[str] = None
    name: str
    subtitle: Optional[str] = None
    team_abbreviation: Optional[str] = None
    abbreviation: Optional[str] = None
    value: Optional[float] = None
    formatted_value: Optional[str] = None
    detail_url: Optional[str] = None
    metrics: Dict[str, Any] = {}


class QueryAnswerCard(BaseModel):
    title: str
    summary: str
    primary_label: Optional[str] = None
    primary_value: Optional[str] = None
    href: Optional[str] = None


class QueryAskResponse(BaseModel):
    question: str
    status: Literal["ready", "empty", "needs_clarification"]
    answer: QueryAnswerCard
    intent: QueryIntent
    rows: List[QueryResultRow] = []
    metrics: List[QueryMetricMetadata] = []
    warnings: List[str] = []
    suggestions: List[str] = []
    source: str = "CourtVue persisted warehouse"
