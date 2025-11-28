# Recording Workflow for Live Tournaments

This document describes the recommended workflow for recording Beyblade tournament matches with per-round finish type tracking.

## Overview

The workflow uses two parallel recording methods during live tournaments:
1. **Challonge** (or similar bracket software) for real-time bracket management
2. **Rounds CSV/Google Sheet** for detailed per-round tracking

After the tournament, these data sources are merged using the `merge_rounds.py` tool.

## Pre-Tournament Setup

### 1. Prepare Challonge Bracket

1. Create your tournament bracket in Challonge
2. Add all participants
3. Note the tournament URL/ID for later reference

### 2. Prepare Rounds Tracking Sheet

Create a Google Sheet or CSV file with these columns:

| Column | Description | Required |
|--------|-------------|----------|
| `match_id` | Challonge match ID or custom identifier | Yes |
| `round_number` | Sequential round number within match | Yes |
| `winner` | Name of the round winner | Yes |
| `finish_type` | Type of finish (spin, pocket, burst, extreme) | No (defaults to spin) |
| `points_awarded` | Points won this round | Yes |
| `notes` | Any additional observations | No |

**Template:** Use `templates/rounds_template.csv` as a starting point.

### 3. Setup Google Sheets (Recommended)

For live tournaments, Google Sheets provides real-time collaboration:

1. Create a new Google Sheet from the template
2. Share with all scorekeepers
3. Enable offline editing for connectivity issues

## During the Tournament

### Real-Time Recording Process

1. **Challonge**: Update bracket with match winners and final scores
2. **Rounds Sheet**: Record each round as it happens:

Example entry:
```
match_id,round_number,winner,finish_type,points_awarded,notes
M001,1,ViperTail,spin,1,Close outspin
M001,2,WizardArc,burst,2,Quick burst finish
M001,3,ViperTail,pocket,2,Stadium KO
M001,4,ViperTail,spin,1,Final outspin
```

### Tips for Efficient Recording

- **Assign dedicated scorekeepers** for rounds tracking
- **Use shorthand codes** if needed (s=spin, p=pocket, b=burst, e=extreme)
- **Record notes** for unusual situations or close calls
- **Mark uncertain finish types** in notes column for later review

### Handling Unknown Finish Types

If the finish type wasn't observed clearly:
1. Record `spin` as the default
2. Add a note: "finish type uncertain"
3. Review video replay if available after the match

## Post-Tournament Processing

### Step 1: Export Data

1. **From Challonge**: Export as CSV or JSON
   - Go to Tournament Settings → Download
   - Select CSV format

2. **From Google Sheets**: Download as CSV
   - File → Download → Comma Separated Values (.csv)

### Step 2: Verify Data

Before merging, check:
- [ ] All matches are recorded in both sources
- [ ] Match IDs are consistent
- [ ] Player names match exactly (spelling, case)
- [ ] No duplicate entries

### Step 3: Merge Data

Use the merge tool to combine Challonge export with rounds data:

```bash
python tools/merge_rounds.py \
    --challonge path/to/challonge_export.csv \
    --rounds path/to/rounds_data.csv \
    --output path/to/merged_matches.json
```

The tool will:
- Match rounds to matches by match_id
- Validate score consistency
- Apply "spin" default for missing finish types
- Generate a validation summary

### Step 4: Review Merge Output

Check the merge summary for:
- Matches successfully merged
- Mismatches between Challonge scores and round totals
- Matches without round data
- Any warnings or errors

### Step 5: Import to Elo System

Once verified, the merged JSON can be imported into the Elo system:

```bash
python update.py --input merged_matches.json
```

## Backfill Procedure for Past Tournaments

For tournaments that were recorded without per-round tracking:

### When to Backfill

- You have video recordings to review
- You have partial notes or memories of finish types
- You want to add round-level detail retroactively

### Backfill Process

1. **Create a rounds CSV** for the past tournament using the template
2. **Set unknown finish types to "spin"** (the default)
3. **Document assumptions** in the backfill log (see `docs/backfill_log_template.md`)
4. **Merge with existing match data** using `merge_rounds.py`

See `docs/backfill_instructions.md` for detailed step-by-step instructions.

## Data Flow Diagram

```
┌─────────────────┐     ┌───────────────────┐
│   Challonge     │     │  Rounds Sheet     │
│  (Bracket/      │     │  (Per-round       │
│   Final Scores) │     │   Finish Types)   │
└────────┬────────┘     └─────────┬─────────┘
         │                        │
         ▼                        ▼
    Export CSV               Export CSV
         │                        │
         └──────────┬─────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │  merge_rounds.py │
         │   (Validation &  │
         │     Merging)     │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  merged_matches  │
         │     .json        │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │   Elo System     │
         │   (update.py)    │
         └──────────────────┘
```

## Troubleshooting

### Match IDs Don't Match

If Challonge match IDs differ from your rounds sheet:
- Use the `--match-by-players` flag in merge_rounds.py
- The tool will attempt to match by player names and scores

### Player Names Have Typos

Ensure consistent spelling by:
1. Exporting the Challonge participant list first
2. Using copy-paste for names in the rounds sheet
3. Using the validation summary to identify mismatches

### Missing Round Data

For matches without round data:
- The merge tool will log them as "unmerged"
- They will keep their original Challonge scores
- Consider backfilling later if you have recordings
