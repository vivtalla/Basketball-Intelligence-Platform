# Basketball Intelligence Platform

A full-stack NBA analytics platform built for people who take basketball seriously. Not a stats lookup tool — a thinking tool. It surfaces the numbers that matter, in the context that makes them meaningful.

---

## What This Is

Most basketball stats sites show you what happened. This platform tries to help you understand *why* and *how much it mattered*.

It pulls from the same raw data as NBA.com but layers on:

- **Advanced metrics** beyond box scores — BPM, VORP, WS, TS%, on/off net rating, lineup efficiency
- **External public metrics** — EPM (Dunks & Threes), RAPTOR (FiveThirtyEight), PIPM (Basketball Index), LEBRON, RAPM — all sourced and attributed, never presented as original
- **Play-by-play derived stats** — clutch performance, second-chance points, fast-break points, and on/off splits calculated from actual stint data with real clock timestamps, not estimates
- **Career context** — aging curves, year-over-year trends, era-adjusted comparisons
- **Team intelligence** — four factors, efficiency ratings, 5-man lineup breakdowns, roster on/off

The platform is built around one principle: a number without context is noise. Sample sizes, opponent adjustments, and era normalization are always surfaced alongside the stats themselves.

---

## Features

### Player Profiles
Each player profile is a full analytical workup:
- Traditional and advanced season stats, with playoff splits
- Shot chart with heatmap mode and zone breakdown
- Per-game log with rolling 5-game trend lines
- Monthly splits and hot/cold streak detection
- On/off net rating from play-by-play stints
- External metrics panel (EPM, RAPTOR, PIPM, LEBRON, RAPM) with source attribution
- Career arc visualization — trajectory across BPM, PPG, PER, WS, TS%, VORP
- Statistical comparps — similar players across eras

### Player Comparison
- Side-by-side stat comparison across any two players
- Dual career arc overlay — align careers by age or season
- Radar chart for multi-dimensional comparison
- Advanced rows including external metrics with footnotes

### Leaderboards
- Sortable by any stat — traditional or advanced
- Compound filters: set multiple stat thresholds simultaneously
- Playoff and regular season modes

### Team Intelligence
- Full team efficiency ratings (ORTG, DRTG, net rating)
- Four factors breakdown
- Roster on/off splits from play-by-play
- 5-man lineup ratings (minimum 100 possessions)
- Season timeline and game-by-game trends

### Play-by-Play Engine
The PBP pipeline is the analytical backbone of the platform. It processes raw game events into:
- Possession counts (FGA + TOV + last-FT-ending possessions, with and-one and technical FT exclusions)
- Stint durations measured from actual clock timestamps
- On/off splits per player per season
- Lineup stats for every 5-man unit
- Clutch performance (last 5 min, score within 5)

### Other
- League standings
- Breakout Tracker — players with the biggest YoY statistical jumps
- PBP Coverage Dashboard — visibility into which games have synced play-by-play data
- Favorites/Watchlist
- Learn page — glossary and methodology

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Data viz | Recharts |
| Data fetching | SWR |
| Backend | FastAPI (Python 3.8), Pydantic v2 |
| Database | PostgreSQL (primary), SQLite (API response cache) |
| ORM | SQLAlchemy 2.0 |
| Data source | `nba_api` (NBA.com Stats API) |
| External metrics | CSV imports (EPM, RAPTOR, PIPM, LEBRON, RAPM) |

---

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 18+
- PostgreSQL (running locally or remote)

### Backend

```bash
cd backend

# Create and activate virtualenv
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up the database (creates all tables)
python -m db.ensure_schema

# Start the API server
uvicorn main:app --reload
# → http://localhost:8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# → http://localhost:3000
```

### Environment Variables

Create a `.env` file in `backend/`:

```env
DATABASE_URL=postgresql://localhost/bip
CORS_ORIGINS=http://localhost:3000
```

Create a `.env.local` file in `frontend/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Loading Data

The platform needs player and season data before it's useful.

```bash
# From backend/

# Import a season's worth of player stats
python data/bulk_import.py --season 2024-25

# Sync play-by-play data for the season (this powers on/off, lineups, clutch stats)
python data/pbp_import.py --season 2024-25

# Import external metrics from CSV (EPM, RAPTOR, PIPM, etc.)
python data/epm_rapm_import.py your_data.csv --metrics epm,raptor,pipm
```

After importing PBP data, trigger the advanced stats computation:

```bash
POST http://localhost:8000/api/advanced/sync-season
Body: {"season": "2024-25"}
```

---

## Project Structure

```
backend/
  main.py               → FastAPI app entry point
  routers/              → API endpoints (players, stats, gamelogs, shotchart, leaderboards, teams, advanced)
  services/             → Business logic (PBP processing, on/off computation, metrics)
  db/
    models.py           → ORM models (Player, SeasonStat, PlayerGameLog, PlayByPlay, PlayerOnOff, LineupStats, ...)
    ensure_schema.py    → Schema management utility
  data/
    nba_client.py       → NBA API wrapper with rate limiting and caching
    cache.py            → SQLite CacheManager

frontend/
  src/
    app/                → Pages (Next.js app directory)
    components/         → UI components (PlayerDashboard, ShotChart, DualCareerArcChart, ComparisonView, ...)
    hooks/              → Data-fetching hooks
    lib/
      api.ts            → Typed API client
      types.ts          → TypeScript interfaces
```

---

## Design Decisions Worth Knowing

**Play-by-play is the ground truth.** Box scores lie — they aggregate. The PBP engine processes every event in every game to compute on/off splits and lineup stats from first principles. Stint durations are measured from clock timestamps, not estimated from possession counts.

**Caching is intentional.** The NBA API rate-limits aggressively. Game logs are persisted to PostgreSQL (historical seasons never re-fetched; current season refreshes after 24h). Shot charts are cached in SQLite with TTL logic tied to whether the season is still active. This keeps the app stable and fast.

**External metrics are labeled.** RAPTOR, EPM, PIPM, LEBRON, and RAPM are imported from public sources. They're displayed with their provenance and never mixed with platform-computed metrics without clear distinction.

**No Alembic.** Schema changes use `ensure_schema.py` — a lightweight `Base.metadata.create_all` + `ALTER TABLE` helper. Simple enough for the current scale.

---

## API Reference

The FastAPI backend auto-generates interactive docs at `http://localhost:8000/docs` when running locally.

Key endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /api/players/search?q=` | Player search |
| `GET /api/players/{id}` | Player profile + career stats |
| `GET /api/gamelogs/{id}?season=` | Per-game log with rolling averages |
| `GET /api/shotchart/{id}?season=` | Shot locations |
| `GET /api/leaderboards?stat=&season=` | Stat leaderboards |
| `GET /api/advanced/{id}/on-off` | On/off splits |
| `GET /api/advanced/lineups` | 5-man lineup stats |
| `GET /api/teams/{id}` | Team stats and roster |
| `POST /api/advanced/sync-season` | Recompute PBP-derived stats |

---

## Contributing

This repo uses a feature branch workflow:

1. Branch from `master`: `git checkout -b feature/your-feature`
2. Open a PR when ready — include what changed and why
3. After merge, update `CLAUDE.md` sprint history

See `CLAUDE.md` for full architecture notes, caching strategy, code style rules, and sprint history.
