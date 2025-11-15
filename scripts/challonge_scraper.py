#!/usr/bin/env python3
"""
challonge_scraper.py - Web scraper for Challonge tournaments

Retrieves tournament data from Challonge and appends match data to matches.csv.
Supports single-elimination and other tournament formats.

Usage:
    python scripts/challonge_scraper.py <tournament_url>
    python scripts/challonge_scraper.py https://challonge.com/om3hx2e9
    python scripts/challonge_scraper.py https://challonge.com/zjbg6ab3 --dry-run
    
Options:
    --dry-run    : Preview matches without writing to CSV
    --date DATE  : Override tournament date (format: YYYY-MM-DD)
"""

import requests
from bs4 import BeautifulSoup
import csv
import os
import sys
import argparse
from datetime import datetime
import re


class ChallongeScraper:
    """Scraper for Challonge tournament data"""
    
    def __init__(self, tournament_url):
        """
        Initialize scraper with tournament URL
        
        Args:
            tournament_url: Full URL or tournament ID (e.g., 'om3hx2e9' or 'https://challonge.com/om3hx2e9')
        """
        self.tournament_url = tournament_url
        self.tournament_id = self._extract_tournament_id(tournament_url)
        self.base_url = f"https://challonge.com/{self.tournament_id}"
        self.matches = []
        
    def _extract_tournament_id(self, url):
        """Extract tournament ID from URL"""
        # Remove protocol and domain if present
        if 'challonge.com/' in url:
            return url.split('challonge.com/')[-1].strip('/')
        return url.strip('/')
    
    def fetch_tournament_data(self):
        """
        Fetch and parse tournament data from Challonge
        
        Returns:
            dict: Tournament data including matches and participants
        """
        try:
            # Set headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(self.base_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to get tournament name
            tournament_name = self._extract_tournament_name(soup)
            
            # Try to get tournament date
            tournament_date = self._extract_tournament_date(soup)
            
            # Extract matches from the bracket
            matches = self._extract_matches(soup)
            
            return {
                'name': tournament_name,
                'date': tournament_date,
                'matches': matches,
                'success': True
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching tournament data: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            print(f"Error parsing tournament data: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_tournament_name(self, soup):
        """Extract tournament name from page"""
        # Try multiple selectors
        name_selectors = [
            ('h1', {'class': 'tournament-title'}),
            ('h1', {}),
            ('title', {})
        ]
        
        for tag, attrs in name_selectors:
            element = soup.find(tag, attrs)
            if element:
                text = element.get_text(strip=True)
                # Clean up title tag if needed
                if tag == 'title':
                    text = text.split('|')[0].strip()
                return text
        
        return f"Tournament {self.tournament_id}"
    
    def _extract_tournament_date(self, soup):
        """Extract tournament date from page"""
        # Look for date in various locations
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            r'(\w+ \d{1,2},? \d{4})'  # Month DD, YYYY
        ]
        
        # Search in text content
        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                try:
                    # Try to parse and standardize the date
                    if '-' in date_str:
                        dt = datetime.strptime(date_str, '%Y-%m-%d')
                    elif '/' in date_str:
                        dt = datetime.strptime(date_str, '%m/%d/%Y')
                    else:
                        # Try to parse month name format
                        dt = datetime.strptime(date_str, '%B %d, %Y')
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        # Default to today's date
        return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_matches(self, soup):
        """
        Extract match data from tournament bracket
        
        Returns:
            list: List of match dictionaries with player names and scores
        """
        matches = []
        
        # Challonge typically uses specific classes for matches
        # Try multiple selectors to find match elements
        match_selectors = [
            {'class': 'match'},
            {'class': 'bracket-match'},
            {'data-match-id': True}
        ]
        
        match_elements = []
        for selector in match_selectors:
            found = soup.find_all('div', selector)
            if found:
                match_elements = found
                break
        
        # If no matches found with div, try li elements
        if not match_elements:
            match_elements = soup.find_all('li', {'class': 'match'})
        
        for match_elem in match_elements:
            match_data = self._parse_match_element(match_elem)
            if match_data:
                matches.append(match_data)
        
        return matches
    
    def _parse_match_element(self, match_elem):
        """
        Parse a single match element to extract player names and scores
        
        Args:
            match_elem: BeautifulSoup element containing match data
            
        Returns:
            dict: Match data with player1, player2, score1, score2
        """
        try:
            # Find player names
            player_elements = match_elem.find_all(['a', 'span'], class_=re.compile('player|participant'))
            
            # Find score elements
            score_elements = match_elem.find_all(['span', 'div'], class_=re.compile('score'))
            
            if len(player_elements) >= 2:
                player1 = player_elements[0].get_text(strip=True)
                player2 = player_elements[1].get_text(strip=True)
                
                # Extract scores if available
                score1 = 0
                score2 = 0
                
                if len(score_elements) >= 2:
                    score1_text = score_elements[0].get_text(strip=True)
                    score2_text = score_elements[1].get_text(strip=True)
                    
                    # Extract numeric score
                    score1 = self._extract_score(score1_text)
                    score2 = self._extract_score(score2_text)
                
                # Only include completed matches (with scores)
                if score1 > 0 or score2 > 0:
                    return {
                        'player1': player1,
                        'player2': player2,
                        'score1': score1,
                        'score2': score2
                    }
        except Exception as e:
            # Skip matches that can't be parsed
            pass
        
        return None
    
    def _extract_score(self, score_text):
        """Extract numeric score from text"""
        # Remove non-numeric characters except digits
        score_match = re.search(r'\d+', score_text)
        if score_match:
            return int(score_match.group())
        return 0
    
    def map_to_beyblade_names(self, player_name, bey_list):
        """
        Map player/participant names to Beyblade names from beys.csv
        
        Args:
            player_name: Name from Challonge tournament
            bey_list: List of valid Beyblade names
            
        Returns:
            str: Matched Beyblade name or original name
        """
        # Remove common prefixes/suffixes and normalize
        cleaned_name = player_name.strip()
        
        # Try exact match (case-insensitive)
        for bey in bey_list:
            if cleaned_name.lower() == bey.lower():
                return bey
        
        # Try partial match
        for bey in bey_list:
            if bey.lower() in cleaned_name.lower() or cleaned_name.lower() in bey.lower():
                return bey
        
        # Return original name if no match
        return cleaned_name
    
    def export_to_csv(self, matches, output_file, tournament_date=None, dry_run=False):
        """
        Export matches to CSV file (append mode)
        
        Args:
            matches: List of match dictionaries
            output_file: Path to CSV file (typically csv/matches.csv)
            tournament_date: Date to use for matches (YYYY-MM-DD format)
            dry_run: If True, only print matches without writing
        """
        if not matches:
            print("No matches to export.")
            return
        
        # Load existing Beyblade names
        bey_list = self._load_bey_list()
        
        # Use provided date or default
        date = tournament_date or datetime.now().strftime('%Y-%m-%d')
        
        # Prepare rows for CSV
        csv_rows = []
        for match in matches:
            player1 = self.map_to_beyblade_names(match['player1'], bey_list)
            player2 = self.map_to_beyblade_names(match['player2'], bey_list)
            
            row = {
                'Date': date,
                'BeyA': player1,
                'BeyB': player2,
                'ScoreA': match['score1'],
                'ScoreB': match['score2']
            }
            csv_rows.append(row)
        
        if dry_run:
            print("\n=== DRY RUN: Preview of matches to be added ===")
            print(f"Tournament Date: {date}")
            print(f"Total Matches: {len(csv_rows)}\n")
            
            for i, row in enumerate(csv_rows, 1):
                print(f"Match {i}: {row['BeyA']} ({row['ScoreA']}) vs {row['BeyB']} ({row['ScoreB']})")
            
            print("\n=== End of preview ===")
            return
        
        # Write to CSV file
        file_exists = os.path.exists(output_file)
        
        try:
            with open(output_file, 'a', newline='', encoding='utf-8') as f:
                fieldnames = ['Date', 'BeyA', 'BeyB', 'ScoreA', 'ScoreB']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header if file doesn't exist
                if not file_exists:
                    writer.writeheader()
                
                # Write matches
                writer.writerows(csv_rows)
            
            print(f"\n✓ Successfully appended {len(csv_rows)} matches to {output_file}")
            
        except Exception as e:
            print(f"Error writing to CSV: {e}")
            raise
    
    def _load_bey_list(self):
        """Load list of valid Beyblade names from beys.csv"""
        bey_list = []
        beys_file = 'csv/beys.csv'
        
        if os.path.exists(beys_file):
            try:
                with open(beys_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    bey_list = [row[0] for row in reader if row]
            except Exception as e:
                print(f"Warning: Could not load beys.csv: {e}")
        
        return bey_list


def main():
    """Main entry point for the scraper"""
    parser = argparse.ArgumentParser(
        description='Scrape tournament data from Challonge and append to matches.csv',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/challonge_scraper.py https://challonge.com/om3hx2e9
  python scripts/challonge_scraper.py om3hx2e9 --dry-run
  python scripts/challonge_scraper.py zjbg6ab3 --date 2025-09-15
        """
    )
    
    parser.add_argument('tournament_url', 
                        help='Challonge tournament URL or ID (e.g., om3hx2e9 or https://challonge.com/om3hx2e9)')
    parser.add_argument('--dry-run', 
                        action='store_true',
                        help='Preview matches without writing to CSV')
    parser.add_argument('--date',
                        help='Override tournament date (format: YYYY-MM-DD)')
    parser.add_argument('--output',
                        default='csv/matches.csv',
                        help='Output CSV file (default: csv/matches.csv)')
    
    args = parser.parse_args()
    
    # Validate date format if provided
    if args.date:
        try:
            datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print("Error: Date must be in YYYY-MM-DD format")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"Challonge Tournament Scraper")
    print(f"{'='*60}")
    print(f"Tournament: {args.tournament_url}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print(f"{'='*60}\n")
    
    # Create scraper and fetch data
    scraper = ChallongeScraper(args.tournament_url)
    
    print("Fetching tournament data...")
    tournament_data = scraper.fetch_tournament_data()
    
    if not tournament_data['success']:
        print(f"\n✗ Failed to fetch tournament data: {tournament_data.get('error', 'Unknown error')}")
        sys.exit(1)
    
    print(f"✓ Tournament: {tournament_data['name']}")
    print(f"✓ Date: {tournament_data['date']}")
    print(f"✓ Matches found: {len(tournament_data['matches'])}")
    
    if not tournament_data['matches']:
        print("\nWarning: No completed matches found in tournament.")
        sys.exit(0)
    
    # Use command-line date if provided, otherwise use detected date
    match_date = args.date or tournament_data['date']
    
    # Export to CSV
    scraper.export_to_csv(
        tournament_data['matches'],
        args.output,
        tournament_date=match_date,
        dry_run=args.dry_run
    )
    
    if not args.dry_run:
        print(f"\nNext steps:")
        print(f"  1. Review the matches added to {args.output}")
        print(f"  2. Run 'python update.py' to recalculate Elo ratings")


if __name__ == '__main__':
    main()
