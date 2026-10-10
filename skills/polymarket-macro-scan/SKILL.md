---
name: polymarket-macro-scan
description: "Use for biweekly Polymarket macro scan knowledge base."
---

# Polymarket Macro Scan — biweekly event-market knowledge base

Snapshots 9 Polymarket category pages every other week (screenshots + structured market data + scan.md), stores them as a knowledge base, and feeds macro priors into `decision-prediction` stock analysis.

## When to use

Use only an available, authorized host research tool and explicit private destination; record actual model/usage only if reported. No schedule or provider integration is supplied.
Use only an available, authorized host research tool and explicit private destination; record actual model/usage only if reported. No schedule or provider integration is supplied.
- Any request to refresh macro priors before a stock analysis (fed rates, geopolitics, inflation, labor).

## Model & cost

Use only an available, authorized host research tool and explicit private destination; record actual model/usage only if reported. No schedule or provider integration is supplied.
- Keep it bounded: 1 screenshot per page (9 total), one Gamma API call per category, ≤5 X searches.

## Scope — 9 category pages

| # | Page | URL |
|---|---|---|
| 1 | Geopolitics | https://polymarket.com/geopolitics |
| 2 | Economy | https://polymarket.com/economy |
| 3 | Finance | https://polymarket.com/finance |
| 4 | Politics | https://polymarket.com/politics |
| 5 | Inflation | https://polymarket.com/economy/inflation |
| 6 | Macro indicators | https://polymarket.com/economy/macro-indicators |
| 7 | Fed rates | https://polymarket.com/economy/fed-rates |
| 8 | Consumer | https://polymarket.com/economy/consumer |
| 9 | Labor | https://polymarket.com/economy/labor |

## Storage

Use only an available, authorized host research tool and explicit private destination; record actual model/usage only if reported. No schedule or provider integration is supplied.
Use only an available, authorized host research tool and explicit private destination; record actual model/usage only if reported. No schedule or provider integration is supplied.
- Delta baseline: most recent earlier `scan.md` in the KB.

## Capture protocol

1. `mkdir -p "$HOME/Documents/Polymarket-Scans/$(date +%F)/shots"`.
2. For each of the 9 URLs:
   - `browser_navigate(url)`; wait for markets to render.
   - Take ONE screenshot (save to `shots/NN-category.png`). Do not screenshot every scroll position.
   - Structured data via Gamma API (no auth):
     - Resolve the tag slug: `GET https://gamma-api.polymarket.com/tags`, match by category slug (e.g. `inflation`, `fed-rates`, `geopolitics`, `labor`). If no tag maps, fall back to `GET /public-search?q=CATEGORY`.
     - `GET https://gamma-api.polymarket.com/events?tag=SLUG&limit=15&active=true&closed=false&order=volume&ascending=false`
     - Parse with python: `outcomePrices` is a JSON **string** (double-encoded) → `json.loads(market['outcomePrices'])`; Yes% = `float(prices[0])*100`; record `volume` (USDC).
   - Redundancy: if the API fails, rely on screenshot + page snapshot text. If the browser fails, API-only. Never block the whole scan on one path.
Use only an available, authorized host research tool and explicit private destination; record actual model/usage only if reported. No schedule or provider integration is supplied.
4. Delta: compare each captured market against the previous scan by question text; flag moves ≥5 points.

## scan.md template

```markdown
# Polymarket Macro Scan — YYYY-MM-DD
Use only an available, authorized host research tool and explicit private destination; record actual model/usage only if reported. No schedule or provider integration is supplied.

## 1 Geopolitics (measured)
| Market | Yes % | Volume | Δ vs prev |
|---|---|---|---|
| ... | 65.2% | $1.2M | +3 |

## 2 Economy
... (same per category, 9 sections)

## Biggest moves (delta)
- Market X: 40% → 55% (+15) — what happened?

## X sentiment (modeled)
- fed/rate/inflation/defense/war posts gist

## Macro → portfolio mapping (narrative, not advice)
| Signal | Portfolio read | Barbell sleeve |
|---|---|---|
| ... | ... | ... |

## TL;DR
- Top 3 macro signals + what they imply for AI / defense / minerals & energy / fintech.
```

## Macro → portfolio mapping (barbell: AI · defense · minerals & energy · fintech)

| Signal (Polymarket odds) | Portfolio read | Positions to watch |
|---|---|---|
| Fed cut odds rise | Growth/AI re-rate | GOOG, NVDA, AVGO, AMAT, META, TSM |
| War / geopolitics escalation | Defense + energy bid | RTX, NOC, LMT, KTOS, LDOS, BE |
| Inflation sticky or up | Minerals & energy bid | FCX, MP, CLSK, TE |
| Recession odds rise | Defensives, cash; compare downside sensitivities | compare hypothetical downside resilience |
| Election / policy shock | Volatility up; fintech watch | fintech sleeve |
| Rate-hike / hawkish odds | Compression for growth | test valuation sensitivity |

## Evidence discipline

- Source-reported API quotes can be **Measured**; screenshots are **Observed · unconfirmed** (record capture time + source URL).
- What the odds *imply* for a portfolio = **modeled / narrative** — label it.
- Polymarket % is an implied probability with skin in the game — a market-implied expectation, not an automatically calibrated base rate. Never let it replace a DCF.
Use only an available, authorized host research tool and explicit private destination; record actual model/usage only if reported. No schedule or provider integration is supplied.

## Pitfalls

- `outcomePrices`, `outcomes`, `clobTokenIds` are double-encoded JSON strings — always `json.loads`.
- Verify tag slugs via `/tags`; they change. Fall back to `/public-search` on mismatch.
- 9 screenshots max per run — more is waste, not evidence.
- This is a knowledge base, not a trade signal. No portfolio changes from a scan alone.
- Keep it cheap: one model, bounded calls, no expensive pipelines.
