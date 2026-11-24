# Adding New Beys Without Match Data

This guide explains how to add new Beyblades to the system without any match history. New beys will automatically appear in the leaderboard with a starting ELO of 1000 and will be available in the quick entry system.

## Overview

When you add a new Beyblade to the system:
- It appears in the **leaderboard** with starting ELO (1000)
- It's available in the **quick entry system** for tournament entry
- It has a **wiki page** with its details
- It's ready to participate in matches
- Stats show 0 matches, 0 wins, 0 losses until it plays its first match

## Step-by-Step Instructions

### 1. Add the Bey to `beys_data.json`

Edit the file `docs/data/beys_data.json` and add a new entry for your Beyblade:

```json
{
  "code": "BX-XX",
  "name": "YourBey 3-60F",
  "blade": "YourBey",
  "ratchet": "3-60",
  "bit": "Flat",
  "type": "Attack",
  "image": "./data/beys/YourBey.png",
  "description": "Description of your beyblade."
}
```

#### Field Descriptions:
- **code**: Product code (e.g., "BX-01", "UX-11")
- **name**: Full name including components (e.g., "DranSword 3-60F")
- **blade**: Blade name only (e.g., "DranSword") - **This is the name used in matches**
- **ratchet**: Ratchet component (e.g., "3-60")
- **bit**: Bit component (e.g., "Flat")
- **type**: Beyblade type - one of: `Attack`, `Defense`, `Stamina`, `Balance`
- **image**: Path to image file (relative to docs folder)
- **description**: Short description of the beyblade

#### Optional Fields:
- **assist_blade**: For combination Beyblades (e.g., "Jaggy" for FoxBrush J9-70GR)

### 2. Add an Image (Optional but Recommended)

Place an image file in `docs/data/beys/` with the blade name (e.g., `YourBey.png`). 

If you don't have an image yet, you can use a placeholder path, and the wiki will still work.

### 3. Run the Update Pipeline

After adding your bey to `beys_data.json`, run:

```bash
python update.py
```

Or just update the ELO calculations:

```bash
python src/beyblade_elo.py --mode official
```

This will:
- Add the new bey to `leaderboard.csv` with ELO 1000
- Add the bey to `beys.csv` (used by quick entry)
- Make it available throughout the system

### 4. Verify the Addition

Check that your bey appears in:
- `docs/data/leaderboard.csv` - Should show ELO 1000, 0 matches
- `docs/data/beys.csv` - Simple list of all bey names
- The wiki page at `docs/wiki.html` (when viewing locally)
- The quick entry system at `docs/quick-entry.html`

## Example

Here's a complete example of adding a new Beyblade called "PhoenixWing":

**1. Edit `docs/data/beys_data.json`:**

```json
{
  "code": "UX-25",
  "name": "PhoenixWing 5-70N",
  "blade": "PhoenixWing",
  "ratchet": "5-70",
  "bit": "Needle",
  "type": "Stamina",
  "image": "./data/beys/PhoenixWing.png",
  "description": "A phoenix that never falls."
}
```

**2. Run the pipeline:**

```bash
python update.py --stats-only
```

**3. Verify:**

```bash
grep PhoenixWing docs/data/leaderboard.csv
# Output: 37,PhoenixWing,1000,0,0,0,0.0%,0,0,0,→ 0,0
```

## Using New Beys in Matches

Once a bey is added to the system:

1. **In Quick Entry**: The bey will appear in the dropdown menus for match entry
2. **In matches.csv**: Use the blade name (e.g., "PhoenixWing") in BeyA or BeyB columns
3. **First Match**: After the first match, the bey's ELO will update from 1000 based on the result

## Important Notes

- **Use the blade name** (not the full name) when recording matches
- The blade name in `beys_data.json` must match exactly what you use in match records
- Blade names are case-sensitive
- Each blade should appear only once in `beys_data.json`
- The `advanced_leaderboard.csv` only includes beys with match history (this is expected)

## Troubleshooting

**Bey doesn't appear in leaderboard:**
- Check that the JSON syntax is valid (no missing commas, brackets, etc.)
- Verify the blade name is not empty
- Run `python src/beyblade_elo.py --mode official` again

**Bey appears with wrong stats:**
- Check that there are no matches in `matches.csv` using the blade name
- If there are old matches you don't want to count, archive them to a different file

**Quick entry doesn't show the new bey:**
- The quick entry system loads from `leaderboard.csv`
- Make sure you ran the update pipeline after adding to `beys_data.json`
- Refresh your browser (Ctrl+F5 to clear cache)

## Technical Details

The system now:
1. Loads all beys from `beys_data.json` at the start of the ELO pipeline
2. Initializes each bey with starting ELO (1000) and zero stats
3. Processes all matches, updating ELOs only for beys that participated
4. Generates the leaderboard including all beys from `beys_data.json`
5. Beys with no matches retain their starting ELO and zero stats

This ensures that all registered Beyblades are visible and available, even before they play their first match.
