# NSR LATAM — Prompt Efficiency Review

Companion to `docs/PROMPT_PIPELINE_SUMMARY.md`. This review assesses how **efficient** the pipeline
prompts are along two axes — **token/cost** (size, redundancy) and **effectiveness** (how reliably
each prompt steers the model: clarity, determinism, freedom from contradiction) — and recommends
concrete strategies per file.

> Documentation only — no prompt files were modified. Section/line references point at the files as
> they exist today.

---

## 1. Why prompt efficiency matters here

In this multi-agent pipeline, **each agent's system prompt is re-sent on every LLM call for that
agent**. A single user question can trigger Intent Clarifier → (ontology dev → validator → executor →
summarizer) → (cube dev → validator → executor → summarizer) → summarizer — i.e. the big prompts are
paid for repeatedly within one question. So:

- **Redundant tokens are a recurring cost**, multiplied by every turn and every retry.
- **Paraphrased / contradictory rules dilute instruction-following.** When the same rule is restated
  six different ways, subtle wording differences give the model room to drift; when two rules
  conflict, the model must guess. Fewer, sharper, non-contradictory rules are both cheaper *and* more
  reliable.

### Corpus size

| File | lines | words | ≈ tokens* | Share |
|---|---:|---:|---:|---:|
| dax_query_developer.md | 3285 | 9271 | ~12,400 | 29% |
| dax_validator.md | 2055 | 6052 | ~8,100 | 19% |
| intent_clarifier.md | 1599 | 4711 | ~6,300 | 15% |
| visualization_agent.md | 1475 | 3492 | ~4,700 | 11% |
| summarizer.md | 361 | 2134 | ~2,900 | 7% |
| dax_result_summarizer.md | 357 | 1861 | ~2,500 | 6% |
| ontology_dax_result_summarizer.md | 387 | 1780 | ~2,400 | 6% |
| ontology_dax_developer.md | 402 | 1723 | ~2,300 | 5% |
| ontology_dax_validator.md | 311 | 709 | ~950 | 2% |
| dax_executor.md | 5 | 96 | ~130 | <1% |
| ontology_dax_executor.md | 5 | 96 | ~130 | <1% |
| system_prompt.md | 13 | 16 | ~25 | <1% |
| shared/business_rules.md | 10 | 35 | ~50 | <1% |
| **Total** | **~10,265** | **~31,700** | **~43,500** | 100% |

\* Rough estimate (~1.33 tokens/word for English + markdown). The **top 4 files are ~74% of the
corpus** — that's where nearly all efficiency gains live.

### Efficiency rating per file

| File | Token bloat | Effectiveness risk | Overall |
|---|---|---|---|
| dax_query_developer.md | 🔴 High | 🟠 Medium (internal repetition + 1 contradiction) | 🔴 Biggest opportunity |
| dax_validator.md | 🔴 High | 🟢 Low | 🟠 Large opportunity |
| intent_clarifier.md | 🟠 Medium | 🟠 Medium (duplicate §, repeated rule) | 🟠 Moderate |
| visualization_agent.md | 🟠 Medium | 🟢 Low | 🟠 Moderate |
| ontology_dax_developer.md | 🟠 Medium (duplicated blocks) | 🔴 High (malformed examples, 10-vs-6) | 🟠 Fix + trim |
| ontology_dax_result_summarizer.md | 🟢 Low | 🟢 Low | 🟢 Minor trims |
| summarizer.md | 🟢 Low | 🟢 Low | 🟢 Keep |
| dax_result_summarizer.md | 🟢 Low | 🟢 Low | 🟢 Keep |
| ontology_dax_validator.md | 🟢 Low | 🟢 Low | 🟢 Keep |
| dax_executor.md / ontology_dax_executor.md | 🟢 Minimal | 🟢 Low | 🟢 Merge (DRY) |
| system_prompt.md / shared/business_rules.md | 🟢 Empty | 🟠 Unused but referenced | 🟠 Populate or remove |

---

## 2. Cross-cutting strategies (highest leverage)

These apply across files and deliver the largest combined token + reliability gains.

### S1 — Build a shared governance include *(biggest single win)*
A core set of rules is **restated in nearly every agent**: Colombia/Mexico country governance, the
445 calendar + exact value formats, the official measure catalog, the semantic value dictionaries,
and "NSR = sell-in". Extract these into **one shared block injected into each agent** (the natural
home is the currently-empty `system_prompt.md` and `prompts/shared/business_rules.md`, or a new
`prompts/shared/governance.md`).

- **Token win:** the duplicated governance text is paid for in 4+ large prompts today; injected once,
  it is authored once.
- **Effectiveness win:** eliminates the cross-file *drift* documented in the audit (e.g. the
  Channel/Product default-column disagreement, the Volume-WTD omission, the column-contract mismatch).
  One source of truth ⇒ no divergence.

