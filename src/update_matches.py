import csv
import re
import shutil
from pathlib import Path

RAW_DIR = Path("archive/raw_sessions")
PROCESSED_DIR = Path("archive/processed_sessions")

GLOBAL_MATCHES = Path("docs/data/matches.csv")
GLOBAL_ROUNDS = Path("docs/data/rounds.csv")


def extract_numeric_id(match_id: str) -> int:
    return int(re.search(r"\d+", match_id).group())


def format_match_id(num: int) -> str:
    return f"M{num:04d}"


def get_latest_session_files():
    match_files = sorted(RAW_DIR.glob("*_session_matches.csv"))
    round_files = sorted(RAW_DIR.glob("*_session_rounds.csv"))

    if not match_files or not round_files:
        raise FileNotFoundError("No session files found.")

    return match_files[-1], round_files[-1]


def get_current_max_match_id():
    if not GLOBAL_MATCHES.exists():
        return 0

    with GLOBAL_MATCHES.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        ids = [extract_numeric_id(row["MatchID"]) for row in reader]

    return max(ids) if ids else 0


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def append_rows(path, fieldnames, rows):
    file_exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for row in rows:
            writer.writerow(row)


def move_to_processed(path: Path):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    target = PROCESSED_DIR / path.name

    if target.exists():
        raise FileExistsError(
            f"Processed file already exists: {target.name}"
        )

    shutil.move(str(path), str(target))


def main():
    session_matches_file, session_rounds_file = get_latest_session_files()

    print(f"Processing session: {session_matches_file.name}")

    offset = get_current_max_match_id()

    # Load session data
    match_fields, match_rows = load_csv(session_matches_file)
    round_fields, round_rows = load_csv(session_rounds_file)

    # Remap match IDs
    id_mapping = {}
    new_match_rows = []

    for row in match_rows:
        old_id_num = extract_numeric_id(row["MatchID"])
        new_id_num = offset + old_id_num
        new_id = format_match_id(new_id_num)

        id_mapping[row["MatchID"]] = new_id
        row["MatchID"] = new_id
        new_match_rows.append(row)

    # Remap rounds
    new_round_rows = []
    for row in round_rows:
        old_id = row["MatchID"]

        if old_id not in id_mapping:
            raise ValueError(f"Round references unknown match_id: {old_id}")

        row["MatchID"] = id_mapping[old_id]
        new_round_rows.append(row)

    # Append to global files
    append_rows(GLOBAL_MATCHES, match_fields, new_match_rows)
    append_rows(GLOBAL_ROUNDS, round_fields, new_round_rows)

    # Only move files if everything above succeeded
    move_to_processed(session_matches_file)
    move_to_processed(session_rounds_file)

    print(f"Appended {len(new_match_rows)} matches.")
    print(f"Appended {len(new_round_rows)} rounds.")
    print("Session moved to processed_sessions.")


if __name__ == "__main__":
    main()
