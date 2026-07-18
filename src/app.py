"""
Streamlit demo app.
Runs the full pipeline live: ingestion -> dedup -> rule-based scoring ->
Gemini extraction -> newsletter generation -> docx/pptx export.

Run: streamlit run app.py  (from inside src/)
"""
import os
import sys
import json

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest import ingest_all
from dedup import run_dedup_pipeline
from score import score_articles
from extract import extract_for_shortlist
from newsletter_gen import build_newsletter
from export_docx import export_newsletter_to_docx
from export_pptx import export_newsletter_to_pptx
from config import TOP_N_FOR_EXTRACTION

st.set_page_config(page_title="FMCG Deal Intelligence Newsletter", layout="wide", page_icon="📰")

st.title("📰 FMCG Deal Intelligence Newsletter Generator")
st.caption(
    "Live FMCG M&A news aggregation \u2192 de-duplication \u2192 relevance/credibility "
    "scoring \u2192 Gemini-powered extraction \u2192 newsletter generation"
)

# ---------------------------------------------------------------------------
# Sidebar: pipeline explanation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    st.markdown(
        "**Pipeline stages**\n\n"
        "1. Ingestion — Google News RSS\n"
        "2. Cleaning — exact + fuzzy de-dup\n"
        "3. Scoring — rule-based relevance/credibility/confidence\n"
        "4. Extraction — Gemini structured JSON (top candidates only)\n"
        "5. Newsletter — templated deal cards + Gemini executive summary"
    )
    st.markdown("---")
    st.caption(
        "Only articles that already pass Stage 3's rule-based threshold are "
        f"sent to Gemini (top {TOP_N_FOR_EXTRACTION}), to keep API usage low and predictable."
    )

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "pipeline_ran" not in st.session_state:
    st.session_state.pipeline_ran = False

# ---------------------------------------------------------------------------
# Run button
# ---------------------------------------------------------------------------
run_clicked = st.button("🚀 Generate Newsletter", type="primary")

