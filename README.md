# Daily Movers Agent

An AI-powered stock analysis system that automates the daily market-movers research workflow. UiPath scrapes Yahoo Finance; a LangGraph multi-agent pipeline analyzes each stock and produces an Excel report and a plain-text summary.

---

## Business Concept

### Problem
Each morning, analysts manually visit financial sites to identify top movers, read articles for context, and summarize insights. By the time results are shared, the market has already shifted.

### Stakeholders
- **Executives** — need a concise daily digest with top movers and recommendations.
- **Analysts** — need a detailed, sortable Excel workbook they can work with directly.
- **IT / Operations** — need a reliable automated system with minimal maintenance.

### Output Channel Rationale
| Channel | Audience | Why |
|---|---|---|
| Excel (2 sheets) | Analysts | Rich data, styled highlights, sortable. Raw sheet is UiPath-safe (no merged cells). |
| Plain-text summary (.txt) | Executives | Zero-dependency digest: top gainer, top loser, top 3 recommendations. |

Both channels are produced in a single pipeline run. The Excel workbook is the source of truth; the `.txt` summary is a curated extract.

---

## Technical Overview

### Architecture

```
┌─────────────────────────────────────────┐
│  UiPath Robot                           │
│  scrapes Yahoo Finance Most Active      │
│  writes ──► input.json                  │
│  triggers ─► uipath run agent --file    │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  LangGraph Pipeline                     │
│                                         │
│  START ──► research ──► analyst         │
│              ▲              │            │
│              │              ▼            │
│         supervisor ◄── strategist       │
│              │  (loop while stocks remain)│
│              ▼                          │
│           report ──► email ──► END      │
└─────────────────────────────────────────┘
```

### Agent Nodes

| Node | Responsibility |
|---|---|
| **research** | Calls Google Search (via Serper API) for current stock news. Gemini summarizes the raw results into `news_summary` + `key_events`. |
| **analyst** | Evaluates price action, volume, valuation (P/E, market cap), and sentiment. Outputs `technical_analysis` + `sentiment`. |
| **strategist** | Produces a `Buy / Hold / Sell` recommendation with a `confidence` score (0–1) and plain-English `reasoning`. |
| **supervisor** | Advances the loop index. When all stocks are processed, routes to the output phase. |
| **report** | Builds the two-sheet Excel workbook with highlights (green = top gainer, red = top loser, gold = top 3 recommendations). |
| **email** | Composes a plain-text summary (top gainer, top loser, top 3 recommendations) and writes it to `daily_movers_summary_YYYYMMDD.txt`. |

### Data Contract: input.json

This is the interface between UiPath and the agent. UiPath writes it after scraping; the agent reads it at startup. A sample payload is checked in for local debugging. Fields match the Yahoo Finance Most Active page:

| Field | Type | Example |
|---|---|---|
| ticker | str | "NVDA" |
| company_name | str | "NVIDIA Corporation" |
| price | float | 180.35 |
| change | float | -5.26 |
| change_percent | float | -2.83 |
| volume | int | 182108000 |
| avg_volume_3m | int | 181311000 |
| market_cap | str | "4.391T" |
| pe_ratio | float \| null | 47.31 or null |
| week_52_change_pct | float | 48.69 |
| week_52_low | float | 86.62 |
| week_52_high | float | 196.95 |

---

## Setup

1. Copy `.env.example` → `.env`. Fill in `GOOGLE_API_KEY` (Gemini) and `SERPER_API_KEY`.
2. `pip install -e .`
3. `uipath init` (generates `entry-points.json` for cloud deployment).

## Running

### With UiPath (production)
UiPath scrapes Yahoo Finance and invokes the agent automatically.

### Locally (debug)
```bash
# input.json is already populated with sample data — run directly:
uipath run agent --file input.json
```

The agent processes all 20 stocks and writes two files to the working directory:
- `daily_movers_report_YYYYMMDD.xlsx` — full two-sheet workbook
- `daily_movers_summary_YYYYMMDD.txt` — plain-text digest

## Key Files

| File | Role |
|---|---|
| `state.py` | TypedDict schemas — `StockData`, `AgentState`, etc. |
| `agents.py` | LLM nodes: research, analyst, strategist, supervisor |
| `graph.py` | LangGraph wiring and conditional loop routing |
| `output.py` | Excel workbook builder and plain-text summary writer |
| `tools.py` | Google Serper search wrapper |
| `input.json` | Sample input — 20 stocks with all Yahoo Finance fields |
| `langgraph.json` | LangGraph deployment entry point |
| `tests/` | Unit tests for state schema and output highlight logic |

---

## Optional Improvements

### Agent Evaluation
The pipeline currently produces recommendations without measuring their quality over time. An eval layer would close that loop:
- **Confidence calibration** — bucket recommendations by the strategist's `confidence` score and check whether high-confidence calls actually outperform low-confidence ones.
- **LLM-as-judge** — have a separate Gemini call score each analyst output for reasoning coherence and factual consistency against the research summary, without needing ground-truth labels.
- **Regression suite** — store a small set of known inputs and their expected recommendation outputs so that model or prompt changes don't silently degrade quality.

### Other ideas
- **Visual summary** — generate a chart-based digest (e.g. a bar chart of daily price changes, a color-coded heatmap of Buy/Hold/Sell recommendations) so that the daily output is glanceable without opening the full workbook. Could be rendered as a PNG image embedded in the `.txt` summary.
- **Cost tracking** — log token usage per stock so the per-run cost is visible and can be optimised.
