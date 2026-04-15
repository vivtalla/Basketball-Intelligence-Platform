# Official Data Source Matrix

**Last updated:** 2026-04-12

This note captures the current official-data foundation for CourtVue Labs: which NBA domains we ingest, where they persist, what product surfaces depend on them, and which official domains are still missing.

The goal is not “pull every endpoint blindly.” The goal is one canonical persisted source per product-relevant official domain, with explicit freshness and no mixed-truth request-time rescue.

---

## Canonical Official Domains

| Domain | Official source | Persisted surface | Primary owner | Product surfaces | Status |
|--------|-----------------|-------------------|---------------|------------------|--------|
| Player profile | `CommonPlayerInfo` / static roster | `players` | `sync_service.py` | player page, roster, compare, scouting | Canonical |
| Player career seasons | `PlayerCareerStats` + league advanced overlay | `season_stats` | `sync_service.py` | player profile, career charts, similarity | Canonical |
| Current-season player base + advanced | `LeagueDashPlayerStats` Base + Advanced | `season_stats` | `sync_service.py` | leaderboards, stats, insights, compare | Canonical |
| Team season base + advanced | `LeagueDashTeamStats` Base + Advanced | `team_season_stats` | `sync_service.py` | team analytics, style compare, insights support | Canonical |
| Team general splits | `TeamDashboardByGeneralSplits` | `team_split_stats` | `sync_service.py` | prep, compare, opponent context | Canonical |
| Player game logs | `PlayerGameLog` | `player_game_logs` | `sync_service.py` | player logs, compare compatibility | Persisted compatibility |
| Shot charts | `ShotChartDetail` | `player_shot_charts` | `warehouse_service.py` / queue | shot lab, team-defense shot views | Canonical |
| Schedule | NBA CDN schedule | `games`, `raw_schedule_payloads` | `warehouse_service.py` | prep queue, schedule context, game explorer | Canonical |
| Box score | NBA CDN live box score | `game_team_stats`, `game_player_stats`, `raw_game_payloads` | `warehouse_service.py` | scouting, compare, decision, game explorer | Canonical |
| Play-by-play | NBA CDN live PBP | `play_by_play_events`, `raw_game_payloads` | `warehouse_service.py` | game explorer, scouting, decision, follow-through | Canonical |
| Injuries | NBA CDN injuries + official report fallback | `player_injuries` | `sync_service.py` | availability, prep, compare | Canonical |
| Standings | derived from persisted logs / games | `team_standings` | `standings_service.py` | standings pages, prep context | Materialized canonical |

---

## Canonical Derived Domains

These are not direct stats.nba.com tables, but they are legitimate first-class domains derived from persisted canonical game/PBP data.

| Domain | Derived from | Persisted surface | Product surfaces | Status |
|--------|--------------|-------------------|------------------|--------|
| Player on/off | `play_by_play_events` stints | `player_on_off` | team intelligence, decision tools | Canonical derived |
| Lineup impact | `play_by_play_events` stints | `lineup_stats` | decision tools, team intelligence | Canonical derived |
| Clutch / second-chance / fast-break splits | warehouse materialization | `season_stats` | decision tools, insights | Canonical derived |
| Standings snapshots | materialized from persisted logs/games | `team_standings` | standings/history | Canonical derived |

---

## Current Gaps

These are the main official NBA domains still missing as first-class persisted layers.

| Domain family | Why it matters | Recommended persisted shape | Priority |
|---------------|----------------|-----------------------------|----------|
| Player split dashboards | richer player context, scouting, trend cards | `player_split_stats` | High |
| Play type | scouting and style interpretation | `play_type_stats` | High |
| Team shooting split dashboards | shot profile and style interpretation | `team_shooting_split_stats` or a split-family extension | High |
| Tracking / hustle / passing / defense dashboards | deeper style and matchup reads | domain-specific tables or a normalized dashboard family | High |
| Team opponent dashboards | opponent-aware decision framing | `team_opponent_stats` | Medium |
| Transactions / roster movement | availability and context continuity | dedicated transaction table | Medium |
| Draft / acquisition history | future roster/planning views | dedicated reference table | Low |

---

## Guardrails Going Forward

- Every new official domain must have one canonical persisted table or one explicitly canonical shared surface.
- User-facing reads should never fetch official APIs directly at request time.
- Current-season dashboards must be refreshed by explicit jobs or daily sync, not by page loads.
- If a domain is incomplete, routes should surface that honestly instead of silently repairing it inside normal reads.
- Derived domains are acceptable when they are transparently derived from canonical persisted game/PBP data and do not conflict with another official source of truth.
