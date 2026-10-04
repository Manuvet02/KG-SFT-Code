# LLM-as-judge evaluation report

## Overall

n = 39 instances judged
model = unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M

| Dimension   | Mean score |
| ----------- | ---------- |
| correctness | 0.645      |
| efficiency  | 0.760      |
| readability | 0.777      |

## Breakdown by competency question

| CQ   | n   | correctness | efficiency | readability |
| ---- | --- | ----------- | ---------- | ----------- |
| CQ1  | 2   | 0.775       | 0.650      | 0.725       |
| CQ10 | 3   | 0.667       | 0.817      | 0.833       |
| CQ11 | 1   | 0.700       | 0.800      | 0.900       |
| CQ12 | 3   | 0.867       | 0.883      | 0.900       |
| CQ13 | 1   | 1.000       | 1.000      | 1.000       |
| CQ14 | 1   | 0.300       | 1.000      | 0.900       |
| CQ15 | 3   | 0.183       | 0.633      | 0.783       |
| CQ17 | 3   | 0.733       | 0.783      | 0.733       |
| CQ2  | 3   | 1.000       | 1.000      | 1.000       |
| CQ3  | 3   | 0.817       | 0.750      | 0.733       |
| CQ4  | 2   | 0.400       | 0.750      | 0.800       |
| CQ5  | 1   | 0.200       | 0.500      | 0.800       |
| CQ6  | 4   | 0.312       | 0.537      | 0.500       |
| CQ7  | 4   | 0.637       | 0.725      | 0.725       |
| CQ8  | 2   | 0.825       | 0.900      | 0.800       |
| CQ9  | 3   | 0.783       | 0.700      | 0.733       |

## Lowest-scoring examples (by correctness)

Useful for the qualitative discussion -- these are the cases
worth explaining in the report, not just citing the aggregate number.

**T_CQ15-01-3844** (CQ15) -- correctness 0.05

> The generated query targets sft:sport_facility instead of entities with has_type 'Locale-Progetto' (project locations), answers a fundamentally different question, and adds an unnecessary has_location projection.

**T_CQ6_ask-01-5252** (CQ6) -- correctness 0.15

> The generated query uses SELECT instead of ASK for a yes/no question, queries the wrong class (sft:association instead of sft:sport_facility), hardcodes service URIs without verifying they are reservation services, and matches the name via string containment on the URI rather than a proper name property.

**T_CQ15-01-7506** (CQ15) -- correctness 0.20

> The generated query uses the wrong type value ('highway project' instead of 'Autostrada-Progetto') and strips the wrong URI prefix ('Route/' instead of 'Path/'), which would likely yield no results or malformed IDs, fundamentally failing to answer the question.

**T_CQ5-01-5736** (CQ5) -- correctness 0.20

> The generated query uses a direct sft:has_facility property to link associations to sport facilities, whereas the golden query correctly routes through the sport (association has_sport sport ← has_sport sport_facility); if sft:has_facility doesn't exist in the KG, the query returns no results.

**T_CQ14-02-6801** (CQ14) -- correctness 0.30

> The query structure is correct but uses 'football' instead of the correct Italian term 'calcio' for the sport URI, which would fail to match any football facilities in this Italian (Trentino) knowledge graph.
