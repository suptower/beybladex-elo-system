# Non-Stock Beyblade Combinations: Design Document

## Executive Summary

This document outlines the technical design for extending the BeybladeX ELO system to support tracking, analyzing, and ranking **non-stock Beyblade combinations** (custom Blade + Ratchet + Bit setups) while maintaining full backward compatibility with the existing stock-only workflow.

**Version:** 1.0  
**Date:** 2026-01-08  
**Status:** Approved for Implementation

---

## 1. Goals and Non-Goals

### Goals
1. ✅ Enable tracking of custom Beyblade combinations (Blade + Ratchet + Bit)
2. ✅ Maintain 100% backward compatibility with stock Bey workflow
3. ✅ Avoid data explosion or heavy duplication
4. ✅ Support hierarchical aggregation (Build → Blade → Part)
5. ✅ Keep stock-only usage simple and unchanged
6. ✅ Provide foundation for future part-level analysis

### Non-Goals
- Full part-balance simulation (initially)
- Manual tracking overhead for every possible combination
- Replacing stock Beys as the primary leaderboard entity
- UI changes in this phase (design is backend-first)
- Automatic legality/format validation

---

## 2. Current System Analysis

### 2.1 Existing Data Model

**beys_data.json** - Static registry of stock Beyblades:
```json
{
  "code": "BX-20",
  "name": "DranDagger 4-60R",
  "blade": "DranDagger",
  "ratchet": "4-60",
  "bit": "Rush",
  "type": "Attack"
}
```

**matches.csv** - Match records reference Bey by blade name:
```csv
MatchID,Date,BeyA,BeyB,ScoreA,ScoreB
M0001,2025-09-07,DranDagger,FoxBrush,4,2
```

**Key Insight:** Currently, matches reference the **blade name** directly. The system treats each blade as having a fixed stock configuration.

### 2.2 Current Limitations
1. **1:1 Blade-to-Configuration**: Each blade name implies exactly one ratchet/bit combo
2. **No Custom Tracking**: Custom builds are invisible to the system
3. **Limited Part Analysis**: Part stats exist but aren't connected to performance data
4. **Missed Insights**: No data on part synergies or meta shifts from custom builds

---

## 3. Proposed Architecture

### 3.1 Core Concept: Build Entity

Introduce a **Build** (or **Loadout**) as a first-class entity that represents any Blade + Ratchet + Bit combination.

```
┌─────────────┐
│    Build    │ ◄── Primary entity for matches
├─────────────┤
│ build_id    │ ← "DranDagger_4-60_Rush" (stock)
│ blade       │ ← "DranDagger"
│ ratchet     │ ← "4-60"
│ bit         │ ← "Rush"
│ is_stock    │ ← true/false
└─────────────┘
```

### 3.2 Build ID Format

**Pattern:** `{Blade}_{Ratchet}_{Bit}`

**Examples:**
- Stock: `DranDagger_4-60_Rush`
- Custom: `DranDagger_5-80_Elevate`
- Custom: `FoxBrush_9-70_LowRush`

**Rationale:**
- Human-readable
- Unique identifier
- Easy parsing
- URL-safe (for future web usage)

### 3.3 Data Model Extensions

#### 3.3.1 New File: `builds.json`

Central registry of all observed builds (stock + custom):

```json
{
  "builds": [
    {
      "build_id": "DranDagger_4-60_Rush",
      "blade": "DranDagger",
      "ratchet": "4-60",
      "bit": "Rush",
      "is_stock": true,
      "stock_code": "BX-20",
      "first_seen": "2025-09-07",
      "match_count": 42
    },
    {
      "build_id": "DranDagger_5-80_Elevate",
      "blade": "DranDagger",
      "ratchet": "5-80",
      "bit": "Elevate",
      "is_stock": false,
      "stock_code": null,
      "first_seen": "2025-12-15",
      "match_count": 8
    }
  ]
}
```

**Key Fields:**
- `build_id`: Unique identifier
- `is_stock`: Distinguishes stock vs custom
- `stock_code`: Links to original beys_data.json entry
- `first_seen`: Track meta evolution
- `match_count`: Quick filter for statistical relevance

#### 3.3.2 Extended `matches.csv`

**Option A: Backward-Compatible Extension** (RECOMMENDED)

Add optional `BuildA` and `BuildB` columns. If empty, fall back to blade name = stock build.

