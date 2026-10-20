"""Visual layer: CSS plus HTML builders for the hero, card faces, recommendations and table.

Design: deep bottle-green "private bank" palette with brass accents. The credit card itself is the
signature element: the hero shows an empty card, and the best match is dealt out as a real card face.
All dynamic text goes through esc() before it reaches unsafe HTML.
"""
from __future__ import annotations

import html

from scoring import inr  # noqa: F401  (re-exported for the HTML builders below)

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Bodoni+Moda:wght@500;700"
    "&family=Instrument+Sans:wght@400;500;600&display=swap');"
)

_CSS = """
:root{
  --ink:#0A1F1C; --panel:#12342E; --line:rgba(205,174,114,.24); --ivory:#F1EBDD; --mist:#9FB6AE;
  --brass:#CDAE72; --brass-hi:#E2C98F; --mint:#7FD1B0; --amber:#E3B07A;
  --display:'Bodoni Moda','Didot','Bodoni 72',Georgia,serif;
  --text:'Instrument Sans','Helvetica Neue',Arial,sans-serif;
}
.stApp{background:radial-gradient(1100px 560px at 88% -8%, rgba(205,174,114,.11), transparent 62%), var(--ink);color:var(--ivory);}
.block-container{max-width:1080px;padding-top:2rem;padding-bottom:4rem;}
#MainMenu, footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stMarkdownContainer"] p, label[data-testid="stWidgetLabel"] p, input, button p, summary p{font-family:var(--text);}

/* hero */
.hero{display:grid;grid-template-columns:1.15fr .85fr;gap:3rem;align-items:center;padding:1.2rem 0 2.4rem;}
.stApp .hero-title{font-family:var(--display)!important;font-weight:500!important;font-size:clamp(2rem,4.4vw,3.35rem)!important;line-height:1.08!important;letter-spacing:-.015em;color:var(--ivory);margin:0 0 1.1rem;padding:0;max-width:15em;}
.hero-sub{font-family:var(--text);font-size:1.06rem;line-height:1.6;color:var(--mist);max-width:34em;margin:0 0 1.5rem;}
.facts-row{display:flex;flex-wrap:wrap;gap:.4rem 0;font-family:var(--text);font-size:.92rem;color:var(--ivory);}
.facts-row span{padding:0 1.1rem;border-left:1px solid var(--line);}
.facts-row span:first-child{padding-left:0;border-left:0;}
.hero .cardface{transform:rotate(-4deg);}

/* card face */
.cardface{position:relative;overflow:hidden;aspect-ratio:1.586/1;border-radius:18px;padding:1.25rem 1.4rem;display:flex;flex-direction:column;justify-content:space-between;
  background:linear-gradient(135deg,#1F5247 0%,#10332D 48%,#1B463C 100%);border:1px solid rgba(205,174,114,.42);
  box-shadow:0 34px 60px -28px rgba(0,0,0,.85),inset 0 1px 0 rgba(255,255,255,.10);color:var(--ivory);font-family:var(--text);}
.cardface::after{content:"";position:absolute;inset:0;pointer-events:none;border-radius:inherit;
  background:repeating-linear-gradient(100deg,rgba(255,255,255,.028) 0 2px,transparent 2px 6px),linear-gradient(115deg,transparent 40%,rgba(255,255,255,.07) 50%,transparent 60%);}
.cf-top{display:flex;justify-content:space-between;align-items:flex-start;color:var(--brass);}
.cf-bank{font-size:.92rem;font-weight:500;color:var(--ivory);opacity:.92;max-width:75%;}
.cf-chip{width:44px;height:33px;border-radius:7px;background:
  linear-gradient(90deg,transparent 31%,rgba(60,40,5,.35) 31% 33%,transparent 33% 66%,rgba(60,40,5,.35) 66% 68%,transparent 68%),
  linear-gradient(0deg,transparent 47%,rgba(60,40,5,.35) 47% 53%,transparent 53%),
  linear-gradient(135deg,#E8D4A2,#B8955A);}
.cf-name{font-family:var(--display);font-weight:500;font-size:clamp(1.1rem,2vw,1.5rem);line-height:1.15;letter-spacing:.005em;}
.cf-bottom{display:flex;justify-content:space-between;align-items:flex-end;gap:1rem;}
.cf-label{font-size:.76rem;color:var(--mist);margin-bottom:.1rem;}
.cf-value{font-family:var(--display);font-weight:700;font-size:1.65rem;color:var(--brass-hi);font-variant-numeric:lining-nums tabular-nums;line-height:1;}
.cf-mask{font-size:1.05rem;letter-spacing:.22em;color:var(--mist);}
.cf-right{text-align:right;}
.cf-right .cf-value{font-size:1.1rem;color:var(--ivory);}
.cardface.reveal{animation:deal .7s cubic-bezier(.2,.7,.2,1) both;}
@keyframes deal{from{opacity:0;transform:translateY(16px) rotate(-1.6deg);}to{opacity:1;transform:none;}}
@media (prefers-reduced-motion:reduce){.cardface.reveal{animation:none;}}

/* section titles */
.stApp .section-title{font-family:var(--display)!important;font-weight:500!important;font-size:1.7rem!important;line-height:1.2!important;letter-spacing:-.01em;color:var(--ivory);margin:0 0 .3rem;padding:0;}
.stApp .section-title.sub{font-size:1.3rem!important;margin-top:1.4rem;}
.section-hint{font-family:var(--text);font-size:.95rem;color:var(--mist);margin:0 0 1rem;}
.divider{height:1px;background:var(--line);margin:2.2rem 0 1.8rem;border:0;}

/* form + widgets */
div[data-testid="stForm"]{border:1px solid var(--line);border-radius:14px;padding:1.5rem 1.6rem 1.2rem;background:rgba(18,52,46,.30);}
label[data-testid="stWidgetLabel"] p{color:var(--mist);font-size:.9rem;}
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="base-input"]{background:var(--panel)!important;border-color:var(--line)!important;border-radius:8px!important;}
input{color:var(--ivory)!important;font-variant-numeric:tabular-nums;}
div[data-testid="stFormSubmitButton"] button{background:var(--brass)!important;color:#0A1F1C!important;border:0!important;border-radius:8px;padding:.65rem 1.8rem;font-weight:600;}
div[data-testid="stFormSubmitButton"] button:hover{background:var(--brass-hi)!important;}
div[data-testid="stFormSubmitButton"] button p{color:#0A1F1C!important;font-weight:600;}
div[data-testid="stButton"] button{background:transparent!important;border:1px solid var(--line)!important;color:var(--brass)!important;border-radius:8px;}
div[data-testid="stButton"] button:hover{border-color:var(--brass)!important;}
div[data-testid="stButton"] button p{color:var(--brass)!important;}
div[data-testid="stExpander"] details{border:1px solid var(--line)!important;border-radius:10px!important;background:transparent!important;}

/* results */
.summary-line{font-family:var(--text);font-size:1rem;color:var(--mist);margin:0 0 1.6rem;}
.summary-line b{color:var(--ivory);font-weight:600;}
.rec-top{display:grid;grid-template-columns:minmax(280px,5fr) 6fr;gap:2.4rem;align-items:start;margin-bottom:2.4rem;}
.rec-detail{font-family:var(--text);}
.rec-top > div:first-child{position:sticky;top:1.5rem;}
.badge{display:inline-block;font-size:.8rem;font-weight:600;color:#0A1F1C;background:var(--brass);border-radius:999px;padding:.18rem .75rem;margin-bottom:.7rem;}
.stApp .rec-title{font-family:var(--display)!important;font-weight:500!important;font-size:1.75rem!important;line-height:1.15!important;margin:0;padding:0;color:var(--ivory);}
.rec-bank{color:var(--mist);font-size:.95rem;margin:.2rem 0 1.1rem;}
.stats{display:flex;flex-wrap:wrap;gap:.6rem 2rem;margin:0 0 1.2rem;padding:.9rem 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);}
.stats div{min-width:7.5rem;}
.stats dt{font-size:.8rem;color:var(--mist);margin:0 0 .15rem;}
.stats dd{margin:0;font-size:1.12rem;font-weight:600;color:var(--ivory);font-variant-numeric:tabular-nums;}
.stats dd.pos{color:var(--mint);}
.stApp .rec-detail h4{font-family:var(--text)!important;font-size:.95rem!important;font-weight:600!important;color:var(--brass);margin:1rem 0 .25rem;padding:0;}
.rec-detail p{font-size:.97rem;line-height:1.6;color:var(--ivory);margin:0;max-width:44em;}
.rec-detail ul{margin:.1rem 0 0;padding-left:1.1rem;color:var(--ivory);font-size:.95rem;line-height:1.55;}
.rec-detail li{margin:.15rem 0;}
.rec-row{display:grid;grid-template-columns:2.4rem 1fr auto;gap:1rem;padding:1.15rem 0;border-top:1px solid var(--line);font-family:var(--text);}
.rank{font-family:var(--display);font-size:1.6rem;color:var(--brass);line-height:1;padding-top:.15rem;}
.rr-name{font-family:var(--display);font-size:1.25rem;line-height:1.2;color:var(--ivory);}
.rr-bank{font-size:.9rem;color:var(--mist);margin:.1rem 0 .5rem;}
.rr-why{font-size:.95rem;line-height:1.55;color:var(--ivory);margin:0;max-width:44em;}
.rr-num{text-align:right;}
.rr-num .n{font-family:var(--display);font-weight:700;font-size:1.35rem;color:var(--brass-hi);font-variant-numeric:lining-nums tabular-nums;}
.rr-num .l{font-size:.8rem;color:var(--mist);}
.rec-row details{margin-top:.6rem;}
.rec-row summary{cursor:pointer;color:var(--brass);font-size:.9rem;font-weight:500;}
.rec-row summary:focus-visible{outline:2px solid var(--brass);outline-offset:3px;border-radius:4px;}
.rec-row details > div{padding-top:.2rem;}
.why-not{font-family:var(--text);font-size:.95rem;line-height:1.6;color:var(--mist);border-top:1px solid var(--line);padding-top:1.1rem;margin-top:0;}
.why-not b{color:var(--ivory);font-weight:600;}

/* table */
.tbl-wrap{overflow-x:auto;}
table.cmp{width:100%;border-collapse:collapse;font-family:var(--text);font-size:.93rem;}
table.cmp th{text-align:left;font-weight:500;color:var(--mist);font-size:.85rem;padding:.5rem .7rem;border-bottom:1px solid var(--line);white-space:nowrap;}
table.cmp td{padding:.7rem;border-bottom:1px solid rgba(205,174,114,.12);color:var(--ivory);vertical-align:top;}
table.cmp th.num, table.cmp td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
table.cmp td.card{min-width:14rem;}
table.cmp td.card small{display:block;color:var(--mist);font-size:.82rem;margin-top:.1rem;}
table.cmp td.fee{color:var(--mist);font-size:.85rem;min-width:12rem;}

.fineprint{font-family:var(--text);font-size:.82rem;line-height:1.55;color:var(--mist);margin-top:2.2rem;max-width:52em;}

@media (max-width:820px){
  .hero{grid-template-columns:1fr;gap:1.6rem;}
  .hero .cardface{max-width:360px;}
  .rec-top{grid-template-columns:1fr;gap:1.4rem;}
  .rec-row{grid-template-columns:1.8rem 1fr;}
  .rr-num{grid-column:2;text-align:left;}
}
"""


