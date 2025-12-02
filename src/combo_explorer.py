# combo_explorer.py
"""
Parts Combination Explorer for Beyblade Analytics

This module generates data for an interactive combo explorer that allows users to:
- Search and filter Blade × Ratchet × Bit combinations
- View combo ratings derived from parts stats and synergy data
- Compare combinations by performance metrics
- Link to individual bey pages and match history

The explorer computes:
- Combo Rating (from 5 stat categories derived from part stats)
- Synergy Score (average of pairwise synergies)
- Win Rate (from match data for beys with this combo)
- Finish Profile (Burst / Pocket / Spin / Extreme percentages)
"""

import json
import os

# File paths
BEYS_DATA_JSON = "./docs/data/beys_data.json"
PARTS_STATS_JSON = "./data/parts_stats.json"
SYNERGY_DATA_JSON = "./docs/data/synergy_data.json"
RPG_STATS_JSON = "./docs/data/rpg_stats.json"
ADV_LEADERBOARD_CSV = "./data/advanced_leaderboard.csv"
COMBO_DATA_JSON = "./docs/data/combo_data.json"


def load_json(filepath: str) -> dict | list:
    """Load JSON data from file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_beys_data() -> list:
    """Load beyblade data with component information."""
    return load_json(BEYS_DATA_JSON)


def load_parts_stats() -> dict:
    """Load parts performance statistics."""
    return load_json(PARTS_STATS_JSON)


def load_synergy_data() -> dict:
    """Load synergy data for part pairings."""
    return load_json(SYNERGY_DATA_JSON)


def load_rpg_stats() -> dict:
    """Load RPG stats for each bey."""
    return load_json(RPG_STATS_JSON)


def load_advanced_leaderboard() -> dict:
    """Load advanced leaderboard data as dict keyed by bey name."""
    import csv
    leaderboard = {}
    with open(ADV_LEADERBOARD_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leaderboard[row["Bey"]] = {
                "rank": int(row["Platz"]),
                "elo": int(row["ELO"]),
                "power_index": float(row["PowerIndex"]),
                "matches": int(row["Matches"]),
                "wins": int(row["Wins"]),
                "losses": int(row["Losses"]),
                "winrate": float(row["Winrate"].rstrip("%")) / 100,
            }
    return leaderboard


def build_synergy_lookup(synergy_data: dict) -> dict:
    """
    Build lookup dictionaries for synergy scores.

    Returns a dict with keys:
    - blade_bit: {(blade, bit): score}
    - blade_ratchet: {(blade, ratchet): score}
    - bit_ratchet: {(bit, ratchet): score}
    """
    lookup = {}
    for pair_type in ["blade_bit", "blade_ratchet", "bit_ratchet"]:
        pair_data = synergy_data.get(pair_type, {})
        data_list = pair_data.get("data", [])
        lookup[pair_type] = {}
        for item in data_list:
            key = (item["part1"], item["part2"])
            lookup[pair_type][key] = {
                "score": item.get("score", 50.0),
                "win_rate": item.get("win_rate", 50.0),
                "matches": item.get("matches", 0),
                "has_sufficient_data": item.get("has_sufficient_data", False),
            }
    return lookup


def calculate_combo_synergy(
    blade: str,
    ratchet: str,
    bit: str,
    synergy_lookup: dict
) -> dict:
    """
    Calculate average synergy score for a 3-part combination.

    Returns dict with:
    - score: average synergy score (0-100)
    - blade_bit: synergy between blade and bit
    - blade_ratchet: synergy between blade and ratchet
    - bit_ratchet: synergy between bit and ratchet
    - has_sufficient_data: bool indicating if all pairs have data
    """
    blade_bit = synergy_lookup["blade_bit"].get((blade, bit), {})
    blade_ratchet = synergy_lookup["blade_ratchet"].get((blade, ratchet), {})
    bit_ratchet = synergy_lookup["bit_ratchet"].get((bit, ratchet), {})

    scores = []
    has_all_data = True

    for synergy in [blade_bit, blade_ratchet, bit_ratchet]:
        if synergy:
            scores.append(synergy.get("score", 50.0))
            if not synergy.get("has_sufficient_data", False):
                has_all_data = False
        else:
            scores.append(50.0)  # Neutral score for missing data
            has_all_data = False

    avg_score = sum(scores) / len(scores) if scores else 50.0

    return {
        "score": round(avg_score, 1),
        "blade_bit": blade_bit.get("score", 50.0) if blade_bit else None,
        "blade_ratchet": blade_ratchet.get("score", 50.0) if blade_ratchet else None,
        "bit_ratchet": bit_ratchet.get("score", 50.0) if bit_ratchet else None,
        "has_sufficient_data": has_all_data,
    }


def calculate_combo_rating(
    blade_stats: dict,
    ratchet_stats: dict,
    bit_stats: dict
) -> dict:
    """
    Calculate a composite combo rating from part stats.

    The rating combines stats from all three parts to estimate:
    - Attack: blade contact_power + bit speed_rating
    - Defense: blade deflection_ability + ratchet burst_resistance
    - Stamina: bit stamina_output + ratchet weight_efficiency
    - Control: blade spin_control + ratchet lock_stability + bit tip_control
    - Meta Impact: overall balanced average

    Each stat is on a 0-5 scale, combined values on 0-10.
    """
    # Get individual stats with defaults
    blade = blade_stats.get("stats", {})
    ratchet = ratchet_stats.get("stats", {})
    bit = bit_stats.get("stats", {})

    # Calculate composite stats (0-10 scale)
    attack = (blade.get("contact_power", 2.5)
              + bit.get("speed_rating", 2.5))

    defense = (blade.get("deflection_ability", 2.5)
               + ratchet.get("burst_resistance", 2.5))

    stamina = (bit.get("stamina_output", 2.5)
               + ratchet.get("weight_efficiency", 2.5))

    control = (blade.get("spin_control", 2.5)
               + ratchet.get("lock_stability", 2.5)
               + bit.get("tip_control", 2.5)) / 1.5  # Normalize to 0-10

    # Meta impact is the balanced average
    meta_impact = (attack + defense + stamina + control) / 4

    # Overall rating (0-100 scale)
    overall = (attack + defense + stamina + control + meta_impact) / 5 * 10

    return {
        "attack": round(attack, 1),
        "defense": round(defense, 1),
        "stamina": round(stamina, 1),
        "control": round(control, 1),
        "meta_impact": round(meta_impact, 1),
        "overall": round(overall, 1),
    }


def find_beys_with_combo(
    blade: str,
    ratchet: str,
    bit: str,
    beys_data: list
) -> list:
    """Find all beys that use the specified combination."""
    matching_beys = []
    for bey in beys_data:
        if (bey.get("blade") == blade
                and bey.get("ratchet") == ratchet
                and bey.get("bit") == bit):
            matching_beys.append({
                "name": bey.get("name", ""),
                "code": bey.get("code", ""),
                "blade": blade,
            })
    return matching_beys


def generate_combo_data() -> dict:
    """
    Generate combination data for the explorer.

    This creates data for all existing bey combinations (not all possible
    theoretical combinations, as that would be overwhelming).

    Returns a dictionary with:
    - combos: list of combo data objects
    - parts: lists of all blades, ratchets, bits for filtering
    - metadata: generation info
    """
    # Load all data
    beys_data = load_beys_data()
    parts_stats = load_parts_stats()
    synergy_data = load_synergy_data()
    rpg_stats = load_rpg_stats()
    adv_leaderboard = load_advanced_leaderboard()

    synergy_lookup = build_synergy_lookup(synergy_data)

    # Extract unique parts for filter options
    blades_set = set()
    ratchets_set = set()
    bits_set = set()

    # Build combo data for each existing bey
    combos = []
    seen_combos = set()

    for bey in beys_data:
        blade = bey.get("blade", "")
        ratchet = bey.get("ratchet", "")
        bit = bey.get("bit", "")

        if not blade or not ratchet or not bit:
            continue

        blades_set.add(blade)
        ratchets_set.add(ratchet)
        bits_set.add(bit)

        # Skip duplicate combos
        combo_key = (blade, ratchet, bit)
        if combo_key in seen_combos:
            continue
        seen_combos.add(combo_key)

        # Get part stats
        blade_data = parts_stats.get("blades", {}).get(blade, {})
        ratchet_data = parts_stats.get("ratchets", {}).get(ratchet, {})
        bit_data = parts_stats.get("bits", {}).get(bit, {})

        # Calculate ratings
        combo_rating = calculate_combo_rating(blade_data, ratchet_data, bit_data)
        combo_synergy = calculate_combo_synergy(blade, ratchet, bit, synergy_lookup)

        # Get performance data from RPG stats and leaderboard
        # Blade name corresponds to bey name in leaderboard data
        # (e.g., "FoxBrush" in advanced_leaderboard.csv)
        bey_lookup_name = blade
        rpg = rpg_stats.get(bey_lookup_name, {})
        lb = adv_leaderboard.get(bey_lookup_name, {})

        # Find all beys using this combo
        matching_beys = find_beys_with_combo(blade, ratchet, bit, beys_data)

        # Build combo entry
        combo_entry = {
            "blade": blade,
            "ratchet": ratchet,
            "bit": bit,
            "blade_type": blade_data.get("type", "Unknown"),
            "bit_category": bit_data.get("category", "Unknown"),
            "combo_name": f"{blade} {ratchet} {bit}",

            # Ratings
            "rating": combo_rating,
            "synergy": combo_synergy,

            # Performance (from most representative bey)
            "elo": lb.get("elo", 1000),
            "power_index": lb.get("power_index", 50.0),
            "win_rate": lb.get("winrate", 0.5) * 100,
            "matches": lb.get("matches", 0),
            "rank": lb.get("rank", 999),

            # RPG stats if available
            "rpg_stats": rpg.get("stats") if rpg else None,

            # Links
            "beys": matching_beys,
            "has_match_data": lb.get("matches", 0) > 0,
        }

        combos.append(combo_entry)

    # Sort combos by overall rating (descending)
    combos.sort(key=lambda x: x["rating"]["overall"], reverse=True)

    # Build parts lists with metadata
    blades_list = []
    for blade_name in sorted(blades_set):
        blade_data = parts_stats.get("blades", {}).get(blade_name, {})
        blades_list.append({
            "name": blade_name,
            "type": blade_data.get("type", "Unknown"),
            "stats": blade_data.get("stats", {}),
        })

    ratchets_list = []
    for ratchet_name in sorted(ratchets_set):
        ratchet_data = parts_stats.get("ratchets", {}).get(ratchet_name, {})
        ratchets_list.append({
            "name": ratchet_name,
            "height": ratchet_data.get("height"),
            "protrusions": ratchet_data.get("protrusions"),
            "stats": ratchet_data.get("stats", {}),
        })

    bits_list = []
    for bit_name in sorted(bits_set):
        bit_data = parts_stats.get("bits", {}).get(bit_name, {})
        bits_list.append({
            "name": bit_name,
            "category": bit_data.get("category", "Unknown"),
            "stats": bit_data.get("stats", {}),
        })

    return {
        "combos": combos,
        "parts": {
            "blades": blades_list,
            "ratchets": ratchets_list,
            "bits": bits_list,
        },
        "metadata": {
            "total_combos": len(combos),
            "total_blades": len(blades_list),
            "total_ratchets": len(ratchets_list),
            "total_bits": len(bits_list),
        }
    }


def save_combo_data(combo_data: dict) -> None:
    """Save combo data to JSON file."""
    os.makedirs(os.path.dirname(COMBO_DATA_JSON), exist_ok=True)

    with open(COMBO_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(combo_data, f, indent=2)

    print(f"Combo data saved to {COMBO_DATA_JSON}")


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    print("Generating Combo Explorer Data...")

    combo_data = generate_combo_data()
    save_combo_data(combo_data)

    print("\n=== Combo Explorer Data Summary ===")
    print(f"Total combos: {combo_data['metadata']['total_combos']}")
    print(f"Total blades: {combo_data['metadata']['total_blades']}")
    print(f"Total ratchets: {combo_data['metadata']['total_ratchets']}")
    print(f"Total bits: {combo_data['metadata']['total_bits']}")

    # Show top 5 combos
    print("\n=== Top 5 Combos by Rating ===")
    for combo in combo_data["combos"][:5]:
        print(f"  {combo['combo_name']}: {combo['rating']['overall']} "
              f"(Synergy: {combo['synergy']['score']})")

    print("\n=== Done! ===")
