from datetime import date, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.nba_client import (  # noqa: E402
    _extract_latest_official_injury_report_pdf_url,
    _parse_official_injury_report_text,
)
from db.database import Base  # noqa: E402
from db.models import InjurySyncUnresolved, Player, PlayerInjury, Team  # noqa: E402
from routers.injuries import get_current_injuries, get_unresolved_injuries  # noqa: E402
from services.player_identity_service import (  # noqa: E402
    build_player_alias_rows,
    sync_player_aliases,
)
from services.sync_service import sync_injuries  # noqa: E402
from services.team_availability_service import build_team_availability  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_extract_latest_official_injury_report_pdf_url_prefers_latest_timestamp():
    html = """
    <html>
      <body>
        <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-04-01_01_00PM.pdf">Early</a>
        <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-04-01_04_30PM.pdf">Latest</a>
      </body>
    </html>
    """

    url = _extract_latest_official_injury_report_pdf_url(
        html,
        "https://official.nba.com/nba-injury-report-2025-26-season/",
    )

    assert url.endswith("Injury-Report_2026-04-01_04_30PM.pdf")


def test_parse_official_injury_report_text_extracts_team_player_and_status():
    text = """
    Injury Report: 04/01/26 04:30 PM
    Page 1 of 1
    Game Date Game Time Matchup Team Player Name Current Status Reason
    04/01/2026 07:00 (ET) ATL@ORL Atlanta Hawks Dennis, RayJ Questionable G League - Two-Way
    Landale, Jock Questionable Injury/Illness - N/A; Illness
    Orlando Magic Black, Anthony Out
    Injury/Illness - Left Lateral
    Abdominal; Strain
    04/01/2026 07:30 (ET) BOS@MIA Boston Celtics Harper Jr., Ron Available Injury/Illness - Right Ankle; Sprain
    Shulga, Max Questionable G League - On Assignment
    Tonje, John Questionable G League - Two-Way
    Miami Heat NOT YET SUBMITTED
    """

    payload = _parse_official_injury_report_text(text, datetime(2026, 4, 1, 16, 30))
    entries = payload["InjuryList"]

    assert payload["date"] == "2026-04-01T16:30:00"
    assert [entry["PlayerName"] for entry in entries] == [
        "Dennis, RayJ",
        "Landale, Jock",
        "Black, Anthony",
        "Harper Jr., Ron",
        "Shulga, Max",
        "Tonje, John",
    ]
    assert entries[0]["Team"] == "Atlanta Hawks"
    assert entries[0]["Status"] == "Questionable"
    assert entries[0]["Injury"] == "G League"
    assert entries[0]["Detail"] == "Two-Way"
    assert entries[2]["Detail"] == "Strain"
    assert entries[3]["Status"] == "Available"


