"""
Build Management System for Beyblade Combinations

This module manages build configurations (Blade + Ratchet + Bit combinations)
for both stock and custom Beyblade setups. It provides:
- Build ID generation and parsing
- Stock build auto-generation from beys_data.json
- Build registry management (builds.json)
- Build validation and resolution
- Hierarchical aggregation support

Build ID Format: {Blade}_{Ratchet}_{Bit}
Example: "DranDagger_4-60_Rush" (stock), "DranDagger_5-80_Elevate" (custom)

Usage:
    from build_manager import BuildManager
    
    manager = BuildManager()
    manager.initialize_from_stock_beys()
    
    build_id = manager.create_build("DranDagger", "5-80", "Elevate")
    build = manager.get_build(build_id)
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Colors for terminal output
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
BOLD = "\033[1m"

# File paths
BUILDS_JSON = "./docs/data/builds.json"
BEYS_DATA_JSON = "./docs/data/beys_data.json"

# Build status thresholds
PROVISIONAL_THRESHOLD = 5  # Matches needed for "active" status
RETIRED_DAYS = 90  # Days of inactivity before "retired"


class Build:
    """Represents a Beyblade build configuration."""
    
    def __init__(self, blade: str, ratchet: str, bit: str, is_stock: bool = False,
                 stock_code: Optional[str] = None, first_seen: Optional[str] = None,
                 last_used: Optional[str] = None, match_count: int = 0,
                 current_elo: float = 1000.0, status: str = "provisional"):
        self.blade = blade
        self.ratchet = ratchet
        self.bit = bit
        self.is_stock = is_stock
        self.stock_code = stock_code
        self.first_seen = first_seen or datetime.now().strftime("%Y-%m-%d")
        self.last_used = last_used or self.first_seen
        self.match_count = match_count
        self.current_elo = current_elo
        self.status = status
    
    @property
    def build_id(self) -> str:
        """Generate build ID from components."""
        return f"{self.blade}_{self.ratchet}_{self.bit}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "build_id": self.build_id,
            "blade": self.blade,
            "ratchet": self.ratchet,
            "bit": self.bit,
            "is_stock": self.is_stock,
            "stock_code": self.stock_code,
            "first_seen": self.first_seen,
            "last_used": self.last_used,
            "match_count": self.match_count,
            "current_elo": self.current_elo,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Build':
        """Create Build instance from dictionary."""
        return cls(
            blade=data["blade"],
            ratchet=data["ratchet"],
            bit=data["bit"],
            is_stock=data.get("is_stock", False),
            stock_code=data.get("stock_code"),
            first_seen=data.get("first_seen"),
            last_used=data.get("last_used"),
            match_count=data.get("match_count", 0),
            current_elo=data.get("current_elo", 1000.0),
            status=data.get("status", "provisional")
        )
    
    def update_status(self) -> None:
        """Update build status based on match count and last usage."""
        if self.match_count >= PROVISIONAL_THRESHOLD:
            self.status = "active"
        else:
            self.status = "provisional"
        
        # Check for retirement (unused for 90+ days)
        if self.last_used:
            try:
                last_date = datetime.strptime(self.last_used, "%Y-%m-%d")
                days_since = (datetime.now() - last_date).days
                if days_since > RETIRED_DAYS:
                    self.status = "retired"
            except ValueError:
                pass  # Invalid date format, keep current status


class BuildManager:
    """Manages build registry and operations."""
    
    def __init__(self, builds_path: str = BUILDS_JSON, beys_data_path: str = BEYS_DATA_JSON):
        self.builds_path = builds_path
        self.beys_data_path = beys_data_path
        self.builds: Dict[str, Build] = {}
        self.blade_to_stock_build: Dict[str, str] = {}
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.builds_path), exist_ok=True)
    
    def load_builds(self) -> None:
        """Load builds from builds.json."""
        if not os.path.exists(self.builds_path):
            print(f"{YELLOW}No builds.json found, starting fresh{RESET}")
            return
        
        try:
            with open(self.builds_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for build_data in data.get("builds", []):
                build = Build.from_dict(build_data)
                self.builds[build.build_id] = build
                
                # Track stock builds for quick lookup
                if build.is_stock:
                    self.blade_to_stock_build[build.blade] = build.build_id
            
            print(f"{GREEN}Loaded {len(self.builds)} builds from {self.builds_path}{RESET}")
            
        except json.JSONDecodeError as e:
            print(f"{RED}Error parsing builds.json: {e}{RESET}")
        except Exception as e:
            print(f"{RED}Error loading builds: {e}{RESET}")
    
    def save_builds(self) -> None:
        """Save builds to builds.json."""
        # Update all build statuses before saving
        for build in self.builds.values():
            build.update_status()
        
        data = {
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "total_builds": len(self.builds)
            },
            "builds": [build.to_dict() for build in self.builds.values()]
        }
        
        with open(self.builds_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"{GREEN}Saved {len(self.builds)} builds to {self.builds_path}{RESET}")
    
    def initialize_from_stock_beys(self) -> int:
        """
        Auto-generate stock builds from beys_data.json.
        Returns number of stock builds created.
        """
        if not os.path.exists(self.beys_data_path):
            print(f"{RED}Error: {self.beys_data_path} not found{RESET}")
            return 0
        
        try:
            with open(self.beys_data_path, 'r', encoding='utf-8') as f:
                beys_data = json.load(f)
        except Exception as e:
            print(f"{RED}Error loading beys_data.json: {e}{RESET}")
            return 0
        
        created = 0
        for bey in beys_data:
            blade = bey.get("blade")
            ratchet = bey.get("ratchet")
            bit = bey.get("bit")
            code = bey.get("code")
            
            if not all([blade, ratchet, bit]):
                print(f"{YELLOW}Skipping incomplete bey: {bey.get('name', 'Unknown')}{RESET}")
                continue
            
            # Create stock build if it doesn't exist
            build_id = f"{blade}_{ratchet}_{bit}"
            if build_id not in self.builds:
                self.builds[build_id] = Build(
                    blade=blade,
                    ratchet=ratchet,
                    bit=bit,
                    is_stock=True,
                    stock_code=code,
                    status="active"  # Stock builds start as active
                )
                self.blade_to_stock_build[blade] = build_id
                created += 1
        
        print(f"{GREEN}Created {created} stock builds{RESET}")
        return created
    
    def create_build(self, blade: str, ratchet: str, bit: str, 
                    is_stock: bool = False, stock_code: Optional[str] = None) -> str:
        """
        Create a new build or return existing build ID.
        Returns the build_id.
        """
        build_id = f"{blade}_{ratchet}_{bit}"
        
        if build_id in self.builds:
            return build_id
        
        self.builds[build_id] = Build(
            blade=blade,
            ratchet=ratchet,
            bit=bit,
            is_stock=is_stock,
            stock_code=stock_code
        )
        
        if is_stock:
            self.blade_to_stock_build[blade] = build_id
        
        return build_id
    
    def get_build(self, build_id: str) -> Optional[Build]:
        """Get build by ID."""
        return self.builds.get(build_id)
    
    def get_stock_build(self, blade: str) -> Optional[str]:
        """Get stock build ID for a blade."""
        return self.blade_to_stock_build.get(blade)
    
    def parse_build_id(self, build_id: str) -> Tuple[str, str, str]:
        """
        Parse build ID into components.
        Returns (blade, ratchet, bit).
        Raises ValueError if format is invalid.
        """
        parts = build_id.split("_")
        if len(parts) != 3:
            raise ValueError(f"Invalid build ID format: {build_id}")
        return parts[0], parts[1], parts[2]
    
    def validate_build(self, blade: str, ratchet: str, bit: str) -> bool:
        """
        Validate that build components are known/valid.
        Currently permissive - accepts any non-empty strings.
        Future: Add part registry validation.
        """
        return all([blade, ratchet, bit])
    
    def resolve_build_from_match(self, blade: str, build_id: Optional[str] = None) -> str:
        """
        Resolve build ID from match data.
        If build_id is provided, validate and use it.
        If build_id is None/empty, fall back to stock build.
        
        Returns: build_id
        Raises: ValueError if validation fails
        """
        # Case 1: No custom build specified, use stock
        if not build_id or build_id.strip() == "":
            stock_id = self.get_stock_build(blade)
            if not stock_id:
                raise ValueError(f"No stock build found for blade: {blade}")
            return stock_id
        
        # Case 2: Custom build specified, validate
        try:
            parsed_blade, ratchet, bit = self.parse_build_id(build_id)
        except ValueError as e:
            raise ValueError(f"Invalid build ID: {e}")
        
        # Verify blade matches
        if parsed_blade != blade:
            raise ValueError(f"Build blade '{parsed_blade}' doesn't match specified blade '{blade}'")
        
        # Create build if it doesn't exist (auto-register custom builds)
        if build_id not in self.builds:
            self.create_build(parsed_blade, ratchet, bit, is_stock=False)
            print(f"{CYAN}Auto-registered new custom build: {build_id}{RESET}")
        
        return build_id
    
    def update_build_usage(self, build_id: str, date: str, elo_change: float = 0) -> None:
        """
        Update build usage statistics after a match.
        
        Args:
            build_id: The build that was used
            date: Match date (YYYY-MM-DD)
            elo_change: Change in ELO (for current_elo update)
        """
        build = self.get_build(build_id)
        if not build:
            print(f"{YELLOW}Warning: Build {build_id} not found for usage update{RESET}")
            return
        
        build.match_count += 1
        build.last_used = date
        build.current_elo += elo_change
        build.update_status()
    
    def get_builds_by_blade(self, blade: str) -> List[Build]:
        """Get all builds for a specific blade."""
        return [b for b in self.builds.values() if b.blade == blade]
    
    def get_active_builds(self) -> List[Build]:
        """Get all active builds (match_count >= threshold)."""
        return [b for b in self.builds.values() if b.status == "active"]
    
    def get_build_stats(self) -> dict:
        """Get summary statistics about builds."""
        total = len(self.builds)
        stock = sum(1 for b in self.builds.values() if b.is_stock)
        custom = total - stock
        active = sum(1 for b in self.builds.values() if b.status == "active")
        provisional = sum(1 for b in self.builds.values() if b.status == "provisional")
        
        # Build diversity per blade
        blade_build_counts = defaultdict(int)
        for build in self.builds.values():
            blade_build_counts[build.blade] += 1
        
        avg_builds_per_blade = (sum(blade_build_counts.values()) / len(blade_build_counts) 
                               if blade_build_counts else 0)
        
        return {
            "total_builds": total,
            "stock_builds": stock,
            "custom_builds": custom,
            "active_builds": active,
            "provisional_builds": provisional,
            "unique_blades": len(blade_build_counts),
            "avg_builds_per_blade": round(avg_builds_per_blade, 2)
        }


def main():
    """CLI for build management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Beyblade Build Manager")
    parser.add_argument("--init", action="store_true", 
                       help="Initialize builds from beys_data.json")
    parser.add_argument("--stats", action="store_true",
                       help="Show build statistics")
    parser.add_argument("--create", nargs=3, metavar=("BLADE", "RATCHET", "BIT"),
                       help="Create a custom build")
    parser.add_argument("--list", action="store_true",
                       help="List all builds")
    parser.add_argument("--blade", type=str,
                       help="Filter builds by blade (use with --list)")
    
    args = parser.parse_args()
    
    manager = BuildManager()
    
    if args.init:
        print(f"{BOLD}Initializing builds from stock beys...{RESET}")
        manager.load_builds()  # Load existing first
        count = manager.initialize_from_stock_beys()
        manager.save_builds()
        print(f"{GREEN}✓ Initialization complete: {count} stock builds created{RESET}")
    
    elif args.stats:
        manager.load_builds()
        stats = manager.get_build_stats()
        print(f"\n{BOLD}Build Statistics:{RESET}")
        print(f"  Total Builds:     {stats['total_builds']}")
        print(f"  Stock:            {stats['stock_builds']}")
        print(f"  Custom:           {stats['custom_builds']}")
        print(f"  Active:           {stats['active_builds']}")
        print(f"  Provisional:      {stats['provisional_builds']}")
        print(f"  Unique Blades:    {stats['unique_blades']}")
        print(f"  Avg Builds/Blade: {stats['avg_builds_per_blade']}")
    
    elif args.create:
        blade, ratchet, bit = args.create
        manager.load_builds()
        build_id = manager.create_build(blade, ratchet, bit, is_stock=False)
        manager.save_builds()
        print(f"{GREEN}✓ Created build: {build_id}{RESET}")
    
    elif args.list:
        manager.load_builds()
        builds = manager.builds.values()
        
        if args.blade:
            builds = [b for b in builds if b.blade == args.blade]
        
        print(f"\n{BOLD}Builds ({len(builds)}):{RESET}")
        for build in sorted(builds, key=lambda b: (b.blade, -b.match_count)):
            stock_marker = "📦" if build.is_stock else "🔧"
            status_color = GREEN if build.status == "active" else YELLOW
            print(f"  {stock_marker} {build.build_id:40} "
                  f"ELO: {build.current_elo:4.0f} "
                  f"Matches: {build.match_count:3} "
                  f"[{status_color}{build.status}{RESET}]")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
