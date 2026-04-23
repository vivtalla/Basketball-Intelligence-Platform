from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Team, TeamShootingSplitStat  # noqa: E402
from models.styles import TeamStyleProfileResponse  # noqa: E402
from routers.styles import build_style_xray_report  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _fake_style_profile(team_abbreviation: str, team_name: str) -> TeamStyleProfileResponse:
    return TeamStyleProfileResponse(
        team_abbreviation=team_abbreviation,
        team_name=team_name,
        season="2025-26",
        window_games=10,
        current_profile=[],
        recent_drift=[],
        league_context=[],
        opponent_comparison=[],
        scenario_bins=[],
        warnings=[],
    )


def test_style_xray_adds_shot_profile_drivers_and_dynamic_scenarios(monkeypatch):
    session = make_session()
    try:
        okc = Team(id=1610612760, abbreviation="OKC", name="Thunder")
        bos = Team(id=1610612738, abbreviation="BOS", name="Celtics")
        nyk = Team(id=1610612752, abbreviation="NYK", name="Knicks")
        session.add_all([okc, bos, nyk])
        session.flush()
        session.add_all(
            [
                TeamShootingSplitStat(team_id=okc.id, season="2025-26", is_playoff=False, split_family="OverallTeamDashboard", split_value="Overall", label="Overall", fga=2000.0, efg_pct=0.57),
                TeamShootingSplitStat(team_id=bos.id, season="2025-26", is_playoff=False, split_family="OverallTeamDashboard", split_value="Overall", label="Overall", fga=1950.0, efg_pct=0.55),
                TeamShootingSplitStat(team_id=nyk.id, season="2025-26", is_playoff=False, split_family="OverallTeamDashboard", split_value="Overall", label="Overall", fga=1900.0, efg_pct=0.54),
                TeamShootingSplitStat(team_id=okc.id, season="2025-26", is_playoff=False, split_family="ShotTypeTeamDashboard", split_value="Above the Break 3", label="Above the Break 3", fga=920.0, efg_pct=0.595, fg3a=920.0, pct_ast_fgm=0.84),
                TeamShootingSplitStat(team_id=bos.id, season="2025-26", is_playoff=False, split_family="ShotTypeTeamDashboard", split_value="Above the Break 3", label="Above the Break 3", fga=700.0, efg_pct=0.552, fg3a=700.0, pct_ast_fgm=0.76),
                TeamShootingSplitStat(team_id=nyk.id, season="2025-26", is_playoff=False, split_family="ShotTypeTeamDashboard", split_value="Above the Break 3", label="Above the Break 3", fga=560.0, efg_pct=0.531, fg3a=560.0, pct_ast_fgm=0.71),
                TeamShootingSplitStat(team_id=okc.id, season="2025-26", is_playoff=False, split_family="AssitedShotTeamDashboard", split_value="Assisted", label="Assisted", fga=1320.0, efg_pct=0.64, pct_ast_fgm=1.0, pct_uast_fgm=0.0),
                TeamShootingSplitStat(team_id=bos.id, season="2025-26", is_playoff=False, split_family="AssitedShotTeamDashboard", split_value="Assisted", label="Assisted", fga=1180.0, efg_pct=0.61, pct_ast_fgm=1.0, pct_uast_fgm=0.0),
                TeamShootingSplitStat(team_id=nyk.id, season="2025-26", is_playoff=False, split_family="AssitedShotTeamDashboard", split_value="Assisted", label="Assisted", fga=1110.0, efg_pct=0.59, pct_ast_fgm=1.0, pct_uast_fgm=0.0),
            ]
        )
        session.commit()

        def fake_league_vectors(db, season):
            profiles = {
                okc.id: {"pace": 103.0, "three_point_rate": 0.47, "ts_pct": 0.61, "assist_rate": 0.69, "net_rating": 8.5, "ftr": 0.24, "oreb_rate": 0.27, "turnover_rate": 0.12, "transition_rate": 0.16, "paint_pressure_proxy": 0.44, "def_rating": 111.0, "efg_pct": 0.58},
                bos.id: {"pace": 99.0, "three_point_rate": 0.39, "ts_pct": 0.58, "assist_rate": 0.61, "net_rating": 6.2, "ftr": 0.22, "oreb_rate": 0.25, "turnover_rate": 0.13, "transition_rate": 0.13, "paint_pressure_proxy": 0.40, "def_rating": 112.0, "efg_pct": 0.56},
                nyk.id: {"pace": 97.0, "three_point_rate": 0.35, "ts_pct": 0.56, "assist_rate": 0.58, "net_rating": 2.4, "ftr": 0.21, "oreb_rate": 0.24, "turnover_rate": 0.14, "transition_rate": 0.12, "paint_pressure_proxy": 0.42, "def_rating": 113.5, "efg_pct": 0.54},
            }
            league_values = {}
            for metric_id in next(iter(profiles.values())).keys():
                league_values[metric_id] = [profile.get(metric_id) for profile in profiles.values()]
            return profiles, {okc.id: okc.name, bos.id: bos.name, nyk.id: nyk.name}, league_values

        monkeypatch.setattr("routers.styles._season_watermark", lambda db, season: "test-with-shooting")
        monkeypatch.setattr("routers.styles._league_vectors", fake_league_vectors)
        monkeypatch.setattr("routers.styles.build_team_style_profile", lambda **kwargs: _fake_style_profile("OKC", "Thunder"))

        response = build_style_xray_report(session, "OKC", "2025-26", 10, None)

        assert response.shot_profile_drivers
        assert response.shot_profile_drivers[0].label in {"Above the Break 3", "Assisted"}
        assert "shot-profile" in response.label_reason.lower() or "above the break 3" in response.label_reason.lower()
        assert any(link.scenario_type == "raise_3pa_rate" for link in response.scenario_links)
        assert any("Above the Break 3" in neighbor.summary or "Shared shot-profile note" in neighbor.summary for neighbor in response.nearest_neighbors)
    finally:
        session.close()


