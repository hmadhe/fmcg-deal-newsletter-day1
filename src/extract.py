"""
Stage 4: LLM-based structured extraction (Gemini).

Day 1's rule-based scoring already filtered out obvious noise cheaply.
This stage runs Gemini ONLY on the shortlist that already passed that
filter — a second, more nuanced relevance pass, not a replacement for
the rules. This keeps API calls low and cost/latency predictable, and
means the rule-based stage still functions as a safety net if the LLM
call fails or the API key is missing.

For each shortlisted article, Gemini returns structured JSON: whether
it's genuinely an FMCG deal, the deal type, parties involved, deal
value if stated, and a one-line summary. Facts extracted here are used
as-is in the newsletter (Stage 5) rather than being re-generated later,
so a hallucination at this stage is visible/traceable to one article's
source link rather than buried in free-form prose.
"""
from llm_client import call_gemini_json
from config import TOP_N_FOR_EXTRACTION

EXTRACTION_PROMPT_TEMPLATE = """You are analyzing a news article for an FMCG (Fast-Moving Consumer Goods) industry deal newsletter.

Article title: {title}
Article snippet: {snippet}
Source: {source}
Published: {published}

Determine if this article describes a genuine FMCG-related M&A deal, investment, funding round, or joint venture.

Respond ONLY with a JSON object in this exact format, no other text, no markdown fences:
{{
  "is_fmcg_deal": true or false,
  "confidence": a number between 0 and 1,
  "deal_type": one of ["acquisition", "merger", "investment", "stake_sale", "joint_venture", "funding_round", "other", "not_a_deal"],
  "acquirer_or_investor": "company name or null",
  "target_or_investee": "company name or null",
  "deal_value": "stated amount with currency, or null if not mentioned in the text",
  "one_line_summary": "a single crisp sentence summarizing the deal, written for a business newsletter reader"
}}

Only state a deal_value if a number is explicitly present in the article text above — never estimate or infer one.
If the article is NOT about a genuine FMCG deal, set is_fmcg_deal to false and one_line_summary to a brief note explaining why (e.g. "General company news, not a deal").
"""


def extract_deal_info(article):
    """Calls Gemini once for a single article, returns the article enriched
    with an 'llm_extraction' field. Falls back gracefully if the call fails
    so one bad article/API hiccup doesn't crash the whole run."""
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
        title=article.get("title", ""),
        snippet=article.get("snippet", ""),
        source=article.get("source", ""),
        published=article.get("published", ""),
    )
    try:
        result = call_gemini_json(prompt)
    except Exception as e:
        result = {
            "is_fmcg_deal": None,  # unknown, not confirmed false — kept in shortlist
            "confidence": 0.0,
            "deal_type": "other",
            "acquirer_or_investor": None,
            "target_or_investee": None,
            "deal_value": None,
            "one_line_summary": f"[LLM extraction unavailable: {e}]",
        }
    return {**article, "llm_extraction": result}


def extract_for_shortlist(scored_articles, top_n=TOP_N_FOR_EXTRACTION):
    """
    Runs Gemini extraction on the top-N rule-scored articles that already
    passed the Day 1 include_in_newsletter threshold, then drops anything
    Gemini explicitly flags as NOT a genuine deal (a nuance the keyword
    rules can miss — e.g. "Nestle donates to charity" contains a company
    name + no deal keyword mismatch that rules alone might still let through
    in edge cases).
    """
    shortlist = [a for a in scored_articles if a.get("include_in_newsletter")][:top_n]
    print(f"Running Gemini extraction on top {len(shortlist)} shortlisted articles...")

    enriched = []
    for i, article in enumerate(shortlist, 1):
        print(f"  [{i}/{len(shortlist)}] {article['title'][:70]}")
        enriched.append(extract_deal_info(article))

    # Keep True and None (extraction failed — err toward inclusion),
    # drop only explicit False (Gemini confirmed this is NOT a deal)
    final = [a for a in enriched if a["llm_extraction"].get("is_fmcg_deal") is not False]
    print(f"Gemini confirmed {len(final)}/{len(enriched)} as genuine FMCG deals")
    return final


if __name__ == "__main__":
    import json
    with open("../data/scored_articles.json", "r", encoding="utf-8") as f:
        scored = json.load(f)

    enriched = extract_for_shortlist(scored)

    with open("../data/enriched_articles.json", "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)
    print("Saved -> data/enriched_articles.json")