def css_block() -> str:
    minified = " ".join(line.strip() for line in _CSS.splitlines() if line.strip())
    return f"<style>{FONT_IMPORT} {minified}</style>"


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


_CONTACTLESS = (
    '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.6" '
    'stroke-linecap="round" aria-hidden="true"><path d="M8.5 8.5a5 5 0 0 1 0 7"/><path d="M11.5 6.5a8 8 0 0 1 0 11"/>'
    '<path d="M14.5 4.5a11 11 0 0 1 0 15"/></svg>'
)


def card_face(bank: str, name: str, label: str, value: str, right_label: str = "", right_value: str = "", reveal=False) -> str:
    right = (
        f'<div class="cf-right"><div class="cf-label">{esc(right_label)}</div><div class="cf-value">{esc(right_value)}</div></div>'
        if right_label
        else ""
    )
    cls = "cardface reveal" if reveal else "cardface"
    return (
        f'<div class="{cls}"><div class="cf-top"><span class="cf-bank">{esc(bank)}</span>{_CONTACTLESS}</div>'
        f'<div class="cf-chip"></div><div class="cf-name">{esc(name)}</div>'
        f'<div class="cf-bottom"><div><div class="cf-label">{esc(label)}</div><div class="cf-value">{esc(value)}</div></div>{right}</div></div>'
    )


