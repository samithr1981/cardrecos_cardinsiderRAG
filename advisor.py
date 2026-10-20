"""LLM review step: reads the raw text of a shortlist of cards and writes the final top-3 recommendation."""
from __future__ import annotations

import difflib
import json
import os
import re

import pandas as pd

from scoring import CATEGORY_LABELS, Profile

DEFAULT_MODEL = "claude-haiku-5-5"  # low cost for a public app; set CLAUDE_MODEL=claude-sonnet-5-5 for deeper reasoning

CARD_FIELDS = [
    ("Joining Fee", "Joining fee"),
    ("Renewal Fee", "Renewal fee"),
    ("Spend-Based Waiver", "Fee waiver"),
    ("Rewards Rate", "Rewards rate"),
    ("Reward Redemption", "Redemption"),
    ("Movie & Dining", "Dining/movies"),
    ("Travel", "Travel"),
    ("Welcome Benefits", "Welcome benefits"),
    ("Domestic Lounge", "Domestic lounge"),
    ("International Lounge", "International lounge"),
    ("Fuel Surcharge", "Fuel surcharge"),
    ("Foreign Currency Markup", "Forex markup"),
]

SYSTEM_PROMPT = (
    "You are a careful Indian credit card analyst. Use ONLY the card data supplied by the user message. "
    "If a rate, cap or condition is not in the data, say it is not stated; never invent numbers or card features. "
    "You are not a licensed financial advisor and must say the user should confirm terms with the issuing bank."
)


def get_model() -> str:
    return os.environ.get("CLAUDE_MODEL") or DEFAULT_MODEL


def _val(x) -> str:
    return "not stated" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x).strip()


def card_block(card_row: pd.Series, est: pd.Series) -> str:
    lines = [f"CARD: {card_row['Card Name']} ({card_row['Bank Name']})"]
    for col, label in CARD_FIELDS:
        lines.append(f"  {label}: {_val(card_row.get(col))}")
    lines.append(
        "  App pre-estimate (rough, text-parsed, may be wrong): "
        f"rewards ~Rs {est['Est. annual rewards (₹)']:,}/yr, fee after waiver Rs {est['Annual fee after waiver (₹)']:,}/yr, "
        f"fee status: {est['Fee status']}"
    )
    return "\n".join(lines)


def build_prompt(profile: Profile, shortlist: pd.DataFrame, cards: pd.DataFrame, extra_note: str = "") -> str:
    spend_lines = "\n".join(
        f"- {CATEGORY_LABELS[c]}: Rs {v:,.0f}/month" for c, v in profile.monthly.items() if v > 0
    )
    prefs = []
    if profile.brands:
        prefs.append("Frequently used merchants: " + ", ".join(profile.brands))
    if profile.lounge_dom or profile.lounge_intl:
        prefs.append(
            f"Would use about {profile.lounge_dom} domestic and {profile.lounge_intl} international airport lounge visits a year"
        )
    if profile.max_fee is not None:
        prefs.append(f"Does not want to pay more than Rs {profile.max_fee:,.0f}/year in annual fees")
    prefs_text = "\n".join(f"- {p}" for p in prefs) or "- none stated"
    blocks = "\n\n".join(card_block(cards.loc[r["idx"]], r) for _, r in shortlist.iterrows())
    return f"""A customer in India wants the best credit card for their spending.

MONTHLY SPEND (total Rs {profile.total_monthly:,.0f}/month = Rs {profile.annual_spend:,.0f}/year):
{spend_lines}

PREFERENCES:
{prefs_text}

CANDIDATE CARDS (the only cards you may recommend):
{blocks}

TASK: Recommend the TOP 3 cards for this customer, best first. Choose ONLY from the candidate cards above and copy the card name exactly.
Respond with ONLY a JSON object (no markdown, no code fences) in this shape:
{{
  "recommendations": [
    {{
      "card_name": "exact name from the list",
      "why_it_fits": "1-2 sentences tied to the customer's biggest spend categories",
      "value_breakdown": "simple arithmetic using ONLY rates in the data (spend x rate), minus the fee; mention caps or conditions, and say clearly if something could not be applied",
      "fees": "joining fee, renewal fee, and whether Rs {profile.annual_spend:,.0f}/year of spend meets the waiver condition",
      "watch_outs": ["short caps, exclusions, redemption limits or forex points; only what is relevant"]
    }}
  ],
  "why_not_others": "1-2 sentences naming 1-2 attractive cards from the list that fall short, and why"
}}
Keep points-to-rupee conversions explicit (e.g. "1 point = Rs 0.25 assumed") when the data does not state a value; the app's assumed value is Rs {profile.point_value:g} per point.
{extra_note}"""


def recommend(prompt: str, api_key: str, max_tokens: int = 2200) -> str:
    """Call the Claude Messages API and return the text of the reply."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=get_model(),
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def parse_recommendations(text: str, valid_names) -> dict | None:
    """Parse the model's JSON reply. Returns None if it is unusable, so the caller can show the raw text instead.

    Cards whose name is not in the shortlist are dropped, which guards against invented cards.
    """
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(t[start : end + 1])
    except ValueError:
        return None
    recs = data.get("recommendations") if isinstance(data, dict) else None
    if not isinstance(recs, list):
        return None
    lookup = {n.lower(): n for n in valid_names}
    out, seen = [], set()
    for r in recs:
        if not isinstance(r, dict):
            continue
        name = str(r.get("card_name", "")).strip().lower()
        key = name if name in lookup else next(iter(difflib.get_close_matches(name, list(lookup), n=1, cutoff=0.85)), None)
        if key is None or key in seen:
            continue
        seen.add(key)
        watch = r.get("watch_outs") or []
        if isinstance(watch, str):
            watch = [watch]
        out.append(
            {
                "name": lookup[key],
                "why": str(r.get("why_it_fits") or "").strip(),
                "value": str(r.get("value_breakdown") or "").strip(),
                "fees": str(r.get("fees") or "").strip(),
                "watch": [str(w).strip() for w in watch if str(w).strip()][:4],
            }
        )
        if len(out) == 3:
            break
    if not out:
        return None
    return {"recommendations": out, "why_not_others": str(data.get("why_not_others") or "").strip()}
