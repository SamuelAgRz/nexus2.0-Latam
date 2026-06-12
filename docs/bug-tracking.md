# Bug tracking

- **Obtaining null on YTD metrics**
Force using slicers based on known pitfalls column of metrics

- **Dates being omited in final output**
Usage of date column code instead of string based date filtering

- **Summarizer verbosity not scaled to result size** — The summarizer always produced a full narrative regardless of data volume; fixed by adding three output modes (Compact/Standard/Oversized) that adjust headline length, narrative, and follow-up count based on row count (1–5 / 6–49 / 50+).