```csv
MatchID,Date,BeyA,BeyB,ScoreA,ScoreB,BuildA,BuildB
M0001,2025-09-07,DranDagger,FoxBrush,4,2,,
M0002,2025-09-07,DranDagger,ImpactDrake,2,5,DranDagger_5-80_Elevate,
M0003,2025-12-15,DranDagger,DranDagger,4,1,DranDagger_5-80_Elevate,DranDagger_4-60_Rush
```

**Parsing Rules:**
1. If `BuildA` is empty → use stock build for `BeyA` blade
2. If `BuildA` is present → use specified build
3. Blade name validation: Extract blade from build_id and compare with `BeyA`

**Migration Path:**
- Existing matches continue to work (BuildA/BuildB empty)
- No data rewriting required
- Graceful degradation for old data

**Option B: Separate File** (Alternative)

Keep `matches.csv` unchanged, create `matches_builds.csv` for custom builds only.

**Decision:** Use Option A for simplicity and unified data pipeline.

#### 3.3.3 Extended `leaderboard.csv`

Add build-level rankings alongside blade rankings:

```csv
Rank,Entity,EntityType,Elo,Wins,Losses,WinRate,Matches
1,PhoenixWing,blade,1245,28,12,0.700,40
2,PhoenixWing_3-60_Point,build,1238,15,5,0.750,20
3,DranSword,blade,1210,25,15,0.625,40
4,PhoenixWing_3-70_HighTaper,build,1198,8,4,0.667,12
...
```

**EntityType Values:**
- `blade`: Aggregated stats across all builds of this blade
- `build`: Stats for specific build

**Default View:** Show only `blade` rows (preserves current UX)  
**Advanced View:** Include `build` rows (new analysis capability)

---

## 4. ELO Strategy

### 4.1 Chosen Approach: Blade-Anchored with Build Divergence (Hybrid)

**Rationale:** Balance between accuracy and data requirements.

#### 4.1.1 Core Principles

1. **Blade Base ELO**: Each blade has a canonical ELO (aggregated from all its builds)
2. **Build Initialization**: New custom builds start near their blade's current ELO
3. **Independent Tracking**: Each build maintains its own ELO that can diverge
4. **Hierarchical Aggregation**: Blade ELO = weighted average of all its builds

#### 4.1.2 Detailed Algorithm

**Step 1: Initialize Build ELO**
```python
def initialize_build_elo(build_id, blade_elo, is_stock):
    if is_stock:
        return blade_elo  # Stock builds directly reflect blade ELO
    else:
        # Custom builds start slightly below blade ELO
        # Rationale: Unproven combos should "earn" their rating
        return blade_elo - 25
```

**Step 2: Match Processing**
```python
def process_match(build_a, build_b, score_a, score_b):
    # Both builds have independent ELOs
    elo_a = builds[build_a].elo
    elo_b = builds[build_b].elo
    
    # Standard ELO calculation with dominance scaling
    new_elo_a, new_elo_b = calculate_elo(elo_a, elo_b, score_a, score_b)
    
    # Update build ELOs
    builds[build_a].elo = new_elo_a
    builds[build_b].elo = new_elo_b
    
    # Aggregate to blade level
    update_blade_elo(builds[build_a].blade)
    update_blade_elo(builds[build_b].blade)
```

**Step 3: Blade Aggregation**
```python
def update_blade_elo(blade_name):
    # Weighted average of all builds for this blade
    blade_builds = [b for b in builds.values() if b.blade == blade_name]
    
    total_weight = 0
    weighted_sum = 0
    
    for build in blade_builds:
        weight = build.match_count ** 0.5  # Square root weighting
        weighted_sum += build.elo * weight
        total_weight += weight
    
    blade_elo[blade_name] = weighted_sum / total_weight if total_weight > 0 else START_ELO
```

#### 4.1.3 Statistical Relevance Threshold

Builds with < 5 matches are marked as "provisional" and excluded from main leaderboard rankings.

**Rationale:** Prevents leaderboard clutter from single-use experimental builds.

### 4.2 Alternative Approaches (Evaluated but Deferred)

**Option A: Independent Build ELO (Most Accurate)**
- Each build completely independent
- **Pros:** Most accurate for established builds
- **Cons:** High data requirements, cold start problem for new builds
- **Status:** Deferred - consider if data volume increases significantly