def test_sync_injuries_resolves_official_report_names_without_person_ids(monkeypatch):
    session = make_session()
    try:
        atl = Team(id=1610612737, abbreviation="ATL", name="Hawks", city="Atlanta")
        bos = Team(id=1610612738, abbreviation="BOS", name="Celtics", city="Boston")
        session.add_all([atl, bos])
        session.add_all(
            [
                Player(
                    id=1,
                    full_name="Landale",
                    first_name="Jock",
                    last_name="Landale",
                    team_id=atl.id,
                    is_active=True,
                ),
                Player(
                    id=2,
                    full_name="Dennis",
                    first_name="RayJ",
                    last_name="Dennis",
                    team_id=atl.id,
                    is_active=True,
                ),
                Player(
                    id=3,
                    full_name="Shulga",
                    first_name="Max",
                    last_name="Shulga",
                    team_id=bos.id,
                    is_active=True,
                ),
            ]
        )
        session.commit()

        monkeypatch.setattr(
            "services.sync_service.get_injuries_payload",
            lambda season=None: {
                "source": "official.nba.com/injury-report-pdf",
                "payload": {
                    "date": "2026-04-01T16:30:00",
                    "InjuryList": [
                        {
                            "Team": "Atlanta Hawks",
                            "PlayerName": "Landale, Jock",
                            "Status": "Questionable",
                            "Injury": "Illness",
                            "Detail": "N/A illness",
                            "Comment": "",
                        },
                        {
                            "Team": "Atlanta Hawks",
                            "PlayerName": "Dennis, RayJ",
                            "Status": "Questionable",
                            "Injury": "G League",
                            "Detail": "Two-Way",
                            "Comment": "",
                        },
                        {
                            "Team": "Boston Celtics",
                            "PlayerName": "Shulga, Max",
                            "Status": "Available",
                            "Injury": "Ankle",
                            "Detail": "Available if needed",
                            "Comment": "",
                        },
                    ],
                },
            },
        )

        summary = sync_injuries(session, "2025-26")
        assert summary == {"fetched": 3, "upserted": 3, "unresolved": 0}

        rows = (
            session.query(PlayerInjury)
            .order_by(PlayerInjury.player_id.asc())
            .all()
        )
        assert [row.player_id for row in rows] == [1, 2, 3]
        assert rows[0].team_id == atl.id
        assert rows[1].detail == "Two-Way"
        assert rows[2].source == "official.nba.com/injury-report-pdf"
    finally:
        session.close()


def test_build_player_alias_rows_covers_last_first_diacritics_apostrophes_and_suffixes():
    players = [
        Player(full_name="Stephen Curry", first_name="Stephen", last_name="Curry"),
        Player(full_name="Kristaps Porzingis", first_name="Kristaps", last_name="Porziņģis"),
        Player(full_name="De'Andre Hunter", first_name="De'Andre", last_name="Hunter"),
        Player(full_name="Ron Harper Jr.", first_name="Ron", last_name="Harper Jr."),
    ]

    alias_sets = [{normalized for normalized, _display in build_player_alias_rows(player)} for player in players]

    assert "curry stephen" in alias_sets[0]
    assert "kristaps porzingis" in alias_sets[1]
    assert "deandre hunter" in alias_sets[2]
    assert "harper ron jr" in alias_sets[3]


def test_sync_injuries_persists_unresolved_entries_idempotently(monkeypatch):
    session = make_session()
    try:
        atl = Team(id=1610612737, abbreviation="ATL", name="Hawks", city="Atlanta")
        session.add(atl)
        session.add(
            Player(
                id=1,
                full_name="Jalen Example",
                first_name="Jalen",
                last_name="Example",
                team_id=atl.id,
                is_active=True,
            )
        )
        session.commit()

        monkeypatch.setattr(
            "services.sync_service.get_injuries_payload",
            lambda season=None: {
                "source": "official.nba.com/injury-report-pdf",
                "source_url": "https://official.nba.com/report.pdf",
                "payload": {
                    "date": "2026-04-01T16:30:00",
                    "InjuryList": [
                        {
                            "Team": "Atlanta Hawks",
                            "TeamAbbreviation": "ATL",
                            "PlayerName": "Curry, Stephen",
                            "Status": "Out",
                            "Injury": "Rest",
                            "Detail": "Scheduled maintenance",
                            "Comment": "",
                        }
                    ],
                },
            },
        )

        first = sync_injuries(session, "2025-26")
        second = sync_injuries(session, "2025-26")

        rows = session.query(InjurySyncUnresolved).all()
        assert first == {"fetched": 1, "upserted": 0, "unresolved": 1}
        assert second == {"fetched": 1, "upserted": 0, "unresolved": 1}
        assert len(rows) == 1
        assert rows[0].source_url == "https://official.nba.com/report.pdf"
        assert rows[0].normalized_lookup_key == "atl curry stephen"
    finally:
        session.close()


