# Skill Benchmark: finance-management

**Model**: claude-opus-5-5
**Date**: 2026-10-05T10:31:18Z
**Evals**: 1-13 with skill; 1-9, 13 without (1 run each)

## Summary (paired evals 1-9, 13)

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 100% ± 0% (36/36) | 90% ± 13% (32/36) | +0.10 |
| Time | 228.2s ± 86.4s | 454.4s ± 362.7s | -226.2s |
| Tokens | 43137 ± 4299 | 58448 ± 6961 | -15311 |

With skill, all 13 evals: 100% ± 0% (47/47).
Times are inflated by up to 7 agents sharing the Teable server at once; compare tokens rather than time.

## Notes

- Evals 10-12 (write discipline) ran with the skill only, so a baseline agent could not write to live data; paired comparison uses evals 1-9 and 13.
- No run wrote to the database: row counts, Woolworths default category and the Step 13 task were identical before and after.
- Baseline losses are all definitional: gross expenses instead of net spend (refunds not netted) in evals 1, 5, 9, and a rolling instead of complete-month window in eval 2.
- Baseline found things the skill missed: 22 incoming transfers ('TRANSFER .. FROM 807590005', $25,060) stored as Transfer and signed negative, so the true balance is ~$979.54, not -$49,140.46 (eval 8); a fixed $2,357.36 monthly transfer; Amaysim bills every 28 days; annual/irregular bills (rego, council rates, water, Anthropic); fortnightly 'Business Income' looks like wages (eval 6).
- The eval-8 assertion encoded the skill's wrong hypothesis ('missing income or accounts'); the with-skill run passes it but the baseline answer is more correct. Skill defect to fix in iteration 2.