def test_style_xray_gracefully_falls_back_when_shooting_splits_missing(monkeypatch):
    session = make_session()
    try:
        okc = Team(id=1610612760, abbreviation="OKC", name="Thunder")
        bos = Team(id=1610612738, abbreviation="BOS", name="Celtics")
        nyk = Team(id=1610612752, abbreviation="NYK", name="Knicks")
        session.add_all([okc, bos, nyk])
        session.commit()

        def fake_league_vectors(db, season):
            profiles = {
                okc.id: {"pace": 103.0, "three_point_rate": 0.47, "ts_pct": 0.61, "assist_rate": 0.69, "net_rating": 8.5, "ftr": 0.24, "oreb_rate": 0.27, "turnover_rate": 0.12, "transition_rate": 0.16, "paint_pressure_proxy": 0.44, "def_rating": 111.0, "efg_pct": 0.58},
                bos.id: {"pace": 99.0, "three_point_rate": 0.39, "ts_pct": 0.58, "assist_rate": 0.61, "net_rating": 6.2, "ftr": 0.22, "oreb_rate": 0.25, "turnover_rate": 0.13, "transition_rate": 0.13, "paint_pressure_proxy": 0.40, "def_rating": 112.0, "efg_pct": 0.56},
                nyk.id: {"pace": 97.0, "three_point_rate": 0.35, "ts_pct": 0.56, "assist_rate": 0.58, "net_rating": 2.4, "ftr": 0.21, "oreb_rate": 0.24, "turnover_rate": 0.14, "transition_rate": 0.12, "paint_pressure_proxy": 0.42, "def_rating": 113.5, "efg_pct": 0.54},
            }
            league_values = {}
            for metric_id in next(iter(profiles.values())).keys():
                league_values[metric_id] = [profile.get(metric_id) for profile in profiles.values()]
            return profiles, {okc.id: okc.name, bos.id: bos.name, nyk.id: nyk.name}, league_values

        monkeypatch.setattr("routers.styles._season_watermark", lambda db, season: "test-no-shooting")
        monkeypatch.setattr("routers.styles._league_vectors", fake_league_vectors)
        monkeypatch.setattr("routers.styles.build_team_style_profile", lambda **kwargs: _fake_style_profile("OKC", "Thunder"))

        response = build_style_xray_report(session, "OKC", "2025-26", 10, None)

        assert response.shot_profile_drivers == []
        assert len(response.scenario_links) == 3
        assert any("shooting splits are missing" in warning.lower() for warning in response.warnings)
    finally:
        session.close()
