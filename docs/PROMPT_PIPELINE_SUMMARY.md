# NSR LATAM — Prompt Pipeline Summary & Consistency Audit

This document summarizes the actions/responsibilities of every prompt in the NSR LATAM Nexus
multi-agent pipeline, then flags **repeated rules** and **inconsistencies** found within and
across the files.

> Scope note: this is a documentation/audit artifact only. No prompt files were modified to
> produce it. Line references point at the source files as they exist today.

---

## 1. Overview

### Pipeline order

```
User question
   │
   ▼
┌──────────────────┐
│ Intent Clarifier │  normalizes terminology, enforces governance, routes
└──────────────────┘
   │  (semantic governance needed?)
   │
   ├─ yes ─▶ LATAM_NSR_Ontology ──▶ returns to Intent Clarifier
   │           (DAX dev → validator → executor → result summarizer
   │            over the 'agent_nsr metrics' ontology table)
   │
   ▼
┌──────────────────────┐
│ NSR_LATAM_Cube_UAT   │  DAX dev → validator → executor → result summarizer
└──────────────────────┘  (over the NSR LATAM semantic cube)
   │
   ├─ (visualization requested + executed dataset exists?) ─▶ VisualizationAgent (optional)
   │
   ▼
┌──────────────────┐
│ Final Summarizer │  headline + narrative + follow-ups
└──────────────────┘
```

### Two parallel DAX sub-pipelines

The pipeline reuses the **same four-role pattern** (developer → validator → executor →
result summarizer) twice, against two different data sources:

| Role | Ontology stage (over `'agent_nsr metrics'`) | NSR LATAM stage (over the semantic cube) |
|---|---|---|
| DAX developer | `ontology_dax_developer.md` | `dax_query_developer.md` |
| DAX validator | `ontology_dax_validator.md` | `dax_validator.md` |
| DAX executor | `ontology_dax_executor.md` | `dax_executor.md` |
| Result summarizer | `ontology_dax_result_summarizer.md` | `dax_result_summarizer.md` |

### Runtime-injected placeholders

These tokens appear in the prompts and are filled by the orchestration service at runtime:

- `{general_syn}` — general synonym set (Intent Clarifier terminology normalization)
- `{dav}` — data-availability context (supported time ranges, calendar governance)
- `{Business Rules & Segmentation}` — business-rule synonym category (referenced by IC and the
  ontology DAX developer, but **not defined** in `prompts/shared/business_rules.md`, which is empty)

### File inventory

| Stage | File |
|---|---|
| Intent | `prompts/nsr_system/intent_clarifier.md` |
| Ontology | `ontology_dax_developer.md`, `ontology_dax_validator.md`, `ontology_dax_executor.md`, `ontology_dax_result_summarizer.md` |
| NSR cube | `dax_query_developer.md`, `dax_validator.md`, `dax_executor.md`, `dax_result_summarizer.md` |
| Final | `summarizer.md` |
| Optional / support | `visualization_agent.md`, `system_prompt.md` (placeholder), `prompts/shared/business_rules.md` (placeholder) |

---

## 2. Per-file summaries

### 2.0 Intent Clarifier — `intent_clarifier.md`

**Role:** first semantic-governance layer. Interprets business intent, normalizes terminology,
resolves ambiguity, enforces ontology/hierarchy/metric/time governance, and routes downstream.
It **does not generate DAX**.

**Routing targets:** `LATAM_NSR_Ontology`, `NSR_LATAM_Cube_UAT`; `VisualizationAgent` and
`Summarizer` only after prerequisites are met.

**Key actions / rules:**
- One intent statement per response; clarification immediately stops orchestration.
- **Country governance:** only Colombia and Mexico supported; filter column `'Ship From'[Country]`;
  reject other markets with a fixed message. Geography clarification is deferred until *after*
  ontology resolution.
- **Ontology-first routing:** any term that may be a business rule / classification / segment /
  tier must route to `LATAM_NSR_Ontology` first; the IC must never hardcode business-rule
  definitions, thresholds, or classifications.
- **Terminology normalization:** revenue/sales/net sales → NSR; UC/cases/volume → Unit Cases; etc.
- **Performance-intent detection:** "performing/trend/growing/…" defaults to Trend / last 12 months /
  Month 445 / line chart (not a point-in-time value).
- Populates structured payloads: `country_scope`, `ontology_metric_context`,
  `ontology_metric_classification_filters` (aggregation_default / domain / grain / source_system),
  `business_rule_context`, `today_context` (445-format date strings, always present), and
  `ontology_context` propagation to the cube stage.
