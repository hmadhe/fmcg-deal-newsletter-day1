"""
Stage 2: Cleaning / De-duplication
Two passes:
  1. Exact dedup: same URL (normalized) or identical title
  2. Near-dedup: fuzzy title match (same story, different outlets/phrasing)
     Also records "also_covered_by" -> used later as a corroboration
     signal for confidence scoring.
"""
import json
import re
from urllib.parse import urlparse
from rapidfuzz import fuzz
from config import NEAR_DUP_TITLE_SIMILARITY_THRESHOLD


def normalize_url(url):
    """Strip tracking params so the same article isn't counted twice
    just because of different ?utm_source= values."""
    parsed = urlparse(url)
    return f"{parsed.netloc}{parsed.path}".rstrip("/").lower()


def normalize_title(title):
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    return re.sub(r"\s+", " ", title).strip()


def exact_dedup(articles):
    seen_urls = set()
    seen_titles = set()
    deduped = []

    for a in articles:
        norm_url = normalize_url(a["url"])
        norm_title = normalize_title(a["title"])

        if norm_url in seen_urls or norm_title in seen_titles:
            continue

        seen_urls.add(norm_url)
        seen_titles.add(norm_title)
        deduped.append(a)

    print(f"Exact dedup: {len(articles)} -> {len(deduped)}")
    return deduped


def near_dedup(articles):
    """
    O(n^2) fuzzy comparison — fine for a few hundred articles (this scale).
    For production scale, replace with embedding + vector similarity search.
    """
    kept = []
    dropped_count = 0

    for article in articles:
        is_duplicate = False
        norm_title = normalize_title(article["title"])

        for kept_article in kept:
            kept_norm_title = normalize_title(kept_article["title"])
            similarity = fuzz.token_set_ratio(norm_title, kept_norm_title)

            if similarity >= NEAR_DUP_TITLE_SIMILARITY_THRESHOLD:
                is_duplicate = True
                kept_article.setdefault("also_covered_by", [])
                kept_article["also_covered_by"].append(article["source"])
                break

        if not is_duplicate:
            kept.append(article)
        else:
            dropped_count += 1

    print(f"Near dedup: dropped {dropped_count} near-duplicate articles, {len(kept)} remain")
    return kept


def run_dedup_pipeline(articles):
    step1 = exact_dedup(articles)
    step2 = near_dedup(step1)
    return step2


if __name__ == "__main__":
    with open("../data/raw_articles.json", "r", encoding="utf-8") as f:
        articles = json.load(f)

    deduped = run_dedup_pipeline(articles)

    with open("../data/deduped_articles.json", "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    print("Saved -> data/deduped_articles.json")
