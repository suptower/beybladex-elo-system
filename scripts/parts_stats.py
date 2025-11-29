# parts_stats.py
"""
Parts Performance Ranking System for Beyblade Analytics

This module manages performance statistics for individual Beyblade parts:
- Blades: Contact Power, Spin Control, Deflection Ability
- Ratchets: Burst Resistance, Lock Stability, Weight Efficiency
- Bits: Tip Control, Speed Rating, Stamina Output

Each stat uses a 0-5 scale with fractional values supported.
"""

import json
import os

# File paths
PARTS_STATS_JSON = "./csv/parts_stats.json"
DOCS_PARTS_STATS_JSON = "./docs/data/parts_stats.json"

# Initialize Windows terminal for ANSI color support (no-op on Unix systems)
os.system("")

# Colors for terminal output
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


# Stat configurations
BLADE_STATS = {
    "contact_power": {
        "name": "Contact Power",
        "description": "Impact strength during direct clashes",
        "icon": "⚔️"
    },
    "spin_control": {
        "name": "Spin Control",
        "description": "Stability contribution during sustained contact",
        "icon": "🎯"
    },
    "deflection_ability": {
        "name": "Deflection Ability",
        "description": "Ability to redirect incoming attacks via shape/weight",
        "icon": "🛡️"
    }
}

RATCHET_STATS = {
    "burst_resistance": {
        "name": "Burst Resistance",
        "description": "How effectively the ratchet prevents bursts",
        "icon": "🔒"
    },
    "lock_stability": {
        "name": "Lock Stability",
        "description": "Consistency of grip and retention over time",
        "icon": "⚡"
    },
    "weight_efficiency": {
        "name": "Weight Efficiency",
        "description": "Contribution to overall balance without excessive weight",
        "icon": "⚖️"
    }
}

BIT_STATS = {
    "tip_control": {
        "name": "Tip Control",
        "description": "Stability and directionality during movement",
        "icon": "🎮"
    },
    "speed_rating": {
        "name": "Speed Rating",
        "description": "Acceleration potential at battle start",
        "icon": "💨"
    },
    "stamina_output": {
        "name": "Stamina Output",
        "description": "Long-term spin efficiency and endurance",
        "icon": "💪"
    }
}


def clamp(value: float, min_val: float = 0.0, max_val: float = 5.0) -> float:
    """Clamp a value to a specified range."""
    return max(min_val, min(max_val, value))


