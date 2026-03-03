"""
Unit tests for src/update_matches.py module.
Tests the session file pairing logic in get_latest_session_files()
and the parse_session_date helper.
"""
import sys
import os
import pytest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import update_matches


class TestParseSessionDate:
    """Tests for the parse_session_date helper."""

    def test_valid_ddmmyy_prefix(self):
        """A valid ddmmyy prefix should return the correct datetime."""
        assert update_matches.parse_session_date("010125") == datetime(2025, 1, 1)
        assert update_matches.parse_session_date("311225") == datetime(2025, 12, 31)

    def test_prefix_longer_than_six_chars_ignored(self):
        """Only the first 6 characters are used; extra chars are ignored."""
        assert update_matches.parse_session_date("010125_extra") == datetime(2025, 1, 1)

    def test_invalid_prefix_raises_value_error(self):
        """A non-ddmmyy prefix should raise ValueError."""
        with pytest.raises(ValueError):
            update_matches.parse_session_date("abcdef")


class TestExtractSessionPrefix:
    """Tests for the extract_session_prefix helper."""

    def test_strips_matches_suffix(self):
        assert update_matches.extract_session_prefix("010125_session_matches.csv") == "010125"

    def test_strips_rounds_suffix(self):
        assert update_matches.extract_session_prefix("010125_session_rounds.csv") == "010125"

    def test_longer_prefix(self):
        assert update_matches.extract_session_prefix("311225_extra_session_matches.csv") == "311225_extra"

    def test_unknown_suffix_raises_value_error(self):
        with pytest.raises(ValueError):
            update_matches.extract_session_prefix("010125_other.csv")

    def test_unrelated_name_raises_value_error(self):
        with pytest.raises(ValueError):
            update_matches.extract_session_prefix("matches.csv")


class TestGetLatestSessionFiles:
    """Tests for the get_latest_session_files function."""

    def test_returns_matching_pair(self, tmp_path, monkeypatch):
        """A single complete pair should be returned."""
        monkeypatch.setattr(update_matches, "RAW_DIR", tmp_path)
        (tmp_path / "010125_session_matches.csv").touch()
        (tmp_path / "010125_session_rounds.csv").touch()

        m, r = update_matches.get_latest_session_files()
        assert m.name == "010125_session_matches.csv"
        assert r.name == "010125_session_rounds.csv"

    def test_returns_latest_complete_pair(self, tmp_path, monkeypatch):
        """When multiple complete pairs exist, the chronologically latest is returned."""
        monkeypatch.setattr(update_matches, "RAW_DIR", tmp_path)
        for prefix in ("010125", "020125", "030125"):
            (tmp_path / f"{prefix}_session_matches.csv").touch()
            (tmp_path / f"{prefix}_session_rounds.csv").touch()

        m, r = update_matches.get_latest_session_files()
        assert m.name == "030125_session_matches.csv"
        assert r.name == "030125_session_rounds.csv"

    def test_returns_chronologically_latest_across_months(self, tmp_path, monkeypatch):
        """Sessions are ordered by actual date, not lexicographically."""
        monkeypatch.setattr(update_matches, "RAW_DIR", tmp_path)
        # 31 Dec 2025 vs 01 Jan 2026 – lexicographic would pick "311225" last,
        # but chronologically "010126" is later.
        for prefix in ("311225", "010126"):
            (tmp_path / f"{prefix}_session_matches.csv").touch()
            (tmp_path / f"{prefix}_session_rounds.csv").touch()

        m, r = update_matches.get_latest_session_files()
        assert m.name == "010126_session_matches.csv"
        assert r.name == "010126_session_rounds.csv"

    def test_skips_incomplete_matches_only(self, tmp_path, monkeypatch):
        """A prefix with only a matches file should not form a pair."""
        monkeypatch.setattr(update_matches, "RAW_DIR", tmp_path)
        (tmp_path / "010125_session_matches.csv").touch()
        (tmp_path / "010125_session_rounds.csv").touch()
        # Newer prefix has only a matches file – should be skipped.
        (tmp_path / "020125_session_matches.csv").touch()

        m, r = update_matches.get_latest_session_files()
        assert m.name == "010125_session_matches.csv"
        assert r.name == "010125_session_rounds.csv"

    def test_skips_incomplete_rounds_only(self, tmp_path, monkeypatch):
        """A prefix with only a rounds file should not form a pair."""
        monkeypatch.setattr(update_matches, "RAW_DIR", tmp_path)
        (tmp_path / "010125_session_matches.csv").touch()
        (tmp_path / "010125_session_rounds.csv").touch()
        # Newer prefix has only a rounds file – should be skipped.
        (tmp_path / "020125_session_rounds.csv").touch()

        m, r = update_matches.get_latest_session_files()
        assert m.name == "010125_session_matches.csv"
        assert r.name == "010125_session_rounds.csv"

    def test_raises_when_no_complete_pair(self, tmp_path, monkeypatch):
        """FileNotFoundError should be raised when no complete pair exists."""
        monkeypatch.setattr(update_matches, "RAW_DIR", tmp_path)
        (tmp_path / "010125_session_matches.csv").touch()
        (tmp_path / "020125_session_rounds.csv").touch()

        with pytest.raises(FileNotFoundError):
            update_matches.get_latest_session_files()

    def test_raises_when_directory_empty(self, tmp_path, monkeypatch):
        """FileNotFoundError should be raised when no session files exist."""
        monkeypatch.setattr(update_matches, "RAW_DIR", tmp_path)

        with pytest.raises(FileNotFoundError):
            update_matches.get_latest_session_files()
