# Backfill Instructions

This document provides step-by-step instructions for manually backfilling past tournaments with per-round finish type data.

## Prerequisites

Before starting a backfill:

1. **Gather source materials**:
   - Video recordings of matches
   - Original scorecards or notes
   - Challonge export or match records

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare workspace**:
   - Create a working directory for the backfill
   - Have the rounds template ready

## Step-by-Step Backfill Process

### Step 1: Export Existing Match Data

Export the matches you want to backfill from the existing CSV:

```bash
# View existing matches for a specific date
grep "2025-09-07" csv/matches.csv
```

Or use the filter tool:

```bash
python src/filter_csv.py --date 2025-09-07 --output backfill_work/original_matches.csv
```

### Step 2: Create Rounds CSV

1. Copy the rounds template:
   ```bash
   cp templates/rounds_template.csv backfill_work/tournament_rounds.csv
   ```

2. Open the CSV in a spreadsheet editor or text editor

3. For each match, add round entries:

   ```csv
   match_id,round_number,winner,finish_type,points_awarded,notes
   M001,1,ViperTail,spin,1,
   M001,2,WizardArc,burst,2,
   M001,3,ViperTail,pocket,2,
   M001,4,ViperTail,spin,1,
   M002,1,TuskMammoth,spin,1,
   M002,2,TuskMammoth,burst,2,
   M002,3,SamuraiSaber,spin,1,
   M002,4,TuskMammoth,spin,1,
   ```

### Step 3: Apply Default for Unknown Finish Types

**Important**: When you don't know the finish type, use `spin` as the default.

This is the safest assumption because:
- Spin finishes are the most common outcome
- Using a default ensures data consistency
- Unknown data is better than missing data

For uncertain entries:
```csv
match_id,round_number,winner,finish_type,points_awarded,notes
M003,1,DranBrave,spin,1,finish type unknown - defaulted to spin
M003,2,DranBrave,spin,1,finish type unknown - defaulted to spin
```

### Step 4: Create Match ID Mapping (if needed)

If your original data doesn't have match IDs, create a mapping file:

```csv
bey_a,bey_b,date,match_id
ViperTail,WizardArc,2025-09-07,M001
SamuraiSaber,TuskMammoth,2025-09-07,M002
BlackShell,GolemRock,2025-09-07,M003
```

### Step 5: Run the Merge Tool

Merge your rounds data with the original match data:

```bash
python tools/merge_rounds.py \
    --challonge backfill_work/original_matches.csv \
    --rounds backfill_work/tournament_rounds.csv \
    --output backfill_work/merged_matches.json
```

If you don't have match IDs, use player-based matching:

```bash
python tools/merge_rounds.py \
    --challonge backfill_work/original_matches.csv \
    --rounds backfill_work/tournament_rounds.csv \
    --output backfill_work/merged_matches.json \
    --match-by-players
```

### Step 6: Review Merge Output

The merge tool will output a summary:

```
=== Merge Summary ===
Total matches in Challonge: 32
Total rounds in rounds file: 128
Matches merged: 30
Matches without rounds: 2
Score mismatches: 1
Defaults applied: 15

Warnings:
- Match M015: Score mismatch (Challonge: 4-2, Rounds: 5-2)
- Match M020: No rounds data found
- Match M025: No rounds data found
```

Review any warnings before proceeding.

### Step 7: Validate the Merged Data

Run validation on the merged output:

```bash
python tools/merge_rounds.py \
    --validate backfill_work/merged_matches.json
```

This checks:
- Score consistency between match totals and round sums
- Valid finish types
- Winner names matching player names

### Step 8: Update the Backfill Log

Document your backfill in the log (see `docs/backfill_log_template.md`):

```markdown
## Tournament: September 2025 Tournament

### Metadata
| Field | Value |
|-------|-------|
| Tournament ID | T001 |
| Original Date | 2025-09-07 |
| Backfill Date | 2025-10-20 |
| Backfilled By | @username |
| Data Source | Video replay |

### Matches Backfilled
| Match ID | Bey A | Bey B | Rounds Added | Confidence |
|----------|-------|-------|--------------|------------|
| M001 | ViperTail | WizardArc | 4 | High |
| M002 | SamuraiSaber | TuskMammoth | 4 | High |
...

### Assumptions Made
- 15 rounds had unknown finish types, defaulted to "spin"
- Matches M020, M025 could not be backfilled (no video coverage)
```

### Step 9: Import to the System (Optional)

If you want to use the extended data in the Elo system:

```bash
# Back up existing data first
cp csv/matches.csv csv/matches_backup.csv

# The system will use the merged data
# Note: Current Elo calculation uses final scores by default
```

## Quick Reference Commands

```bash
# Create working directory
mkdir backfill_work

# Copy template
cp templates/rounds_template.csv backfill_work/rounds.csv

# Merge with Challonge CSV
python tools/merge_rounds.py \
    --challonge challonge_export.csv \
    --rounds backfill_work/rounds.csv \
    --output backfill_work/merged.json

# Merge with player matching (no match IDs)
python tools/merge_rounds.py \
    --challonge challonge_export.csv \
    --rounds backfill_work/rounds.csv \
    --output backfill_work/merged.json \
    --match-by-players

# Validate merged output
python tools/merge_rounds.py --validate backfill_work/merged.json

# Clean up
rm -rf backfill_work  # Only after confirming successful import
```

## Troubleshooting

### "No matching match found for rounds"

This happens when:
- Match IDs don't correspond between files
- Player names are spelled differently

Solution: Use `--match-by-players` flag or fix the match IDs manually.

### "Score mismatch warning"

The sum of rounds doesn't match the Challonge final score.

Check:
1. Are all rounds recorded?
2. Are points_awarded values correct?
3. Is there a data entry error in Challonge?

By default, the tool prefers round-level data when there's a mismatch.

### "Invalid finish_type"

Only these values are allowed: `spin`, `pocket`, `burst`, `extreme`

Check for typos or use the correct value.

## Tips for Efficient Backfilling

1. **Batch similar tournaments**: Process tournaments from the same event together
2. **Use keyboard shortcuts**: In spreadsheet editors, use fill-down for match IDs
3. **Default aggressively**: When in doubt, use "spin" and note the uncertainty
4. **Review video at 2x speed**: Most finishes are identifiable even at faster playback
5. **Collaborate**: Split large tournaments among multiple people