def load_parts_stats() -> dict:
    """Load parts stats from JSON file."""
    with open(PARTS_STATS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_parts_stats(data: dict) -> None:
    """Save parts stats to JSON files."""
    # Save to csv folder
    with open(PARTS_STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Copy to docs folder
    with open(DOCS_PARTS_STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"{GREEN}Parts stats saved to {PARTS_STATS_JSON}{RESET}")
    print(f"{GREEN}Parts stats copied to {DOCS_PARTS_STATS_JSON}{RESET}")


def get_blade_stats(blade_name: str) -> dict | None:
    """Get stats for a specific blade."""
    data = load_parts_stats()
    return data.get("blades", {}).get(blade_name)


def get_ratchet_stats(ratchet_name: str) -> dict | None:
    """Get stats for a specific ratchet."""
    data = load_parts_stats()
    return data.get("ratchets", {}).get(ratchet_name)


def get_bit_stats(bit_name: str) -> dict | None:
    """Get stats for a specific bit."""
    data = load_parts_stats()
    return data.get("bits", {}).get(bit_name)


def update_blade_stats(blade_name: str, stats: dict) -> None:
    """Update stats for a specific blade."""
    data = load_parts_stats()

    if blade_name not in data.get("blades", {}):
        print(f"{YELLOW}Warning: Blade '{blade_name}' not found. Creating new entry.{RESET}")
        data.setdefault("blades", {})[blade_name] = {"type": "Unknown", "stats": {}}

    # Validate and clamp stats
    for stat_key in ["contact_power", "spin_control", "deflection_ability"]:
        if stat_key in stats:
            data["blades"][blade_name]["stats"][stat_key] = clamp(stats[stat_key])

    save_parts_stats(data)


def update_ratchet_stats(ratchet_name: str, stats: dict) -> None:
    """Update stats for a specific ratchet."""
    data = load_parts_stats()

    if ratchet_name not in data.get("ratchets", {}):
        print(f"{YELLOW}Warning: Ratchet '{ratchet_name}' not found. Creating new entry.{RESET}")
        data.setdefault("ratchets", {})[ratchet_name] = {"stats": {}}

    # Validate and clamp stats
    for stat_key in ["burst_resistance", "lock_stability", "weight_efficiency"]:
        if stat_key in stats:
            data["ratchets"][ratchet_name]["stats"][stat_key] = clamp(stats[stat_key])

    save_parts_stats(data)


def update_bit_stats(bit_name: str, stats: dict) -> None:
    """Update stats for a specific bit."""
    data = load_parts_stats()

    if bit_name not in data.get("bits", {}):
        print(f"{YELLOW}Warning: Bit '{bit_name}' not found. Creating new entry.{RESET}")
        data.setdefault("bits", {})[bit_name] = {"category": "Unknown", "stats": {}}

    # Validate and clamp stats
    for stat_key in ["tip_control", "speed_rating", "stamina_output"]:
        if stat_key in stats:
            data["bits"][bit_name]["stats"][stat_key] = clamp(stats[stat_key])

    save_parts_stats(data)


def calculate_total_score(stats: dict) -> float:
    """Calculate the total score from a stats dictionary."""
    return sum(stats.values())


def get_blades_ranking(sort_by: str = "total") -> list:
    """Get blades sorted by a specific stat or total score."""
    data = load_parts_stats()
    blades = data.get("blades", {})

    result = []
    for blade_name, blade_data in blades.items():
        stats = blade_data.get("stats", {})
        total = calculate_total_score(stats)
        result.append({
            "name": blade_name,
            "type": blade_data.get("type", "Unknown"),
            **stats,
            "total": round(total, 2)
        })

    if sort_by == "total":
        result.sort(key=lambda x: x["total"], reverse=True)
    elif sort_by in ["contact_power", "spin_control", "deflection_ability"]:
        result.sort(key=lambda x: x.get(sort_by, 0), reverse=True)

    return result


def get_ratchets_ranking(sort_by: str = "total") -> list:
    """Get ratchets sorted by a specific stat or total score."""
    data = load_parts_stats()
    ratchets = data.get("ratchets", {})

    result = []
    for ratchet_name, ratchet_data in ratchets.items():
        stats = ratchet_data.get("stats", {})
        total = calculate_total_score(stats)
        result.append({
            "name": ratchet_name,
            "height": ratchet_data.get("height"),
            "protrusions": ratchet_data.get("protrusions"),
            **stats,
            "total": round(total, 2)
        })

    if sort_by == "total":
        result.sort(key=lambda x: x["total"], reverse=True)
    elif sort_by in ["burst_resistance", "lock_stability", "weight_efficiency"]:
        result.sort(key=lambda x: x.get(sort_by, 0), reverse=True)

    return result


def get_bits_ranking(sort_by: str = "total") -> list:
    """Get bits sorted by a specific stat or total score."""
    data = load_parts_stats()
    bits = data.get("bits", {})

    result = []
    for bit_name, bit_data in bits.items():
        stats = bit_data.get("stats", {})
        total = calculate_total_score(stats)
        result.append({
            "name": bit_name,
            "category": bit_data.get("category", "Unknown"),
            **stats,
            "total": round(total, 2)
        })

    if sort_by == "total":
        result.sort(key=lambda x: x["total"], reverse=True)
    elif sort_by in ["tip_control", "speed_rating", "stamina_output"]:
        result.sort(key=lambda x: x.get(sort_by, 0), reverse=True)

    return result


def print_parts_summary() -> None:
    """Print a summary of all parts stats."""
    data = load_parts_stats()

    print(f"\n{CYAN}=== Parts Performance Summary ==={RESET}\n")

    # Blades summary
    blades = data.get("blades", {})
    print(f"{GREEN}Blades: {len(blades)} total{RESET}")
    types_count = {}
    for blade_data in blades.values():
        t = blade_data.get("type", "Unknown")
        types_count[t] = types_count.get(t, 0) + 1
    for t, count in sorted(types_count.items()):
        print(f"  - {t}: {count}")

    print()

    # Ratchets summary
    ratchets = data.get("ratchets", {})
    print(f"{GREEN}Ratchets: {len(ratchets)} total{RESET}")

    print()

    # Bits summary
    bits = data.get("bits", {})
    print(f"{GREEN}Bits: {len(bits)} total{RESET}")
    categories_count = {}
    for bit_data in bits.values():
        c = bit_data.get("category", "Unknown")
        categories_count[c] = categories_count.get(c, 0) + 1
    for c, count in sorted(categories_count.items()):
        print(f"  - {c}: {count}")


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    print(f"{CYAN}=== Parts Stats Manager ==={RESET}")
    print_parts_summary()
    print(f"\n{GREEN}=== Done! ==={RESET}")
