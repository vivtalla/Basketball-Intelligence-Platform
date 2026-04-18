# MVP Tracker Methodology Brief — v3 Refined

Last updated: 2026-04-18

This is the canonical methodology for the refined MVP tracker. The tracker separates the MVP race into four layers: Basketball Value, Award Case, Context and Confidence, and Structured Analyst Lenses.

## Core Principle

One score should not answer every MVP question. A player can have the best on-court regular season while carrying a weaker real-world ballot case because of missed games, team standing, clutch sample, or narrative momentum. The v3 tracker therefore exposes two primary scores:

- **Basketball Value Score**: season-long on-court value.
- **Award Case Score**: MVP candidacy under voter-facing award logic.

The main leaderboard rank is Award Case Rank. Basketball Value Rank remains visible so users can separate “best basketball season” from “strongest MVP candidacy.”

## Layer 1: Basketball Value Score

Basketball Value answers: **How strong has this player’s regular season been on the court?**

Weights:

| Pillar | Weight | Purpose |
|---|---:|---|
| Impact | 30% | Overall on-court value from independent impact signals |
| Efficiency | 20% | Scoring quality under load and against stronger contexts |
| Scoring Load | 15% | Volume and burden of scoring creation |
| Playmaking Load | 10% | Creation, assist value, and turnover control |
| Team Value | 15% | Winning value tied to the player’s participation |
| Availability | 10% | Games, qualified games, and minutes reliability |

Implementation notes:

- Impact prioritizes EPM, LEBRON, RAPTOR, PIPM, DARKO, and RAPM when present, with BPM/on-off as reduced-confidence fallback or diagnostic support.
- Efficiency combines TS%, eFG%, usage-adjusted TS%, opponent-adjusted TS where sample allows, and turnover penalty.
- Scoring Load uses PPG, usage, and usage-adjusted efficiency.
- Playmaking Load uses APG, assist-to-turnover, and turnover control.
- Team Value prefers candidate game W-L, on-court net, and reliable on/off before full-team record.
- Availability is explicit so cumulative metrics do not silently double-count it.

## Layer 2: Award Case Score

Award Case answers: **How strong is this player’s actual MVP candidacy?**

Formula:

```text
Award Case Score = Basketball Value Score + capped award modifiers
```

Award modifiers:

- Team framing
- Eligibility pressure
- Clutch
- Momentum
- Signature games

Modifiers are capped and moderate. They can move rankings meaningfully, but they should not overwhelm the base Basketball Value Score.

Eligibility policy:

- Eligibility does not erase Basketball Value.
- The tracker exposes Basketball Value Rank, Award Case Rank, and Ballot-Eligible Rank.
- At-risk and ineligible players receive Award Case pressure, not a hidden deletion from the basketball model.

Clutch policy:

- Clutch belongs in Award Case, not Basketball Value.
- It is split conceptually into clutch volume, clutch efficiency, and result impact.
- Confidence scaling remains required because clutch samples are volatile.

Momentum policy:

- Momentum should use last-5 and last-10 context.
- Hot/cold labels should align with full momentum, not only PPG delta.
- Momentum influence remains capped.

Signature game policy:

- Signature games are award evidence, not a core season-value pillar.
- Leverage blends production, opponent strength, efficiency, win result, and plus-minus.
- Future versions should add head-to-head candidate games and late-season stakes when reliable.

## Layer 3: Context And Confidence

Context signals explain the case without heavily driving the main rank.

Context signals include:

- Gravity
- Support burden
- Opponent context
- Play-style translation
- Metric disagreement
- Coverage quality
- Sample-size confidence

Gravity remains context-first. The capped context-adjusted score may show how off-box-score attention changes interpretation, but Gravity should not heavily alter the default leaderboard until source coverage is more stable.

Every major candidate exposes a confidence object:

- Overall confidence: high, medium, or low
- Coverage score
- Sample stability score
- Signal agreement score
- Short notes explaining weak spots

Confidence is derived from data coverage, sample size, and disagreement among independent signals.

## Layer 4: Structured Analyst Lenses

Every major candidate should be interpreted through the same qualitative lenses:

- **Role Difficulty**: how hard the player’s offensive and defensive job is.
- **Scalability**: how portable the player’s value looks across lineups and roster constructions.
- **Game Control**: how much the player shapes creation, pace, late-clock pressure, and late-game command.
- **Two-Way Pressure**: how much stress the player creates offensively while adding defensive utility.
- **Playoff Translation**: which parts of the regular-season case are likely to hold up against elite competition.

These lenses do not override the quantitative model. They turn evidence into disciplined interpretation.

## Voter Timeline

The Voter Timeline remains a dated reconstruction from weekly game-log cutoffs.

Current mode:

- **Value-driven weekly reconstruction**
- Uses game logs only at each cutoff.
- Scores production, TS%, availability, candidate game W-L, and last-five momentum.

Future mode:

- **Voter-style ballot simulation**
- Add ballot points such as 10-7-5-3-1.
- Add dynamic early-season minimum-game thresholds.
- Add movement tags and race-state explanations.

Historical impact, Gravity, clutch, and opponent-adjusted values should remain out of historical scoring until dated source rows are persisted.

## UI Policy

The `/mvp` page should show three coordinated views:

| View | Purpose |
|---|---|
| Leaderboard | Fast snapshot with Award Case, Basketball Value, confidence, and eligibility |
| Case Breakdown | Transparent pillars, modifiers, context labels, and uncertainty |
| Analyst Lenses | Structured qualitative interpretation |

Old `box_first`, `balanced`, and `impact_consensus` profile comparisons remain useful, but they are sensitivity tools rather than the primary model.

## Labeling Policy

Every displayed metric should be identifiable as one of:

- **Core Score Input**
- **Award Modifier**
- **Context Signal**
- **Qualitative Lens**

This prevents users from confusing explanatory context with direct scoring weight.

## Implementation Defaults

- Main leaderboard rank: Award Case Rank.
- Main score shown on cards: Award Case Score.
- Secondary score shown on cards: Basketball Value Score.
- Legacy profile comparison: sensitivity chart only.
- Gravity: capped context adjustment, not a main pillar.
- Support burden: context signal for v3, candidate for future formal sub-score.
- Opponent-adjusted TS: part of Efficiency when sample allows.
- No database migration is required for v3 because existing season stats, game logs, on/off, clutch, opponent, Gravity, and play-by-play-derived context provide the first-pass inputs.

