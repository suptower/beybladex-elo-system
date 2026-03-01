"""
Unit tests for src/update_matches.py module.
Tests the session file pairing logic in get_latest_session_files().
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import update_matches


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
        """When multiple complete pairs exist, the latest (by sort order) is returned."""
        monkeypatch.setattr(update_matches, "RAW_DIR", tmp_path)
        for prefix in ("010125", "020125", "030125"):
            (tmp_path / f"{prefix}_session_matches.csv").touch()
            (tmp_path / f"{prefix}_session_rounds.csv").touch()

        m, r = update_matches.get_latest_session_files()
        assert m.name == "030125_session_matches.csv"
        assert r.name == "030125_session_rounds.csv"

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
