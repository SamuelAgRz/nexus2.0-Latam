# Bug tracking

- **Obtaining null on YTD metrics**
Force using slicers based on known pitfalls column of metrics

- **Dates being omited in final output**
Usage of date column code instead of string based date filtering

- **Summarizer verbosity not scaled to result size** — The summarizer always produced a full narrative regardless of data volume; fixed by adding three output modes (Compact/Standard/Oversized) that adjust headline length, narrative, and follow-up count based on row count (1–5 / 6–49 / 50+).

- **Oversized tables (50+ rows) not being summarized** — Instead of summarizing large tables as-is, added a pivot attempt step that tries to reduce row count by pivoting on a suitable dimension (e.g., Month, Channel). If pivoting succeeds and reduces rows below 50, the pivoted table is summarized in Mode B; if pivoting fails or still results in 50+ rows, the original table is rendered in Mode C with a note about the pivot attempt.

- **Unassigned values in results** — Added a check for unassigned values in the summarizer output and included a note in the narrative if any are found, prompting users to review the data for potential issues.


