# Gold error direction (Claude coder vs experts)

**PROVISIONAL: Claude coder only, not resolved.** Coder = sonnet (claude-sonnet-5-5 via Claude Code subagent), effective score (a 1+ without a verified quote counts as 0). NA cells left out. Over-credit means the coder scored higher than the published expert score. ABC gold is unlicensed, so only per-item aggregates are written. ABC is binary (9 benchmarks); BetterBench is 0-3 (22 benchmarks, 20 items).

## ABC

- Cells compared: 198 (22 items; 0 NA cells left out). Agreement 0.657 (Wilson 95% 0.588-0.719).
- Disagreements: 68. Over-credit (coder higher) 29 (42.6%); under-credit (coder lower) 39 (57.4%). Over-credit share Wilson 95% 31.6%-54.5%.
- Items with agreement < 0.5 (5): R.11, T.1, T.2, T.3, T.6.
- Three lowest: T.6 0.11 (n=9, over 0, under 8); T.3 0.22 (n=9, over 0, under 7); T.1 0.33 (n=9, over 0, under 6).

## BetterBench

- Cells compared: 425 (20 items; 15 NA cells left out). Agreement 0.527 (Wilson 95% 0.480-0.574).
- Disagreements: 201. Over-credit (coder higher) 102 (50.7%); under-credit (coder lower) 99 (49.3%). Over-credit share Wilson 95% 43.9%-57.6%.
- Items with agreement < 0.5 (8): J.1-5, J.1-9, J.2-2, J.2-9, J.3-12, J.3-17, J.3-19, J.4-1.
- Three lowest: J.2-2 0.23 (n=22, over 14, under 3); J.3-17 0.27 (n=22, over 11, under 5); J.1-5 0.32 (n=22, over 1, under 14).

## Overall (both sets pooled; scales differ, direction is within scale)

- 623 cells, agreement 0.568; over-credit 131 (48.7% of 269 disagreements), under-credit 138 (51.3%).
