# Challonge Web Scraper

## Overview

The Challonge web scraper (`scripts/challonge_scraper.py`) is a tool for automatically importing tournament data from Challonge into the BeybladeX Elo system.

## Features

- **Automatic Data Extraction**: Fetches tournament brackets and match results from Challonge
- **Smart Name Mapping**: Automatically maps participant names to Beyblade names from `csv/beys.csv`
- **Date Detection**: Extracts tournament dates from the page or allows manual override
- **Dry-Run Mode**: Preview matches before adding them to the database
- **Error Handling**: Robust error handling for network issues and parsing failures

## Usage

### Basic Usage

```bash
# Scrape a tournament and append to matches.csv
python scripts/challonge_scraper.py https://challonge.com/om3hx2e9
```

### Advanced Options

```bash
# Preview matches without writing (dry-run mode)
python scripts/challonge_scraper.py om3hx2e9 --dry-run

# Specify a custom date for the tournament
python scripts/challonge_scraper.py zjbg6ab3 --date 2025-09-15

# Output to a different CSV file
python scripts/challonge_scraper.py om3hx2e9 --output custom_matches.csv
```

### After Scraping

After successfully scraping a tournament, update the Elo ratings:

```bash
python update.py
```

## Input Format

The scraper accepts either:
- Full Challonge URL: `https://challonge.com/om3hx2e9`
- Tournament ID only: `om3hx2e9`

## Output Format

Matches are appended to `csv/matches.csv` in the following format:

```csv
Date,BeyA,BeyB,ScoreA,ScoreB
2025-09-07,FoxBrush,DranSword,5,3
2025-09-07,ImpactDrake,ViperTail,4,2
```

## Name Mapping

The scraper attempts to match participant names from Challonge to Beyblade names in `csv/beys.csv`:

1. **Exact Match**: Case-insensitive exact matching
2. **Partial Match**: Substring matching (e.g., "Fox" matches "FoxBrush")
3. **Fallback**: If no match found, uses the original name from Challonge

You may need to manually correct names in `matches.csv` if the automatic mapping is incorrect.

## Limitations

- Only completed matches with scores are extracted
- Requires internet connectivity to access Challonge
- HTML structure changes on Challonge may require updates to the scraper
- Some participant names may not map correctly and require manual correction

## Troubleshooting

### No matches found

- Ensure the tournament has completed matches with scores
- Check that the tournament URL is correct and accessible
- Try using `--dry-run` to see what the scraper is detecting

### Name mapping issues

After scraping, review the matches added and manually correct any mismatched names in `csv/matches.csv`.

### Connection errors

- Verify internet connectivity
- Check that Challonge is accessible
- The scraper includes a 30-second timeout for requests

### 403 Forbidden errors

If you encounter "403 Client Error: Forbidden" when scraping:

1. **Challonge anti-bot protection**: Challonge may be blocking automated requests. The scraper now includes comprehensive browser headers to mimic a real browser.

2. **Rate limiting**: If scraping multiple tournaments, add a delay between requests:
   ```bash
   python scripts/challonge_scraper.py tournament1
   sleep 5
   python scripts/challonge_scraper.py tournament2
   ```

3. **IP blocking**: If you're making many requests, your IP may be temporarily blocked. Wait a few minutes before trying again.

4. **Alternative approach**: If automated scraping continues to fail, you can manually export tournament data from Challonge and import it into `csv/matches.csv` following the format: `Date,BeyA,BeyB,ScoreA,ScoreB`

5. **Check tournament visibility**: Ensure the tournament is public and not set to private/unlisted on Challonge.

## Testing

Run the test suite to validate the scraper functionality:

```bash
python test_challonge_scraper.py
```

## Dependencies

- `requests` - HTTP library for fetching web pages
- `beautifulsoup4` - HTML parsing library

Install dependencies:

```bash
pip install -r requirements.txt
```