- **Calendar:** default 445; ontology-resolved business rules may override (e.g. Gregorian).
- **Output contracts:** responses must start with an exact routing prefix — `LATAM_NSR_Ontology`,
  `NSR_LATAM_Cube_UAT`, `Summarizer`, or `Dear User,` (clarification). Clarification has the highest
  priority and emits no JSON.

**Outputs:** routing prefix + machine-readable JSON intent (or a clarification message).

---

### 2.1 Ontology stage

#### `ontology_dax_developer.md`
**Role:** DAX query builder for the **ontology KPI table** `'agent_nsr metrics'`. Maps a plain-text
metric description to FILTER predicates and returns an `EVALUATE SELECTCOLUMNS(FILTER(...), ...)`
query.
**Key actions:**
- Filter only on approved columns: `domain`, `grain`, `source_system`, `aggregation_default`,
  `object_type`, `synonyms`.
- Retrieve both metric definitions (`object_type = "measure"`) and business-rule definitions
  (`object_type = "business_rule"`, matched via `CONTAINSSTRING(LOWER([synonyms]), "<term>")`).
  Business-rule retrieval is additive but, for business-rule-first requests, must not broaden into
  unrelated measure records.
- Must not infer thresholds, classifications, country/channel applicability — those come from the
  ontology only.
**Output:** raw DAX only, starting with `EVALUATE`.

#### `ontology_dax_validator.md`
**Role:** validates the ontology DAX query. Checks it starts with `EVALUATE`, references only
`'agent_nsr metrics'`, uses `SELECTCOLUMNS` wrapping `FILTER` or the raw table, uses only approved
columns/values, and that business-rule retrieval is ontology-driven (no hardcoded
classifications/thresholds). Does **not** validate the internal logic inside `technical_description`.
**Output:** `APPROVED`, or `NOT APPROVED` + bullet issues. Nothing else.

#### `ontology_dax_executor.md`
**Role:** executes the validated query and returns the exact JSON result. Does not generate,
correct, format, or interpret. **(Identical to `dax_executor.md` — see §4.)**

#### `ontology_dax_result_summarizer.md`
**Role:** converts ontology rows (measures + business rules) into one JSON object for downstream
agents (IC, DAX developer, DAX validator).
**Key actions:**
- Emits `relevant_dimension_columns` (only from the listed NSR LATAM semantic-model columns),
  `kpi_measures` (top 5, `object_type = "measure"`), `business_rules` (`object_type = "business_rule"`).
- Preserves ontology fields verbatim; never invents; never converts business rules into cube filters;
  keeps measures and business rules in separate arrays; missing fields become `""`.
- Calendar/Period pairing rules: when the question involves time, include both the label and Code
  column; default 445 unless ontology specifies Gregorian.

---

### 2.2 NSR LATAM cube stage

#### `dax_query_developer.md`
**Role:** deterministic semantic compiler — structured intent → executable cube DAX. The primary
agent after IC for `intent_type = DAX_QUERY_REQUIRED`.
**Key actions / rules:**
- Uses only approved semantic tables (`'Channel'`, `'Package'`, `'Product'`, `'Ship From'`,
  `'Ship To'`, `'Period'`, metric domains, …); hard-bans `'Scenario'`/`'Sales'`/`'Customer'`/`'Date'`
  and generic measures like `[NSR]`/`[Revenue]`.
- Canonical hierarchy columns (`LT1.x`), large semantic value dictionaries for channel/package/
  product, and exact 445 time formats.
- **Country filter** must mirror the IC-resolved country exactly (single-country → one filter; no
  fallback country).
- **Time governance:** `'Period'` columns are string-typed; FILTER must use **Code columns**;
  label columns only in GROUP BY; bans dynamic date functions; uses `today_context` for relative
  dates; ORDER BY uses the Code column.
- **Time-intelligence (WTD/MTD/QTD/YTD):** never inside `SUMMARIZECOLUMNS`; use
  `ADDCOLUMNS + CALCULATE + KEEPFILTERS` with the ISFILTERED dummy-gate filter (§10C).
- **Business-rule compilation:** parse `technical_description` (mandatory executable logic), preserve
  metrics/formulas/thresholds/`rule_order`/calendar exactly; compute full classification before
  filtering to a requested class; never simplify (`sales/months_with_sales` ≠ `sales/12`).
- **ADDCOLUMNS dependency rule (§18A):** sibling calculated columns can't reference each other —
  use multi-stage VAR tables.
