from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ConfidenceLabel = Literal["high", "medium", "low"]


class UncertaintyBand(BaseModel):
    lower: Optional[float] = None
    upper: Optional[float] = None
    level: float = 0.90
    method: str = "normal_approximation"


class SampleContext(BaseModel):
    sample_size: Optional[int] = None
    effective_sample_size: Optional[float] = None
    population_size: Optional[int] = None
    minimum_recommended: Optional[int] = None
    notes: List[str] = Field(default_factory=list)


class DriverBreakdown(BaseModel):
    key: str
    label: str
    value: Optional[float] = None
    weight: Optional[float] = None
    contribution: Optional[float] = None
    explanation: str


class AnalysisMetadata(BaseModel):
    methodology_version: str
    reliability_score: Optional[float] = None
    confidence: Optional[ConfidenceLabel] = None
    uncertainty_band: Optional[UncertaintyBand] = None
    sample_context: Optional[SampleContext] = None
    driver_breakdown: List[DriverBreakdown] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    validation_notes: List[str] = Field(default_factory=list)


class MethodologyDomain(BaseModel):
    domain: str
    label: str
    methodology_version: str
    status: str
    model_stage: str = "production"
    question_answered: str
    input_families: List[str]
    season_type_support: List[str] = Field(default_factory=lambda: ["Regular Season"])
    sample_gates: List[str] = Field(default_factory=list)
    confidence_rules: List[str] = Field(default_factory=list)
    reliability_policy: str
    explainability_policy: str
    known_limitations: List[str] = Field(default_factory=list)
    validation_notes: List[str] = Field(default_factory=list)
    last_validation_date: Optional[str] = None
    docs_path: str = "specs/platform-methodology.md"
    implementation_refs: List[str] = Field(default_factory=list)


class MethodologyRegistryResponse(BaseModel):
    version: str
    domains: List[MethodologyDomain]


class MethodologyDetailResponse(MethodologyDomain):
    related_domains: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)


class MethodologyValidationFixture(BaseModel):
    fixture_key: str
    domain: str
    label: str
    expected_result: str
    current_result: str
    passed: bool
    notes: List[str] = Field(default_factory=list)


class MethodologyValidationResponse(BaseModel):
    version: str
    fixtures: List[MethodologyValidationFixture]
