# Custom Tournament Management System - User Guide

## Overview

The custom tournament management system allows you to create and manage tournaments directly on the website without relying on external services like Challonge. This provides full control over tournament formats, faster data entry, and better integration with the Beyblade X analytics ecosystem.

## Features

### Supported Formats
- **Swiss System**: Automatic pairing with no rematches, tie-breaker calculations (Buchholz, Opponent Win %)
- **Single Elimination**: Classic knockout bracket
- **Double Elimination**: Winners and losers brackets
- **Round Robin**: Everyone plays everyone
- **Hybrid Formats**: Swiss → Top Cut → SE/DE

### Key Capabilities
- Create tournaments with custom settings
- Automatic pairing generation
- Real-time match reporting
- Swiss standings with detailed statistics
- Match history viewing
- Tournament state persistence (JSON)
- Mobile-optimized interfaces

## User Workflow

### 1. Create a Tournament

Navigate to **Tournament Manager** (`tournament-manager.html`):

1. Fill in tournament details:
   - **Name**: Tournament name (e.g., "Spring Championship 2025")
   - **Date**: Tournament date
   - **Format**: Swiss, Single Elimination, etc.
   - **Number of Rounds**: Auto-calculated or custom
   - **Participants**: Enter one participant per line

2. Click **Create Tournament**

3. Tournament appears in the "Active Tournaments" section

### 2. Start & Manage Matches

From the Tournament Manager, click **Start** on your tournament, then **Manage**:

1. **Round Navigation**: Switch between rounds using round buttons
2. **Enter Results**: For each match:
   - Use quick score buttons (4, 3, 5) or manual entry
   - Click **Report Result** to submit
3. **Undo**: Click **Undo** to reverse a reported match
4. **Advance Round**: When all matches are complete, generate the next round

### 3. View Tournament

Click **View** to see tournament details:

- **Standings Tab**: Current rankings with tie-breakers
- **Matches Tab**: All matches grouped by round
- **Bracket Tab**: Bracket visualization (for knockout formats)
- **Statistics Tab**: Tournament statistics (coming soon)

### 4. Public Viewing

Navigate to **Tournaments** page (`tournaments.html`):

- Custom tournaments are marked with a "CUSTOM" badge
- Click any tournament card to view details
- Challonge tournaments show embedded brackets

## For Administrators

### Creating Tournaments Programmatically

Use the Python backend (`src/tournament_manager.py`):

```python
from src.tournament_manager import TournamentManager

manager = TournamentManager()

# Create tournament
tournament = manager.create_tournament(
    name="My Tournament",
    format="swiss",
    participants=["Player1", "Player2", "Player3", "Player4"],
    num_rounds=3
)

# Start tournament
tournament.start()

# Report matches
tournament.report_match(round_num=1, match_num=0, winner="Player1", score_a=4, score_b=2)

# Export for frontend
manager.export_for_frontend()
manager.export_tournament_details(tournament.tournament_id)
```

### Data Storage

Tournaments are stored in two locations:

1. **Backend Storage**: `data/tournaments/` (JSON files)
   - Individual tournament files: `{tournament_id}.json`
   - Tournament index: `tournaments_index.json`

2. **Frontend Data**: `docs/data/tournaments/`
   - Public tournament list: `tournaments.json`
   - Individual tournament files: `{tournament_id}.json`

### Integration with Existing Systems

To integrate custom tournaments with the ELO system:

1. Export tournament matches to `data/matches.csv`
2. Add tournament metadata to match entries
3. Run `python update.py` to recalculate ELO ratings
4. Tournaments automatically appear in match history and analytics

## Technical Architecture

### Backend (Python)
- **tournament_engine.py**: Core tournament logic
  - Tournament class with format support
  - Pairing algorithms (Swiss, SE, DE)
  - Standings calculation with tie-breakers
  - State persistence

- **tournament_manager.py**: Multi-tournament management
  - Create/load/save tournaments
  - Export for frontend
  - Tournament indexing

### Frontend (HTML/JS)
- **tournament-manager.html**: Tournament creation and overview
- **tournament-match-manager.html**: Match reporting interface
- **tournament-viewer.html**: Public tournament viewing
- **tournaments.html**: Tournament listing (updated for custom support)

### Data Flow
```
Create → Start → Manage Matches → Export → View
   ↓        ↓           ↓            ↓       ↓
Manager  Manager   Match Mgr      Files   Viewer
```

## Testing

Run the test suite:
```bash
python -m pytest tests/test_tournament_engine.py -v
```

All 38 tests cover:
- Tournament creation
- Pairing algorithms
- Match reporting
- Standings calculation
- Persistence (save/load)
- Edge cases (byes, rematches, etc.)

## Troubleshooting

### Tournament Not Found
- Check that the tournament ID is correct
- Ensure tournament files exist in `data/tournaments/`
- Verify tournament is in the index

### Matches Not Appearing
- Ensure tournament has been started
- Check that round pairings were generated
- Verify tournament state is saved

### Standings Not Updating
- Confirm matches are marked as "completed"
- Check that tie-breakers are being calculated
- Reload the page to refresh data

## Future Enhancements

- **Bracket Visualization**: SVG-based bracket rendering for SE/DE
- **Live Updates**: WebSocket support for real-time updates
- **Match Details**: Round-by-round score tracking
- **Export Formats**: PDF brackets, CSV results
- **Placement Matches**: 3rd place, 5th place, etc.
- **Player Statistics**: Per-tournament player analytics
- **Tournament Templates**: Save and reuse tournament configurations

## Support

For issues or questions:
1. Check the test suite for examples
2. Review the inline documentation in source files
3. Create an issue in the repository
