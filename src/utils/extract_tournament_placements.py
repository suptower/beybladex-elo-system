import csv
import re
import shutil
from datetime import datetime
from pathlib import Path

import sys
import os as _os
_root = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
del _os, _root
from src.config.paths import TOURNAMENT_API_JSONS_DIR, TOURNAMENT_PLACEMENTS_JSON

def extract_tournament_placements():
    for json_file in Path(TOURNAMENT_API_JSONS_DIR).glob("*.json"):
        with open(json_file, "r") as f:
            

if __name__ == "__main__":
    extract_tournament_placements()