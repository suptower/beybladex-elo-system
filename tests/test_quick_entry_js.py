"""
Tests for quick-entry.js Season 4 integration and logic.
Verifies Season 4 formats, tier calculations, challenge league standings,
and match participant lookup via Node.js.
"""
import subprocess
import json
import pytest


def run_node_code(js_code: str):
    """Execute javascript code with Node and return parsed JSON result."""
    try:
        result = subprocess.run(
            ['node', '-e', js_code],
            capture_output=True,
            text=True,
            cwd='.',
            timeout=5,
            encoding="utf-8"
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            pytest.fail(f"Node execution failed with code {result.returncode}:\n{result.stderr}")
    except FileNotFoundError:
        pytest.skip("Node.js not available on host")


class TestQuickEntrySeason4:
    """Test suite for Quick Entry Season 4 logic."""

    def test_season_format_s4(self):
        js = """
        const qe = require('./docs/quick-entry.js');
        const fmt = qe.getSeasonFormat('S4');
        console.log(JSON.stringify(fmt));
        """
        fmt = run_node_code(js)
        assert fmt['tiers'] == 3
        assert fmt['beysPerTier'] == 8
        assert fmt['regularMatchdays'] == 10
        assert fmt['hasChallengeLeague'] is True
        assert fmt['challengeGroups'] == ['A', 'B', 'C', 'D']
        assert fmt['challengeGroupRounds'] == 3
        assert fmt['challengeFinalRounds'] == 3
        assert fmt['rulesVersion'] == 4

    def test_season_format_s2_s3(self):
        js = """
        const qe = require('./docs/quick-entry.js');
        const fmt2 = qe.getSeasonFormat('S2');
        const fmt3 = qe.getSeasonFormat('S3');
        console.log(JSON.stringify({ fmt2, fmt3 }));
        """
        data = run_node_code(js)
        for fmt in [data['fmt2'], data['fmt3']]:
            assert fmt['tiers'] == 4
            assert fmt['beysPerTier'] == 8
            assert fmt['regularMatchdays'] == 7
            assert fmt['hasChallengeLeague'] is False
            assert fmt['rulesVersion'] == 2

    def test_season_format_s1(self):
        js = """
        const qe = require('./docs/quick-entry.js');
        const fmt = qe.getSeasonFormat('S1');
        console.log(JSON.stringify(fmt));
        """
        fmt = run_node_code(js)
        assert fmt['tiers'] == 3
        assert fmt['beysPerTier'] == 10
        assert fmt['regularMatchdays'] == 9
        assert fmt['hasChallengeLeague'] is False
        assert fmt['rulesVersion'] == 1

    def test_sort_tier_standings(self):
        js = """
        const qe = require('./docs/quick-entry.js');
        const raw = {
            'BeyA': { bey: 'BeyA', seasonPoints: 6, pointDiff: 4, pointsFor: 8, elo: 1050 },
            'BeyB': { bey: 'BeyB', seasonPoints: 7, pointDiff: 5, pointsFor: 9, elo: 1000 },
            'BeyC': { bey: 'BeyC', seasonPoints: 6, pointDiff: 5, pointsFor: 8, elo: 1020 },
            'BeyD': { bey: 'BeyD', seasonPoints: 6, pointDiff: 4, pointsFor: 9, elo: 990 }
        };
        const sorted = qe.sortTierStandings(raw);
        console.log(JSON.stringify(sorted.map(s => s.bey)));
        """
        sorted_names = run_node_code(js)
        # Expected order:
        # 1. BeyB: 7 pts
        # 2. BeyC: 6 pts, +5 diff
        # 3. BeyD: 6 pts, +4 diff, 9 PF
        # 4. BeyA: 6 pts, +4 diff, 8 PF
        assert sorted_names == ['BeyB', 'BeyC', 'BeyD', 'BeyA']

    def test_get_participants_for_match(self):
        js = """
        const qe = require('./docs/quick-entry.js');
        qe.setSeasonData({
            seasons: {
                S4: {
                    league_tables: {
                        '1': [{ bey: 'ImpactDrake' }, { bey: 'SharkScale' }]
                    },
                    challenge_league: {
                        groups: {
                            'A': [{ bey: 'HellsBrave' }, { bey: 'DranStrike' }],
                            'B': ['ShelterDrake', 'BulletGriffon']
                        },
                        group_qualifiers: ['HellsBrave', 'ShelterDrake']
                    }
                }
            }
        });
        const t1 = qe.getParticipantsForMatch({ matchType: 'season', tier: '1', seasonId: 'S4' });
        const grpA = qe.getParticipantsForMatch({ matchType: 'challenge_group', tier: 'A', seasonId: 'S4' });
        const grpB = qe.getParticipantsForMatch({ matchType: 'challenge_group', tier: 'B', seasonId: 'S4' });
        const finalMatch = qe.getParticipantsForMatch({ matchType: 'challenge_final', seasonId: 'S4' });

        console.log(JSON.stringify({ t1, grpA, grpB, finalMatch }));
        """
        data = run_node_code(js)
        assert data['t1']['beys'] == ['ImpactDrake', 'SharkScale']
        assert data['grpA']['beys'] == ['HellsBrave', 'DranStrike']
        assert data['grpB']['beys'] == ['ShelterDrake', 'BulletGriffon']
        assert data['finalMatch']['beys'] == ['HellsBrave', 'ShelterDrake']

    def test_calculate_season_tier_standings_s4(self):
        js = """
        const qe = require('./docs/quick-entry.js');
        qe.setSeasonData({
            seasons: {
                S4: {
                    league_tables: {
                        '1': [
                            { bey: 'BeyA', matches: 0, wins: 0, losses: 0, season_points: 0, points_for: 0, points_against: 0, point_diff: 0, elo: 1100 },
                            { bey: 'BeyB', matches: 0, wins: 0, losses: 0, season_points: 0, points_for: 0, points_against: 0, point_diff: 0, elo: 1050 }
                        ]
                    },
                    challenge_league: {
                        groups: {
                            'A': [
                                { bey: 'BeyC', elo: 1000 },
                                { bey: 'BeyD', elo: 950 }
                            ]
                        }
                    }
                }
            }
        });
        qe.setMatches([
            // Regular match: 4-0 dominant win for BeyA -> 4 pts
            { beyA: 'BeyA', beyB: 'BeyB', scoreA: 4, scoreB: 0, matchType: 'season', seasonId: 'S4', tier: '1', matchday: 1 },
            // Challenge group match: 4-2 normal win for BeyD -> 3 pts
            { beyA: 'BeyC', beyB: 'BeyD', scoreA: 2, scoreB: 4, matchType: 'challenge_group', seasonId: 'S4', tier: 'A', matchday: 1 }
        ]);

        const standings = qe.calculateSeasonTierStandings();
        console.log(JSON.stringify(standings));
        """
        data = run_node_code(js)
        t1 = data['tiers']['1']
        assert t1['BeyA']['seasonPoints'] == 4
        assert t1['BeyA']['wins'] == 1
        assert t1['BeyA']['pointDiff'] == 4
        assert t1['BeyB']['seasonPoints'] == 0
        assert t1['BeyB']['losses'] == 1

        grpA = data['challengeGroups']['A']
        assert grpA['BeyD']['seasonPoints'] == 3
        assert grpA['BeyD']['wins'] == 1
        assert grpA['BeyD']['pointDiff'] == 2
        assert grpA['BeyC']['seasonPoints'] == 0
        assert grpA['BeyC']['losses'] == 1
