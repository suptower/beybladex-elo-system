# simulate_tournament.py
"""
Simuliere: 36 Spieler -> 6 Runden Swiss -> Top24 Single-Elim mit Top8-Byes.
Live-ELO: ELOs werden innerhalb jeder Simulation nach jedem Match aktualisiert
            (temporär, werden nicht in leaderboard.csv zurückgeschrieben).
Input: ./csv/leaderboard.csv mit mindestens Spalten: Name (oder Bey) und ELO
Output: ./sim_output/sim_results_summary.csv
"""

import pandas as pd
import numpy as np
import random
import os
from collections import defaultdict, Counter

# ---------- Konfiguration ----------
LEADERBOARD_CSV = "./csv/leaderboard.csv"
OUT_DIR = "./sim_output"
N_SIMULATIONS = 1000    # Anzahl Simulationen (anpassen)
RANDOM_SEED = 42        # für Reproduzierbarkeit (setze None für Zufall)
N_PLAYERS = 36
SWISS_ROUNDS = 6
TOP_K = 24
TOP_BYES = 8

# K-Faktoren (Option C: Swiss K=32, Playoffs K=24)
K_SWISS = 32
K_PLAYOFFS = 24
# -----------------------------------

os.makedirs(OUT_DIR, exist_ok=True)
if RANDOM_SEED is not None:
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

# ---------- Hilfsfunktionen ----------


def win_prob(elo_a, elo_b):
    """ELO-basierte Siegwahrscheinlichkeit für A vs B"""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))


def simulate_match_by_elo(elo_a, elo_b):
    """Return True if A wins, False if B wins. Single-match sampling."""
    p = win_prob(elo_a, elo_b)
    return random.random() < p


def update_elo_pair(elo_a, elo_b, a_wins, k):
    """Update and return new (elo_a, elo_b) given result and k-factor."""
    ea = win_prob(elo_a, elo_b)
    eb = 1 - ea
    sa = 1.0 if a_wins else 0.0
    sb = 1.0 - sa
    new_a = elo_a + k * (sa - ea)
    new_b = elo_b + k * (sb - eb)
    return new_a, new_b


def round1_pairing(sorted_players):
    """Pairing for round 1: top-half vs bottom-half as Challonge did."""
    half = len(sorted_players) // 2
    top = sorted_players[:half]
    bottom = sorted_players[half:]
    pairs = []
    for i in range(half):
        pairs.append((top[i], bottom[i]))
    return pairs


def swiss_pairing(players_ordered, scores, prev_opponents):
    """
    Greedy Swiss pairing inside score groups.
    players_ordered: list of player ids (used for deterministic tie-breaking)
    scores: dict player -> score
    prev_opponents: dict player -> set(opponents)
    Returns list of (A,B) pairs for next round.
    """
    score_groups = defaultdict(list)
    for p in players_ordered:
        score_groups[scores[p]].append(p)
    pairs = []
    used = set()

    # iterate groups from high to low score
    for score in sorted(score_groups.keys(), reverse=True):
        group = score_groups[score][:]
        group.sort(key=lambda x: players_ordered.index(x))
        while group:
            a = group.pop(0)
            if a in used:
                continue
            # try same group partner avoiding rematch
            found = None
            for i, b in enumerate(group):
                if b not in prev_opponents[a]:
                    found = b
                    break
            if found:
                group.remove(found)
                pairs.append((a, found))
                used.add(a)
                used.add(found)
            else:
                # seek alternative across lower score groups first
                found = None
                for lower_score in sorted(score_groups.keys(), reverse=True):
                    if lower_score >= score:
                        continue
                    for candidate in score_groups[lower_score]:
                        if candidate not in used and candidate not in prev_opponents[a]:
                            found = candidate
                            break
                    if found:
                        break
                # fallback: any not used and not same
                if found is None:
                    for candidate in players_ordered:
                        if candidate == a or candidate in used:
                            continue
                        if candidate not in prev_opponents[a]:
                            found = candidate
                            break
                if found is None:
                    # last resort: any not used
                    for candidate in players_ordered:
                        if candidate == a or candidate in used:
                            continue
                        found = candidate
                        break
                # remove found from its group if present
                for g in score_groups.values():
                    if found in g:
                        try:
                            g.remove(found)
                        except ValueError:
                            pass
                pairs.append((a, found))
                used.add(a)
                used.add(found)

    # final: pair remaining arbitrarily
    all_players = [p for p in players_ordered]
    unpaired = [p for p in all_players if p not in used]
    while len(unpaired) >= 2:
        a = unpaired.pop(0)
        b = unpaired.pop(0)
        pairs.append((a, b))
    return pairs

