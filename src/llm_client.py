"""
Thin wrapper around the Gemini API so the rest of the pipeline never
touches the google-genai SDK directly. Two entry points:
  - call_gemini_json(prompt)  -> forces JSON output, retries on parse failure
  - call_gemini_text(prompt)  -> free-form prose (used for the executive summary)

Uses the current `google-genai` SDK (the older `google-generativeai`
package is deprecated as of 2025 and is intentionally not used here).

API key resolution order: Streamlit secrets -> environment variable.
This lets the same code run both in the Streamlit app (secrets.toml or
sidebar input) and as a standalone script (export GEMINI_API_KEY=...).
"""
import os
import json
from google import genai
from google.genai import types
from config import GEMINI_MODEL


def get_api_key():
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # not running inside Streamlit, or no secrets.toml -- fall through
    return os.environ.get("GEMINI_API_KEY")


def get_client():
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Set it as an environment variable, "
            "in .streamlit/secrets.toml, or via the Streamlit sidebar input."
        )
    return genai.Client(api_key=api_key)


def call_gemini_json(prompt, model_name=GEMINI_MODEL, max_retries=2):
    """
    Calls Gemini with response_mime_type='application/json' so the model
    is constrained to return valid JSON. Retries on parse failure since
    LLM JSON output can occasionally be malformed on the first try.
    """
    client = get_client()
    config = types.GenerateContentConfig(response_mime_type="application/json")

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name, contents=prompt, config=config
            )
            text = response.text.strip()
            return json.loads(text)
        except json.JSONDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Gemini JSON call failed after {max_retries + 1} attempts: {last_error}")


def call_gemini_text(prompt, model_name=GEMINI_MODEL):
    """Free-form text generation -- used only for the executive summary,
    never for facts/numbers that must be traceable to a source article."""
    client = get_client()
    response = client.models.generate_content(model=model_name, contents=prompt)
    return response.text.strip()
