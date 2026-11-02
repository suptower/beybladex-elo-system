# Feature Request: Season 4 League Overhaul

## 1. Overview

Season 4 introduces a redesigned league system with three regular tiers and a separate Challenge League.

The goals are to:

* Increase the number of active Beys participating in competitive matches.
* Make regular league placements more meaningful through an additional Swiss phase.
* Establish clear promotion and relegation paths between tiers.
* Give Beys outside the regular tiers a weighted opportunity to qualify for Tier III.
* Remove Tier IV and replace it with a Qualification Pool and Challenge League.
* PSA: Any match planning/scheduling/fixtures are done by Challonge and do not need implementation.

### Season 4 structure

| Competition      |               Participants | Format                    | Matches |
| ---------------- | -------------------------: | ------------------------- | ------: |
| Tier I           |                          8 | Round Robin + Swiss       |      40 |
| Tier II          |                          8 | Round Robin + Swiss       |      40 |
| Tier III         |                          8 | Round Robin + Swiss       |      40 |
| Challenge League |                         24 | Group Swiss + Final Swiss |      48 |
| **Total**        | **48 active participants** |                           | **168** |

The Qualification Pool contains all Beys not assigned to Tier I, II, or III. From this pool, 24 Beys are selected for the Challenge League each season.

---

## 2. Regular Tiers I–III

Each regular tier contains exactly 8 Beys and consists of two phases.

### Phase 1: Round Robin

* Every Bey plays against every other Bey in its tier exactly once.
* Each Bey plays 7 matches.
* Each tier has 28 matches in total.
* The resulting standings determine the initial seeding for Phase 2.

### Phase 2: Swiss Placement Phase

* All 8 Beys participate in 3 additional Swiss rounds.
* The first-round pairings are based on the Phase 1 standings:

  * 1st vs. 2nd
  * 3rd vs. 4th
  * 5th vs. 6th
  * 7th vs. 8th
* The remaining two rounds use Swiss pairings based on the current Phase 2 standings and records.
* Pairings should avoid rematches where possible.
* Pairings/schedule will be computed via Challonge, this implementation does not need a fixture logic itself but compatibility to Challonge API JSONs.

### Scoring and final standings

* Normal league scoring applies in both phases:
  * Loss equals 0 points
  * Win equals 3 points
  * A dominant win (opponent did not score any point, e.g. 4-0, 5-0) equals 4 points
* Phase 1 and Phase 2 points are added together.
* The final tier standings are based on all 10 matches per Bey.
* These final standings determine promotion, relegation, and qualification outcomes.

Each regular tier therefore consists of **40 matches**: 28 Round Robin matches and 12 Swiss matches.

---

## 3. Promotion and Relegation

Promotion and relegation are determined by the final standings of the regular tiers. The rules below define the movement between Tier I, Tier II, and Tier III for the following season.

### Tier I ↔ Tier II

#### Tier I

| Final position | Outcome                                                      |
| -------------- | ------------------------------------------------------------ |
| 1–6            | Remain in Tier I                                             |
| 7              | Participate in a relegation match against Tier II position 2 |
| 8              | Directly relegated to Tier II                                |

#### Tier II

| Final position | Outcome                                                                     |
| -------------- | --------------------------------------------------------------------------- |
| 1              | Directly promoted to Tier I                                                 |
| 2              | Participate in a relegation match against Tier I position 7                 |
| 3–5            | Remain in Tier II                                                           |
| 6              | Participate in a relegation match against Tier III position 3               |
| 7–8            | Directly relegated to Tier III                                              |

#### Tier I–Tier II relegation match

* Tier I position 7 plays against Tier II position 2.
* The winner competes in Tier I next season.
* The loser competes in Tier II next season.

This means that Tier I position 8 and Tier II position 1 exchange tiers directly, while the remaining contested Tier I place is decided by a relegation match.

### Tier II ↔ Tier III

#### Tier II

| Final position | Outcome                                                                              |
| -------------- | ------------------------------------------------------------------------------------ |
| 1–5            | Remain in Tier II or are promoted to Tier I, according to the Tier I ↔ Tier II rules |
| 6              | Participate in a relegation match against Tier III position 3                        |
| 7–8            | Directly relegated to Tier III                                                       |

#### Tier III

| Final position | Outcome                                                      |
| -------------- | ------------------------------------------------------------ |
| 1–2            | Directly promoted to Tier II                                 |
| 3              | Participate in a relegation match against Tier II position 6 |
| 4–8            | Move to the Qualification Pool                               |

#### Tier II–Tier III relegation match

* Tier II position 6 plays against Tier III position 3.
* The winner competes in Tier II next season.
* The loser competes in Tier III next season.

The relegation match determines the final contested place between the two tiers.

### Promotion and relegation summary

* **Tier I:** Positions 1–6 remain; position 7 enters the relegation match; position 8 drops directly to Tier II.
* **Tier II:** Position 1 rises directly to Tier I; position 2 enters the Tier I relegation match; positions 3–5 remain; position 6 enters the Tier III relegation match; positions 7–8 drop directly to Tier III.
* **Tier III:** Positions 1–2 rise directly to Tier II; position 3 enters the Tier II relegation match; positions 4–8 enter the Qualification Pool.

