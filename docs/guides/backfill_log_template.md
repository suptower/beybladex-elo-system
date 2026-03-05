# Backfill Log Template

Use this template to track which tournaments and matches have been backfilled with per-round finish type data.

## Template Format

```markdown
# Backfill Log

## Summary
| Metric | Value |
|--------|-------|
| Total Tournaments Backfilled | X |
| Total Matches Backfilled | X |
| Last Updated | YYYY-MM-DD |

---

## Tournament: [Tournament Name]

### Metadata
| Field | Value |
|-------|-------|
| Tournament ID | T001 |
| Original Date | 2025-09-07 |
| Backfill Date | YYYY-MM-DD |
| Backfilled By | [Name/Username] |
| Data Source | [Video replay / Memory / Partial notes] |

### Matches Backfilled
| Match ID | Bey A | Bey B | Rounds Added | Confidence |
|----------|-------|-------|--------------|------------|
| M001 | ViperTail | WizardArc | 4 | High |
| M002 | SamuraiSaber | TuskMammoth | 3 | Medium |

### Assumptions Made
- Unknown finish types defaulted to "spin"
- [Any other assumptions specific to this tournament]

### Notes
- [Any relevant notes about the backfill process]
- [Data quality issues encountered]
- [Matches that couldn't be backfilled and why]

---

## Tournament: [Next Tournament Name]

[Repeat structure above]

---
```

## Field Descriptions

### Confidence Levels

| Level | Description |
|-------|-------------|
| **High** | Based on video review or reliable written records |
| **Medium** | Based on partial video/notes plus reasonable inference |
| **Low** | Based primarily on memory or very limited records |

### Data Sources

Common data sources for backfilling:

| Source | Typical Confidence |
|--------|-------------------|
| Full video recording | High |
| Partial video clips | Medium-High |
| Written scorecards | Medium-High |
| Social media posts | Medium |
| Personal memory | Low-Medium |
| No records | Low (default to spin) |

## Example Backfill Log Entry

```markdown
## Tournament: BeybladeX Regional Championship

### Metadata
| Field | Value |
|-------|-------|
| Tournament ID | BXR2025-01 |
| Original Date | 2025-09-07 |
| Backfill Date | 2025-10-15 |
| Backfilled By | @organizer_name |
| Data Source | Video replay + scorekeeper notes |

### Matches Backfilled
| Match ID | Bey A | Bey B | Rounds Added | Confidence |
|----------|-------|-------|--------------|------------|
| BXR-001 | ViperTail | WizardArc | 6 | High |
| BXR-002 | DranBrave | HellsReaper | 5 | High |
| BXR-003 | FoxBrush | DranBuster | 5 | Medium |
| BXR-004 | PhoenixWing | SharkEdge | 4 | Medium |

### Assumptions Made
- Rounds 2-3 of BXR-003 had unclear video, defaulted to "spin"
- BXR-004 round 1 finish type uncertain, marked as "spin"

### Notes
- Video quality was poor for some group stage matches
- Finals matches have complete round-by-round data
- 3 preliminary matches could not be backfilled (no footage)
```

## Best Practices

1. **Be consistent**: Use the same format for all backfill entries
2. **Document assumptions**: Always note when you've defaulted to "spin"
3. **Record confidence**: This helps future analysis understand data quality
4. **Date your work**: Track when backfills were done
5. **Credit contributors**: Note who did the backfill work
6. **Keep originals**: Maintain the original data before backfill changes
