from typing import Optional

from pydantic import BaseModel


class PlayerSearchResult(BaseModel):
    id: int
    full_name: str
    is_active: bool


class PlayerProfile(BaseModel):
    id: int
    full_name: str
    first_name: str
    last_name: str
    team_name: str
    team_abbreviation: str
    team_id: Optional[int] = None
    jersey: str
    position: str
    height: str
    weight: str
    birth_date: str
    country: str
    school: Optional[str] = None
    draft_year: Optional[str] = None
    draft_round: Optional[str] = None
    draft_number: Optional[str] = None
    from_year: Optional[int] = None
    to_year: Optional[int] = None
    headshot_url: str