# ---------- Tournament routines (live-ELO aware) ----------


def play_swiss_once(players, initial_seed_index, start_elos):
    """
    Plays one Swiss tournament with live-ELO updates.
    players: list of player names in initial seed order (best->worst)
    initial_seed_index: dict player->seed_index (0-based)
    start_elos: dict player->initial (real) elo
    Returns:
      result: dict player -> dict {score, buchholz, pointdiff, points_for, opponents}
      final_sim_elos: dict player->elo after swiss
    """
    # Make a working copy of elos for this simulation
    sim_elos = start_elos.copy()

    # initial state
    scores = {p: 0 for p in players}
    opponents = {p: [] for p in players}
    prev_opponents = {p: set() for p in players}
    points_for = {p: 0 for p in players}
    points_against = {p: 0 for p in players}

    # Round 1 pairing (initial seeding by initial_elos order -> players list)
    pairs = round1_pairing(players)

    for rnd in range(1, SWISS_ROUNDS + 1):
        if rnd == 1:
            current_pairs = pairs
        else:
            # players_ordered: sort by (-score, -liveElo, initial seed index)
            players_ordered = sorted(players, key=lambda x: (-scores[x], -sim_elos[x], initial_seed_index[x]))
            current_pairs = swiss_pairing(players_ordered, scores, prev_opponents)

        # Play current pairs, update sim_elos after each match (live)
        for a, b in current_pairs:
            # decide match outcome based on current sim elos
            a_wins = simulate_match_by_elo(sim_elos[a], sim_elos[b])
            # update sim elos (Swiss phase uses K_SWISS)
            new_a, new_b = update_elo_pair(sim_elos[a], sim_elos[b], a_wins, K_SWISS)
            sim_elos[a], sim_elos[b] = new_a, new_b

            # assign points (win=1)
            if a_wins:
                scores[a] += 1
                points_for[a] += 1
                points_against[a] += 0
                points_for[b] += 0
                points_against[b] += 1
            else:
                scores[b] += 1
                points_for[b] += 1
                points_against[b] += 0
                points_for[a] += 0
                points_against[a] += 1

            # record opponents
            opponents[a].append(b)
            opponents[b].append(a)
            prev_opponents[a].add(b)
            prev_opponents[b].add(a)

    # compute Buchholz (sum of opponents' scores)
    buchholz = {}
    for p in players:
        buchholz[p] = sum(scores[o] for o in opponents[p]) if opponents[p] else 0

    # build result dict
    result = {}
    for p in players:
        result[p] = {
            "score": scores[p],
            "buchholz": buchholz[p],
            "pointdiff": points_for[p] - points_against[p],
            "points_for": points_for[p],
            "opponents": opponents[p]
        }

    return result, sim_elos