**Option B: Blade ELO + Part Modifiers (Predictive)**
- Blade base + learned modifiers for ratchet/bit
- **Pros:** Can predict new combos, lower data needs
- **Cons:** Assumes additive part effects (not always true)
- **Status:** Future extension after sufficient custom build data

---

## 5. Migration Strategy

### 5.1 Backward Compatibility Requirements

1. **Zero Breaking Changes**: Existing matches.csv must continue to work
2. **Stock Workflow Unchanged**: Default data entry remains simple
3. **Opt-in Complexity**: Custom builds are optional, not mandatory

### 5.2 Migration Steps

**Phase 1: Data Structure Setup**
1. Create `builds.json` with auto-generated stock builds
2. Add `BuildA`/`BuildB` columns to matches.csv schema (optional)
3. Update `beys_data.json` to include all unique blades

**Phase 2: Code Updates**
1. Extend `beyblade_elo.py` to read BuildA/BuildB columns
2. Add build resolution logic (BuildA → blade + ratchet + bit)
3. Update leaderboard generation to include build-level rows
4. Modify stats aggregation to support hierarchical views

**Phase 3: Auto-Migration**
```python
def migrate_stock_builds():
    """Generate stock builds from beys_data.json"""
    builds = []
    for bey in load_beys_data():
        build_id = f"{bey['blade']}_{bey['ratchet']}_{bey['bit']}"
        builds.append({
            "build_id": build_id,
            "blade": bey["blade"],
            "ratchet": bey["ratchet"],
            "bit": bey["bit"],
            "is_stock": True,
            "stock_code": bey["code"]
        })
    save_builds(builds)
```

**Phase 4: Testing**
1. Run existing test suite (must pass 100%)
2. Run ELO pipeline on historical data (compare results)
3. Validate stock-only matches produce identical output

### 5.3 Rollback Plan

If issues arise:
1. Revert code changes
2. Remove `BuildA`/`BuildB` columns from new matches
3. `builds.json` can remain (ignored by old code)
4. No data loss (original matches.csv intact)

---

## 6. Data Entry and UX Considerations

### 6.1 Quick Entry Workflow

**Stock Match (No Changes):**
```
1. Select BeyA: "DranDagger"
2. Select BeyB: "FoxBrush"
3. Enter scores: 4-2
→ Writes: MatchID,Date,BeyA,BeyB,ScoreA,ScoreB,BuildA,BuildB
           M1234,2025-12-15,DranDagger,FoxBrush,4,2,,
```

**Custom Build Match (Optional Override):**
```
1. Select BeyA: "DranDagger"
2. [Toggle "Custom Build"] ← NEW
3. Override Ratchet: "5-80" (dropdown)
4. Override Bit: "Elevate" (dropdown)
5. Select BeyB: "FoxBrush" (stock)
6. Enter scores: 4-2
→ Writes: M1234,2025-12-15,DranDagger,FoxBrush,4,2,DranDagger_5-80_Elevate,
```

**Key Points:**
- Default workflow unchanged
- Custom builds are **opt-in** per match
- Dropdowns populated from known parts (via beys_data.json + builds.json)
- Build ID auto-generated from selections

### 6.2 UI Display Format

**Leaderboard Entry:**
```
┌────────────────────────────────────────┐
│ 🥇 #1  PhoenixWing          1245 ELO  │ ← Blade view (default)
│ 📊 Stock: 3-60 Point                  │
├────────────────────────────────────────┤
│ [Show builds ▼]                        │ ← Expandable
│   └─ 3-60 Point:      1238 (20 matches)│ ← Build details
│   └─ 3-70 HighTaper:  1198 (12 matches)│
└────────────────────────────────────────┘
```

**Match History:**
```
Match M1234 | 2025-12-15
DranDagger [5-80 Elevate] vs FoxBrush [Stock]
4-2
```

### 6.3 Data Validation

**Rules:**
1. Blade must exist in `beys_data.json` (known blades)
2. Ratchet must exist in known parts list
3. Bit must exist in known parts list
4. Build ID format must match `{Blade}_{Ratchet}_{Bit}`

**Error Handling:**
- Invalid build → reject match entry with error message
- Unknown parts → prompt to add to parts registry
- Mismatched blade in build ID → validation error

---

## 7. Hierarchical Aggregation

### 7.1 Aggregation Levels

