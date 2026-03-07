import csv
import re
import shutil
from datetime import datetime
from pathlib import Path

import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))); del _sys, _os
from src.config.paths import MATCHES_CSV, ROUNDS_CSV

RAW_DIR = Path("archive/raw_sessions")
PROCESSED_DIR = Path("archive/processed_sessions")

GLOBAL_MATCHES = Path(MATCHES_CSV)
GLOBAL_ROUNDS = Path(ROUNDS_CSV)


def extract_numeric_id(match_id: str) -> int:
    return int(re.search(r"\d+", match_id).group())


def format_match_id(num: int) -> str:
    return f"M{num:04d}"


def parse_session_date(prefix: str) -> datetime:
    try:
        return datetime.strptime(prefix[:6], "%d%m%y")
    except ValueError:
        raise ValueError(
            f"Session prefix '{prefix}' does not start with a valid "
            "ddmmyy date."
        )


_SESSION_SUFFIXES = ("_session_matches.csv", "_session_rounds.csv")


def extract_session_prefix(filename: str) -> str:
    for suffix in _SESSION_SUFFIXES:
        if filename.endswith(suffix):
            return filename.removesuffix(suffix)
    raise ValueError(
        f"Filename '{filename}' does not end with a known session suffix "
        f"({', '.join(_SESSION_SUFFIXES)})."
    )


def get_latest_session_files():
    matches_suffix, rounds_suffix = _SESSION_SUFFIXES
    match_files = {
        extract_session_prefix(p.name): p
        for p in RAW_DIR.glob(f"*{matches_suffix}")
    }
    round_files = {
        extract_session_prefix(p.name): p
        for p in RAW_DIR.glob(f"*{rounds_suffix}")
    }

    complete_sessions = sorted(
        set(match_files) & set(round_files),
        key=parse_session_date,
    )

    if not complete_sessions:
        raise FileNotFoundError(
            "No complete session pair (matches + rounds) found in "
            f"{RAW_DIR}. "
            "Ensure both '<prefix>_session_matches.csv' and "
            "'<prefix>_session_rounds.csv' are present."
        )

    latest = complete_sessions[-1]
    return match_files[latest], round_files[latest]


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

    # make subdirectory based on session prefix
    session_prefix = extract_session_prefix(path.name)
    subdir = PROCESSED_DIR / session_prefix
    subdir.mkdir(exist_ok=True)

    target = subdir / path.name

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
