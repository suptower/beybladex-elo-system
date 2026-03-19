from pathlib import Path
import json

import sys
import os as _os
_root = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
del _os, _root
from src.config.paths import TOURNAMENT_API_JSONS_DIR, TOURNAMENT_PLACEMENTS_JSON  # noqa: E402


def extract_tournament_placements():
    """
    Extract tournament placements from the raw API JSON files and
    return a structured dictionary indexed by tournament ID.
    """
    tournaments = {}
    for json_file in Path(TOURNAMENT_API_JSONS_DIR).glob("*.json"):
        with open(json_file, "r") as f:
            data = json.load(f)
            name = data.get("data", {}).get("attributes", {}).get("name")
            participants_count = data.get("data", {}).get("attributes", {}).get("participants_count")
            tournaments[name] = {
                "participants_count": participants_count,
                "placements": []
            }
            # only extract included with type "participant", extract name and final_rank
            included = data.get("included", [])
            for item in included:
                if item.get("type") == "participant":
                    bey = item.get("attributes", {}).get("name")
                    final_rank = item.get("attributes", {}).get("final_rank")
                    tournaments[name]["placements"].append((bey, final_rank))

    return tournaments


def create_tournament_placements_json(tournament_data):
    """
    Create a JSON section with the required format for
    the tournament_placements.json file.
    Therefore we iterate the dictionary and sort the placements by final_rank
    and create a list of only bey names per tournament in the correct order,
    also adding the participants count.
    """
    output = {"tournaments": {}}
    for tournament_name, data in tournament_data.items():
        placements = sorted(data["placements"], key=lambda x: x[1])  # sort by final_rank
        bey_placements = [bey for bey, rank in placements]  # extract only bey names
        output["tournaments"][tournament_name] = {
            "participants": data["participants_count"],
            "placements": bey_placements
        }

    return output


def write_to_json_file(data, file_path):
    """
    Write the given data to a JSON file at the specified path.
    The data has to be pasted into the "tournaments" section of the tournament_placements.json file,
    so we read the existing file and overwrite the "tournaments" section with the new data.
    If the file does not exist, we create a new one with the given data.
    """
    try:
        with open(file_path, "r") as f:
            existing_data = json.load(f)
        existing_data["tournaments"] = data["tournaments"]
        with open(file_path, "w") as f:
            json.dump(existing_data, f, indent=2)
    except FileNotFoundError:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    tournament_data = extract_tournament_placements()
    json_output = create_tournament_placements_json(tournament_data)
    write_to_json_file(json_output, TOURNAMENT_PLACEMENTS_JSON)
    print("Tournament placements extracted and written to JSON file successfully. Do not forget to manually add dates.")