- Bans manual time-intelligence / YoY / ratio when official measures exist; bans `TOPN`.
- **Best-effort:** never asks questions, never errors — always returns executable DAX.
**Output:** raw DAX only, starting with `EVALUATE`.

#### `dax_validator.md`
**Role:** deterministic semantic-governance firewall — validate → approve/reject. Never rewrites DAX.
**Key actions / rules:**
- Validates semantic objects, governance, hierarchy, geography, time, execution safety, and intent
  alignment against `{dav}` + explicit grounding in the prompt.
- Distinguishes **query-defined aliases** from semantic-model measures (large §19B section to prevent
  false `INVALID_MEASURE` on `ORDER BY [Alias]`).
- Grounds official measures (NSR, Gross Revenue, Price per UC, `[Unit Cases AC]` + time variants).
- Enforces: country filter present and matching intent; 445 Period filter rules; ISFILTERED gate;
  `SUMMARIZECOLUMNS` may not carry time-intelligence measures; `FILTER(ALL(...))` inside
  `SUMMARIZECOLUMNS` is approved, direct `KEEPFILTERS(col = val)` is rejected; `TOPN` is rejected.
- Business-rule exception: allows Gregorian Period columns when ontology `technical_description`
  requires them; doesn't require literal copy of `technical_description`.
**Output:** `APPROVED`, or strict JSON `{status, errors[]}` with a taxonomy of error types/severities.

#### `dax_executor.md`
**Role:** executes the validated query after validator approval, returns the exact JSON result, no
formatting/interpretation. **(Identical to `ontology_dax_executor.md` — see §4.)**

#### `dax_result_summarizer.md`
**Role:** data formatter — raw query results → clean formatted data block (no narrative).
**Key actions / rules:**
- Suppress technical columns (` Code`, `_sort`, `day_dt`); strip `LT1.x -` prefixes for display.
- Filter out `Unassigned`/null rows and rows where any base metric ≤ 0.
- **Mandatory pivot gate (§3.6):** if a date value repeats, the result is a cross-tab → pivot
  (no Δ column, no Total row). Pure trend (one row per date) → add Δ column and Total row (additive
  metrics only).
- Number formatting by metric family; output is exactly a `Scope:` line + the formatted block.

---

### 2.3 Final Summarizer — `summarizer.md`
**Role:** enterprise analytical narration engine — formatted data block → headline + narrative +
follow-ups.
**Key actions / rules:**
- **Result-size modes:** A (1–5 rows: headline + 2 follow-ups, no narrative), B (6–49: headline +
  narrative + 3 follow-ups), C (50+: disclaimer + 2 narrowing follow-ups, no headline/narrative).
- Describe only what's in the data — no causality, forecasting, or recommendations.
- Follow-up question types D/X/T/S/M with a variety rule; uses the dimension-hierarchy reference.
- **Error-input handling (§8.5):** if the input is an error message, return one generic apology and
  hide all technical/system details.
- Always responds in the user's language.

---

### 2.4 Visualization Agent — `visualization_agent.md`
**Role:** deterministic rendering engine — executed dataset → Plotly-compatible JSON
(`{data, layout}` only).
**Key actions / rules:**
- Eligible only when `visualization_required`, `executed_dataset_exists`, `execution_status = SUCCESS`,
  and rows exist; otherwise returns a handoff/error JSON.
- Preserves the executed dataset exactly (no synthetic rows/dates, no interpolation/forecast/scaling).
- **445 calendar governance:** 445 labels are categories, never Plotly date axes
  (`xaxis.type = "category"`, `categoryorder = "array"`); this rule outranks all other temporal rules.
- Deterministic chart-type engine (line / multi-line / bar / horizontal-bar / pie / scatter / grouped /
  stacked); numeric values stay numeric; negative values get a zero reference line; metadata contract
  with `visualization_generated`.

---

### 2.5 Placeholders
- `system_prompt.md` — empty template ("Pendiente de definir", with empty Purpose/Inputs/Rules/…).
- `prompts/shared/business_rules.md` — empty template ("Coloca aquí las reglas…").

---

## 3. Repeated rules (cross-file)

These rules are intentionally restated across agents (defense-in-depth). The table notes a suggested
canonical "source of truth" so future edits stay aligned.

