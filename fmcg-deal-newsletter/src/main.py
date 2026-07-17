"""
Day 1 pipeline runner: ingestion -> dedup -> scoring
Run from inside src/:   python main.py
Output lands in ../data/
"""
import os
import json
import pandas as pd
from ingest import ingest_all
from dedup import run_dedup_pipeline
from score import score_articles

os.makedirs("../data", exist_ok=True)

print("=" * 50)
print("STAGE 1: INGESTION")
print("=" * 50)
raw_articles = ingest_all()
with open("../data/raw_articles.json", "w", encoding="utf-8") as f:
    json.dump(raw_articles, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 50)
print("STAGE 2: CLEANING / DEDUPLICATION")
print("=" * 50)
deduped = run_dedup_pipeline(raw_articles)
with open("../data/deduped_articles.json", "w", encoding="utf-8") as f:
    json.dump(deduped, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 50)
print("STAGE 3: SCORING")
print("=" * 50)
scored = score_articles(deduped)
pd.DataFrame(scored).to_csv("../data/scored_articles.csv", index=False)
with open("../data/scored_articles.json", "w", encoding="utf-8") as f:
    json.dump(scored, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 50)
print("PIPELINE SUMMARY")
print("=" * 50)
print(f"Raw articles:      {len(raw_articles)}")
print(f"After dedup:       {len(deduped)}")
print(f"Passing threshold: {sum(1 for s in scored if s['include_in_newsletter'])}")
print("\nDone. Check data/scored_articles.csv for results.")
