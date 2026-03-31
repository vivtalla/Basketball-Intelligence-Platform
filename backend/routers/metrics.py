from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.leaderboard import CustomMetricRequest, CustomMetricResponse
from services.custom_metric_service import build_custom_metric_report

router = APIRouter()


@router.post("/custom", response_model=CustomMetricResponse)
def custom_metric(
    payload: CustomMetricRequest,
    db: Session = Depends(get_db),
):
    return build_custom_metric_report(db, payload)
