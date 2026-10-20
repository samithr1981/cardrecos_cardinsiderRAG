"""Heuristic scoring of credit cards from the free-text feature sheet.

The Excel sheet stores rewards, fees and waivers as free text, so nothing here is
exact. This module turns that text into rough numbers (reward rate per spend
category, annual fee after waiver, forex cost, lounge value) and ranks cards by an
*estimated* net annual benefit. It is used to build a shortlist; the final
recommendation is reviewed against the raw card text (see advisor.py).

Known simplifications (also surfaced to the user in the app):
  * Reward caps, minimum-spend tiers and milestone benefits are not modelled.
  * Reward points are valued at a single adjustable rupee value unless the card's
    redemption text states "1 point = Rs X".
  * Merchant-specific rewards only count if the user picks that merchant, and are
    applied to an assumed share of that category's spend.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import pandas as pd

GST = 0.18
DEFAULT_FOREX_MARKUP = 3.5  # % used only when the sheet has no value
MAX_RATE_PCT = 10.0  # sanity cap on any single parsed reward rate

CATEGORY_LABELS = {
    "groceries": "Groceries & supermarkets",
    "dining": "Dining & food delivery",
    "online": "Online shopping",
    "travel": "Travel (flights, hotels, cabs)",
    "fuel": "Fuel",
    "utilities": "Utilities, bills & insurance",
    "other": "Everything else",
    "intl": "International / foreign-currency spends",
}
CATEGORIES = list(CATEGORY_LABELS)

CATEGORY_PATTERNS = {
    "groceries": r"grocer|supermarket|bigbasket|blinkit|instamart|zepto|dmart|jiomart",
    "dining": r"dining|restaurant|\bfood|swiggy|zomato|dineout|eazydiner|\bcafe",
    "online": r"online|e-?commerce|amazon|flipkart|myntra|ajio|nykaa|shopping",
    "travel": r"travel|flight|airline|hotel|irctc|makemytrip|cleartrip|goibibo|\buber\b|\bola\b|railway|\brail\b",
    "fuel": r"fuel|petrol|diesel|hpcl|bpcl|indian ?oil|iocl",
    "utilities": r"utilit|bill pay|bill payment|insurance|telecom|recharge|electricity|broadband|\bdth\b",
    "intl": r"international|foreign|overseas|forex|abroad",
}

# Merchants the user can say they shop at. Rewards tied to a merchant count only if selected.
BRAND_PATTERNS = {
    "Amazon": r"amazon",
    "Flipkart / Myntra": r"flipkart|myntra",
    "Swiggy / Instamart": r"swiggy|instamart",
    "Zomato / Blinkit": r"zomato|blinkit",
    "BigBasket": r"bigbasket",
    "Uber / Ola": r"\buber\b|\bola\b",
    "MakeMyTrip / Goibibo / Cleartrip / IRCTC": r"makemytrip|goibibo|cleartrip|irctc",
    "Indian Oil": r"indian ?oil|iocl",
    "BPCL": r"bpcl",
    "HPCL": r"hpcl",
    "Tata Neu / Tata brands": r"tata ?neu|\btata\b|croma",
}
# Other named merchants: rewards tied to them are ignored (we can't know if the user shops there).
OTHER_BRAND_PATTERN = (
    r"air india|vistara|indigo|shoppers stop|lifestyle|bookmyshow|\bpvr\b|paytm|phonepe|reliance|\bjio\b|"
    r"decathlon|ikea|titan|tanishq|patanjali|apollo|1mg|pharmeasy|netmeds|spotify|netflix|hotstar|"
    r"marriott|\btaj\b|\bitc\b|\boyo\b|yatra|easemytrip|ixigo|nykaa|ajio|bajaj|jiomart|zepto|dmart"
)

BASE_WORDS = (
    r"\bother\b|everyday|every ?day|all spend|all purchase|all transaction|remaining|rest of|"
    r"every purchase|all eligible|eligible (?:spend|transaction)|offline"
)
# Partner discounts / offers are not earn rates, so they are ignored in the estimate.
PROMO_WORDS = r"\boff\b|discount|buy 1|bogo|complimentary|free "
CAP_WORDS = r"up ?to (?:₹|rs)|capped|maximum|\bmax\b"
POINT_UNITS = (
    r"(?:reward\s*points?|rewards?\s*points?|\brps?\b|points?|edge\s*miles|miles|travel\s*credits?|"
    r"cash\s*points?|delight\s*points?|neu\s*coins?|neucoins?|infinity\s*points?)"
)

COLUMN_DEFAULT_CATEGORY = {"Rewards Rate": None, "Movie & Dining": "dining", "Travel": "travel"}


# ----------------------------------------------------------------------------- parsing helpers
def inr(x: float) -> str:
    """Rupees with Indian digit grouping, e.g. ₹8,76,000."""
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


def _clean(text) -> str:
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return ""
    t = str(text).replace("₹", "₹")
    t = re.sub(r"\brs\.", "rs", t, flags=re.I)  # "Rs. 50,000" -> "rs 50,000" so '.' splits sentences only
    return t.strip()


def parse_amounts(text: str, allow_bare: bool = False) -> list[float]:
    """Rupee amounts in text. Handles '₹1 Lakh', 'Rs 1,50,000', '5,00,000'."""
    out = []
    pat = r"(₹|rs|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|lacs?|crores?)?"
    for m in re.finditer(pat, text, flags=re.I):
        symbol, num, unit = m.group(1), m.group(2), m.group(3)
        try:
            value = float(num.replace(",", ""))
        except ValueError:
            continue
        if unit:
            value *= 1e7 if unit.lower().startswith("crore") else 1e5
        elif not symbol and not allow_bare and value < 10000:
            continue
        out.append(value)
    return out


def parse_fee(text) -> float | None:
    """Annual-fee-style text -> rupees per year including GST. None if unparseable."""
    t = _clean(text).lower()
    if not t:
        return None
    amounts = parse_amounts(t, allow_bare=True)
    if not amounts:
        return 0.0 if re.search(r"nil|free|no fee|waived|none", t) else None
    fee = amounts[0]
    if re.search(r"monthly|per month|/ ?month", t):
        fee *= 12
    if "gst" in t and "+" in t:
        fee *= 1 + GST
    return round(fee, 2)


def parse_waiver_threshold(text) -> float | None:
    """Annual spend (₹) that waives the renewal/annual fee. Ignores first-30-day joining waivers."""
    t = _clean(text)
    if not t or re.fullmatch(r"nil|none|n/a|na", t, flags=re.I):
        return None
    sentences = re.split(r"(?<=[.;])\s+|\n+", t)
    for s in sentences:
        low = s.lower()
        if re.search(r"joining|first\s*(?:\d+\s*)?(?:days?|year)|within\s*\d+\s*days|\d+\s*days", low) and not re.search(
            r"annual|renewal", low
        ):
            continue
        amounts = parse_amounts(low)
        if amounts:
            threshold = max(amounts)
            if re.search(r"monthly|last month|per month|each month|a month", low) and not re.search(r"annual|year", low):
                threshold *= 12  # monthly-fee card: convert the monthly spend condition to a yearly figure
            return threshold
    return None


def parse_forex_markup(text) -> float:
    """Forex markup as % including GST."""
    t = _clean(text).lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
    if not m:
        return 0.0 if re.search(r"nil|zero|no markup|waived", t) else DEFAULT_FOREX_MARKUP * (1 + GST)
    pct = float(m.group(1))
    return pct * (1 + GST) if "gst" in t else pct


def parse_point_value(text) -> float | None:
    """'1 Cash Point = Rs 1' style statements -> rupees per point."""
    t = _clean(text).lower()
    m = re.search(r"1\s*(?:[a-z]+\s*){0,3}?=\s*(?:₹|rs)\s*(\d+(?:\.\d+)?)", t)
    return float(m.group(1)) if m else None


def parse_lounge_visits_per_year(text) -> int:
    t = _clean(text).lower()
    if not t:
        return 0
    if "unlimited" in t:
        return 12
    m = re.search(r"(\d+)\s*(?:complimentary\s*|free\s*)?(?:[a-z]+\s*){0,3}?(?:visits?|accesses|access|entries|entry)\b(.{0,30})", t)
    if not m:
        return 0
    n, tail = int(m.group(1)), m.group(2)
    if re.search(r"quarter", tail):
        n *= 4
    elif re.search(r"month", tail):
        n *= 12
    return n


def _split_clauses(text: str) -> list[str]:
    return [
        c.strip()
        for c in re.split(r"(?<=[.;])\s+|\n+|,\s+(?=\d)|,\s+and\s+|\s+and\s+(?=\d)|\s+&\s+(?=\d)", text)
        if c.strip()
    ]


def _rates_in_clause(clause: str, point_value: float) -> float:
    """Best effective reward rate (% of spend) stated in a clause, 0 if none."""
    if re.search(PROMO_WORDS, clause, flags=re.I) and not re.search(r"cash ?back|reward|points?|coins?", clause, flags=re.I):
        return 0.0
    rates = []
    effective = re.findall(r"~\s*(\d+(?:\.\d+)?)\s*%", clause)  # e.g. "20% coins (~4%)": use the effective value
    if effective:
        rates.extend(float(x) for x in effective)
    else:
        # a "%" directly followed by a points unit ("7% Reward Points/₹150") is a points multiplier, handled below
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%(?!\s*x?\s*" + POINT_UNITS + r")", clause, flags=re.I):
            rates.append(float(m.group(1)))
    pts = (
        r"(\d+(?:\.\d+)?)\s*%?\s*x?\s*" + POINT_UNITS + r"\b[^.\d]{0,40}?(?:per|for every|for each|on every|every|/)\s*(?:₹|rs)?\s*(\d[\d,]*)"
    )
    for m in re.finditer(pts, clause, flags=re.I):
        n, amt = float(m.group(1)), float(m.group(2).replace(",", ""))
        if amt > 0:
            rates.append(n * point_value / amt * 100)
    if not rates:
        return 0.0
    rate = min(max(rates), MAX_RATE_PCT)
    if re.search(CAP_WORDS, clause, flags=re.I):
        rate *= 0.5  # capped rewards realise less than the headline rate
    return rate


def _categories_in_clause(clause: str, default: str | None) -> list[str]:
    cats = [c for c, p in CATEGORY_PATTERNS.items() if re.search(p, clause, flags=re.I)]
    if "offline" in clause.lower() and "online" in cats:
        cats.remove("online")
    if not cats and default:
        cats = [default]
    return cats


# ----------------------------------------------------------------------------- per-card features
def extract_card_features(row: pd.Series) -> dict:
    """Profile-independent features parsed once per card."""
    pv_stated = parse_point_value(row.get("Reward Redemption"))
    clauses = []  # (categories, brands, is_base, text, column)
    for col, default in COLUMN_DEFAULT_CATEGORY.items():
        text = _clean(row.get(col))
        for clause in _split_clauses(text):
            cats = _categories_in_clause(clause, default)
            brands = [b for b, p in BRAND_PATTERNS.items() if re.search(p, clause, flags=re.I)]
            other_brand = bool(re.search(OTHER_BRAND_PATTERN, clause, flags=re.I)) and not brands
            is_base = bool(re.search(BASE_WORDS, clause, flags=re.I))
            clauses.append(
                {"cats": cats, "brands": brands, "other_brand": other_brand, "base": is_base, "text": clause}
            )
    return {
        "pv_stated": pv_stated,
        "clauses": clauses,
        "joining_fee": parse_fee(row.get("Joining Fee")),
        "renewal_fee": parse_fee(row.get("Renewal Fee")),
        "waiver_threshold": parse_waiver_threshold(row.get("Spend-Based Waiver")),
        "forex_pct": parse_forex_markup(row.get("Foreign Currency Markup")),
        "lounge_dom": parse_lounge_visits_per_year(row.get("Domestic Lounge")),
        "lounge_intl": parse_lounge_visits_per_year(row.get("International Lounge")),
    }


def prepare_cards(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the sheet and attach parsed features (object column 'feat')."""
    df = df.drop(columns=["S.No", "Unnamed: 23", "Card Insider"], errors="ignore").copy()
    df = df.dropna(subset=["Card Name"]).copy()
    for col in ("Card Name", "Bank Name"):  # tidy stray whitespace/quotes in the sheet, e.g. "Federal Bank'"
        df[col] = df[col].astype(str).str.strip().str.strip("'\"`")
    df = df.drop_duplicates(subset=["Card Name", "Bank Name"]).reset_index(drop=True)
    df["feat"] = [extract_card_features(r) for _, r in df.iterrows()]
    return df


