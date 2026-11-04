"""Shared styling for the ERP Sim suite.

Everything below is built on Streamlit's own theme CSS variables
(--background-color, --secondary-background-color, --text-color,
--primary-color) instead of hardcoded hex values, so the whole app follows
whatever theme the viewer has selected (Settings -> Choose app theme ->
Light / Dark / Use system) with no extra work.
"""

import streamlit as st

_CSS = """
<style>
    .block-container { padding-top: 2.5rem; padding-bottom: 3rem; max-width: 1200px; }

    /* ---- Module strip (small "what is X" explainer banner) ---- */
    .erp-strip {
        border-left: 4px solid var(--primary-color);
        background-color: var(--secondary-background-color);
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-bottom: 1.1rem;
        font-size: 0.92rem;
    }
    .erp-strip b { color: var(--primary-color); }

    /* ---- Data-flow diagram (Home: "what is an ERP") ---- */
    .erp-flow { display: flex; align-items: stretch; gap: 0.4rem; margin: 0.5rem 0 0.25rem 0; flex-wrap: wrap; }
    .erp-flow-node {
        flex: 1 1 120px;
        text-align: center;
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 10px;
        padding: 0.7rem 0.5rem;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .erp-flow-arrow { align-self: center; opacity: 0.5; font-size: 1.2rem; padding: 0 0.1rem; }
    .erp-flow-center {
        text-align: center;
        border: 1px dashed var(--primary-color);
        border-radius: 10px;
        padding: 0.6rem 0.5rem;
        font-size: 0.82rem;
        margin-top: 0.5rem;
        opacity: 0.9;
    }

    /* ---- Status badges ---- */
    .erp-badge {
        display: inline-block;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .erp-badge-green  { background-color: rgba(34, 197, 94, 0.16); color: #16a34a; }
    .erp-badge-amber  { background-color: rgba(245, 158, 11, 0.18); color: #b45309; }
    .erp-badge-red    { background-color: rgba(239, 68, 68, 0.16); color: #dc2626; }
    .erp-badge-blue   { background-color: rgba(59, 130, 246, 0.16); color: #2563eb; }
    .erp-badge-gray   { background-color: rgba(128, 128, 128, 0.18); color: var(--text-color); }

    /* ---- Compact caption row under the topbar ---- */
    .erp-eyebrow { font-size: 0.78rem; letter-spacing: 0.04em; text-transform: uppercase; opacity: 0.65; margin-bottom: 0.1rem; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def badge(label: str, color: str) -> str:
    """Return an inline HTML status badge. color one of: green, amber, red, blue, gray."""
    return f'<span class="erp-badge erp-badge-{color}">{label}</span>'