def rank_after_swiss(result_dict, seed_list, live_elos):
    """
    Rank players after swiss using tie-breakers:
      Score -> Buchholz -> PointDiff -> PointsFor -> live ELO
    Returns ordered list (1..N) and standings DataFrame.
    """
    rows = []
    for p in seed_list:
        r = result_dict[p]
        rows.append({
            "Bey": p,
            "Score": r["score"],
            "Buchholz": r["buchholz"],
            "PointDiff": r["pointdiff"],
            "PointsFor": r["points_for"],
            "LiveELO": live_elos[p]
        })
    df = pd.DataFrame(rows)
    df.sort_values(by=["Score", "Buchholz", "PointDiff", "PointsFor", "LiveELO"],
                   ascending=[False, False, False, False, False], inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.index += 1
    return list(df["Bey"]), df


def build_24_bracket(top24_ordered):
    """
    Returns list of matches for Playoff Round (9..24 vs 24..9 mapping).
    """
    seed = top24_ordered
    pairs = [
        (seed[8], seed[23]),
        (seed[9], seed[22]),
        (seed[10], seed[21]),
        (seed[11], seed[20]),
        (seed[12], seed[19]),
        (seed[13], seed[18]),
        (seed[14], seed[17]),
        (seed[15], seed[16])
    ]
    return pairs


def run_playoffs_with_live_elo(top24_ordered, sim_elos):
    """
    Simulate playoffs with live-ELO updates (K_PLAYOFFS).
    Returns champion and progress mapping for players in top24_ordered.
    """
    # Playoff round (9..24)
    round24_pairs = build_24_bracket(top24_ordered)
    winners_round24 = []
    for a, b in round24_pairs:
        a_wins = simulate_match_by_elo(sim_elos[a], sim_elos[b])
        # update elos with playoff K
        new_a, new_b = update_elo_pair(sim_elos[a], sim_elos[b], a_wins, K_PLAYOFFS)
        sim_elos[a], sim_elos[b] = new_a, new_b
        winners_round24.append(a if a_wins else b)

    # order winners to match seeds 1..8 mapping (as described earlier)
    winners_ordered = [
        winners_round24[7],
        winners_round24[6],
        winners_round24[5],
        winners_round24[4],
        winners_round24[3],
        winners_round24[2],
        winners_round24[1],
        winners_round24[0],
    ]

    # Round of 16: seeds 1..8 vs winners_ordered
    round16_pairs = []
    for i in range(8):
        seed_player = top24_ordered[i]  # seed 1..8
        opp = winners_ordered[i]
        round16_pairs.append((seed_player, opp))

    # simulate R16
    winners_r16 = []
    eliminated = set()
    for a, b in round16_pairs:
        a_wins = simulate_match_by_elo(sim_elos[a], sim_elos[b])
        new_a, new_b = update_elo_pair(sim_elos[a], sim_elos[b], a_wins, K_PLAYOFFS)
        sim_elos[a], sim_elos[b] = new_a, new_b
        winner = a if a_wins else b
        winners_r16.append(winner)
        eliminated.add(a if not a_wins else b)

    # Quarterfinals
    winners_qf = []
    qf_pairs = [(winners_r16[0], winners_r16[7]),
                (winners_r16[1], winners_r16[6]),
                (winners_r16[2], winners_r16[5]),
                (winners_r16[3], winners_r16[4])]
    for a, b in qf_pairs:
        a_wins = simulate_match_by_elo(sim_elos[a], sim_elos[b])
        new_a, new_b = update_elo_pair(sim_elos[a], sim_elos[b], a_wins, K_PLAYOFFS)
        sim_elos[a], sim_elos[b] = new_a, new_b
        winner = a if a_wins else b
        winners_qf.append(winner)
        eliminated.add(a if not a_wins else b)

    # Semifinals
    winners_sf = []
    sf_pairs = [(winners_qf[0], winners_qf[3]), (winners_qf[1], winners_qf[2])]
    for a, b in sf_pairs:
        a_wins = simulate_match_by_elo(sim_elos[a], sim_elos[b])
        new_a, new_b = update_elo_pair(sim_elos[a], sim_elos[b], a_wins, K_PLAYOFFS)
        sim_elos[a], sim_elos[b] = new_a, new_b
        winner = a if a_wins else b
        winners_sf.append(winner)
        eliminated.add(a if not a_wins else b)

    # Final
    a, b = winners_sf
    a_wins = simulate_match_by_elo(sim_elos[a], sim_elos[b])
    new_a, new_b = update_elo_pair(sim_elos[a], sim_elos[b], a_wins, K_PLAYOFFS)
    sim_elos[a], sim_elos[b] = new_a, new_b
    champion = a if a_wins else b
    runner_up = b if a_wins else a
    eliminated.add(runner_up)

    # build progress mapping
    progress = {}
    for p in top24_ordered:
        progress[p] = 0
    for p in top24_ordered:
        progress[p] = 1
    for w in winners_round24:
        progress[w] = max(progress[w], 2)
    for w in winners_r16:
        progress[w] = max(progress[w], 3)
    for w in winners_qf:
        progress[w] = max(progress[w], 4)
    for w in winners_sf:
        progress[w] = max(progress[w], 5)
    progress[champion] = 6

    return champion, progress, sim_elos


# ---------- Main Simulation Loop ----------
# load leaderboard
df_lb = pd.read_csv(LEADERBOARD_CSV)
if 'Bey' not in df_lb.columns and 'Name' in df_lb.columns:
    df_lb.rename(columns={'Name': 'Bey'}, inplace=True)
if 'ELO' not in df_lb.columns and 'Elo' in df_lb.columns:
    df_lb.rename(columns={'Elo': 'ELO'}, inplace=True)

if 'Bey' not in df_lb.columns or 'ELO' not in df_lb.columns:
    raise SystemExit("leaderboard.csv muss Spalten 'Bey' und 'ELO' enthalten.")

# ensure exactly N_PLAYERS are used (top N by ELO)
df_lb.sort_values(by='ELO', ascending=False, inplace=True)
df_lb = df_lb.head(N_PLAYERS).copy()
players = df_lb['Bey'].tolist()
# initial real elos (float)
initial_elos = {row['Bey']: float(row['ELO']) for _, row in df_lb.iterrows()}

# initial seed index for deterministic tie-breaks
initial_seed_index = {p: i for i, p in enumerate(players)}

# stats counters across simulations
count_champion = Counter()
count_progress = {p: Counter() for p in players}  # counts of stage reached
count_top_cut = Counter()  # how often made top24
# accumulate final sim elos for averaging
final_elo_sums = {p: 0.0 for p in players}

for sim in range(1, N_SIMULATIONS + 1):
    # start with a fresh copy of initial elos for this sim
    sim_start_elos = initial_elos.copy()

    # Swiss with live elos
    swiss_result, sim_elos_after_swiss = play_swiss_once(players, initial_seed_index, sim_start_elos)

    # rank and get standings (use live elos after swiss for tiebreak)
    ranking_order, standings_df = rank_after_swiss(swiss_result, players, sim_elos_after_swiss)

    # select top24 according to ranking_order
    top24 = ranking_order[:TOP_K]
    for p in top24:
        count_top_cut[p] += 1

    # build top24 ordered list in seed order (1..24)
    top24_ordered = top24[:TOP_K]  # already ordered by rank_after_swiss

    # Playoffs with live elos (continuing from sim_elos_after_swiss)
    champ, prog, sim_elos_after_playoffs = run_playoffs_with_live_elo(top24_ordered, sim_elos_after_swiss)

    count_champion[champ] += 1
    for p, stage in prog.items():
        count_progress[p][stage] += 1

    # accumulate final elos (for everyone: if not in top24, their final elos are sim_elos_after_swiss)
    for p in players:
        final_val = sim_elos_after_playoffs.get(p, sim_elos_after_swiss.get(p, initial_elos[p]))
        final_elo_sums[p] += final_val

    if sim % max(1, N_SIMULATIONS // 10) == 0:
        print(f"Sim {sim}/{N_SIMULATIONS} done")

# ---------- Prepare output ----------
summary_rows = []
for p in players:
    made_playoffs = count_top_cut[p]
    champ_cnt = count_champion[p]
    prob_top24 = made_playoffs / N_SIMULATIONS
    prob_champion = champ_cnt / N_SIMULATIONS
    prob_R16 = sum(v for k, v in count_progress[p].items() if k >= 2) / N_SIMULATIONS
    prob_QF = sum(v for k, v in count_progress[p].items() if k >= 3) / N_SIMULATIONS
    prob_SF = sum(v for k, v in count_progress[p].items() if k >= 5) / N_SIMULATIONS
    avg_final_elo = final_elo_sums[p] / N_SIMULATIONS
    summary_rows.append({
        "Bey": p,
        "ELO": initial_elos[p],
        "AvgFinalSimELO": round(avg_final_elo, 2),
        "P(Top24)": round(prob_top24, 3),
        "P(R16)": round(prob_R16, 3),
        "P(QF)": round(prob_QF, 3),
        "P(SF)": round(prob_SF, 3),
        "P(Champion)": round(prob_champion, 3)
    })

out_df = pd.DataFrame(summary_rows).sort_values(by="ELO", ascending=False)
out_df.to_csv(os.path.join(OUT_DIR, "sim_results_summary.csv"), index=False)
print("Simulation abgeschlossen.")
print(f"Ergebnis: {os.path.join(OUT_DIR, 'sim_results_summary.csv')}")