# ----------------------------------------------------------------------------- profile + scoring
@dataclass
class Profile:
    monthly: dict[str, float]  # keys from CATEGORIES
    brands: list[str] = field(default_factory=list)
    point_value: float = 0.25  # rupees per reward point when the card doesn't state one
    brand_share: float = 0.5  # share of a category spent at a selected merchant
    lounge_dom: int = 0  # domestic lounge visits per year the user would actually use
    lounge_intl: int = 0
    lounge_visit_value: float = 800.0
    max_fee: float | None = None  # max acceptable annual fee after waiver; None = no limit

    @property
    def total_monthly(self) -> float:
        return float(sum(self.monthly.values()))

    @property
    def annual_spend(self) -> float:
        return self.total_monthly * 12


def _category_rates(feat: dict, profile: Profile) -> dict[str, float]:
    """Effective reward rate (%) per category for this card and profile."""
    pv = feat["pv_stated"] or profile.point_value
    generic = {c: 0.0 for c in CATEGORIES}
    brand = {c: 0.0 for c in CATEGORIES}
    base_candidates, other_generic = [], []
    selected = set(profile.brands)
    for cl in feat["clauses"]:
        rate = _rates_in_clause(cl["text"], pv)
        if rate <= 0 or cl["other_brand"]:
            continue
        if cl["brands"]:
            if selected.intersection(cl["brands"]):
                for c in cl["cats"] or ["other"]:
                    brand[c] = max(brand[c], rate)
            continue
        if cl["base"]:
            base_candidates.append(rate)
        if cl["cats"]:
            for c in cl["cats"]:
                generic[c] = max(generic[c], rate)
        elif not cl["base"]:
            other_generic.append(rate)
    base = max(base_candidates) if base_candidates else (min(other_generic) if other_generic else 0.0)
    out = {}
    for c in CATEGORIES:
        general = max(generic[c], base)
        if brand[c] > general:
            out[c] = profile.brand_share * brand[c] + (1 - profile.brand_share) * general
        else:
            out[c] = general
    return out


