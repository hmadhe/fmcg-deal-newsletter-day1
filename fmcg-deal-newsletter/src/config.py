# --- FMCG companies to track (expand as needed) ---
FMCG_COMPANIES = [
    "Unilever", "Nestle", "Procter & Gamble", "P&G", "Reckitt",
    "Colgate-Palmolive", "Danone", "Mondelez", "Kraft Heinz",
    "PepsiCo", "Coca-Cola", "Hindustan Unilever", "HUL", "ITC",
    "Dabur", "Britannia", "Godrej Consumer", "Marico", "Nirma",
    "Tata Consumer", "Patanjali", "L'Oreal", "Kimberly-Clark"
]

# --- Deal-type keywords ---
DEAL_KEYWORDS = [
    "acquires", "acquisition", "acquire", "merger", "merges",
    "stake", "invests in", "investment", "funding round",
    "buys", "to acquire", "raises funding", "takeover",
    "divests", "joint venture", "stake sale"
]

# --- Generic FMCG sector terms (used to catch deals not naming a big company) ---
FMCG_SECTOR_TERMS = [
    "FMCG", "consumer goods", "packaged goods", "consumer products",
    "personal care", "beverage company", "snack brand", "D2C brand"
]

# --- Language signals for confidence scoring ---
DEFINITIVE_TERMS = [
    "has acquired", "completed the acquisition", "announced the acquisition",
    "has agreed to acquire", "finalizes", "closes deal"
]
SPECULATIVE_TERMS = [
    "in talks", "may consider", "reportedly", "exploring options",
    "considering a bid", "sources say", "could acquire"
]

# --- Credibility tiers (domain -> score). Extend freely. ---
CREDIBILITY_TIERS = {
    "reuters.com": 1.0, "bloomberg.com": 1.0, "ft.com": 1.0,
    "wsj.com": 1.0, "economictimes.indiatimes.com": 0.9,
    "livemint.com": 0.85, "business-standard.com": 0.85,
    "moneycontrol.com": 0.8, "cnbc.com": 0.85,
    "techcrunch.com": 0.75, "forbes.com": 0.75,
    "businesswire.com": 0.7, "prnewswire.com": 0.7,
}
DEFAULT_CREDIBILITY = 0.5  # unknown source fallback — stated assumption

# --- Scoring weights (relevance + credibility + confidence = 1.0) ---
RELEVANCE_WEIGHT = 0.45
CREDIBILITY_WEIGHT = 0.30
CONFIDENCE_WEIGHT = 0.25
INCLUDE_THRESHOLD = 0.55  # below this -> dropped from newsletter candidates

# --- Dedup ---
# Tune this if you see the same story slipping through as two entries,
# or conversely two genuinely different deals getting merged.
NEAR_DUP_TITLE_SIMILARITY_THRESHOLD = 85  # rapidfuzz score, 0-100

# --- Ingestion window ---
LOOKBACK_DAYS = 10

# --- Day 2: Gemini / newsletter settings ---
# Uses the current google-genai SDK. If this model name is ever retired,
# check available models at https://ai.google.dev/gemini-api/docs/models
GEMINI_MODEL = "gemini-flash-lite-latest"
# Only the top-N rule-scored articles go to Gemini for structured extraction —
# keeps API calls low/cost predictable. Rules pre-filter, Gemini refines.
TOP_N_FOR_EXTRACTION = 12
