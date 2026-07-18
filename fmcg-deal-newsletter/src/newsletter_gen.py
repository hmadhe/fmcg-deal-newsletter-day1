"""
Stage 5: Newsletter assembly.

Deliberately split into two parts with different reliability guarantees:

  1. Deal cards are built DETERMINISTICALLY from Gemini's structured
     extraction output (Stage 4) — company names, deal values, and
     summaries are placed into the newsletter exactly as extracted,
     not re-generated. This means facts are traceable back to a single
     source article rather than re-synthesized (and possibly altered)
     by a second LLM pass.

  2. The executive summary paragraph IS free-form Gemini output — this
     is commentary/synthesis across deals, not a fact needing traceability,
     so it's the one place a full LLM writing pass is appropriate.
"""
from datetime import datetime, timedelta
from llm_client import call_gemini_text
from config import LOOKBACK_DAYS

SUMMARY_PROMPT_TEMPLATE = """You are writing the opening paragraph of a weekly FMCG (Fast-Moving Consumer Goods) 
industry M&A newsletter for business readers.

Here are the deals covered this period:
{deal_list}

Write a single, punchy 3-4 sentence executive summary paragraph highlighting the overall
theme or pattern across these deals (e.g. consolidation, category focus, geography, deal size trend).
Do not invent any deal details not listed above. Do not use bullet points or markdown. Plain prose only.
"""


def build_deal_cards(enriched_articles):
    """Turns Gemini extraction output into clean, render-ready deal-card dicts."""
    cards = []
    for a in enriched_articles:
        ext = a.get("llm_extraction", {})
        cards.append({
            "headline": a["title"],
            "deal_type": ext.get("deal_type") or "other",
            "acquirer": ext.get("acquirer_or_investor") or "Not specified",
            "target": ext.get("target_or_investee") or "Not specified",
            "deal_value": ext.get("deal_value") or "Undisclosed",
            "summary": ext.get("one_line_summary") or a.get("snippet", "")[:200],
            "source": a.get("source", "Unknown"),
            "url": a.get("url", ""),
            "published": a.get("published", ""),
            "combined_score": a.get("combined_score", 0),
            "also_covered_by": a.get("also_covered_by", []),
        })
    return cards


def _normalize_name(name):
    if not name:
        return None
    name = name.strip().lower()
    return name if name and name != "not specified" else None


def merge_duplicate_deals(cards):
    """
    Multiple outlets often cover the same underlying deal under very
    different headlines ("CMA reviews Danone-Huel deal" vs "Competition
    watchdog probes Danone's Huel takeover") -- too different in wording to
    be caught by dedup.py's fuzzy title match, so they survive as separate
    cards. Stage 4 already extracts a structured acquirer/target per
    article, so group on that instead: cards agreeing on the same
    (acquirer, target) pair are the same deal and get merged into one
    record with every source listed, rather than shown twice.

    Cards where either side wasn't extracted (acquirer or target is
    "Not specified") are left standalone rather than merged -- grouping two
    unrelated deals just because both failed extraction would be worse
    than not merging at all.

    Confidence is a simple, stated rule, not a model output:
      - 2+ independent sources           -> High
      - 1 source, but a deal value stated -> Medium
      - 1 source, no deal value            -> Low
    """
    groups = {}
    order = []
    for card in cards:
        key = (_normalize_name(card["acquirer"]), _normalize_name(card["target"]))
        if key[0] is None or key[1] is None:
            key = ("__standalone__", id(card))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(card)

    merged = []
    for key in order:
        group = groups[key]
        group.sort(key=lambda c: c["combined_score"], reverse=True)
        primary = group[0]

        deal_value = next(
            (c["deal_value"] for c in group if c["deal_value"] not in (None, "Undisclosed")),
            primary["deal_value"],
        )

        sources = []
        for c in group:
            if c["source"] not in sources:
                sources.append(c["source"])
            for extra in c.get("also_covered_by", []):
                if extra not in sources:
                    sources.append(extra)

        if len(sources) >= 2:
            confidence = "High"
        elif deal_value not in (None, "Undisclosed"):
            confidence = "Medium"
        else:
            confidence = "Low"

        merged.append({
            "headline": primary["headline"],
            "acquirer": primary["acquirer"],
            "target": primary["target"],
            "deal_type": primary["deal_type"],
            "deal_value": deal_value,
            "summary": primary["summary"],
            "sources": sources,
            "corroboration_count": len(sources),
            "confidence": confidence,
            "url": primary["url"],
            "published": primary["published"],
            "combined_score": max(c["combined_score"] for c in group),
        })

    merged.sort(key=lambda c: c["combined_score"], reverse=True)
    for i, deal in enumerate(merged, 1):
        deal["deal_id"] = f"D{i:03d}"

    return merged


def generate_executive_summary(deal_cards):
    if not deal_cards:
        return "No qualifying FMCG deal activity was found in this period."

    deal_list_text = "\n".join(
        f"- {c['acquirer']} / {c['target']}: {c['deal_type']} ({c['deal_value']}) — {c['summary']}"
        for c in deal_cards
    )
    prompt = SUMMARY_PROMPT_TEMPLATE.format(deal_list=deal_list_text)

    try:
        return call_gemini_text(prompt)
    except Exception as e:
        # Deterministic fallback so the pipeline never blocks on this one call
        deal_types = sorted(set(c["deal_type"] for c in deal_cards))
        return (
            f"This period covered {len(deal_cards)} notable FMCG deal(s), spanning "
            f"{', '.join(t.replace('_', ' ') for t in deal_types)} activity. "
            f"(Auto-generated executive summary unavailable — {e})"
        )


def build_newsletter(enriched_articles):
    """Returns a structured newsletter dict, ready for docx/pptx rendering."""
    deal_cards = build_deal_cards(enriched_articles)
    deal_cards = merge_duplicate_deals(deal_cards)

    top_deals = deal_cards[:6]
    other_deals = deal_cards[6:12]

    period_end = datetime.now()
    period_start = period_end - timedelta(days=LOOKBACK_DAYS)

    return {
        "title": "FMCG Deal Intelligence Newsletter",
        "period": f"{period_start.strftime('%d %b %Y')} \u2013 {period_end.strftime('%d %b %Y')}",
        "generated_on": period_end.strftime("%d %b %Y, %H:%M"),
        "executive_summary": generate_executive_summary(top_deals),
        "top_deals": top_deals,
        "other_deals": other_deals,
        "total_deals_found": len(deal_cards),
    }


if __name__ == "__main__":
    import json
    with open("../data/enriched_articles.json", "r", encoding="utf-8") as f:
        enriched = json.load(f)

    newsletter = build_newsletter(enriched)

    with open("../data/newsletter.json", "w", encoding="utf-8") as f:
        json.dump(newsletter, f, indent=2, ensure_ascii=False)
    print("Saved -> data/newsletter.json")