def test_sync_injuries_prefers_team_alias_then_unique_league_alias(monkeypatch):
    session = make_session()
    try:
        atl = Team(id=1610612737, abbreviation="ATL", name="Hawks", city="Atlanta")
        bos = Team(id=1610612738, abbreviation="BOS", name="Celtics", city="Boston")
        session.add_all([atl, bos])
        session.add_all(
            [
                Player(id=30, full_name="Stephen Curry", first_name="Stephen", last_name="Curry", team_id=1610612744, is_active=True),
                Player(id=31, full_name="Seth Curry", first_name="Seth", last_name="Curry", team_id=bos.id, is_active=True),
                Player(id=32, full_name="Kristaps Porziņģis", first_name="Kristaps", last_name="Porziņģis", team_id=bos.id, is_active=True),
            ]
        )
        session.commit()
        for player in session.query(Player).all():
            sync_player_aliases(session, player, source="test")
        session.commit()

        monkeypatch.setattr(
            "services.sync_service.get_injuries_payload",
            lambda season=None: {
                "source": "official.nba.com/injury-report-pdf",
                "payload": {
                    "date": "2026-04-01T16:30:00",
                    "InjuryList": [
                        {
                            "Team": "Boston Celtics",
                            "TeamAbbreviation": "BOS",
                            "PlayerName": "Porzingis, Kristaps",
                            "Status": "Probable",
                            "Injury": "Knee",
                            "Detail": "Soreness",
                            "Comment": "",
                        },
                        {
                            "Team": "Boston Celtics",
                            "TeamAbbreviation": "BOS",
                            "PlayerName": "Curry, Seth",
                            "Status": "Questionable",
                            "Injury": "Back",
                            "Detail": "Tightness",
                            "Comment": "",
                        },
                    ],
                },
            },
        )

        summary = sync_injuries(session, "2025-26")
        rows = session.query(PlayerInjury).order_by(PlayerInjury.player_id.asc()).all()

        assert summary == {"fetched": 2, "upserted": 2, "unresolved": 0}
        assert [row.player_id for row in rows] == [31, 32]
        assert rows[0].injury_status == "Questionable"
        assert rows[1].injury_status == "Probable"
    finally:
        session.close()


def test_sync_injuries_ambiguous_last_name_stays_unresolved(monkeypatch):
    session = make_session()
    try:
        atl = Team(id=1610612737, abbreviation="ATL", name="Hawks", city="Atlanta")
        session.add(atl)
        session.add_all(
            [
                Player(id=1, full_name="Jalen Williams", first_name="Jalen", last_name="Williams", team_id=atl.id, is_active=True),
                Player(id=2, full_name="Jaylin Williams", first_name="Jaylin", last_name="Williams", team_id=atl.id, is_active=True),
            ]
        )
        session.commit()
        for player in session.query(Player).all():
            sync_player_aliases(session, player, source="test")
        session.commit()

        monkeypatch.setattr(
            "services.sync_service.get_injuries_payload",
            lambda season=None: {
                "source": "official.nba.com/injury-report-pdf",
                "payload": {
                    "date": "2026-04-01T16:30:00",
                    "InjuryList": [
                        {
                            "Team": "Atlanta Hawks",
                            "TeamAbbreviation": "ATL",
                            "PlayerName": "Williams",
                            "Status": "Questionable",
                            "Injury": "Ankle",
                            "Detail": "Sprain",
                            "Comment": "",
                        }
                    ],
                },
            },
        )

        summary = sync_injuries(session, "2025-26")

        assert summary == {"fetched": 1, "upserted": 0, "unresolved": 1}
        assert session.query(PlayerInjury).count() == 0
        unresolved = session.query(InjurySyncUnresolved).one()
        assert unresolved.player_name == "Williams"
    finally:
        session.close()


