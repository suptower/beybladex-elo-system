# Match Format Documentation

This document describes the JSON structure for Beyblade match data, including the new per-round finish type tracking feature.

## Overview

The Beyblade Elo system supports two match data formats:
1. **Simple format**: Basic match data with final scores only (backward compatible)
2. **Extended format**: Detailed match data with per-round information including finish types

## Simple Match Format (CSV)

The existing CSV format remains fully supported:

```csv
Date,BeyA,BeyB,ScoreA,ScoreB
2025-09-07,ViperTail,WizardArc,4,2
2025-09-07,SamuraiSaber,TuskMammoth,2,4
```

## Extended Match Format (JSON)

The extended JSON format adds optional round-level tracking:

```json
{
  "match_id": "T1-M001",
  "date": "2025-09-07",
  "bey_a": "ViperTail",
  "bey_b": "WizardArc",
  "score_a": 4,
  "score_b": 2,
  "rounds": [
    {
      "round_number": 1,
      "winner": "ViperTail",
      "points_awarded": 1,
      "finish_type": "spin",
      "notes": ""
    },
    {
      "round_number": 2,
      "winner": "WizardArc",
      "points_awarded": 2,
      "finish_type": "burst",
      "notes": ""
    },
    {
      "round_number": 3,
      "winner": "ViperTail",
      "points_awarded": 2,
      "finish_type": "ring_out",
      "notes": ""
    },
    {
      "round_number": 4,
      "winner": "ViperTail",
      "points_awarded": 1,
      "finish_type": "spin",
      "notes": ""
    }
  ],
  "tournament_id": "T1",
  "notes": "Group stage match"
}
```

## Allowed Finish Types

| Finish Type | Default Points | Description |
|-------------|----------------|-------------|
| `spin` | 1 | Outspin finish - opponent stops spinning first |
| `ring_out` | 2 | Ring out - opponent exits the stadium |
| `pocket` | 2 | Pocket finish - opponent falls into a pocket (treated same as ring_out) |
| `burst` | 2 | Burst finish - opponent's beyblade bursts apart |
| `extreme` | 3 | Extreme finish - special finish condition worth maximum points |

## Field Descriptions

### Match-Level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `match_id` | No | string | Unique identifier for the match |
| `date` | Yes | string | Match date in ISO 8601 format (YYYY-MM-DD) |
| `bey_a` | Yes | string | Name of the first beyblade/player |
| `bey_b` | Yes | string | Name of the second beyblade/player |
| `score_a` | No* | integer | Final score for bey_a |
| `score_b` | No* | integer | Final score for bey_b |
| `rounds` | No | array | Array of round objects |
| `tournament_id` | No | string | Tournament identifier |
| `notes` | No | string | Additional notes |

*If `rounds` array is provided, `score_a` and `score_b` can be computed automatically.

### Round-Level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `round_number` | No | integer | Sequential round number (1-based) |
| `winner` | Yes | string | Name of the round winner |
| `points_awarded` | Yes | integer | Points awarded for this round |
| `finish_type` | No | string | Type of finish (defaults to "spin") |
| `notes` | No | string | Additional notes about the round |

## Default Behavior

- **Missing `finish_type`**: Defaults to `"spin"` (1 point)
- **Missing scores with rounds**: Computed by summing `points_awarded` for each player
- **Score mismatch**: If provided scores don't match computed round totals, a warning is logged and round-level data is preferred

## Validation Rules

1. `winner` in each round must match either `bey_a` or `bey_b`
2. `finish_type` must be one of: `spin`, `ring_out`, `pocket`, `burst`, `extreme`
3. `points_awarded` must be a positive integer
4. If both `score_a`/`score_b` and `rounds` are provided, they should be consistent

## Schema Reference

The full JSON Schema is available at: `docs/schema/match_schema.json`

## Backward Compatibility

All existing functionality is preserved:
- CSV files with simple `Date,BeyA,BeyB,ScoreA,ScoreB` format continue to work
- Matches without `rounds` array are processed using existing logic
- The Elo calculation algorithm remains unchanged unless weighted scoring is explicitly enabled