if run_clicked:
    if not os.environ.get("GEMINI_API_KEY"):
        st.error("Gemini API key not found. Please set the GEMINI_API_KEY environment variable before starting the app.")
        st.stop()

    try:
        with st.status("Running pipeline...", expanded=True) as status:
            st.write("**Stage 1/5 — Ingestion:** querying Google News RSS...")
            raw_articles = ingest_all()
            st.write(f"→ {len(raw_articles)} raw articles collected")

            st.write("**Stage 2/5 — Cleaning:** removing duplicates & near-duplicates...")
            deduped = run_dedup_pipeline(raw_articles)
            st.write(f"→ {len(raw_articles)} → {len(deduped)} articles after dedup")

            st.write("**Stage 3/5 — Scoring:** relevance, credibility, confidence...")
            scored = score_articles(deduped)
            passing = sum(1 for s in scored if s["include_in_newsletter"])
            st.write(f"→ {passing} articles pass the relevance/credibility threshold")

            st.write(f"**Stage 4/5 — Gemini extraction** on top {TOP_N_FOR_EXTRACTION} candidates...")
            enriched = extract_for_shortlist(scored)
            st.write(f"→ Gemini confirmed {len(enriched)} genuine FMCG deals")

            st.write("**Stage 5/5 — Newsletter generation:** deal cards + executive summary...")
            newsletter = build_newsletter(enriched)
            st.write("→ Newsletter ready")

            status.update(label="Pipeline complete", state="complete")

        st.session_state.raw_articles = raw_articles
        st.session_state.deduped = deduped
        st.session_state.scored = scored
        st.session_state.enriched = enriched
        st.session_state.newsletter = newsletter
        st.session_state.pipeline_ran = True

    except Exception as e:
        st.error(f"Pipeline failed: {e}")
        st.stop()

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
if st.session_state.pipeline_ran:
    newsletter = st.session_state.newsletter

    st.markdown("---")
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1F4E79 0%, #2E6DA4 100%);
                    border-radius: 10px; padding: 1.75rem 2rem; margin-bottom: 1.5rem;">
            <span style="display:inline-block; background: rgba(255,255,255,0.15); color:#ffffff;
                        font-size:0.75rem; font-weight:600; letter-spacing:0.05em;
                        padding:0.25rem 0.75rem; border-radius:999px; margin-bottom:0.6rem;">
                {newsletter['period'].upper()}
            </span>
            <h1 style="color:#ffffff; margin:0.3rem 0 0.3rem 0; font-size:1.9rem;">{newsletter['title']}</h1>
            <p style="color:rgba(255,255,255,0.85); margin:0; font-size:0.9rem;">
                Generated {newsletter['generated_on']} &middot; {newsletter['total_deals_found']} deals tracked this period
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("###### EXECUTIVE SUMMARY")
    st.markdown(
        f"<p style='font-size:1.05rem; line-height:1.6;'>{newsletter['executive_summary']}</p>",
        unsafe_allow_html=True,
    )

    st.subheader(f"Top Deals ({len(newsletter['top_deals'])})")
    if not newsletter["top_deals"]:
        st.info("No deals cleared both the rule-based and Gemini relevance checks in this period.")
    for deal in newsletter["top_deals"]:
        with st.container(border=True):
            st.markdown(f"**{deal['headline']}**")
            st.markdown(
                f"{deal['acquirer']} \u2192 {deal['target']}  |  "
                f"*{deal['deal_type'].replace('_', ' ').title()}*  |  {deal['deal_value']}"
            )
            st.write(deal["summary"])
            n = deal["corroboration_count"]
            st.caption(
                f"Deal ID: {deal['deal_id']}  |  Sources: {', '.join(deal['sources'])}  |  "
                f"Corroboration: {n} independent source{'s' if n != 1 else ''}  |  "
                f"Confidence: {deal['confidence']}"
            )

    if newsletter["other_deals"]:
        st.subheader("Other Notable Activity")
        for deal in newsletter["other_deals"]:
            st.markdown(
                f"- **{deal['acquirer']} \u2192 {deal['target']}**: {deal['summary']} "
                f"({', '.join(deal['sources'])})"
            )

    st.markdown("---")
    st.caption(
        f"Sourced from {len(st.session_state.raw_articles)} raw articles \u2192 "
        f"{len(st.session_state.deduped)} after de-duplication \u2192 "
        f"{newsletter['total_deals_found']} deals included. Generated {newsletter['generated_on']}."
    )

    # -----------------------------------------------------------------
    # Downloads
    # -----------------------------------------------------------------
    st.markdown("---")
    st.header("Downloads")

    dl_col1, dl_col2, dl_col3, dl_col4 = st.columns(4)

    with dl_col1:
        docx_path = export_newsletter_to_docx(newsletter, "../output/newsletter.docx")
        with open(docx_path, "rb") as f:
            st.download_button(
                "📄 Word (.docx)", f, file_name="fmcg_newsletter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    with dl_col2:
        pptx_path = export_newsletter_to_pptx(newsletter, "../output/newsletter.pptx")
        with open(pptx_path, "rb") as f:
            st.download_button(
                "📊 PowerPoint (.pptx)", f, file_name="fmcg_newsletter.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

    with dl_col3:
        df_scored = pd.DataFrame(st.session_state.scored)
        st.download_button(
            "📋 Scored Data (CSV)", df_scored.to_csv(index=False),
            file_name="scored_articles.csv", mime="text/csv",
        )

    with dl_col4:
        st.download_button(
            "🗂️ Raw Data (JSON)", json.dumps(st.session_state.raw_articles, indent=2),
            file_name="raw_articles.json", mime="application/json",
        )

    # -----------------------------------------------------------------
    # Pipeline transparency: raw -> deduped -> scored tables
    # -----------------------------------------------------------------
    with st.expander("🔍 Inspect pipeline data (raw \u2192 deduped \u2192 scored)"):
        tab1, tab2, tab3 = st.tabs(["Raw Articles", "After Dedup", "Scored"])
        with tab1:
            st.dataframe(pd.DataFrame(st.session_state.raw_articles), use_container_width=True)
        with tab2:
            st.dataframe(pd.DataFrame(st.session_state.deduped), use_container_width=True)
        with tab3:
            st.dataframe(pd.DataFrame(st.session_state.scored), use_container_width=True)
else:
    st.info("Please set the GEMINI_API_KEY environment variable and then click **Generate Newsletter** to begin.")
