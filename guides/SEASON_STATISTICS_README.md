# Advanced Season Statistics & Analytics System

## Overview

The Advanced Season Statistics module provides comprehensive statistical tracking and analysis for Beyblade league seasons. It processes round-level data to generate performance metrics, efficiency statistics, and season awards.

## Features

### Core Statistics
- **Basic Performance Metrics**: Matches played/won/lost, points scored/conceded, rounds won/lost
- **Efficiency Metrics**: Points per round (PPR), average rounds per match, average points per match
- **Finish-Type Statistics**: Burst/Pocket/Extreme/Spin wins and losses
- **Defensive Metrics**: Bursts suffered, defensive stability index
- **Clutch & Comeback Metrics**: Clutch wins, comeback victories, reverse sweeps
- **Advanced Indices**: Offensive Power Index, Dominance Index, Volatility Index

### Phase Separation
Statistics can be computed separately for:
- **All matches** combined
- **Swiss phase** (regular season) only
- **Playoffs phase** only

This ensures playoff matches don't inflate regular-season awards.

### Season Awards
The system automatically generates awards including:
- 🏆 Most Dominant Bey (Highest Dominance Index)
- 💥 Burst King (Most Burst Wins)
- 🌀 Stamina Master (Most Spin Wins)
- 🔥 Aggression Award (Highest Aggression Ratio)
- 🛡 Iron Wall (Fewest Bursts Suffered)
- ⚡ Efficiency Award (Highest PPR)
- 🧠 Clutch Performer (Highest Clutch Win Rate)
- 📊 Highest Match Win Rate
- 📈 Best Points Differential
- 🎯 Best Round Differential
- ⚔️ Highest Offensive Power Index
- 📐 Most Consistent (Lowest Volatility)

## Usage

### Command Line

Generate statistics for all matches:
```bash
python src/season_statistics.py
```

Generate statistics for a specific season:
```bash
python src/season_statistics.py --season S1
```

Generate statistics for a specific tier:
```bash
python src/season_statistics.py --tier 1
```

Generate statistics for a specific phase:
```bash
python src/season_statistics.py --phase swiss
python src/season_statistics.py --phase playoffs
```

Set minimum matches for awards:
```bash
python src/season_statistics.py --min-matches 10
```

### Python API

```python
from season_statistics import SeasonStatistics

# Initialize
stats = SeasonStatistics()

# Load data
stats.load_data(season_id="S1", tier=1)

# Compute statistics
stats.compute_statistics()

# Generate awards
awards = stats.generate_awards(phase="swiss", min_matches=5)

# Export to JSON
stats.export_to_json("output.json", phase="all", include_awards=True)

# Export to CSV
stats.export_to_csv("output.csv", phase="all")

# Get leaderboards
leaderboards = stats.generate_leaderboards("all")
win_rate_leaders = leaderboards["match_win_rate"]
```

## Data Model

### Match Entity
```python
@dataclass
class Match:
    match_id: str
    tier: Optional[int]
    phase: str  # Swiss, Playoffs, Placement, Exhibition
    bey_a: str
    bey_b: str
    final_score_a: int
    final_score_b: int
    winner: str
    total_rounds: int
    timestamp: str
    season_id: Optional[str]
```

### Round Entity
```python
@dataclass
class Round:
    round_id: str
    match_id: str
    round_number: int
    bey_a: str
    bey_b: str
    winner: str
    loser: str
    finish_type: str  # BURST, POCKET, EXTREME, SPIN
    points_awarded: int
    round_duration: Optional[float]
```

## Metrics Explained

### Basic Performance
- **Match Win Rate**: Percentage of matches won
- **Points Differential**: Total points scored minus total points conceded
- **Round Differential**: Total rounds won minus total rounds lost

### Efficiency Metrics
- **Points Per Round (PPR)**: Average points scored per round played
- **Average Rounds Per Match**: Average number of rounds in each match
- **Average Points Per Match**: Average points scored per match

### Finish-Type Statistics
- **Burst Win Rate**: Percentage of round wins achieved by burst finish
- **Aggression Ratio**: Percentage of round wins achieved by aggressive finishes (Burst + Pocket + Extreme)

### Defensive Metrics
- **Defensive Stability Index**: `1 - (Bursts Suffered / Total Rounds Played)`
  - Higher values indicate better resistance to burst finishes
  - Range: 0.0 (always burst) to 1.0 (never burst)

### Clutch & Comeback Metrics
- **Clutch Matches Won**: Matches won with close final scores (within 1 point)
- **Comeback Wins**: Matches won after falling behind early
- **Reverse Sweeps**: Matches won after being down 0-2 or worse

### Advanced Indices

#### Offensive Power Index (OPI)
Weighted scoring system for finish types:
```
OPI = (3×Burst + 2.5×Extreme + 2×Pocket + 1×Spin) / Matches Played
```
- Higher values indicate more aggressive, high-impact finishes
- Range: typically 0-6, where 6 would mean all burst wins

#### Dominance Index
Overall measure of competitive dominance:
```
Dominance Index = (Points Differential per Match) + (PPR × 1.5)
```
- Combines scoring advantage with efficiency
- Higher values indicate stronger overall performance

#### Volatility Index
Standard deviation of points scored per match:
- Lower values indicate more consistent performance
- Higher values indicate high variance (feast or famine)

## Output Files

### JSON Output
```json
{
  "phase": "all",
  "statistics": {
    "BeyName": {
      "bey_name": "BeyName",
      "matches_played": 20,
      "matches_won": 15,
      "match_win_rate": 75.0,
      "offensive_power_index": 3.5,
      "dominance_index": 2.8,
      ...
    }
  },
  "leaderboards": {
    "match_win_rate": [...],
    "offensive_power_index": [...],
    ...
  },
  "awards": {
    "most_dominant": {
      "title": "Most Dominant Bey",
      "icon": "🏆",
      "winner": "BeyName",
      "value": 5.2,
      "metric": "Dominance Index"
    }
  }
}
```

### CSV Output
CSV file with one row per Bey, including all computed statistics.

## Integration with Update Pipeline

The module is automatically run as part of the main update pipeline:

```bash
python update.py  # Runs season statistics with other analysis modules
```

## Testing

Comprehensive test suite included:

```bash
python -m pytest tests/test_season_statistics.py -v
```

Test coverage includes:
- BeySeasonStats class properties
- Data loading and filtering
- Statistics computation
- Phase separation logic
- Award generation
- JSON/CSV export
- Clutch and comeback detection

## Future Enhancements

Potential additions:
- ELO integration for ranking-adjusted awards
- Cross-season comparison analytics
- Historical stat tracking across seasons
- Promotion/relegation impact analysis
- Head-to-head matchup statistics
- Part-specific effectiveness metrics

## Requirements

- Python 3.7+
- pandas (for data handling)
- Standard library: csv, json, statistics, collections, dataclasses

## File Structure

```
src/
  season_statistics.py          # Main module
tests/
  test_season_statistics.py     # Test suite
docs/data/
  matches.csv                    # Input: Match results
  rounds.csv                     # Input: Round-level data
  season_statistics.json         # Output: Statistics and awards
  season_statistics.csv          # Output: Statistics table
```

## License

Part of the BeybladeX Elo System project.