All movement takes effect for the next season.

---

## 4. Removal of Tier IV and Qualification Pool

Tier IV is completely removed starting with Season 4.

The Qualification Pool contains all Beys that are not assigned to one of the three regular tiers after promotion and relegation have been resolved.

The following Beys enter the pool through the regular league structure:

* Tier III positions 4–8.
* All other Beys that do not occupy a Tier I, Tier II, or Tier III spot, including the former Tier IV participants.

The pool is expected to contain **34 Beys**, assuming 58 total Beys and 24 regular-tier spots. The amount will increase if new beys are added to the system in future.

### Weighted random selection

Each season, exactly 24 Beys are selected from the Qualification Pool to participate in the Challenge League. The size of the Challenge League may change in future if more total beys are added to the system, but 24 is the set size for now.

Selection must use weighted random sampling without replacement.

The selection should favor Beys with fewer relevant prior participations or matches, giving less frequently featured Beys a better chance of being selected.

A possible baseline weighting function is:

`weight = 1 / (1 + relevant_matches)`

The implementation may include configurable, modest multipliers for factors such as:

* Not having participated in the previous Challenge League.
* Having missed multiple seasons.

The weighting system should use a relevant participation counter rather than an unrestricted all-time match count. This avoids unfairly penalizing Beys that accumulated many matches while competing in the regular tiers.

Requirements:

* Exactly 24 distinct Beys must be selected.
* A Bey must not be selected more than once in the same draw.
* Selection must be reproducible when an explicit random seed is supplied, for debugging and testing.
* The weighting formula and optional bonuses should be configurable.

---

## 5. Challenge League

The Challenge League gives 24 selected Beys the opportunity to qualify for Tier III next season.

It consists of a group phase and a final Swiss phase.

### Phase 1: Group Stage

* 24 Beys are divided into 4 groups of 6.
* Each group plays 3 Swiss rounds.
* Pairings are based on the current records within each group.
* Rematches should be avoided where possible.
* The top 2 Beys from each group advance to Phase 2.

This phase produces:

* 4 groups.
* 6 Beys per group.
* 3 matches per Bey.
* 9 matches per group.
* 36 matches in total.

#### Group assignment

Group assignment should be configurable between:

* A random draw.
* ELO-based snake seeding, distributing higher- and lower-rated Beys across the groups.

The default method should be chosen explicitly in the implementation. ELO-based snake seeding is a suitable default if the goal is to balance the groups.

### Phase 2: Final Swiss Stage

* The 8 group-stage qualifiers participate in 3 additional Swiss rounds.
* All 8 qualifiers start this phase with zero points.
* Group-stage standings determine qualification only; they do not carry points into Phase 2.
* Pairings use the current Phase 2 standings and records.
* Rematches should be avoided where possible.

After the three rounds, the final standings determine qualification for Tier III next season.

| Final position | Outcome                          |
| -------------- | -------------------------------- |
| 1–5            | Qualify for Tier III next season |
| 6–8            | Return to the Qualification Pool |

### Challenge League match volume

| Phase             | Matches |
| ----------------- | ------: |
| Group Stage       |      36 |
| Final Swiss Stage |      12 |
| **Total**         |  **48** |

Each Challenge League participant plays 3 matches in the group stage. The 8 qualifiers play 3 additional matches in Phase 2.

---

## 6. Season Flow

The season should follow this logical sequence:

1. Complete the Round Robin and Swiss placement phases in Tiers I–III.
2. Finalize the regular-tier standings.
3. Resolve direct promotions and relegations.
4. Play the Tier I–Tier II and Tier II–Tier III relegation matches.
5. Determine the final tier assignments for the next season.
6. Build the Qualification Pool from all Beys outside the three regular tiers.
7. Select 24 Beys from the pool using weighted random sampling without replacement.
8. Assign the 24 selected Beys to the Challenge League groups.
9. Complete the three-round group stage.
10. Advance the top 2 Beys from each group to the Final Swiss Stage.
11. Complete the three-round Final Swiss Stage.
12. Promote the top 5 Challenge League finishers to Tier III next season.
13. Return Challenge League positions 6–8 to the Qualification Pool for the next season.

The implementation must ensure that all final tier assignments are consistent and that no Bey occupies more than one regular-tier slot.

---

## 7. Match Volume and Participation

### Regular leagues

| Tier      | Round Robin | Swiss Phase |   Total |
| --------- | ----------: | ----------: | ------: |
| Tier I    |          28 |          12 |      40 |
| Tier II   |          28 |          12 |      40 |
| Tier III  |          28 |          12 |      40 |
| **Total** |      **84** |      **36** | **120** |

### Challenge League

| Phase             | Matches |
| ----------------- | ------: |
| Group Stage       |      36 |
| Final Swiss Stage |      12 |
| **Total**         |  **48** |

### Season total