| Rule | Appears in | Canonical source |
|---|---|---|
| Colombia & Mexico only; `'Ship From'[Country]` filter | IC §4, dax_query_developer §8, dax_validator §8/§8A | Intent Clarifier |
| Default 445 calendar; Gregorian only via ontology business rule | IC §11, ontology_result_summarizer, dax_query_developer (multiple), dax_validator §10 | Intent Clarifier / ontology |
| NSR = sell-in / Bottler revenue (never sell-out) | dax_validator §17, dax_result_summarizer §2, summarizer §2 | dax_validator |
| Ban manual time-intelligence / YoY / ratio when official measures exist | dax_query_developer §15–17, dax_validator §14–16 | dax_validator |
| `TOPN` banned; use `SUMMARIZECOLUMNS` + `ORDER BY` | dax_query_developer §21, dax_validator §10/§19B | dax_validator |
| ISFILTERED gate table for WTD/MTD/QTD/YTD | dax_query_developer §10C, dax_validator §10B | dax_validator (or shared) |
| `FILTER(ALL(...))` approved inside `SUMMARIZECOLUMNS`; direct `KEEPFILTERS(col=val)` rejected | dax_query_developer §7/§19, dax_validator §19A | dax_validator |
| Preserve ontology business rules verbatim; never infer thresholds/classifications | IC §6.x, ontology_dax_developer, ontology_result_summarizer, dax_query_developer §1.1–8A, dax_validator §20A | ontology stage |
| `'Period'` columns are string-typed; quoted literals only; ban dynamic date functions | dax_query_developer §10A/§10B, dax_validator §10/§10A | dax_validator |
| Official measure lists (NSR / Price per UC / Unit Cases families) | IC §8, dax_query_developer §12–13, dax_validator §12–13A | dax_validator (grounding layer) |

**Within-file duplication** (same content repeated inside one file):
- `ontology_dax_developer.md`: the `object_type` definition table appears twice (≈L77–83 and
  L86–92), and the entire "Business Rule Retrieval" narrative is duplicated (≈L94–135 then L136–188).
