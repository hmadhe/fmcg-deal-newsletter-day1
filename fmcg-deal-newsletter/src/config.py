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

# --- Non-deal noise signals: financial-report / stock-trading language that
# often co-occurs with a company name + a deal-keyword substring match
# (e.g. "PAT jumps", "acquires 18,511 Shares of") without describing an
# actual M&A transaction. Penalized rather than hard-excluded, since a
# genuine deal article can still legitimately mention quarterly context. ---
NOISE_TERMS = [
    "shares of", "shares acquired by", "q1 results", "q2 results", "q3 results", "q4 results",
    "quarterly results", "net profit", "pat jumps", "pat rises", "pat falls",
    "pat up", "pat down", "revenue grows", "revenue rises", "revenue falls",
    "profit rises", "profit falls", "profit jumps", "acquired brands",
    "shares fall", "shares decline", "shares rise", "shares gain", "shares jump",
    "yoy", "dividend", "price target", "stock price",
]
NOISE_PENALTY = 0.4

# --- Known company-name collisions: a bare name/initialism that also matches
# an unrelated company (e.g. "ITC" the FMCG conglomerate vs "ITC Properties,"
# an unrelated Hong Kong real-estate company). If any listed phrase is
# present, that company match is not counted for this article. Extend as
# new collisions are found. ---
COMPANY_NAME_EXCLUSIONS = {
    "itc": ["itc propertie", "itc holdings"],
}

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

# Google News RSS gives article["url"] as a news.google.com redirect link,
# not the publisher's real domain, so CREDIBILITY_TIERS can rarely be
# matched against the URL. article["source"] holds Google's display name
# for the outlet instead (e.g. "Reuters", "The Economic Times") -- this maps
# recognizable name substrings to the same tier score, matched
# case-insensitively against article["source"] in score.py.
SOURCE_NAME_TIERS = {
    "reuters": 1.0, "bloomberg": 1.0, "financial times": 1.0,
    "wall street journal": 1.0,
    "economic times": 0.9,
    "livemint": 0.85, "mint": 0.85, "business standard": 0.85,
    "moneycontrol": 0.8, "cnbc": 0.85,
    "techcrunch": 0.75, "forbes": 0.75,
    "business wire": 0.7, "pr newswire": 0.7, "prnewswire": 0.7,
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
LOOKBACK_DAYS = 30

# --- Day 2: Gemini / newsletter settings ---
# Uses the current google-genai SDK. If this model name is ever retired,
# check available models at https://ai.google.dev/gemini-api/docs/models
GEMINI_MODEL = "gemini-flash-lite-latest"
# Only the top-N rule-scored articles go to Gemini for structured extraction —
# keeps API calls low/cost predictable. Rules pre-filter, Gemini refines.
TOP_N_FOR_EXTRACTION = 12