def score_cards(cards: pd.DataFrame, profile: Profile) -> pd.DataFrame:
    rows = []
    annual_spend = profile.annual_spend
    for idx, row in cards.iterrows():
        f = row["feat"]
        rates = _category_rates(f, profile)
        rewards = sum(profile.monthly.get(c, 0) * 12 * rates[c] / 100 for c in CATEGORIES)
        renewal = f["renewal_fee"] if f["renewal_fee"] is not None else 0.0
        threshold = f["waiver_threshold"]
        waived = bool(threshold and annual_spend >= threshold)
        fee = 0.0 if waived else renewal
        forex_cost = profile.monthly.get("intl", 0) * 12 * f["forex_pct"] / 100
        lounge = profile.lounge_visit_value * (
            min(profile.lounge_dom, f["lounge_dom"]) + min(profile.lounge_intl, f["lounge_intl"])
        )
        net = rewards - fee - forex_cost + lounge
        if renewal == 0:
            waiver_status = "No annual fee"
        elif waived:
            waiver_status = f"Fee waived (spend of {inr(threshold)} a year or more)"
        elif threshold:
            waiver_status = f"Not waived. Needs {inr(threshold)} a year ({inr(threshold / 12)} a month)"
        else:
            waiver_status = "No waiver found in data"
        rows.append(
            {
                "idx": idx,
                "Card": row["Card Name"],
                "Bank": row["Bank Name"],
                "Est. annual rewards (₹)": round(rewards),
                "Annual fee after waiver (₹)": round(fee),
                "Forex cost (₹)": round(forex_cost),
                "Lounge value (₹)": round(lounge),
                "Est. net benefit (₹)": round(net),
                "Fee status": waiver_status,
                "matched_categories": sum(1 for c in CATEGORIES if profile.monthly.get(c, 0) > 0 and rates[c] > 0),
            }
        )
    scored = pd.DataFrame(rows).sort_values("Est. net benefit (₹)", ascending=False).reset_index(drop=True)
    if profile.max_fee is not None:
        scored = scored[scored["Annual fee after waiver (₹)"] <= profile.max_fee].reset_index(drop=True)
    return scored


def build_shortlist(scored: pd.DataFrame, profile: Profile, n_top: int = 20, n_extra: int = 6) -> pd.DataFrame:
    """Top cards by estimated net benefit, plus a few that match many of the user's categories or lounge needs."""
    top = scored.head(n_top)
    rest = scored.iloc[n_top:]
    extras = rest.sort_values(["matched_categories", "Est. net benefit (₹)"], ascending=False).head(n_extra)
    if profile.lounge_dom or profile.lounge_intl:
        extras = pd.concat([extras, rest.sort_values("Lounge value (₹)", ascending=False).head(4)])
    return pd.concat([top, extras]).drop_duplicates(subset="idx").reset_index(drop=True)
