"""
Stage 1: Ingestion
Pulls recent news via Google News RSS for a set of FMCG-company and
deal-keyword queries. No API key required.
"""
import feedparser
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparser
from config import FMCG_COMPANIES, DEAL_KEYWORDS, FMCG_SECTOR_TERMS, LOOKBACK_DAYS

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def build_queries():
    """
    Build a manageable set of queries: each FMCG company paired with
    a couple of high-signal deal keywords, plus a few broad sector queries.
    """
    queries = []
    core_deal_terms = ["acquisition", "acquires", "merger", "stake", "invests in"]

    for company in FMCG_COMPANIES:
        for term in core_deal_terms[:2]:  # keep query count sane for a 2-day demo
            queries.append(f'"{company}" {term}')

    for sector_term in FMCG_SECTOR_TERMS:
        queries.append(f'{sector_term} acquisition OR merger OR funding')

    return queries


def fetch_articles_for_query(query, cutoff_date):
    encoded = urllib.parse.quote(query)
    url = GOOGLE_NEWS_RSS.format(query=encoded)
    feed = feedparser.parse(url)

    articles = []
    for entry in feed.entries:
        try:
            published = dtparser.parse(entry.published)
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except Exception:
            continue  # skip entries with unparseable dates

        if published < cutoff_date:
            continue

        source = entry.get("source", {}).get("title", "unknown")
        articles.append({
            "title": entry.title,
            "url": entry.link,
            "source": source,
            "published": published.isoformat(),
            "snippet": entry.get("summary", ""),
            "query": query,
        })
    return articles


def ingest_all():
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    queries = build_queries()
    all_articles = []

    print(f"Running {len(queries)} queries against Google News RSS...")
    for i, q in enumerate(queries, 1):
        try:
            results = fetch_articles_for_query(q, cutoff_date)
            all_articles.extend(results)
            print(f"[{i}/{len(queries)}] '{q}' -> {len(results)} articles")
        except Exception as e:
            # network hiccup on one query shouldn't kill the whole run
            print(f"[WARN] query failed: '{q}' — {e}")
            continue

    print(f"\nTotal raw articles collected: {len(all_articles)}")
    return all_articles


if __name__ == "__main__":
    articles = ingest_all()
    with open("../data/raw_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    print("Saved -> data/raw_articles.json")
