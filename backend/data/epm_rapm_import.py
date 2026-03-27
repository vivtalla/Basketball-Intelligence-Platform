"""Import EPM/RAPM per player-season from CSV into SeasonStat table."""
import csv
import os
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import SeasonStat


def import_by_csv(csv_path: str, batch_size: int = 100):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    session: Session = SessionLocal()
    update_count = 0

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Expected header: player_id,season,epm,rapm
            player_id = int(row.get("player_id") or 0)
            season = row.get("season")
            epm = row.get("epm")
            rapm = row.get("rapm")
            if not player_id or not season:
                continue

            stat = (
                session.query(SeasonStat)
                .filter(
                    SeasonStat.player_id == player_id,
                    SeasonStat.season == season,
                    SeasonStat.is_playoff == False,
                )
                .first()
            )
            if not stat:
                continue

            stat.epm = float(epm) if epm not in (None, "", "NA") else None
            stat.rapm = float(rapm) if rapm not in (None, "", "NA") else None
            update_count += 1

            if update_count % batch_size == 0:
                session.commit()

        session.commit()

    session.close()
    return update_count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import EPM/RAPM from CSV into season_stats")
    parser.add_argument("csv_path", type=str, help="Path to CSV file")
    args = parser.parse_args()

    updated = import_by_csv(args.csv_path)
    print(f"Updated {updated} rows")