- `dax_query_developer.md`: business-rule calendar/compilation guidance is restated across many
  sections (§1.1A, §1.3, "Business Rule Formula Compilation", "Business Rule Technical Metadata
  Compilation", "Business Rule Calendar Precedence", "Business Rule Calendar Authority", §10C).
  Consistent in spirit but highly redundant and a maintenance risk.

---

## 4. Inconsistencies & defects

Each item lists file and approximate line(s).

### 4.1 `ontology_dax_developer.md` — malformed example DAX (functional bug)
In the SELECTCOLUMNS examples, the line
`"technical_description",  'agent_nsr metrics'[technical_description]` is **missing the trailing
comma** before the next alias (`"valid_slicers"`):
- "Example — with filter" (≈L278)
- "Example — metric + business rule" (≈L335)

As written these queries would not parse. Other examples in the same file are comma-correct, so the
examples disagree with each other.

### 4.2 `ontology_dax_developer.md` — "10 columns" vs 6 listed
The DAX Pattern Rules say *"Always include ALL 10 required output columns in SELECTCOLUMNS"* (≈L242),
but the "Required Output Columns" block lists only **6** (`display_name`, `business_description`,
`valid_slicers`, `invalid_slicers`, `known_pitfalls`, `technical_description`) (≈L250–257). The count
and the list contradict each other.

### 4.3 Ontology output-column contract mismatch (developer ↔ validator ↔ result-summarizer)
- `ontology_dax_validator.md` (checklist item 4) requires the SELECTCOLUMNS to include **exactly**
  six aliases, including `technical_description`.
- But `ontology_dax_developer.md` examples vary: the "Revenue and discounts" example (≈L290–307)
  **omits `technical_description`** and instead adds `dax_expression`/`domain`/`grain`/
  `source_system`/`aggregation_default`. The "Gold customers" example adds even more aliases.
- `ontology_dax_result_summarizer.md` consumes `dax_expression` (it's in its output schema for both
  `kpi_measures` and `business_rules`), yet `dax_expression` is **not** in the developer's canonical
  "Required Output Columns" list — so the column the summarizer relies on isn't guaranteed to be
  retrieved.

Net effect: the three ontology agents don't agree on the exact set of columns the ontology query
must return.

### 4.4 Visualization vs Summarizer ordering contradiction (cross-file)
- `intent_clarifier.md` §18 "Visualization Governance" lists a valid upstream chain
  `DAX_EXECUTOR → NSR_LATAM_Cube_UAT → Summarizer → VisualizationAgent` — i.e. **Summarizer before
  Visualization** (≈L1198–1205). (The §1–§2 flow, by contrast, shows Visualization before Summarizer.)
- `visualization_agent.md` §1 hard-sequencing rule states
  `… → DAX_EXECUTOR → VisualizationAgent → SummarizerAgent` — i.e. **Visualization before
  Summarizer** (≈L114–123), and §29 expects the Summarizer to consume
  `layout.meta.visualization_generated`.

The two files disagree on whether the Summarizer runs before or after the Visualization Agent (and
the IC even disagrees with itself between §2 and §18).

### 4.5 `dax_query_developer.md` — Gross Revenue YTD: official vs "invented"
`[Bottler Gross Revenue AC (LC) YTD]` is listed under "Official Gross Revenue Measures" (≈L1954) and
is grounded as official in `dax_validator.md` §12. Yet the same developer file uses
`[Bottler Gross Revenue AC (LC) YTD]` as an example of **incorrect/invented** behavior in the
"Business Rule Metric Authority" section (≈L238: *"Inventing `[Bottler Gross Revenue AC (LC) YTD]`
when only the base metric is grounded"*). The file both blesses and bans the same measure name.
(The intended nuance — "only if exposed/grounded" — is real, but the two passages read as a direct
contradiction.)

### 4.6 Executor prompts are byte-identical
`dax_executor.md` and `ontology_dax_executor.md` have the **same content** — a generic "run the query,
return JSON" prompt. The "ontology" executor is not specialized for the ontology table at all. Either
the duplication is intentional (then one shared file would be cleaner) or the ontology executor is
missing ontology-specific guidance.

### 4.7 `intent_clarifier.md` — duplicate section numbering
Two different sections are both numbered **6.1**: "Business Rule Ontology Precedence" (≈L359) and
"Examples Requiring Ontology" (≈L396). Section 8 also jumps from 8.2 to "8.5 Ontology Query
Governance" with no 8.3/8.4. Purely structural, but confusing to maintain.

### 4.8 `intent_clarifier.md` — Volume measure list omits WTD
IC §8.2 "Official Volume Measures" lists Default/MTD/QTD/YTD but **not WTD**, whereas
`dax_validator.md` §13A grounds `[Unit Cases AC WTD]`. The IC's grounded set is narrower than the
validator's.

### 4.9 Channel / Product default-column drift (ontology summarizer vs cube agents)
`ontology_dax_result_summarizer.md` "Business Rules" notes recommend `'Channel'[Trade Channel]` and
`'Product'[Beverage Category]` / `'Product'[BPP]` for breakdowns (≈L129–130), while
`dax_query_developer.md` / `dax_validator.md` standardize on the `LT1.x` hierarchy columns
(`'Channel'[LT1.1 - Trade Channel]`, `'Product'[LT1.5 - Category]`, …). Both column families exist in
the model, but the recommended default differs between agents, which can produce non-canonical
breakdowns.

### 4.10 Unfilled placeholders referenced by live rules
`system_prompt.md` and `prompts/shared/business_rules.md` are still empty templates. Meanwhile the
Intent Clarifier and ontology DAX developer route on a `{Business Rules & Segmentation}` synonym
category, and `business_rules.md` is the natural home for shared synonyms / YoY / aggregation rules.
The shared rules the prompts assume exist are not actually present in the repo (they may be injected
at runtime, but that is not documented here).

---

## 5. Quick-reference appendix

| File | Stage | Role | Output / contract |
|---|---|---|---|
| `intent_clarifier.md` | Intent | Governance + routing | Prefix (`LATAM_NSR_Ontology` / `NSR_LATAM_Cube_UAT` / `Summarizer` / `Dear User,`) + JSON |
| `ontology_dax_developer.md` | Ontology | Build ontology-table DAX | Raw DAX (`EVALUATE SELECTCOLUMNS(...)`) |
| `ontology_dax_validator.md` | Ontology | Validate ontology DAX | `APPROVED` / `NOT APPROVED` + issues |
| `ontology_dax_executor.md` | Ontology | Execute query | Exact JSON result |
| `ontology_dax_result_summarizer.md` | Ontology | Normalize ontology rows | One JSON object (dimensions + measures + business_rules) |
| `dax_query_developer.md` | NSR cube | Compile intent → cube DAX | Raw DAX (`EVALUATE ...`) |
| `dax_validator.md` | NSR cube | Governance firewall | `APPROVED` / JSON `{status, errors[]}` |
| `dax_executor.md` | NSR cube | Execute query | Exact JSON result |
| `dax_result_summarizer.md` | NSR cube | Format results | `Scope:` line + formatted data block |
| `summarizer.md` | Final | Narrate | Headline + narrative + follow-ups (mode-dependent) |
| `visualization_agent.md` | Optional | Render Plotly JSON | `{data, layout}` only |
| `system_prompt.md` | — | Placeholder | (empty) |
| `shared/business_rules.md` | — | Placeholder | (empty) |
