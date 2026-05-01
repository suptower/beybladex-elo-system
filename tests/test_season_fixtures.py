"""
Unit tests for filtering upcoming season fixtures.
"""
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.season.challonge_fixtures import make_fixture_id  # noqa: E402
from src.season.season_processing import filter_unplayed_fixtures  # noqa: E402


def _make_fixture(bey_a, bey_b, season_id="S1", tier=1, matchday=1):
    return {
        "fixture_id": make_fixture_id(bey_a, bey_b, season_id, tier),
        "bey_a": bey_a,
        "bey_b": bey_b,
        "season_id": season_id,
        "tier": tier,
        "matchday": matchday,
        "match_type": "season",
    }


def _make_match(bey_a, bey_b, score_a, score_b, season_id="S1", tier=1):
    return {
        "bey_a": bey_a,
        "bey_b": bey_b,
        "score_a": score_a,
        "score_b": score_b,
        "season_id": season_id,
        "tier": tier,
        "match_type": "season",
    }


def test_filter_unplayed_fixtures_excludes_played_pair():
    fixtures = [_make_fixture("A", "B")]
    matches = [_make_match("B", "A", 4, 2)]

    remaining = filter_unplayed_fixtures(fixtures, matches, "S1")

    assert remaining == []


def test_filter_unplayed_fixtures_keeps_zero_score():
    fixtures = [_make_fixture("A", "B"), _make_fixture("C", "D")]
    matches = [_make_match("A", "B", 0, 0)]

    remaining = filter_unplayed_fixtures(fixtures, matches, "S1")

    assert len(remaining) == 2
    assert [(fixture["bey_a"], fixture["bey_b"]) for fixture in remaining] == [
        ("A", "B"),
        ("C", "D"),
    ]
