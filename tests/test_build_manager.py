"""
Tests for build_manager.py

Tests the build management system including:
- Build creation and parsing
- Stock build initialization
- Build validation and resolution
- Usage tracking and status updates
"""

import pytest
import json
import os
import tempfile
from datetime import datetime, timedelta
from src.build_manager import Build, BuildManager, PROVISIONAL_THRESHOLD


class TestBuild:
    """Test Build class."""
    
    def test_build_id_generation(self):
        """Test that build_id is correctly generated from components."""
        build = Build("DranDagger", "4-60", "Rush", is_stock=True)
        assert build.build_id == "DranDagger_4-60_Rush"
    
    def test_build_to_dict(self):
        """Test Build serialization to dict."""
        build = Build("DranDagger", "5-80", "Elevate", is_stock=False)
        data = build.to_dict()
        
        assert data["build_id"] == "DranDagger_5-80_Elevate"
        assert data["blade"] == "DranDagger"
        assert data["ratchet"] == "5-80"
        assert data["bit"] == "Elevate"
        assert data["is_stock"] is False
        assert data["match_count"] == 0
        assert data["current_elo"] == 1000.0
        assert data["status"] == "provisional"
    
    def test_build_from_dict(self):
        """Test Build deserialization from dict."""
        data = {
            "blade": "PhoenixWing",
            "ratchet": "3-60",
            "bit": "Point",
            "is_stock": True,
            "stock_code": "BX-01",
            "match_count": 10,
            "current_elo": 1250.5,
            "status": "active"
        }
        build = Build.from_dict(data)
        
        assert build.blade == "PhoenixWing"
        assert build.ratchet == "3-60"
        assert build.bit == "Point"
        assert build.is_stock is True
        assert build.stock_code == "BX-01"
        assert build.match_count == 10
        assert build.current_elo == 1250.5
        assert build.status == "active"
    
    def test_status_update_provisional(self):
        """Test that build stays provisional with few matches."""
        build = Build("TestBlade", "1-60", "TestBit")
        build.match_count = PROVISIONAL_THRESHOLD - 1
        build.update_status()
        
        assert build.status == "provisional"
    
    def test_status_update_active(self):
        """Test that build becomes active with enough matches."""
        build = Build("TestBlade", "1-60", "TestBit")
        build.match_count = PROVISIONAL_THRESHOLD
        build.update_status()
        
        assert build.status == "active"
    
    def test_status_update_retired(self):
        """Test that build becomes retired when unused for 90+ days."""
        old_date = (datetime.now() - timedelta(days=91)).strftime("%Y-%m-%d")
        build = Build("TestBlade", "1-60", "TestBit", last_used=old_date)
        build.match_count = 10
        build.update_status()
        
        assert build.status == "retired"


