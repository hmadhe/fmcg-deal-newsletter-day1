# FMCG Deal Intelligence Newsletter

An agent that turns live, publicly available news into a short, structured
FMCG (Fast-Moving Consumer Goods) M&A / investment newsletter — end to end,
from raw RSS results to a downloadable Word doc and PowerPoint deck, with a
Streamlit demo app on top.

## What it does

- **Aggregates** deal-related FMCG news in real time from Google News RSS
  (no API key required for ingestion).
- **Removes duplicates and near-duplicates** (exact URL/title match, then
  fuzzy title similarity).
- **Filters for relevance** with a rule-based pass, then a Gemini LLM pass
  on the shortlist for nuance the rules alone would miss.
- **Scores source credibility** with a transparent, static tier list.
- **Generates a structured newsletter draft** — executive summary + deal
  cards, each traceable back to a source article — and exports it to
  Word and PowerPoint.
- Ships as a **Streamlit app** with a live run button and CSV/JSON/DOCX/PPTX
  downloads.

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
3. SCORING (score.py)  — rule-based, fully transparent
   - relevance_score   : keyword/entity rule match (is this an FMCG deal?)
   - credibility_score : source-tier lookup (is the publisher reliable?)
   - confidence_score  : content signals — deal amount present, definitive
                         vs speculative language, cross-source corroboration
                         (is THIS article well-evidenced?)
   - combined_score = 0.45*relevance + 0.30*credibility + 0.25*confidence
   - include_in_newsletter = combined_score >= 0.55
        │
        ▼
4. EXTRACTION (extract.py) — Gemini, shortlist only
   - Runs ONLY on articles that already passed the Stage 3 threshold
     (keeps LLM calls low and cost/latency predictable)
   - Returns structured JSON: is this a genuine deal, deal type, parties,
     deal value (only if explicitly stated), one-line summary
   - Drops anything Gemini explicitly flags as NOT a genuine deal — a
     second, more nuanced relevance pass on top of the Stage 3 rules
        │
        ▼
5. NEWSLETTER GENERATION (newsletter_gen.py)
   - Deal cards are built DETERMINISTICALLY from Stage 4's structured
     output — facts are placed as extracted, not re-generated, so they
     stay traceable to one source article
   - Cards are then MERGED by (acquirer, target): articles covering the
     same underlying deal under very differently-worded headlines (which
     Stage 2's fuzzy title match can miss) collapse into one deal record
     with every source listed, a corroboration count, and a confidence
     label — not shown as repeat entries
   - Executive summary paragraph is the one place a free-form Gemini
     pass is used (synthesis/commentary, not facts needing traceability)
        │
        ▼
[Streamlit app / export_docx.py / export_pptx.py]
   - Word (.docx) and PowerPoint (.pptx) newsletter exports
   - CSV/JSON download of the raw and scored data
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

Stages 1–3 are rule-based and fully transparent. Stage 4 adds Gemini as a
second, more nuanced relevance layer on top of that baseline — not a
replacement for it, and it never runs on articles the rules already
rejected.

## De-duplication logic (brief)

Two passes, in `dedup.py`:
1. **Exact dedup** — normalizes the URL (strips tracking params, lowercases,
   drops trailing slash) and the title (lowercase, strip punctuation), drops
   any article whose normalized URL *or* title has already been seen.
2. **Near-dedup** — for everything left, computes fuzzy title similarity
   (`rapidfuzz.token_set_ratio`) against every article already kept; a score
   ≥ 85 is treated as the same underlying story reported by a different
   outlet, and it's dropped rather than kept as a duplicate. Before
   dropping, the outlet name is recorded on the surviving article's
   `also_covered_by` list — that list becomes a corroboration signal in
   Stage 3's confidence score (a story picked up by multiple outlets is
   more likely to be a real, confirmed deal).

This is O(n²) — fine at the scale this pipeline runs at (a few hundred
articles per run). At larger scale it would be replaced with embedding
similarity + a vector index.

## Relevance-check logic (brief)

Two layers:
1. **Rule-based (Stage 3)** — an article scores relevance from 0–1 based on
   whether a known FMCG company is named (+0.5), a deal keyword like
   "acquires"/"merger"/"stake" is present (+0.4), and a generic sector term
   is present (+0.1). This is cheap and runs on every ingested article.
