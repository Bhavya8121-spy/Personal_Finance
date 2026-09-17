<p align="center">
  <img src="assets/banner.svg" alt="Statement Reader: turn a messy bank CSV into merchant names, categories, and one honest sentence about where the money went." width="100%">
</p>

# Statement Reader

Bank statements are unreadable by design. `AMZN MKTP US*839201` tells you nothing. Statement Reader takes a CSV export from any bank, identifies the actual merchant behind each line, sorts it into a spending category, and hands back a plain-language read of where the money went - including the habits worth cutting and what it would take to save for something specific.

## What it does

- **Reads any bank's CSV.** Auto-detects the description, date, and amount columns; asks only when it can't tell.
- **Identifies merchants.** A local rules engine handles known patterns first; unrecognized descriptions are sanitized and sent to Gemini for classification. Corrections you make are remembered for next time.
- **Categorizes spending** into a fixed taxonomy, with a confidence score and a review queue for anything uncertain.
- **Finds the habits.** Recurring subscriptions, the payee you visit most, and whether a spending pattern has repeated across multiple uploads.
- **Explains the number**, not just shows it - a plain sentence on whether you came out ahead, plus the largest single charge and the biggest category.
- **Plans toward a goal.** Tell it what you're saving for and by when; it splits your existing savings and investing between that goal and everything else, and says honestly whether the timeline is realistic.
- **Never gives financial advice.** Guidance shown is general, sourced from published benchmarks and historical return ranges, always labeled as such, and always paired with the downside.

## Tech stack

Python, Streamlit, pandas, SQLite,Gemini API

## Setup

**1. Clone and create a virtual environment**
```
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
```

**2. Install dependencies**
```
pip install -r requirements.txt
```

**3. Add your Gemini API key**

Copy the example secrets file and fill in your key:
```
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```
Edit `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "your-key-here"
```

**4. Run it**
```
streamlit run app.py
```

The app opens at `localhost:8501`. Upload a CSV bank statement to try it.

## Project structure

```
.
├── app.py                     # Streamlit interface
├── impact_report.py           # Prints usage stats from the local database
├── requirements.txt
├── .streamlit/
│   └── secrets.toml.example   # Copy to secrets.toml and fill in your key
├── data/
│   └── transactions.db        # SQLite - merchant knowledge, history, sessions
└── src/
    ├── engine.py               # Transaction classification
    ├── database.py             # Merchant/keyword storage
    ├── categories.py           # Category taxonomy
    ├── corrections.py          # User correction handling
    ├── statement_processor.py  # CSV column detection and parsing
    ├── analytics.py            # Cashflow summaries and trends
    ├── habits.py                # Recurring charges and spending leaks
    ├── commentary.py           # Tone-gated observations on spending
    ├── investments.py          # Investment activity detection
    ├── planner.py               # Savings capacity and general guidance
    ├── goals.py                  # Goal-based savings allocation
    ├── history.py                 # Cross-statement memory
    ├── sessions.py                # Anonymous usage logging
    └── impact.py                  # Aggregate stats
```

## Deploying

This app deploys for free on [Streamlit Community Cloud](https://share.streamlit.io). Connect your GitHub repo, point it at `app.py`, and add `GEMINI_API_KEY` under the app's Secrets settings.

Note: the free tier's filesystem is ephemeral - `data/transactions.db` resets on redeploy. Run `python impact_report.py` periodically if you want to keep a running record of usage.

## A note on the guidance features

The investing and goal-planning sections are built to educate, not advise. They compute your own numbers, cite general benchmarks, and show historical return ranges alongside their downside - they never recommend a specific investment. This isn't a disclaimer footnote; it's a constraint the code itself enforces (see `src/planner.py`). Nothing here replaces a licensed financial adviser.


