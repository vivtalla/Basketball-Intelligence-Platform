"""One-off generator for `player_injury_history_seed.csv`.

Run from backend/:
    python data/seed/_generate_player_injury_history_seed.py

Output is committed to the repo. The historical seed is fabricated-but-realistic
synthetic data, used by FO5 (Sprint 78) for the injury duration model
fallback distribution. Real ProSportsTransactions ingestion is a future
enhancement (see TODO in `data/sync_injury_history.py`).
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

# Stable seed so repeated runs are deterministic.
random.seed(20260428)

# Real NBA person_ids spanning star-, mid-, and bench-tier players. Mix of
# active and recently-retired players. The upsert script skips rows whose
# player_id is not present in the DB, so even partial roster overlap is fine.
PLAYER_POOL = [
    (2544, 39),       # LeBron James (age estimate end of 2023-24)
    (201939, 36),     # Stephen Curry
    (201142, 35),     # Kevin Durant
    (203507, 30),     # Giannis Antetokounmpo
    (203999, 29),     # Nikola Jokic
    (1628369, 26),    # Jayson Tatum
    (1629029, 24),    # Luka Doncic
    (1628378, 27),    # Donovan Mitchell
    (1627759, 27),    # Jaylen Brown
    (1628973, 25),    # Jalen Brunson
    (1630162, 21),    # Anthony Edwards
    (1629627, 23),    # Zion Williamson
    (1628983, 25),    # Shai Gilgeous-Alexander
    (1629029, 24),
    (203954, 31),     # Joel Embiid
    (1626156, 28),    # Devin Booker
    (1627783, 28),    # Pascal Siakam
    (1626164, 28),    # Karl-Anthony Towns
    (203501, 31),     # Tobias Harris
    (1628368, 27),    # De'Aaron Fox
    (1626174, 28),    # Andrew Wiggins
    (1628384, 26),    # OG Anunoby
    (203944, 30),     # Julius Randle
    (203484, 32),     # Kentavious Caldwell-Pope
    (203952, 32),     # Andre Drummond
    (1628386, 27),    # Bam Adebayo
    (203497, 32),     # Rudy Gobert
    (1628389, 27),    # John Collins
    (1626168, 30),    # D'Angelo Russell
    (1628973, 25),
    (1629631, 23),    # Anthony Black? Substitute generic id
    (203083, 32),     # Harrison Barnes
    (1626162, 27),    # Jerami Grant? subs
    (1627742, 28),    # Brandon Ingram
    (203114, 30),     # Khris Middleton
    (203076, 30),     # Anthony Davis
    (202691, 33),     # Klay Thompson
    (201935, 35),     # James Harden
    (202326, 33),     # DeMar DeRozan
    (203900, 31),     # Reggie Bullock
    (101108, 38),     # Chris Paul
    (1629630, 23),    # LaMelo Ball
    (1629028, 26),    # Deandre Ayton
    (1628404, 28),    # Markelle Fultz
    (1628991, 24),    # Lonnie Walker
    (1629680, 23),    # PJ Washington
    (1626179, 27),    # Norman Powell
    (1629597, 25),    # Tyler Herro
    (1629637, 23),    # Cole Anthony
    (1629659, 23),    # Tyrese Maxey
]

# Body parts and their distributions of severity + games_missed median.
# These shape the synthetic distribution so the model has signal to learn.
BODY_PARTS = {
    "knee":         {"min": 4,  "median": 14, "max": 60, "severity_dist": {"minor": 0.15, "moderate": 0.45, "severe": 0.30, "season-ending": 0.10}},
    "ankle":        {"min": 1,  "median": 7,  "max": 25, "severity_dist": {"minor": 0.45, "moderate": 0.40, "severe": 0.13, "season-ending": 0.02}},
    "hamstring":    {"min": 2,  "median": 9,  "max": 20, "severity_dist": {"minor": 0.30, "moderate": 0.50, "severe": 0.18, "season-ending": 0.02}},
    "lower-back":   {"min": 1,  "median": 5,  "max": 18, "severity_dist": {"minor": 0.50, "moderate": 0.35, "severe": 0.13, "season-ending": 0.02}},
    "shoulder":     {"min": 2,  "median": 11, "max": 35, "severity_dist": {"minor": 0.25, "moderate": 0.45, "severe": 0.25, "season-ending": 0.05}},
    "finger":       {"min": 1,  "median": 3,  "max": 10, "severity_dist": {"minor": 0.70, "moderate": 0.25, "severe": 0.05, "season-ending": 0.00}},
    "calf":         {"min": 2,  "median": 8,  "max": 22, "severity_dist": {"minor": 0.35, "moderate": 0.45, "severe": 0.18, "season-ending": 0.02}},
    "foot":         {"min": 3,  "median": 12, "max": 40, "severity_dist": {"minor": 0.20, "moderate": 0.45, "severe": 0.30, "season-ending": 0.05}},
    "wrist":        {"min": 1,  "median": 6,  "max": 18, "severity_dist": {"minor": 0.55, "moderate": 0.35, "severe": 0.10, "season-ending": 0.00}},
    "groin":        {"min": 1,  "median": 6,  "max": 15, "severity_dist": {"minor": 0.50, "moderate": 0.40, "severe": 0.10, "season-ending": 0.00}},
}

# Seasons we cover. Three full prior seasons + most of the current one.
SEASONS = [
    ("2022-23", date(2022, 10, 18), date(2023, 4, 9)),
    ("2023-24", date(2023, 10, 24), date(2024, 4, 14)),
    ("2024-25", date(2024, 10, 22), date(2025, 4, 13)),
    ("2025-26", date(2025, 10, 21), date(2026, 4, 12)),
]


def _pick_severity(severity_dist):
    roll = random.random()
    cum = 0.0
    for severity, prob in severity_dist.items():
        cum += prob
        if roll <= cum:
            return severity
    return "moderate"


def _games_missed(body_meta, severity):
    base = body_meta["median"]
    lo = body_meta["min"]
    hi = body_meta["max"]
    if severity == "minor":
        return max(lo, int(round(random.gauss(max(lo + 1, base * 0.5), 1.5))))
    if severity == "moderate":
        return max(lo + 1, int(round(random.gauss(base, max(2.0, base * 0.25)))))
    if severity == "severe":
        return min(hi, max(base + 3, int(round(random.gauss(base * 1.7, base * 0.30)))))
    # season-ending
    return min(hi, max(base * 2, int(round(random.gauss(hi * 0.85, hi * 0.10)))))


def _pick_season_window(season_meta):
    name, start, end = season_meta
    span_days = (end - start).days
    offset = random.randint(0, max(1, span_days - 3))
    return name, start + timedelta(days=offset)


def main():
    out_path = Path(__file__).resolve().parent / "player_injury_history_seed.csv"
    rows = []
    target_rows = 220
    body_part_keys = list(BODY_PARTS.keys())
    body_part_weights = [3, 4, 3, 2, 2, 2, 2, 2, 1, 1]  # rough realism

    seen_keys = set()
    # First pass — give each player at least one row per season they're active.
    for player_id, age_now in PLAYER_POOL:
        for season_meta in SEASONS:
            if random.random() < 0.55:
                continue  # not every player gets injured every season
            body_part = random.choices(body_part_keys, weights=body_part_weights, k=1)[0]
            body_meta = BODY_PARTS[body_part]
            severity = _pick_severity(body_meta["severity_dist"])
            games_missed = _games_missed(body_meta, severity)
            season_name, started_on = _pick_season_window(season_meta)
            resolved_on = started_on + timedelta(days=int(games_missed * 2.2))
            # Age at start: roll back from age_now using how many seasons ago.
            seasons_back = SEASONS.index(season_meta)
            age_at_start = max(19.0, float(age_now) - (len(SEASONS) - 1 - seasons_back))
            is_recurring = False
            key = (player_id, season_name, body_part, started_on.isoformat())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append({
                "player_id": player_id,
                "season": season_name,
                "body_part": body_part,
                "severity": severity,
                "started_on": started_on.isoformat(),
                "resolved_on": resolved_on.isoformat() if severity != "season-ending" else "",
                "games_missed": games_missed,
                "age_at_start": round(age_at_start, 1),
                "is_recurring": "true" if is_recurring else "false",
                "source": "seed_synthetic",
            })

    # Recurring-injury padding: pick 30 random players and give them a same-
    # body-part repeat in a later season.
    by_player = {}
    for row in rows:
        by_player.setdefault(row["player_id"], []).append(row)

    repeat_pool = [pid for pid, runs in by_player.items() if len(runs) >= 2]
    random.shuffle(repeat_pool)
    for player_id in repeat_pool[:30]:
        runs = sorted(by_player[player_id], key=lambda r: r["started_on"])
        first = runs[0]
        body_part = first["body_part"]
        # find a later season slot
        first_season_index = next(
            i for i, meta in enumerate(SEASONS) if meta[0] == first["season"]
        )
        if first_season_index >= len(SEASONS) - 1:
            continue
        later_seasons = SEASONS[first_season_index + 1:]
        season_meta = random.choice(later_seasons)
        body_meta = BODY_PARTS[body_part]
        severity = _pick_severity(body_meta["severity_dist"])
        games_missed = _games_missed(body_meta, severity)
        season_name, started_on = _pick_season_window(season_meta)
        resolved_on = started_on + timedelta(days=int(games_missed * 2.2))
        age_at_start = float(first["age_at_start"]) + (
            SEASONS.index(season_meta) - first_season_index
        )
        key = (player_id, season_name, body_part, started_on.isoformat())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        rows.append({
            "player_id": player_id,
            "season": season_name,
            "body_part": body_part,
            "severity": severity,
            "started_on": started_on.isoformat(),
            "resolved_on": resolved_on.isoformat() if severity != "season-ending" else "",
            "games_missed": games_missed,
            "age_at_start": round(age_at_start, 1),
            "is_recurring": "true",
            "source": "seed_synthetic",
        })

    # Top up to target if we're short.
    while len(rows) < target_rows:
        player_id, age_now = random.choice(PLAYER_POOL)
        season_meta = random.choice(SEASONS)
        body_part = random.choices(body_part_keys, weights=body_part_weights, k=1)[0]
        body_meta = BODY_PARTS[body_part]
        severity = _pick_severity(body_meta["severity_dist"])
        games_missed = _games_missed(body_meta, severity)
        season_name, started_on = _pick_season_window(season_meta)
        resolved_on = started_on + timedelta(days=int(games_missed * 2.2))
        seasons_back = SEASONS.index(season_meta)
        age_at_start = max(19.0, float(age_now) - (len(SEASONS) - 1 - seasons_back))
        key = (player_id, season_name, body_part, started_on.isoformat())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        rows.append({
            "player_id": player_id,
            "season": season_name,
            "body_part": body_part,
            "severity": severity,
            "started_on": started_on.isoformat(),
            "resolved_on": resolved_on.isoformat() if severity != "season-ending" else "",
            "games_missed": games_missed,
            "age_at_start": round(age_at_start, 1),
            "is_recurring": "false",
            "source": "seed_synthetic",
        })

    rows.sort(key=lambda r: (r["player_id"], r["started_on"]))

    fieldnames = [
        "player_id",
        "season",
        "body_part",
        "severity",
        "started_on",
        "resolved_on",
        "games_missed",
        "age_at_start",
        "is_recurring",
        "source",
    ]
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print("wrote", out_path, "rows=", len(rows))


if __name__ == "__main__":
    main()