def test_build_team_availability_ignores_available_status_entries():
    session = make_session()
    try:
        atl = Team(id=1610612737, abbreviation="ATL", name="Hawks", city="Atlanta")
        session.add(atl)
        session.add_all(
            [
                Player(id=1, full_name="Alpha Guard", first_name="Alpha", last_name="Guard", team_id=atl.id, is_active=True),
                Player(id=2, full_name="Bravo Wing", first_name="Bravo", last_name="Wing", team_id=atl.id, is_active=True),
            ]
        )
        session.add_all(
            [
                PlayerInjury(
                    player_id=1,
                    team_id=atl.id,
                    report_date=date(2026, 4, 1),
                    season="2025-26",
                    injury_status="Available",
                    injury_type="Ankle",
                    detail="Available if needed",
                ),
                PlayerInjury(
                    player_id=2,
                    team_id=atl.id,
                    report_date=date(2026, 4, 1),
                    season="2025-26",
                    injury_status="Out",
                    injury_type="Hamstring",
                    detail="Will miss game",
                ),
            ]
        )
        session.commit()

        availability = build_team_availability(session, "ATL", "2025-26", today=date(2026, 4, 1))

        assert availability.unavailable_count == 1
        assert availability.questionable_count == 0
        assert availability.available_count == 1
        assert [player.player_name for player in availability.unavailable_players] == ["Bravo Wing"]
    finally:
        session.close()


def test_get_current_injuries_excludes_available_rows():
    session = make_session()
    try:
        atl = Team(id=1610612737, abbreviation="ATL", name="Hawks", city="Atlanta")
        session.add(atl)
        session.add_all(
            [
                Player(id=1, full_name="Alpha Guard", first_name="Alpha", last_name="Guard", team_id=atl.id, is_active=True),
                Player(id=2, full_name="Bravo Wing", first_name="Bravo", last_name="Wing", team_id=atl.id, is_active=True),
            ]
        )
        session.add_all(
            [
                PlayerInjury(
                    player_id=1,
                    team_id=atl.id,
                    report_date=date(2026, 4, 1),
                    season="2025-26",
                    injury_status="Available",
                    injury_type="Ankle",
                    detail="Available if needed",
                ),
                PlayerInjury(
                    player_id=2,
                    team_id=atl.id,
                    report_date=date(2026, 4, 1),
                    season="2025-26",
                    injury_status="Probable",
                    injury_type="Hamstring",
                    detail="Warmup decision",
                ),
            ]
        )
        session.commit()

        response = get_current_injuries(season="2025-26", db=session)

        assert response.count == 1
        assert [injury.player_name for injury in response.injuries] == ["Bravo Wing"]
    finally:
        session.close()


def test_get_unresolved_injuries_filters_by_season_and_report_date():
    session = make_session()
    try:
        session.add_all(
            [
                InjurySyncUnresolved(
                    season="2025-26",
                    report_date=date(2026, 4, 1),
                    team_abbreviation="ATL",
                    team_name="Atlanta Hawks",
                    player_name="Example, One",
                    injury_status="Out",
                    injury_type="Ankle",
                    detail="Sprain",
                    source="official.nba.com/injury-report-pdf",
                    source_url="https://official.nba.com/report.pdf",
                    normalized_lookup_key="atl example one",
                ),
                InjurySyncUnresolved(
                    season="2024-25",
                    report_date=date(2025, 4, 1),
                    team_abbreviation="BOS",
                    team_name="Boston Celtics",
                    player_name="Example, Two",
                    injury_status="Questionable",
                    injury_type="Knee",
                    detail="Soreness",
                    source="official.nba.com/injury-report-pdf",
                    source_url="https://official.nba.com/report.pdf",
                    normalized_lookup_key="bos example two",
                ),
            ]
        )
        session.commit()

        rows = get_unresolved_injuries(season="2025-26", report_date=date(2026, 4, 1), db=session)

        assert len(rows) == 1
        assert rows[0].player_name == "Example, One"
        assert rows[0].team_abbreviation == "ATL"
    finally:
        session.close()
