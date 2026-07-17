"""
Stage 3: Scoring
Three separate, explainable signals combined into one score:

  - relevance_score   : is this article about an FMCG deal at all?
                        (keyword/entity match on title+snippet)
  - credibility_score : is the *publisher* generally reliable?
                        (static domain -> tier lookup)
  - confidence_score  : is *this specific article* well-evidenced?
                        (concrete deal amount, definitive vs speculative
                        language, cross-source corroboration from dedup)

Rule-based only for Day 1 — an LLM-based relevance refinement
(Gemini) is added on Day 2 as a second pass on top of this baseline.
"""
import re
import json
import pandas as pd
from urllib.parse import urlparse
from config import (
    FMCG_COMPANIES, DEAL_KEYWORDS, FMCG_SECTOR_TERMS,
    DEFINITIVE_TERMS, SPECULATIVE_TERMS,
    CREDIBILITY_TIERS, DEFAULT_CREDIBILITY,
    RELEVANCE_WEIGHT, CREDIBILITY_WEIGHT, CONFIDENCE_WEIGHT,
    INCLUDE_THRESHOLD
)


def get_domain(url):
    return urlparse(url).netloc.replace("www.", "").lower()


def relevance_score(article):
    """
    +0.5 if a known FMCG company is named
    +0.4 if a deal keyword is present
    +0.1 if a generic sector term is present
    Capped at 1.0. Articles scoring 0 have neither a company nor a
    deal keyword and are almost certainly noise.
    """
    text = f"{article['title']} {article['snippet']}".lower()
    score = 0.0

    if any(company.lower() in text for company in FMCG_COMPANIES):
        score += 0.5
    if any(kw.lower() in text for kw in DEAL_KEYWORDS):
        score += 0.4
    if any(term.lower() in text for term in FMCG_SECTOR_TERMS):
        score += 0.1

    return min(score, 1.0)


def credibility_score(article):
    domain = get_domain(article["url"])
    return CREDIBILITY_TIERS.get(domain, DEFAULT_CREDIBILITY)


def confidence_score(article):
    """
    Content-based confidence — separate from source credibility.
    A Reuters article can still be a vague rumor; a smaller outlet can
    carry a fully-confirmed deal with hard numbers. This looks at the
    claim itself, not who published it.
    """
    text = f"{article['title']} {article['snippet']}".lower()
    score = 0.0

    # Signal 1: specific deal amount mentioned
    has_amount = bool(re.search(r'[\$₹€£]\s?\d+|\d+\s?(million|billion|crore|%)', text))
    if has_amount:
        score += 0.4

    # Signal 2: definitive vs speculative language
    if any(term in text for term in DEFINITIVE_TERMS):
        score += 0.3
    elif any(term in text for term in SPECULATIVE_TERMS):
        score -= 0.2  # penalize rumor-stage language

    # Signal 3: corroboration — picked up by multiple outlets during dedup
    also_covered = len(article.get("also_covered_by", []))
    if also_covered >= 1:
        score += min(0.3, also_covered * 0.15)

    return max(0.0, min(score, 1.0))


def score_articles(articles):
    scored = []
    for a in articles:
        rel = relevance_score(a)
        cred = credibility_score(a)
        conf = confidence_score(a)
        combined = round(
            RELEVANCE_WEIGHT * rel + CREDIBILITY_WEIGHT * cred + CONFIDENCE_WEIGHT * conf, 3
        )

        scored.append({
            **a,
            "relevance_score": rel,
            "credibility_score": cred,
            "confidence_score": conf,
            "combined_score": combined,
            "include_in_newsletter": combined >= INCLUDE_THRESHOLD,
        })

    scored.sort(key=lambda x: x["combined_score"], reverse=True)
    included = sum(1 for s in scored if s["include_in_newsletter"])
    print(f"Scored {len(scored)} articles — {included} pass threshold ({INCLUDE_THRESHOLD})")
    return scored


if __name__ == "__main__":
    with open("../data/deduped_articles.json", "r", encoding="utf-8") as f:
        articles = json.load(f)

    scored = score_articles(articles)

    df = pd.DataFrame(scored)
    df.to_csv("../data/scored_articles.csv", index=False)
    print("Saved -> data/scored_articles.csv")