```
Part Level (Future)
    ↓
Blade Level (New)
    ↓
Build Level (Atomic)
    ↓
Match Level (Raw Data)
```

### 7.2 Statistics Per Level

**Build Level (Most Precise):**
- ELO rating
- Wins/Losses
- Win rate
- Average score differential
- Head-to-head records
- First seen date
- Last used date
- Match count

**Blade Level (Current + Enhanced):**
- Aggregated ELO (weighted avg of builds)
- Total wins/losses (sum of all builds)
- Most popular build (by match count)
- Build diversity metric (# unique builds used)
- Stock vs custom usage ratio

**Part Level (Future Extension):**
- Ratchet performance across all blades
- Bit performance across all blades
- Part synergy scores (Blade-Bit, Blade-Ratchet)

### 7.3 Query Examples

**Q1: "How does DranDagger perform overall?"**
- Return blade-level stats (all builds aggregated)

**Q2: "What's the best build for DranDagger?"**
- Return all DranDagger builds sorted by ELO
- Filter: match_count >= 5 (statistical relevance)

**Q3: "Does Elevate bit improve Attack blades?"**
- Future: Aggregate all builds using Elevate on Attack-type blades
- Compare to average ELO of those blades with other bits

---

## 8. Implementation Plan

### 8.1 Phase 1: Foundation (Week 1)
- ✅ Create design document (this document)
- [ ] Add `builds.json` schema and sample data
- [ ] Extend matches.csv with BuildA/BuildB columns
- [ ] Auto-generate stock builds from beys_data.json
- [ ] Update beyblade_elo.py to parse builds
- [ ] Add build resolution logic (ID → components)

### 8.2 Phase 2: ELO Integration (Week 2)
- [ ] Implement build-level ELO tracking
- [ ] Add blade aggregation logic
- [ ] Update leaderboard generation (build + blade rows)
- [ ] Add statistical relevance filtering
- [ ] Test with historical data (verify no regressions)

### 8.3 Phase 3: Testing & Validation (Week 3)
- [ ] Write unit tests for build parsing
- [ ] Write integration tests for ELO calculation
- [ ] Run full pipeline on test data
- [ ] Compare stock-only results (must match existing)
- [ ] Validate custom build scenarios

### 8.4 Phase 4: Documentation (Week 4)
- [ ] Update README with build tracking info
- [ ] Add migration guide for existing users
- [ ] Create example matches with custom builds
- [ ] Document data entry workflow
- [ ] Add FAQ section

### 8.5 Future Phases (Post-Launch)
- [ ] Add build quick-select UI widget
- [ ] Implement part-level statistics
- [ ] Add synergy heatmaps (Blade-Bit, Blade-Ratchet)
- [ ] Build recommendation engine
- [ ] Meta diversity metrics (stock vs custom usage)

---

## 9. Open Questions & Decisions

### 9.1 Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| How to store builds? | New `builds.json` file | Clean separation, no data duplication |
| ELO strategy? | Blade-anchored with build divergence | Balances accuracy and data needs |
| Match format? | Extend matches.csv with optional columns | Backward compatible, simple migration |
| Stock workflow impact? | Zero changes | Critical for adoption |

### 9.2 Open Questions (To Be Resolved)

1. **Build Display Name Format**
   - Current: "DranDagger_5-80_Elevate"
   - Alternative: "DranDagger [5-80E]" (compact)
   - **Decision needed by:** Phase 2 start

2. **Provisional Build Threshold**
   - Current: 5 matches minimum
   - Alternative: Adaptive based on total dataset size
   - **Decision needed by:** Phase 2 start

3. **Part Registry Source**
   - Current: Extract from beys_data.json
   - Alternative: Separate parts.json file
   - **Decision needed by:** Phase 1 completion

4. **Build Legality Validation**
   - Current: No validation (all parts compatible)
   - Future: Format-specific rules (e.g., X blades only with X bits)
   - **Decision needed by:** Post-launch (if needed)

---

## 10. Success Metrics

### 10.1 Technical Metrics
- ✅ 100% backward compatibility (all existing tests pass)
- ✅ Zero performance degradation (pipeline runtime < 5% increase)
- ✅ No data loss during migration
- ✅ Stock-only workflow requires zero additional steps

### 10.2 Usage Metrics (Post-Launch)
- % of matches using custom builds
- Number of unique builds observed
- Build diversity per blade (avg builds per blade)
- Custom build win rate vs stock

### 10.3 Quality Metrics
- ELO accuracy (predicted vs actual match outcomes)
- Build statistical relevance (% builds with >= 5 matches)
- User error rate (invalid build entries)

---

## 11. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking changes to existing workflow | High | Low | Comprehensive testing, feature flags |
| Performance degradation | Medium | Low | Profiling, optimization, caching |
| Data inconsistency | High | Medium | Validation rules, schema enforcement |
| User confusion | Medium | Medium | Clear documentation, default to stock |
| Leaderboard clutter | Low | High | Statistical relevance filtering |

---

## 12. Appendices

### 12.1 Example Builds JSON

```json
{
  "metadata": {
    "version": "1.0",
    "last_updated": "2025-12-15",
    "total_builds": 127
  },
  "builds": [
    {
      "build_id": "DranDagger_4-60_Rush",
      "blade": "DranDagger",
      "ratchet": "4-60",
      "bit": "Rush",
      "is_stock": true,
      "stock_code": "BX-20",
      "first_seen": "2025-09-07",
      "last_used": "2025-12-14",
      "match_count": 42,
      "current_elo": 1210
    },
    {
      "build_id": "DranDagger_5-80_Elevate",
      "blade": "DranDagger",
      "ratchet": "5-80",
      "bit": "Elevate",
      "is_stock": false,
      "stock_code": null,
      "first_seen": "2025-12-10",
      "last_used": "2025-12-14",
      "match_count": 8,
      "current_elo": 1195,
      "status": "provisional"
    }
  ]
}
```

### 12.2 Code Snippet: Build Resolution

```python
def resolve_build(match_row):
    """
    Resolve build from match row.
    Falls back to stock if BuildA/BuildB not specified.
    """
    bey_a = match_row["BeyA"]
    bey_b = match_row["BeyB"]
    
    # Check for custom builds
    build_a = match_row.get("BuildA") or get_stock_build(bey_a)
    build_b = match_row.get("BuildB") or get_stock_build(bey_b)
    
    # Validate blade matches
    if not build_a.startswith(bey_a + "_"):
        raise ValueError(f"Build {build_a} doesn't match blade {bey_a}")
    
    return build_a, build_b

def get_stock_build(blade_name):
    """Get stock build ID for a blade."""
    bey_data = find_bey_by_blade(blade_name)
    return f"{blade_name}_{bey_data['ratchet']}_{bey_data['bit']}"
```

### 12.3 Migration Script Outline

```python
# migrate_to_builds.py
def migrate():
    print("=== Build System Migration ===")
    
    # Step 1: Generate stock builds
    print("Generating stock builds from beys_data.json...")
    stock_builds = generate_stock_builds()
    save_builds(stock_builds)
    print(f"✓ Created {len(stock_builds)} stock builds")
    
    # Step 2: Extend matches.csv schema
    print("Extending matches.csv with build columns...")
    add_build_columns_to_matches()
    print("✓ Schema updated (existing matches unchanged)")
    
    # Step 3: Verify backward compatibility
    print("Running validation tests...")
    run_validation_tests()
    print("✓ All tests passed")
    
    # Step 4: Run ELO pipeline
    print("Recalculating ELO with build support...")
    run_elo_pipeline()
    print("✓ Pipeline complete")
    
    print("\n=== Migration Complete ===")
    print("- Stock builds: Ready")
    print("- Custom builds: Ready for entry")
    print("- Existing data: Unchanged")
```

---

## 13. Conclusion

This design provides a **robust, scalable, and backward-compatible** foundation for tracking non-stock Beyblade combinations. The blade-anchored ELO approach with build divergence balances statistical accuracy with practical data requirements, while the hierarchical aggregation model enables flexible analysis at multiple levels.

**Key Strengths:**
1. **Zero disruption** to existing stock-only workflow
2. **Incremental adoption** - custom builds are opt-in
3. **Future-proof** - foundation for part-level analysis
4. **Data integrity** - comprehensive validation and migration
5. **Scalable** - handles both small and large datasets efficiently

**Next Steps:**
1. Review and approve design document
2. Begin Phase 1 implementation (foundation)
3. Set up test environment with sample custom builds
4. Iterate based on early testing feedback

---

**Document Revision History:**
- v1.0 (2026-01-08): Initial design document
