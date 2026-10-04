# LLM-as-judge evaluation report

## Overall

n = 39 instances judged
model = cohere/north-mini-code:free

| Dimension   | Mean score |
| ----------- | ---------- |
| correctness | 0.622      |
| efficiency  | 0.705      |
| readability | 0.792      |

## Breakdown by competency question

| CQ   | n   | correctness | efficiency | readability |
| ---- | --- | ----------- | ---------- | ----------- |
| CQ1  | 2   | 1.000       | 0.700      | 0.800       |
| CQ10 | 3   | 0.767       | 0.667      | 0.700       |
| CQ11 | 1   | 0.900       | 1.000      | 1.000       |
| CQ12 | 3   | 0.933       | 0.833      | 0.900       |
| CQ13 | 1   | 1.000       | 1.000      | 1.000       |
| CQ14 | 1   | 0.200       | 1.000      | 1.000       |
| CQ15 | 3   | 0.100       | 0.333      | 0.833       |
| CQ17 | 3   | 0.667       | 0.667      | 0.867       |
| CQ2  | 3   | 1.000       | 1.000      | 1.000       |
| CQ3  | 3   | 0.883       | 0.767      | 0.767       |
| CQ4  | 2   | 0.000       | 0.750      | 0.900       |
| CQ5  | 1   | 0.300       | 0.900      | 0.800       |
| CQ6  | 4   | 0.250       | 0.475      | 0.425       |
| CQ7  | 4   | 0.450       | 0.575      | 0.725       |
| CQ8  | 2   | 0.900       | 0.900      | 0.850       |
| CQ9  | 3   | 0.733       | 0.633      | 0.733       |

## Lowest-scoring examples (by correctness)

Useful for the qualitative discussion -- these are the cases
worth explaining in the report, not just citing the aggregate number.

**T_CQ15-01-3277** (CQ15) -- correctness 0.00

> Generated query uses an incorrect type literal and adds an unnecessary class triple pattern.

**T_CQ15-01-3844** (CQ15) -- correctness 0.00

> Generated query targets sport_facility resources instead of project paths, missing the required type filter.

**T_CQ17-01-1227** (CQ17) -- correctness 0.00

> Name literal mismatch and extra ID computation.

**T_CQ4-01-0904** (CQ4) -- correctness 0.00

> The query filters on a different status value, causing potential mismatch with the KG.

**T_CQ4-01-2242** (CQ4) -- correctness 0.00

> Uses wrong status literal for renovation.
