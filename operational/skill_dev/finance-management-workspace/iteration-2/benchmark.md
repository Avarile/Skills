# Skill Benchmark: finance-management, iteration 2

Re-ran the two evals whose gaps the iteration-1 baselines exposed, with the skill only, after the fixes:
- incoming transfers (TRANSFER .. FROM ..) are counted as money in, so the corrected balance is $979.54 and the formula figure (-$49,140.46) is explained;
- recurring adds a 4-weekly cadence, regular transfers and payments to people as their own section, and annual or irregular bills paid in the last 12 months;
- SKILL.md rule 3 is rewritten.

| Eval | Iteration 1 (with skill) | Iteration 2 (with skill) | Tokens |
|---|---|---|---|
| 04 subscriptions | 4/4 (old assertions; missed annual bills, transfers, 4-weekly) | 5/5 (incl. new irregular-bills assertion) | 51,078 -> 44,634 |
| 08 balance | 3/3 (old assertions encoded the wrong cause) | 3/3 on corrected assertions: reports $979.54 and the real cause | 39,322 -> 37,643 |

On the iteration-1 corrected assertions, the iteration-1 with-skill eval-08 answer would have failed 2/3; the iteration-1 baseline passed them.
