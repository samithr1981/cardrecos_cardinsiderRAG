# Credit Card Finder (India)

**Live app:** https://cardrecoscardinsiderrag-dhsqzxzbm3aerjhhj6awzt.streamlit.app/  

A Streamlit app where people enter their monthly spends and get the credit cards that fit best, using the 300+ card sheet in `cardrecommender_input.xlsx`.

## How it works

1. **Form** – monthly spend per category (groceries, dining, online, travel, fuel, utilities, other, international), favourite merchants, annual-fee limit, lounge needs.
2. **Numeric pass (`scoring.py`)** – reads reward rates, fees, fee waivers, forex markup and lounge visits out of the sheet's free text, then ranks all cards by estimated yearly rewards minus annual fee (after waiver).
3. **AI review (`advisor.py`)** – sends only a shortlist (about 26 cards) to the Claude API, which writes the final top 3 from the raw card text. This replaces the original script, which put every card in each prompt.
4. **Design (`ui.py`, `.streamlit/config.toml`)** – dark green and brass theme, card-face results and a comparison table.
5. If no API key is set (or the call fails), the app still shows the numeric top matches.

## Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your ANTHROPIC_API_KEY
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

1. Push these files to your GitHub repo (keep `cardrecommender_input.xlsx` next to `app.py`).
2. On share.streamlit.io choose the repo, branch `main`, main file `app.py`.
3. In **App settings → Secrets** add `ANTHROPIC_API_KEY = "..."`. Never commit the key.
4. Deploy. Any push to `main` redeploys.
5. Copy the app's address (you can pick a short one under **Advanced settings → App URL**) and paste it into the **Live app** line at the top of this README. Also add it to the repo's **About → Website** field on GitHub.

Other hosts (Hugging Face Spaces with the Streamlit SDK, Render, a VM) work the same way: install `requirements.txt`, set `ANTHROPIC_API_KEY` as an environment variable, run `streamlit run app.py`.

## Things to know

- The default model is `claude-haiku-5-5` (cheapest). Set `CLAUDE_MODEL` in secrets/env, e.g. to `claude-sonnet-5-5`, for stronger reasoning at higher cost. Check current model names in Anthropic's docs.
- Each browser session is limited to 5 AI reviews (`MAX_AI_CALLS_PER_SESSION` in `app.py`) to protect your key. Add your own rate limiting for heavy public use.
- Estimates ignore reward caps and spend tiers, and the sheet's data can go stale. Refresh the Excel file periodically.
- Check that you're allowed to republish the card data (e.g. if it was taken from CardInsider).