class TestBuildManager:
    """Test BuildManager class."""
    
    @pytest.fixture
    def temp_files(self):
        """Create temporary files for testing."""
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        builds_path = os.path.join(temp_dir, "builds.json")
        beys_data_path = os.path.join(temp_dir, "beys_data.json")
        
        # Create sample beys_data.json
        beys_data = [
            {
                "code": "BX-01",
                "name": "PhoenixWing 3-60P",
                "blade": "PhoenixWing",
                "ratchet": "3-60",
                "bit": "Point",
                "type": "Attack"
            },
            {
                "code": "BX-20",
                "name": "DranDagger 4-60R",
                "blade": "DranDagger",
                "ratchet": "4-60",
                "bit": "Rush",
                "type": "Attack"
            }
        ]
        
        with open(beys_data_path, 'w') as f:
            json.dump(beys_data, f)
        
        yield builds_path, beys_data_path
        
        # Cleanup
        if os.path.exists(builds_path):
            os.remove(builds_path)
        if os.path.exists(beys_data_path):
            os.remove(beys_data_path)
        os.rmdir(temp_dir)
    
    def test_initialize_from_stock_beys(self, temp_files):
        """Test stock build initialization from beys_data.json."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        
        count = manager.initialize_from_stock_beys()
        
        assert count == 2
        assert len(manager.builds) == 2
        assert "PhoenixWing_3-60_Point" in manager.builds
        assert "DranDagger_4-60_Rush" in manager.builds
        
        # Check stock build properties
        phoenix_build = manager.builds["PhoenixWing_3-60_Point"]
        assert phoenix_build.is_stock is True
        assert phoenix_build.stock_code == "BX-01"
        assert phoenix_build.blade == "PhoenixWing"
    
    def test_create_custom_build(self, temp_files):
        """Test creating a custom build."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        
        build_id = manager.create_build("DranDagger", "5-80", "Elevate", is_stock=False)
        
        assert build_id == "DranDagger_5-80_Elevate"
        assert build_id in manager.builds
        
        build = manager.builds[build_id]
        assert build.is_stock is False
        assert build.stock_code is None
        assert build.blade == "DranDagger"
        assert build.ratchet == "5-80"
        assert build.bit == "Elevate"
    
    def test_get_stock_build(self, temp_files):
        """Test getting stock build for a blade."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        
        stock_id = manager.get_stock_build("DranDagger")
        
        assert stock_id == "DranDagger_4-60_Rush"
    
    def test_parse_build_id(self, temp_files):
        """Test parsing build ID into components."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        
        blade, ratchet, bit = manager.parse_build_id("DranDagger_5-80_Elevate")
        
        assert blade == "DranDagger"
        assert ratchet == "5-80"
        assert bit == "Elevate"
    
    def test_parse_build_id_invalid(self, temp_files):
        """Test that invalid build IDs raise ValueError."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        
        with pytest.raises(ValueError):
            manager.parse_build_id("InvalidFormat")
        
        with pytest.raises(ValueError):
            manager.parse_build_id("Too_Many_Parts_Here")
    
    def test_resolve_build_stock(self, temp_files):
        """Test resolving to stock build when no custom build specified."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        
        build_id = manager.resolve_build_from_match("DranDagger", None)
        
        assert build_id == "DranDagger_4-60_Rush"
    
    def test_resolve_build_custom(self, temp_files):
        """Test resolving custom build from match data."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        
        build_id = manager.resolve_build_from_match("DranDagger", "DranDagger_5-80_Elevate")
        
        assert build_id == "DranDagger_5-80_Elevate"
        # Should auto-register the custom build
        assert build_id in manager.builds
        assert manager.builds[build_id].is_stock is False
    
    def test_resolve_build_blade_mismatch(self, temp_files):
        """Test that blade mismatch raises ValueError."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        
        with pytest.raises(ValueError, match="doesn't match"):
            manager.resolve_build_from_match("DranDagger", "PhoenixWing_3-60_Point")
    
    def test_update_build_usage(self, temp_files):
        """Test updating build usage after a match."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        
        build_id = "DranDagger_4-60_Rush"
        initial_elo = manager.builds[build_id].current_elo
        
        manager.update_build_usage(build_id, "2025-12-15", elo_change=20)
        
        build = manager.builds[build_id]
        assert build.match_count == 1
        assert build.last_used == "2025-12-15"
        assert build.current_elo == initial_elo + 20
    
    def test_get_builds_by_blade(self, temp_files):
        """Test getting all builds for a blade."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        manager.create_build("DranDagger", "5-80", "Elevate")
        manager.create_build("DranDagger", "3-70", "Point")
        
        builds = manager.get_builds_by_blade("DranDagger")
        
        assert len(builds) == 3
        blade_names = [b.blade for b in builds]
        assert all(blade == "DranDagger" for blade in blade_names)
    
    def test_save_and_load_builds(self, temp_files):
        """Test saving and loading builds.json."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        manager.create_build("DranDagger", "5-80", "Elevate")
        
        manager.save_builds()
        
        # Create new manager and load
        manager2 = BuildManager(builds_path, beys_data_path)
        manager2.load_builds()
        
        assert len(manager2.builds) == 3
        assert "DranDagger_5-80_Elevate" in manager2.builds
        assert manager2.builds["DranDagger_5-80_Elevate"].is_stock is False
    
    def test_get_build_stats(self, temp_files):
        """Test build statistics calculation."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        manager.create_build("DranDagger", "5-80", "Elevate")
        
        stats = manager.get_build_stats()
        
        assert stats["total_builds"] == 3
        assert stats["stock_builds"] == 2
        assert stats["custom_builds"] == 1
        assert stats["unique_blades"] == 2
    
    def test_get_active_builds(self, temp_files):
        """Test filtering active builds."""
        builds_path, beys_data_path = temp_files
        manager = BuildManager(builds_path, beys_data_path)
        manager.initialize_from_stock_beys()
        
        # Manually set match counts to make builds active
        for build_id in ["PhoenixWing_3-60_Point", "DranDagger_4-60_Rush"]:
            manager.builds[build_id].match_count = PROVISIONAL_THRESHOLD
            manager.builds[build_id].update_status()
        
        active_builds = manager.get_active_builds()
        
        assert len(active_builds) == 2
        assert all(b.status == "active" for b in active_builds)
