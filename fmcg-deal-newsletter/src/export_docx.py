"""
Renders the structured newsletter dict (from newsletter_gen.build_newsletter)
into a formatted Word document using python-docx.
"""
import os
from docx import Document
from docx.shared import Pt, RGBColor

BRAND_COLOR = RGBColor(0x1F, 0x4E, 0x79)


def export_newsletter_to_docx(newsletter, output_path="../output/newsletter.docx"):
    doc = Document()

    title = doc.add_heading(newsletter["title"], level=0)
    for run in title.runs:
        run.font.color.rgb = BRAND_COLOR

    meta = doc.add_paragraph()
    meta_run = meta.add_run(f"Period: {newsletter['period']}   |   Generated: {newsletter['generated_on']}")
    meta_run.italic = True
    meta_run.font.size = Pt(10)

    doc.add_heading("Executive Summary", level=1)
    doc.add_paragraph(newsletter["executive_summary"])

    doc.add_heading(f"Top Deals This Period ({len(newsletter['top_deals'])})", level=1)
    for deal in newsletter["top_deals"]:
        _add_deal_block(doc, deal, heading_level=2)

    if newsletter["other_deals"]:
        doc.add_heading("Other Notable Activity", level=1)
        for deal in newsletter["other_deals"]:
            _add_deal_block(doc, deal, heading_level=3)

    doc.add_page_break()
    doc.add_heading("Methodology", level=1)
    doc.add_paragraph(
        f"Generated from {newsletter['total_deals_found']} deduplicated, relevance- and "
        "credibility-scored FMCG news articles, refined using Gemini-based structured "
        "extraction. Deal facts are taken directly from extraction output; only the "
        "executive summary above is LLM-generated free-form prose. Each deal card links "
        "back to its original source article for verification."
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path


def _add_deal_block(doc, deal, heading_level=2):
    h = doc.add_heading(deal["headline"], level=heading_level)
    for run in h.runs:
        run.font.color.rgb = BRAND_COLOR

    p = doc.add_paragraph()
    p.add_run(f"{deal['acquirer']} \u2192 {deal['target']}").bold = True
    p.add_run(f"   |   {deal['deal_type'].replace('_', ' ').title()}   |   {deal['deal_value']}")

    doc.add_paragraph(deal["summary"])

    src_p = doc.add_paragraph()
    src_run = src_p.add_run(f"Source: {deal['source']}")
    src_run.italic = True
    src_run.font.size = Pt(9)
    if deal.get("also_covered_by"):
        also_run = src_p.add_run(f"  (also covered by: {', '.join(deal['also_covered_by'])})")
        also_run.italic = True
        also_run.font.size = Pt(9)


if __name__ == "__main__":
    import json
    with open("../data/newsletter.json", "r", encoding="utf-8") as f:
        newsletter = json.load(f)
    path = export_newsletter_to_docx(newsletter)
    print(f"Saved -> {path}")