### S2 — Deduplicate within files
Collapse paraphrased restatements of the same rule into **one authoritative statement**. Repetition
does not make a rule "stickier"; it adds tokens and invites subtle contradictions. (Worst offender:
the business-rule guidance in `dax_query_developer.md`, restated across ~6 sections.)

### S3 — Runtime-inject volatile enumerations
The exhaustive value lists (every trade channel, container, package size, product category, brand…)
are large, go stale, and are better sourced from `{dav}` / model metadata than hardcoded in the
prompt. Keep a few *representative* examples + the normalization rule; inject the authoritative list.
This is simultaneously a token win, a staleness fix, and an accuracy fix.

### S4 — Prose → compact tables / imperative bullets
Terse imperative rules and tables steer the model as well as long prose at a fraction of the tokens.
Several sections are paragraphs that could be 2–3 bullets.

### S5 — One canonical example per pattern
Keep a single worked example per pattern; drop near-duplicates (e.g. `dax_validator.md` shows the
same Unit-Cases query twice for Colombia and twice for Mexico).

### S6 — Remove contradictions
Conflicting instructions force the model to guess and waste reasoning. Fold in the audit fixes
(Gross-Revenue-YTD official-vs-invented; Visualization-vs-Summarizer order; ontology column contract).
Pure effectiveness win, near-zero token cost.

### S7 — Front-load (and tail-anchor) critical constraints
In very long prompts, rules in the middle get the least attention ("lost in the middle"). Keep the
output contract and the hard bans at the **top and bottom**; push exhaustive reference tables to the
middle or to the shared include.

---

## 3. Per-file efficiency strategies

### `dax_query_developer.md` — 🔴 biggest opportunity (~12.4k tokens)
**Bloat/risk:**
- Business-rule guidance restated across ~6 sections (§1.1A, §1.3, "Business Rule Formula
  Compilation", "Business Rule Technical Metadata Compilation", "Business Rule Calendar Precedence",
  "Business Rule Calendar Authority", §10C) — heavy overlap.