| Metric                        |   Value |
| ----------------------------- | ------: |
| Regular league matches        |     120 |
| Challenge League matches      |      48 |
| **Total matches per season**  | **168** |
| Regular-tier participants     |      24 |
| Challenge League participants |      24 |
| **Total active participants** |  **48** |

Compared with the previous structure of four 8-Bey tiers with 28 Round Robin matches each, the new system increases the regular and Challenge League match volume while removing Tier IV.

---

## 8. Conceptual Structure

```text
                  ┌─────────────┐
                  │   Tier I    │
                  │   8 Beys    │
                  └──────┬──────┘
                         │
              ┌──────────┴──────────┐
              │                     │
       Position 8 drops      Position 7 plays
              │               relegation match
              ▼                     │
                  ┌─────────────┐   │
                  │   Tier II   │◄──┘
                  │   8 Beys    │
                  └──────┬──────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
      Positions       Position 6    Positions
         7–8          relegation      1–2
          │             match          │
          ▼              │             ▼
                  ┌─────────────┐
                  │  Tier III   │
                  │   8 Beys    │
                  └──────┬──────┘
                         │
                   Positions 4–8
                         │
                         ▼
              ┌────────────────────┐
              │  Qualification     │
              │  Pool – 34 Beys    │
              └─────────┬──────────┘
                        │
                Weighted random
                   selection
                        │
                        ▼
              ┌────────────────────┐
              │  Challenge League  │
              │      24 Beys       │
              └─────────┬──────────┘
                        │
                   4 groups of 6
                        │
                  3 Swiss rounds
                        │
                 Top 2 per group
                        │
                        ▼
                     8 Beys
                        │
                  3 Swiss rounds
                        │
                     Top 5
                        │
                        ▼
                     Tier III
```

---

## 9. Implementation Requirements

* Remove all Tier IV-specific season logic and replace it with Qualification Pool logic.
* Implement the new Round Robin + Swiss format for Tiers I–III.
* Calculate final regular-tier standings using the combined points from both phases.
* Implement direct promotion and relegation according to the final standings.
* Implement both relegation matches and apply their outcomes to next-season tier assignments.
* Ensure that Tier II position 6 and Tier III position 3 are handled consistently in the Tier II–Tier III relegation match.
* Implement weighted random sampling without replacement for the Qualification Pool.
* Keep selection weights, participation counters, and optional bonuses configurable.
* Implement the Challenge League group stage and Final Swiss Stage.
* Reset Challenge League Phase 2 points to zero.
* Promote the top 5 Challenge League finishers to Tier III for the next season.
* Return Challenge League positions 6–8 to the Qualification Pool.
* Prevent duplicate assignments and enforce exactly 8 Beys per regular tier.
* Add tests for tier transitions, relegation match outcomes, pool construction, weighted selection, group qualification, and final Challenge League qualification.
* Ensure the season-generation process can be rerun deterministically for debugging when a random seed is supplied.

## 10. Acceptance Criteria

* [ ] Tiers I–III each contain exactly 8 Beys.
* [ ] Each regular tier plays 28 Round Robin matches and 12 Swiss matches.
* [ ] Each Bey in a regular tier plays 10 matches across both phases.
* [ ] Phase 1 and Phase 2 points contribute to the same final tier standings.
* [ ] Tier I position 8 is directly relegated to Tier II.
* [ ] Tier II position 1 is directly promoted to Tier I.
* [ ] Tier I position 7 and Tier II position 2 play a relegation match.
* [ ] The winner of the Tier I–Tier II relegation match plays in Tier I next season; the loser plays in Tier II.
* [ ] Tier II positions 7–8 are directly relegated to Tier III.
* [ ] Tier III positions 1–2 are directly promoted to Tier II.
* [ ] Tier II position 6 and Tier III position 3 play a relegation match.
* [ ] The winner of the Tier II–Tier III relegation match plays in Tier II next season; the loser plays in Tier III.
* [ ] Tier III positions 4–8 enter the Qualification Pool.
* [ ] Exactly 24 distinct Beys are selected from the Qualification Pool.
* [ ] The Challenge League contains 4 groups of 6 Beys.
* [ ] Each group plays 3 Swiss rounds, with the top 2 advancing.
* [ ] The 8 qualifiers play 3 additional Swiss rounds starting from zero points.
* [ ] The top 5 Challenge League finishers qualify for Tier III next season.
* [ ] Challenge League positions 6–8 return to the Qualification Pool.
* [ ] The season contains 168 matches under the specified format.
* [ ] No Bey is assigned to more than one regular tier or occupies duplicate slots.
* [ ] Automated tests cover promotion, relegation, selection, and qualification edge cases.

---

## 11. Open Implementation Decisions

The following details should be confirmed during implementation rather than silently assumed:

* The exact tie-breaking rules for equal final league points.
* Whether the group assignment default is random or ELO-based snake seeding.
* The final weighting formula and the exact definition of relevant prior participation.
* The handling of missing Beys, forfeits, or incomplete match results.
* The scheduling and tie-breaking procedure for relegation matches.
* Whether relegation matches are played as standalone matches or use an existing match format.