def hero(n_cards: int) -> str:
    placeholder = (
        '<div class="cardface"><div class="cf-top"><span class="cf-bank">Your best match</span>' + _CONTACTLESS + "</div>"
        '<div class="cf-chip"></div><div class="cf-mask" aria-hidden="true">••••&nbsp;&nbsp;••••&nbsp;&nbsp;••••</div>'
        '<div class="cf-bottom"><div><div class="cf-label">Net benefit a year</div><div class="cf-value">₹ ——</div></div></div></div>'
    )
    return (
        '<section class="hero"><div>'
        '<h1 class="hero-title">Find the credit card that rewards how you actually spend</h1>'
        f'<p class="hero-sub">Enter a typical month of spending. We compare {n_cards} cards available in India, '
        "count annual fees and waivers, and show the ones worth applying for.</p>"
        f'<div class="facts-row"><span>{n_cards} cards compared</span><span>Fee waivers counted</span><span>No sign-up</span></div>'
        f"</div><div>{placeholder}</div></section>"
    )


def section_title(title: str, hint: str = "", small: bool = False) -> str:
    hint_html = f'<p class="section-hint">{esc(hint)}</p>' if hint else ""
    cls = "section-title sub" if small else "section-title"
    return f'<h2 class="{cls}">{esc(title)}</h2>{hint_html}'