2. **LLM-based (Stage 4)** — Gemini re-checks only the articles that already
   passed the Stage 3 threshold and can explicitly say "this isn't actually
   a deal" (e.g. a company name mentioned in an unrelated CSR/charity story
   that happens to also contain a keyword like "acquires" elsewhere on the
   page). This catches edge cases keyword matching alone lets through,
   without paying LLM cost on the full raw stream.

The rule-based pass also applies two corrections found by inspecting real
ingested output (`config.NOISE_TERMS` / `COMPANY_NAME_EXCLUSIONS`):
- **Financial-report noise** — "acquires"/"acquired" also shows up
  constantly in routine stock-market wire content ("X Acquires 18,511
  Shares of Procter & Gamble," "ITC Hotels Q1 Results: PAT jumps 35%,"
  "Marico's acquired brands generate ₹1,552 crore") — none of that is an
  M&A deal. `NOISE_TERMS` detects this language and penalizes relevance
  rather than hard-excluding, since a genuine deal article can still
  mention quarterly context.
- **Company-name collisions** — a bare company name/initialism can match
  an unrelated company (e.g. "ITC" the FMCG conglomerate vs. "ITC
  Properties," an unrelated Hong Kong real-estate company).
  `COMPANY_NAME_EXCLUSIONS` lists known collisions to discount.

## Credibility-check logic (brief)

`score.py` looks up the publisher against a manually curated tier list in
`config.CREDIBILITY_TIERS` (Reuters/Bloomberg/FT/WSJ = 1.0, national
business press = 0.8–0.9, trade press/wire services = 0.7, unknown = 0.5
default). Google News RSS returns `article["url"]` as a `news.google.com`
redirect link rather than the publisher's real domain, so the lookup can't
rely on the URL — it matches against `article["source"]` instead (Google's
display name for the outlet, e.g. "Reuters", "The Economic Times"), first
as a direct key, then by name substring via `config.SOURCE_NAME_TIERS`.
This is a manually curated, illustrative list, not a verified media-bias or
fact-checking database — see Known Limitations below.

## Newsletter generation

`newsletter_gen.py` builds a structured dict — title, period, executive
summary, top deals, other notable activity — and `export_docx.py` /
`export_pptx.py` render it to Word and PowerPoint. Deal-card facts (parties,
deal type, deal value, summary) come directly from Stage 4's Gemini
extraction rather than being re-generated at this stage, so every fact in
the newsletter is traceable to a single source article and link. Only the
executive-summary paragraph is free-form LLM prose, with a deterministic
fallback (built from the deal list, no LLM) if that call fails.

**Deal merging (`merge_duplicate_deals`).** Two articles about the same
deal, phrased too differently to clear Stage 2's fuzzy title match (e.g.
"CMA reviews Danone's Huel acquisition" vs. "Competition watchdog probes
Danone's Huel takeover"), previously showed up as two separate cards for
the same story. Since Stage 4 already extracts a structured
acquirer/target per article, cards are grouped by that pair instead of by
title text: matching cards merge into a single deal record —

```
Deal ID: D001
Acquirer: Danone            Target: Huel
Deal Type: Acquisition      Deal Value: €1bn
Headline: <highest-scored article's headline>
Sources: Dairy News Today, Sharecast.com
Corroboration: 2 independent sources
Confidence: High
```

Confidence is a stated rule, not a model output: 2+ independent sources →
High; 1 source with a deal value stated → Medium; 1 source, no deal value →
Low. Cards where either side wasn't extracted ("Not specified") are kept
standalone rather than merged — grouping two unrelated deals just because
both failed extraction would be worse than not merging at all.

## Newsletter format

No specific format is mandated by the brief beyond "short, structured, and
skimmable by a business reader" — this is the format chosen, applied
consistently across the Streamlit app, Word export, and PowerPoint export:

- **Hero header** — title + a date-badge showing the reporting period, so
  the newsletter reads as a dated recurring digest rather than a one-off.
- **Prose-first executive summary** — a short paragraph immediately below
  the header, for a reader who only has ten seconds.
- **Deal cards** — one per distinct deal (near-duplicate articles merged,
  see below): headline, acquirer → target, deal type, deal value, one-line
  summary, and every corroborating source with a confidence label, for a
  reader who has two minutes.
- **Other Notable Activity** — condensed one-liners for lower-scored deals,
  so nothing is silently dropped from the period.
- **Methodology / sourcing footer** — article counts through each pipeline
  stage, so the numbers behind the newsletter are auditable.

Deliberately excluded: no author byline, no company branding, no
call-to-action, no social-share elements — this is an internal-style
research briefing, not a marketing page.

## Known limitations / assumptions (stated explicitly)

- Credibility tiers are a manually curated, illustrative list — not a
  verified media-bias/fact-check database. Extend `CREDIBILITY_TIERS` /
  `SOURCE_NAME_TIERS` in `config.py` as needed. Matching is done against
  Google's outlet display name, not a resolved publisher domain, so an
  outlet whose display name doesn't match any known alias falls back to
  the 0.5 default even if it's a reputable source.
- Near-dedup uses fuzzy title matching (cheap, explainable). At larger scale
  this would be replaced with sentence-embedding similarity for better
  recall on stories with very different headlines.
- Ingestion query set favors precision (company name + keyword pairs) over
  recall, to keep query volume manageable.
- The FMCG company list and RSS locale (`hl=en-IN&gl=IN`) are India-weighted
  by default — extend `FMCG_COMPANIES` in `config.py` for broader
  geographic coverage.
- Deal values are only ever taken from explicit numbers in the source text
  (Gemini is instructed never to estimate one) — many articles will
  correctly show "Undisclosed."
- Deal merging groups by exact (acquirer, target) name match after
  lowercasing/trimming — minor extraction variance (e.g. "Danone" vs.
  "Danone SA") won't merge. Future work: fuzzy or entity-resolution
  matching instead of exact string match.

## How to run

**Pipeline only (no LLM stages, CLI):**
```bash
pip install -r requirements.txt
cd src
python main.py
```
Outputs land in `data/`:
- `raw_articles.json` — Stage 1 output
- `deduped_articles.json` — Stage 2 output
- `scored_articles.csv` / `scored_articles.json` — Stage 3 output (final, sorted by combined_score)

**Full pipeline + Streamlit demo app (ingestion through newsletter export):**
```bash
pip install -r requirements.txt
cd src
streamlit run app.py
```
Enter a free Gemini API key in the sidebar (get one at
https://aistudio.google.com/apikey), or set it via `GEMINI_API_KEY` env var
/ `.streamlit/secrets.toml` (copy `.streamlit/secrets.toml.example`). Click
**Generate Newsletter** to run all 5 stages live and download the
newsletter as Word/PowerPoint/CSV/JSON.

## Repo structure
```
fmcg-deal-newsletter/
├── README.md
├── requirements.txt
├── .streamlit/secrets.toml.example
├── src/
│   ├── config.py          (keyword lists, weights, thresholds, tiers)
│   ├── ingest.py           (Stage 1 — RSS ingestion)
│   ├── dedup.py             (Stage 2 — cleaning / de-duplication)
│   ├── score.py              (Stage 3 — relevance/credibility/confidence)
│   ├── extract.py             (Stage 4 — Gemini structured extraction)
│   ├── newsletter_gen.py       (Stage 5 — newsletter assembly)
│   ├── llm_client.py            (thin Gemini API wrapper)
│   ├── export_docx.py            (Word export)
│   ├── export_pptx.py             (PowerPoint export)
│   ├── app.py                      (Streamlit demo app)
│   └── main.py                      (CLI runner: Stages 1–3 only)
├── data/                    (pipeline outputs, generated on run)
└── output/                  (newsletter.docx / newsletter.pptx, generated on run)
```

## Architecture Diagram
## Architecture

                Google News RSS
                       |
                       v
                  Ingestion
             (query + fetch, no API key)
                       |
                       v
              Dedup (exact + fuzzy)
                       |
                       v
                   Scoring
        (relevance, credibility, confidence)
                       |
                       v
              Gemini Extraction
             (LLM runs on shortlist only)
                       |
                       v
             Newsletter Assembly
           (merge duplicate deals + summary)
                       |
                       v
             Export: Word / PowerPoint


        Streamlit App
   (drives the run above, shows
   progress, offers downloads)