- The 445 value-format spec appears twice (§7.5 "Period Semantic Values" and §9 "Official Time Value
  Formats") — near-identical.
- Large hardcoded value dictionaries (channel/package/product) — hundreds of lines.
- Internal contradiction: `[Bottler Gross Revenue AC (LC) YTD]` is "official" (~L1954) and an
  "invented measure" example (~L238).

**Recommendations:**
1. Collapse the 6 business-rule subsections into **one** "Business Rule Compilation" section (rules +
   one worked example). (S2)
2. Merge the duplicate 445 format specs into one; move it to the shared include. (S1, S2)
3. Move the value dictionaries to runtime injection / shared reference; keep normalization rules + a
   few examples. (S3)
4. Resolve the Gross-Revenue-YTD wording (state the "only if grounded/exposed" nuance once). (S6)

**Est. reduction: 40–50%** (≈ 5–6k tokens off every developer call).

### `dax_validator.md` — 🟠 large opportunity (~8.1k tokens)
**Bloat/risk:**
- 445/Period rules, ISFILTERED gate table, and official-measure catalog duplicate the developer's.
- Repeated identical APPROVED examples (Colombia then Mexico, each shown twice).
- The §19B alias false-positive section is long and overlaps §22 "Output Alias Governance".

**Recommendations:**
1. Source the shared catalog/calendar/gate content from the shared include. (S1)
2. Keep one canonical APPROVED example; drop the country-swapped duplicates. (S5)
3. Merge §19B + §22 into a single "Query-defined aliases are not measures" rule with one example. (S2)

**Est. reduction: 30–40%.** Keep the alias rule and the `APPROVED` / strict-JSON output contract —
those are doing real work.

### `intent_clarifier.md` — 🟠 moderate (~6.3k tokens)
**Bloat/risk:**
- The "ontology resolution before geography clarification" rule is restated in §4, §6.1, §6.4, §15,
  §22, §23.
- Duplicate section numbering (two §6.1).
- The `country_scope` JSON example is shown three times (Mexico / Colombia / both).

**Recommendations:**
1. State the ontology-before-clarification rule **once** and reference it. (S2)
2. One parametrized `country_scope` example with a note that `values` varies. (S5)
3. Fix duplicate/!sequential numbering for parseability. (S4)

**Est. reduction: 20–30%.** Preserve the routing-prefix output contracts and the classification-filter
inference rules — high value.

### `visualization_agent.md` — 🟠 moderate (~4.7k tokens)
**Bloat/risk:**
- Preservation/hallucination warnings restated in §0, §5, §6, and §33.
- Each chart type (line, bar, h-bar, pie, scatter, grouped, stacked) has its own prose section + full
  JSON; much is boilerplate.

**Recommendations:**
1. One "Data preservation & no-hallucination" rule block, referenced elsewhere. (S2)
2. Collapse chart-type governance into a **compact decision table** (condition → chart type → key
   layout flags) + 1–2 canonical JSON examples (the 445 line chart and the ranking h-bar). (S4, S5)
3. Keep the 445-axis-is-category rule prominent — it's the critical correctness rule.

**Est. reduction: 30–40%.**

### `ontology_dax_developer.md` — 🟠 fix + trim (~2.3k tokens)
**Bloat/risk:**
- The `object_type` table is duplicated (~L77–83 and L86–92).
- The entire "Business Rule Retrieval" block is duplicated (~L94–135 then L136–188).
- "Include ALL **10** required output columns" but only **6** are listed.
- Two SELECTCOLUMNS examples are missing a comma after `technical_description` (malformed DAX).

**Recommendations:**
1. Delete the duplicated table and duplicated block. (S2) **~40% off immediately.**
2. Fix "10" → the actual count and make the required-columns list authoritative and aligned with the
   validator + result-summarizer (see audit §4.3). (S6)
3. Fix the malformed example commas. (S6)

### `ontology_dax_result_summarizer.md` — 🟢 minor (~2.4k tokens)
"Preserve verbatim / don't infer" is stated ~5 times (KPI Measure Preservation, Business Rule
Preservation, Technical Description Preservation, Business Rule Interpretation Boundary, Schema
Consistency). Fold into **one** "Preservation principle" + the field list. Align the consumed columns
(`dax_expression`) with what the ontology developer guarantees. **Est. 15–25%.**

### `dax_executor.md` + `ontology_dax_executor.md` — 🟢 already minimal
Both are ~5 lines and **byte-identical**. No token concern. Recommendation: keep one shared executor
prompt referenced by both stages (DRY) so they can't drift; or, if the ontology executor should
behave differently, give it ontology-specific guidance (today it has none).

### `summarizer.md`, `dax_result_summarizer.md`, `ontology_dax_validator.md` — 🟢 keep
These are already lean and well-structured (mode tables, formatting tables, a tight checklist).
Minor trims only; **do not over-compress** — the result-summarizer's pivot gate and the summarizer's
mode/follow-up rules carry real behavior. `ontology_dax_validator.md` (709 words) is a good model for
how terse a validator can be.

### `system_prompt.md`, `shared/business_rules.md` — 🟠 populate or remove
Both are empty placeholders, yet the live prompts reference a `{Business Rules & Segmentation}`
synonym set and a shared-rules concept. **Best use:** make these the home for the **S1 shared
governance include**. If they will never be used, remove them so they don't mislead.

---

## 4. Prioritized action list (impact × ease)

| # | Action | Impact | Ease | Files |
|---|---|---|---|---|
| 1 | Build the shared governance include (country, 445 + formats, measure catalog, NSR=sell-in); inject into each agent | 🔴 High (token + consistency) | 🟠 Medium | new `shared/governance.md` + all big files; populate `system_prompt.md` / `business_rules.md` |
| 2 | Collapse `dax_query_developer` business-rule sections into one; dedupe 445 spec | 🔴 High | 🟢 Easy | dax_query_developer.md |
| 3 | Remove duplicated blocks + fix malformed examples + "10 vs 6" | 🟠 Medium (correctness) | 🟢 Easy | ontology_dax_developer.md |
| 4 | Extract value dictionaries to runtime injection | 🟠 Medium | 🟠 Medium | dax_query_developer.md (+ validator) |
| 5 | Dedupe validator examples + merge alias sections | 🟠 Medium | 🟢 Easy | dax_validator.md |
| 6 | Compact visualization chart-type table + dedupe warnings | 🟠 Medium | 🟢 Easy | visualization_agent.md |
| 7 | Unify IC ontology-before-clarification rule; fix numbering; 1 country_scope example | 🟠 Medium | 🟢 Easy | intent_clarifier.md |
| 8 | Resolve contradictions from the audit (Gross-Rev-YTD; Viz/Summarizer order; column contract) | 🟠 Medium (determinism) | 🟢 Easy | dax_query_developer, intent_clarifier, visualization_agent, ontology trio |
| 9 | Merge the two executor prompts into one shared file | 🟢 Low | 🟢 Easy | dax_executor.md, ontology_dax_executor.md |

**Bottom line:** the prompts are thorough and defensively written, but **token-inefficient** — the
top 4 files carry ~74% of the text and contain large amounts of internal repetition and hardcoded
reference data. Actions 1–2 alone could cut roughly **5–8k tokens per developer/validator call** while
*improving* reliability, because most of the redundancy being removed is also the source of the
drift/contradictions found in the audit. The smaller files (summarizer, result-summarizers, ontology
validator) are already efficient and should mostly be left alone.
