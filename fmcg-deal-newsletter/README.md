# FMCG Deal Intelligence Newsletter — Day 1

Pipeline stage complete: **Ingestion → Cleaning/De-duplication → Scoring**

Day 2 will add: LLM (Gemini) relevance refinement, newsletter generation, and the Streamlit demo app.

## Pipeline Overview

```
[Google News RSS] 
        │
        ▼
1. INGESTION (ingest.py)
   - Queries built from FMCG company list x deal keywords
   - Last 10 days (config.LOOKBACK_DAYS)
   - No API key required
        │
        ▼
2. CLEANING / DEDUP (dedup.py)
   - Exact dedup: normalized URL + normalized title match
   - Near-dedup: fuzzy title similarity (rapidfuzz, threshold 85)
   - Tracks "also_covered_by" -> used later as a corroboration signal
        │
        ▼
3. SCORING (score.py)
   - relevance_score   : keyword/entity rule match (is this an FMCG deal?)
   - credibility_score : static source-tier lookup (is the publisher reliable?)
   - confidence_score  : content signals — deal amount present, definitive
                         vs speculative language, cross-source corroboration
                         (is THIS article well-evidenced?)
   - combined_score = 0.45*relevance + 0.30*credibility + 0.25*confidence
   - include_in_newsletter = combined_score >= 0.55
```

## Why three separate scores instead of one?

- **Relevance** answers "is this about an FMCG deal at all?"
- **Credibility** answers "do we generally trust this publisher?" — a static
  assumption-based tier list (Reuters/Bloomberg/FT = high, known trade press
  = medium, unknown = 0.5 default).
- **Confidence** answers "is this specific claim well-evidenced?" — a
  credible outlet can still report a vague rumor ("in talks to acquire..."),
  and a lesser-known outlet can carry a fully-confirmed deal with hard
  numbers. Separating these avoids conflating "who published it" with
  "how solid is the claim."

This is rule-based and fully transparent for Day 1. Day 2 adds an LLM pass
(Gemini) as a second, more nuanced relevance/summary layer on top of this
baseline — not a replacement for it.

## Known limitations / assumptions (stated explicitly)

- Credibility tiers are a manually curated, illustrative list — not a
  verified media-bias/fact-check database. Extend `CREDIBILITY_TIERS` in
  `config.py` as needed.
- Google News RSS sometimes surfaces `news.google.com` redirect URLs rather
  than the final publisher domain, which can cause a known-credible source
  to fall back to the default score. Noted as future work (resolve redirect
  before domain lookup).
- Near-dedup uses fuzzy title matching (cheap, explainable). At larger scale
  this would be replaced with sentence-embedding similarity for better
  recall on stories with very different headlines.
- Ingestion query set favors precision (company name + keyword pairs) over
  recall, to keep query volume manageable within a 2-day build.

## How to run

```bash
pip install -r requirements.txt
cd src
python main.py
```

Outputs land in `data/`:
- `raw_articles.json` — Stage 1 output
- `deduped_articles.json` — Stage 2 output
- `scored_articles.csv` / `scored_articles.json` — Stage 3 output (final, sorted by combined_score)

## Repo structure
```
fmcg-deal-newsletter/
├── README.md
├── requirements.txt
├── src/
│   ├── config.py       (keyword lists, weights, thresholds)
│   ├── ingest.py        (Stage 1)
│   ├── dedup.py          (Stage 2)
│   ├── score.py           (Stage 3)
│   └── main.py             (runs all three stages)
└── data/                    (pipeline outputs, generated on run)
```
