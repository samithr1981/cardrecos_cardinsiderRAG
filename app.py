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
import ui
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
EXAMPLE_SPEND = {
    "groceries": 12000,
    "dining": 8000,
    "online": 10000,
    "travel": 6000,
    "fuel": 4000,
    "utilities": 5000,
    "other": 8000,
    "intl": 0,
}

st.set_page_config(page_title="Find your best credit card (India)", page_icon="💳", layout="wide")
st.markdown(ui.css_block(), unsafe_allow_html=True)


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


def fill_example() -> None:
    for k, v in EXAMPLE_SPEND.items():
        st.session_state[f"spend_{k}"] = v


def items_from_scored(rows: pd.DataFrame) -> list[dict]:
    return [
        {
            "name": r["Card"],
            "bank": r["Bank"],
            "rewards": r["Est. annual rewards (₹)"],
            "fee": r["Annual fee after waiver (₹)"],
            "net": r["Est. net benefit (₹)"],
            "fee_status": r["Fee status"],
        }
        for _, r in rows.iterrows()
    ]


def merge_ai(scored: pd.DataFrame, recs: list[dict]) -> list[dict]:
    by_name = scored.drop_duplicates("Card").set_index("Card")
    items = []
    for rec in recs:
        if rec["name"] not in by_name.index:
            continue
        row = by_name.loc[rec["name"]]
        items.append(
            {
                "name": rec["name"],
                "bank": row["Bank"],
                "rewards": row["Est. annual rewards (₹)"],
                "fee": row["Annual fee after waiver (₹)"],
                "net": row["Est. net benefit (₹)"],
                "fee_status": row["Fee status"],
                "why": rec["why"],
                "value": rec["value"],
                "fees": rec["fees"],
                "watch": rec["watch"],
            }
        )
    return items


cards = load_cards()

# ----------------------------------------------------------------------------- hero
st.markdown(ui.hero(len(cards)), unsafe_allow_html=True)

# ----------------------------------------------------------------------------- input form
head_l, head_r = st.columns([3, 1], vertical_alignment="bottom")
with head_l:
    st.markdown(
        ui.section_title("Your monthly spending", "Enter what you spend in a typical month. Leave a box at 0 if it doesn't apply."),
        unsafe_allow_html=True,
    )
with head_r:
    st.button("Fill an example", on_click=fill_example, help="Loads sample spends so you can see how the results look.")

with st.form("spend_form"):
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
                f"{CATEGORY_LABELS[key]} (₹ per month)",
                min_value=0,
                max_value=5_000_000,
                step=500,
                key=f"spend_{key}",
                help=help_text,
            )

    st.markdown(ui.section_title("Preferences", "Optional. These sharpen the match.", small=True), unsafe_allow_html=True)
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
            "Share of a category spent at your chosen merchants (%)",
            10,
            100,
            50,
            step=10,
            help="E.g. 50% means half of your online spend happens at the merchants you selected.",
        )
        lounge_value = st.number_input("Value of one lounge visit (₹)", 100, 5000, 800, step=100)

    submitted = st.form_submit_button("Find my best cards", type="primary")

# ----------------------------------------------------------------------------- compute
if submitted:
    if sum(monthly.values()) <= 0:
        st.warning("Enter your spend in at least one category, or use “Fill an example”.")
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
        result = {
            "annual": profile.annual_spend,
            "n_categories": sum(1 for v in profile.monthly.values() if v > 0),
            "n_cards": len(scored),
            "items": [],
            "why_not": "",
            "raw_text": None,
            "notice": None,
            "table": [],
        }
        if not scored.empty:
            api_key = get_api_key()
            calls = st.session_state.get("ai_calls", 0)
            ai_items = []
            if not api_key:
                result["notice"] = "The written review isn't switched on for this app, so these are the top matches from the numeric comparison."
            elif calls >= MAX_AI_CALLS_PER_SESSION:
                result["notice"] = "You've reached the written-review limit for this session. Refresh the page to start over. These are the top numeric matches."
            else:
                shortlist = build_shortlist(scored, profile)
                names = [cards.loc[i, "Card Name"] for i in shortlist["idx"]]
                prompt = advisor.build_prompt(profile, shortlist, cards)
                try:
                    with st.spinner("Reviewing the best-fit cards…"):
                        text = advisor.recommend(prompt, api_key)
                    st.session_state["ai_calls"] = calls + 1
                    parsed = advisor.parse_recommendations(text, names)
                    if parsed:
                        ai_items = merge_ai(scored, parsed["recommendations"])
                        result["why_not"] = parsed["why_not_others"]
                    else:
                        result["raw_text"] = text
                        result["notice"] = "The written review came back in an unexpected format, so these are the top numeric matches."
                except Exception as exc:  # network, quota, bad key, model retired…
                    result["notice"] = f"The written review couldn't be completed ({type(exc).__name__}), so these are the top numeric matches."
            result["items"] = ai_items or items_from_scored(scored.head(3))
            shown = {i["name"] for i in result["items"]}
            more = scored[~scored["Card"].isin(shown)].head(7)
            result["table"] = items_from_scored(more)
        st.session_state["result"] = result

# ----------------------------------------------------------------------------- results
result = st.session_state.get("result")
if result:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    if not result["items"]:
        st.warning("No cards match your annual-fee limit at this spending level. Try raising the limit.")
    else:
        st.markdown(ui.section_title("Your best cards"), unsafe_allow_html=True)
        st.markdown(ui.summary_line(result["annual"], result["n_categories"], result["n_cards"]), unsafe_allow_html=True)
        if result["notice"]:
            st.markdown(ui.fineprint(result["notice"]), unsafe_allow_html=True)

        body = ui.top_recommendation(result["items"][0])
        body += "".join(ui.runner_up(n, it) for n, it in enumerate(result["items"][1:], start=2))
        body += ui.why_not(result["why_not"])
        st.markdown(body, unsafe_allow_html=True)

        if result["raw_text"]:
            with st.expander("Written review (raw)"):
                st.markdown(result["raw_text"])

        if result["table"]:
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown(
                ui.section_title("Also worth a look", "Next best by estimated net benefit."),
                unsafe_allow_html=True,
            )
            st.markdown(ui.compare_table(result["table"]), unsafe_allow_html=True)

        with st.expander("How these numbers are estimated"):
            st.markdown(
                "- Card details come from a spreadsheet of 300+ cards. Rewards, fees and waivers are free text, "
                "so rates are **read from the text automatically and can be wrong**.\n"
                "- Reward **caps, minimum-spend tiers and milestone bonuses are not modelled**, so rewards are an upper-end estimate.\n"
                "- Points are valued at your assumed rupee value unless the card states one. Fees include 18% GST.\n"
                "- Merchant-specific rewards count only for merchants you selected, on the share of spend you set.\n"
                "- The written review comes from an AI model reading the card text for the best-fit shortlist. It can still make mistakes."
            )

    st.markdown(
        ui.fineprint(
            "For information only, not financial advice. Card terms change often and the card data may be out of date. "
            "Check current fees, rewards and eligibility with the issuing bank before you apply."
        ),
        unsafe_allow_html=True,
    )