def summary_line(annual: float, n_categories: int, n_cards: int) -> str:
    return (
        f'<p class="summary-line"><b>{inr(annual)}</b> a year across {n_categories} '
        f'{"category" if n_categories == 1 else "categories"}. <b>{n_cards}</b> cards compared.</p>'
    )


def _stats(item: dict) -> str:
    net_cls = "pos" if item["net"] > 0 else ""
    return (
        '<dl class="stats">'
        f'<div><dt>Estimated rewards a year</dt><dd>{inr(item["rewards"])}</dd></div>'
        f'<div><dt>Annual fee after waiver</dt><dd>{inr(item["fee"])}</dd></div>'
        f'<div><dt>Estimated net a year</dt><dd class="{net_cls}">{inr(item["net"])}</dd></div>'
        "</dl>"
    )


def _detail_sections(item: dict) -> str:
    out = []
    if item.get("why"):
        out.append(f'<h4>Why it fits</h4><p>{esc(item["why"])}</p>')
    if item.get("value"):
        out.append(f'<h4>How the value adds up</h4><p>{esc(item["value"])}</p>')
    fees = item.get("fees") or item.get("fee_status")
    if fees:
        out.append(f'<h4>Fees</h4><p>{esc(fees)}</p>')
    if item.get("watch"):
        lis = "".join(f"<li>{esc(w)}</li>" for w in item["watch"])
        out.append(f"<h4>Watch for</h4><ul>{lis}</ul>")
    return "".join(out)


def top_recommendation(item: dict) -> str:
    face = card_face(
        item["bank"], item["name"], "Estimated net a year", inr(item["net"]), "Annual fee", inr(item["fee"]), reveal=True
    )
    return (
        f'<div class="rec-top"><div>{face}</div><div class="rec-detail"><span class="badge">Best match</span>'
        f'<h3 class="rec-title">{esc(item["name"])}</h3><div class="rec-bank">{esc(item["bank"])}</div>'
        f"{_stats(item)}{_detail_sections(item)}</div></div>"
    )


def runner_up(rank: int, item: dict) -> str:
    more = ""
    extra = []
    if item.get("value"):
        extra.append(f'<h4>How the value adds up</h4><p>{esc(item["value"])}</p>')
    fees = item.get("fees") or item.get("fee_status")
    if fees:
        extra.append(f'<h4>Fees</h4><p>{esc(fees)}</p>')
    if item.get("watch"):
        extra.append("<h4>Watch for</h4><ul>" + "".join(f"<li>{esc(w)}</li>" for w in item["watch"]) + "</ul>")
    if extra:
        more = f'<details><summary>Value, fees and watch-outs</summary><div class="rec-detail">{"".join(extra)}</div></details>'
    why = f'<p class="rr-why">{esc(item["why"])}</p>' if item.get("why") else ""
    return (
        f'<div class="rec-row"><div class="rank">{rank}</div><div><div class="rr-name">{esc(item["name"])}</div>'
        f'<div class="rr-bank">{esc(item["bank"])}</div>{why}{more}</div>'
        f'<div class="rr-num"><div class="n">{inr(item["net"])}</div><div class="l">estimated net a year</div></div></div>'
    )


def why_not(text: str) -> str:
    return f'<p class="why-not"><b>Why not the others.</b> {esc(text)}</p>' if text else ""


def compare_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    head = (
        "<thead><tr><th>Card</th><th class='num'>Rewards a year</th><th class='num'>Fee after waiver</th>"
        "<th class='num'>Net a year</th><th>Fee status</th></tr></thead>"
    )
    body = "".join(
        f'<tr><td class="card">{esc(r["name"])}<small>{esc(r["bank"])}</small></td>'
        f'<td class="num">{inr(r["rewards"])}</td><td class="num">{inr(r["fee"])}</td>'
        f'<td class="num">{inr(r["net"])}</td><td class="fee">{esc(r["fee_status"])}</td></tr>'
        for r in rows
    )
    return f'<div class="tbl-wrap"><table class="cmp">{head}<tbody>{body}</tbody></table></div>'


def fineprint(text: str) -> str:
    return f'<p class="fineprint">{esc(text)}</p>'
