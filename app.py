"""Streamlit front end: people enter monthly spends and get the credit cards that fit best.

Run locally:   streamlit run app.py
Secrets:       ANTHROPIC_API_KEY (Streamlit secrets or environment variable) enables the AI review step.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

import advisor
from scoring import (
    BRAND_PATTERNS,
    CATEGORY_LABELS,
    Profile,
    build_shortlist,
    prepare_cards,
    score_cards,
)

DATA_FILE = Path(__file__).parent / "cardrecommender_input.xlsx"
MAX_AI_CALLS_PER_SESSION = 5  # protects the shared API key from heavy use

st.set_page_config(page_title="Find your best credit card (India)", page_icon="💳", layout="centered")


@st.cache_data(show_spinner="Loading card database…")
def load_cards() -> pd.DataFrame:
    return prepare_cards(pd.read_excel(DATA_FILE))


def get_api_key() -> str | None:
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
        model = st.secrets.get("CLAUDE_MODEL")
        if model:
            os.environ["CLAUDE_MODEL"] = str(model)
    except Exception:  # no secrets file configured
        key = None
    return key or os.environ.get("ANTHROPIC_API_KEY")


def rupees(x: float) -> str:
    """Format with Indian digit grouping, e.g. ₹8,76,000."""
    digits = f"{abs(round(x)):d}"
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return ("-" if x < 0 else "") + "₹" + digits


# ----------------------------------------------------------------------------- header
st.title("💳 Find your best credit card")
st.write(
    "Tell us what you spend in a typical month. We compare 300+ credit cards available in India and "
    "show the ones that give you the most value after annual fees."
)

cards = load_cards()

# ----------------------------------------------------------------------------- input form
with st.form("spend_form"):
    st.subheader("Your monthly spends (₹)")
    left, right = st.columns(2)
    monthly: dict[str, float] = {}
    for i, key in enumerate(CATEGORY_LABELS):
        col = left if i % 2 == 0 else right
        help_text = (
            "Spends in a foreign currency (overseas trips, international websites). "
            "Don't repeat these in the other boxes."
            if key == "intl"
            else None
        )
        with col:
            monthly[key] = st.number_input(
                CATEGORY_LABELS[key], min_value=0, max_value=5_000_000, step=500, value=0, key=f"spend_{key}", help=help_text
            )

    st.subheader("Preferences")
    brands = st.multiselect(
        "Merchants you shop at often",
        options=list(BRAND_PATTERNS),
        help="Cards with rewards tied to a merchant only count if you pick that merchant here.",
    )
    fee_options = {
        "No limit": None,
        "Free only (₹0)": 0,
        "Up to ₹1,000": 1000,
        "Up to ₹2,500": 2500,
        "Up to ₹5,000": 5000,
        "Up to ₹10,000": 10000,
    }
    fee_choice = st.selectbox(
        "Most you'd pay in annual fees",
        options=list(fee_options),
        help="Fee after waiver at your spending level.",
    )
    lc1, lc2 = st.columns(2)
    lounge_dom = lc1.number_input("Domestic lounge visits you'd use per year", 0, 24, 0)
    lounge_intl = lc2.number_input("International lounge visits per year", 0, 24, 0)

    with st.expander("Assumptions you can change"):
        point_value = st.number_input(
            "Value of 1 reward point (₹) when a card doesn't state it",
            min_value=0.05,
            max_value=2.0,
            value=0.25,
            step=0.05,
            help="Used for points-based cards. Cards that state '1 point = ₹X' use their own value.",
        )
        brand_share = st.slider(
            "Share of a category spent at your chosen merchants (%)", 10, 100, 50, step=10,
            help="E.g. 50% means half of your online spend happens at the merchants you selected.",
        )
        lounge_value = st.number_input("Value of one lounge visit (₹)", 100, 5000, 800, step=100)

    submitted = st.form_submit_button("Find my best cards", type="primary")

# ----------------------------------------------------------------------------- compute
if submitted:
    if sum(monthly.values()) <= 0:
        st.warning("Please enter your spend in at least one category.")
        st.session_state.pop("result", None)
    else:
        profile = Profile(
            monthly={k: float(v) for k, v in monthly.items()},
            brands=brands,
            point_value=float(point_value),
            brand_share=brand_share / 100,
            lounge_dom=int(lounge_dom),
            lounge_intl=int(lounge_intl),
            lounge_visit_value=float(lounge_value),
            max_fee=fee_options[fee_choice],
        )
        scored = score_cards(cards, profile)
        result = {"profile": profile, "scored": scored, "ai_text": None, "ai_error": None}

        if scored.empty:
            st.session_state["result"] = result
        else:
            api_key = get_api_key()
            calls = st.session_state.get("ai_calls", 0)
            if not api_key:
                result["ai_error"] = "AI review is not configured on this deployment (no ANTHROPIC_API_KEY)."
            elif calls >= MAX_AI_CALLS_PER_SESSION:
                result["ai_error"] = "You've reached the AI review limit for this session. Refresh the page to start over."
            else:
                shortlist = build_shortlist(scored, profile)
                prompt = advisor.build_prompt(profile, shortlist, cards)
                try:
                    with st.spinner("Reviewing the best-fit cards…"):
                        result["ai_text"] = advisor.recommend(prompt, api_key)
                    st.session_state["ai_calls"] = calls + 1
                except Exception as exc:  # network, quota, bad key, model retired…
                    result["ai_error"] = f"The AI review could not be completed ({type(exc).__name__})."
            st.session_state["result"] = result

# ----------------------------------------------------------------------------- results
result = st.session_state.get("result")
if result:
    profile: Profile = result["profile"]
    scored: pd.DataFrame = result["scored"]

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Monthly spend", rupees(profile.total_monthly))
    m2.metric("Yearly spend", rupees(profile.annual_spend))
    m3.metric("Cards compared", f"{len(scored)}")

    if scored.empty:
        st.warning("No cards match your annual-fee limit at this spending level. Try raising the limit.")
    else:
        st.subheader("Recommended cards")
        if result["ai_text"]:
            st.markdown(result["ai_text"])
        else:
            if result["ai_error"]:
                st.info(f"{result['ai_error']} Showing the top matches from the numeric comparison instead.")
            for i, row in scored.head(3).iterrows():
                st.markdown(
                    f"**{i + 1}. {row['Card']}** ({row['Bank']})  \n"
                    f"Estimated rewards {rupees(row['Est. annual rewards (₹)'])}/yr · "
                    f"annual fee {rupees(row['Annual fee after waiver (₹)'])} · "
                    f"net **{rupees(row['Est. net benefit (₹)'])}/yr** · {row['Fee status']}"
                )

        st.subheader("Top 10 by estimated net benefit")
        show_cols = [
            "Card",
            "Bank",
            "Est. annual rewards (₹)",
            "Annual fee after waiver (₹)",
            "Est. net benefit (₹)",
            "Fee status",
        ]
        st.dataframe(scored[show_cols].head(10), hide_index=True)

        with st.expander("How these numbers are estimated (read this)"):
            st.markdown(
                "- Card details come from a spreadsheet of 300+ cards; rewards, fees and waivers are free text, "
                "so rates are **read from the text automatically and can be wrong**.\n"
                "- Reward **caps, minimum-spend tiers and milestone bonuses are not modelled**, so rewards are an upper-end estimate.\n"
                "- Points are valued at your assumed rupee value unless the card states one. Fees include 18% GST.\n"
                "- Merchant-specific rewards count only for merchants you selected, on the share of spend you set.\n"
                "- The written recommendation comes from an AI model reading the card text for the best-fit shortlist; "
                "it can still make mistakes."
            )

    st.caption(
        "Information only, not financial advice. Card terms change often and the card data may be out of date. "
        "Check current fees, rewards and eligibility with the issuing bank before applying."
    )
