import html
import os

import pandas as pd
import streamlit as st

# On Streamlit Cloud, secrets arrive in st.secrets, not the environment.
# This makes them available to os.getenv() calls elsewhere (e.g. in
# src/engine.py) without changing how that code reads the key locally.
for _key, _value in st.secrets.items():
    os.environ.setdefault(_key, str(_value))

from src.database import create_tables
from src.engine import analyze_transaction
from src.categories import CATEGORY_TAXONOMY
from src.corrections import save_user_correction
from src.statement_processor import detect_columns, prepare_statement

from src import analytics, commentary, goals, habits, history, investments, planner, sessions


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------

MAX_FILE_SIZE_MB = 5
MAX_TRANSACTIONS = 2000
CURRENCIES = ["$", "₹", "€", "£", "¥", "No symbol"]

st.set_page_config(page_title="Statement Reader", page_icon="💳", layout="centered")

create_tables()
history.create_history_tables()
sessions.create_session_table()
sessions.log_session()

for key, default in {
    "results_df": None,
    "summary": None,
    "flash": None,
    "currency": "$",
    "show_details": False,
    "wants_guidance": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ----------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=Instrument+Serif&display=swap');

:root {
    --bg:#F6F6F4; --card:#FFFFFF; --ink:#16191D; --muted:#6B7380;
    --line:#E3E3DD; --accent:#1F5F4E; --in:#2C6E8F; --flag:#A85A16;
}

.stApp { background: var(--bg); }
.stApp, .stApp p, .stApp label, .stApp input, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp div[data-testid="stMarkdownContainer"] {
    font-family: 'Instrument Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--ink);
}

.block-container { max-width: 44rem; padding-top: 3rem; padding-bottom: 5rem; }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

h1 { font-size: 1.9rem !important; font-weight: 600 !important; letter-spacing: -0.02em; }
h2 { font-size: 1.05rem !important; font-weight: 600 !important; margin: 2.25rem 0 0.75rem !important; }

.lede { color: var(--muted); font-size: 1rem; line-height: 1.55; margin: 0.4rem 0 2rem; }
.period { color: var(--muted); font-size: 0.85rem; margin: 1rem 0 0.7rem; }

.hero-amount {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 3.75rem; line-height: 1; letter-spacing: -0.015em;
    font-variant-numeric: tabular-nums;
}
.hero-label { color: var(--muted); font-size: 0.92rem; margin-top: 0.55rem; }

.stat-grid {
    display: flex; gap: 2.75rem; flex-wrap: wrap;
    margin: 1.6rem 0 1.2rem; padding-top: 1.2rem; border-top: 1px solid var(--line);
}
.stat-value { font-size: 1.2rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.stat-value.in { color: var(--in); }
.stat-label { color: var(--muted); font-size: 0.82rem; margin-top: 0.2rem; }

.takeaway { font-size: 1rem; line-height: 1.6; margin: 0.5rem 0 0.75rem; }
.note { color: var(--muted); font-size: 0.85rem; line-height: 1.55; }

.quip {
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 0.95rem 1.1rem; margin-bottom: 0.6rem; font-size: 0.97rem; line-height: 1.55;
}
.quip .tag { color: var(--muted); font-size: 0.75rem; display: block; margin-bottom: 0.3rem; }

.bar-row { margin-bottom: 1.05rem; }
.bar-head { display: flex; justify-content: space-between; align-items: baseline;
            font-size: 0.93rem; margin-bottom: 0.35rem; }
.bar-head .figure { color: var(--muted); font-variant-numeric: tabular-nums; }
.bar-track { height: 6px; background: #E9E9E4; border-radius: 99px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--accent); border-radius: 99px; }
.bar-sub { color: var(--muted); font-size: 0.78rem; margin-top: 0.3rem; }

.flag-note { border-left: 2px solid var(--flag); padding: 0.1rem 0 0.1rem 0.85rem;
             color: var(--flag); font-size: 0.92rem; margin-bottom: 1rem; }
.disclaimer { color: var(--muted); font-size: 0.78rem; line-height: 1.5;
              border-top: 1px solid var(--line); padding-top: 0.8rem; margin-top: 1.5rem; }

.stButton > button { border-radius: 10px; border: 1px solid var(--line);
                     font-weight: 500; padding: 0.55rem 1rem; background: var(--card); }
.stButton > button[kind="primary"] { background: var(--accent); border-color: var(--accent); color: #FFF; }
.stButton > button[kind="primary"]:hover { background: #184A3D; border-color: #184A3D; }

[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 12px;
                             background: var(--card); box-shadow: none; margin-bottom: 0.6rem; }
[data-testid="stFileUploaderDropzone"] { background: var(--card); border: 1px dashed #CBCBC3;
                                         border-radius: 14px; padding: 2rem 1.25rem; }
[data-testid="stDataFrame"] { border-radius: 12px; }

:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------

def money(value, signed=False):
    symbol = st.session_state.currency
    symbol = "" if symbol == "No symbol" else symbol
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    text = f"{symbol}{abs(number):,.2f}"
    return (("+" if number >= 0 else "−") + text) if signed else text


def guess_currency(df, detected):
    sample = " ".join(str(column) for column in df.columns)
    for key in ("amount", "debit", "credit"):
        column = detected.get(key)
        if column in df.columns:
            sample += " " + " ".join(df[column].astype(str).head(50))
    for symbol in ("₹", "€", "£", "¥", "$"):
        if symbol in sample:
            return symbol
    lowered = sample.lower()
    for code, symbol in (("inr", "₹"), ("usd", "$"), ("eur", "€"), ("gbp", "£"), ("jpy", "¥")):
        if code in lowered:
            return symbol
    return "$"


def describe_period(summary):
    start, end = summary["start"], summary["end"]
    if start is None:
        return None

    def day_month(value, with_year=True):
        return value.strftime("%d %b %Y" if with_year else "%d %b").lstrip("0")

    if start.date() == end.date():
        return day_month(start)
    if start.year == end.year:
        return f"{day_month(start, False)} – {day_month(end)}"
    return f"{day_month(start)} – {day_month(end)}"


def render_bars(rows, total):
    markup = []
    for name, spent, count in rows:
        share = (spent / total * 100) if total else 0
        markup.append(
            f'<div class="bar-row">'
            f'<div class="bar-head"><span>{html.escape(str(name))}</span>'
            f'<span class="figure">{money(spent)} · {share:.0f}%</span></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{max(share,1):.1f}%"></div></div>'
            f'<div class="bar-sub">{count} transaction{"s" if count != 1 else ""}</div>'
            f'</div>'
        )
    st.markdown("".join(markup), unsafe_allow_html=True)


def disclaimer():
    st.markdown(f'<div class="disclaimer">{planner.DISCLAIMER}</div>', unsafe_allow_html=True)


def reset():
    st.session_state.results_df = None
    st.session_state.summary = None
    st.session_state.flash = None
    st.session_state.wants_guidance = False


# ======================================================================
# SCREEN 1 — Upload
# ======================================================================

if st.session_state.results_df is None:

    st.title("Statement Reader")
    st.markdown(
        '<p class="lede">Drop in a CSV from your bank. You get back clean merchant '
        'names, categories, a plain reading of where the money went, and what it '
        'would take to buy the thing you are saving for.</p>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader("Bank statement (CSV)", type=["csv"])

    if uploaded_file is not None:

        if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            st.error(f"That file is over {MAX_FILE_SIZE_MB} MB. Try a shorter date range.")
            st.stop()

        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            st.error("This file couldn't be read as a CSV. Export it again from your bank and retry.")
            st.stop()

        if df.empty:
            st.error("This file has no rows in it.")
            st.stop()

        detected = detect_columns(df)
        columns = list(df.columns)
        optional = ["None"] + columns

        def index_of(name, pool, fallback=0):
            return pool.index(name) if name in pool else fallback

        found_description = detected.get("description") in columns
        found_money = any(detected.get(k) in columns for k in ("amount", "debit", "credit"))
        needs_help = not (found_description and found_money)

        if needs_help:
            st.markdown(
                '<div class="flag-note">We couldn\'t tell which columns to use. Pick them below.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption(f"Reading **{detected['description']}** as the description, {len(df):,} rows found.")

        with st.expander("Column settings", expanded=needs_help):
            description_column = st.selectbox("Description", columns, index=index_of(detected.get("description"), columns))
            date_column = st.selectbox("Date", optional, index=index_of(detected.get("date"), optional))
            amount_column = st.selectbox("Amount", optional, index=index_of(detected.get("amount"), optional))
            debit_column = st.selectbox("Debit", optional, index=index_of(detected.get("debit"), optional))
            credit_column = st.selectbox("Credit", optional, index=index_of(detected.get("credit"), optional))
            currency = st.selectbox("Currency", CURRENCIES, index=index_of(guess_currency(df, detected), CURRENCIES))
            st.caption("Leave Debit and Credit on None if your statement has a single Amount column.")

        column_map = {
            "description": description_column,
            "date": None if date_column == "None" else date_column,
            "amount": None if amount_column == "None" else amount_column,
            "debit": None if debit_column == "None" else debit_column,
            "credit": None if credit_column == "None" else credit_column,
        }

        if not any(column_map[k] for k in ("amount", "debit", "credit")):
            st.warning("Without an Amount, Debit, or Credit column, totals will be empty.")

        if st.button("Read my statement", type="primary", use_container_width=True):

            try:
                transactions = prepare_statement(df, column_map)
            except ValueError as error:
                st.error(str(error))
                st.stop()

            if not transactions:
                st.warning("No usable transactions in this file.")
                st.stop()

            if len(transactions) > MAX_TRANSACTIONS:
                st.error(
                    f"This statement has {len(transactions):,} transactions. "
                    f"The limit is {MAX_TRANSACTIONS:,}."
                )
                st.stop()

            progress = st.progress(0.0)
            status = st.empty()
            results = []
            total = len(transactions)

            for number, transaction in enumerate(transactions, start=1):
                status.caption(f"Reading {number:,} of {total:,}")
                try:
                    classification = analyze_transaction(transaction["description"])
                    results.append({
                        "Date": transaction["date"],
                        "Description": transaction["description"],
                        "Amount": transaction["amount"],
                        "Transaction Type": classification["transaction_type"],
                        "Merchant": classification["merchant"],
                        "Merchant Confidence": classification["merchant_confidence"],
                        "Category": classification["category"],
                        "Subcategory": classification["subcategory"],
                        "Category Confidence": classification["category_confidence"],
                        "Source": classification["source"],
                        "Review Required": classification["review_required"],
                        "Review Reason": classification["review_reason"],
                    })
                except Exception as error:
                    results.append({
                        "Date": transaction["date"],
                        "Description": transaction["description"],
                        "Amount": transaction["amount"],
                        "Transaction Type": "Unknown",
                        "Merchant": None,
                        "Merchant Confidence": 0.0,
                        "Category": "Other",
                        "Subcategory": "Unknown",
                        "Category Confidence": 0.0,
                        "Source": f"error: {type(error).__name__}",
                        "Review Required": True,
                        "Review Reason": "processing_error",
                    })
                progress.progress(number / total)

            results_df = pd.DataFrame(results)
            summary = analytics.summarize(results_df)

            try:
                history.save_run(results_df, summary)
            except Exception:
                pass  # history is a nice-to-have, never block the read

            st.session_state.currency = currency
            st.session_state.results_df = results_df
            st.session_state.summary = summary
            st.rerun()

    with st.expander("What happens to my data"):
        st.write(
            "Your statement is processed for this session and never stored. Descriptions "
            "we don't recognise are stripped of account and reference numbers, then sent "
            "to Gemini to identify the merchant. What we keep between visits is merchant "
            "knowledge and monthly totals, not your statement."
        )


# ======================================================================
# SCREEN 2 — Results
# ======================================================================

else:

    results_df = st.session_state.results_df
    summary = analytics.summarize(results_df)
    st.session_state.summary = summary

    currency = st.session_state.currency

    leaks = habits.add_history(habits.find_leaks(results_df), history.merchant_history)
    recurring = habits.find_recurring(results_df)
    detection = investments.detect(results_df)
    capacity = planner.capacity(summary)

    if st.button("← Read another statement"):
        reset()
        st.rerun()

    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = None

    overview, habits_tab, investing_tab, goals_tab, table_tab = st.tabs(
        ["Overview", "Habits", "Investing", "Goals", "Transactions"]
    )

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------
    with overview:

        period = describe_period(summary)
        if period:
            st.markdown(f'<div class="period">{html.escape(period)}</div>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="hero-amount">{money(summary["money_out"])}</div>'
            f'<div class="hero-label">left your account across {summary["debits"]:,} debits</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="stat-grid">'
            f'<div><div class="stat-value in">{money(summary["money_in"])}</div>'
            f'<div class="stat-label">came in</div></div>'
            f'<div><div class="stat-value">{money(summary["net"], signed=True)}</div>'
            f'<div class="stat-label">net change</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        lines = []
        if summary["net"] >= 0:
            lines.append(f"More came in than went out. You kept {money(summary['net'])}.")
        else:
            lines.append(f"You spent {money(-summary['net'])} more than came in.")

        if summary["days"] and summary["days"] > 1:
            lines.append(f"About {money(summary['money_out'] / summary['days'])} a day.")

        st.markdown(f'<div class="takeaway">{" ".join(lines)}</div>', unsafe_allow_html=True)

        # The funny bit, gated by commentary.should_joke()
        for item in commentary.generate(summary, leaks, currency=currency):
            tag = f'<span class="tag">{html.escape(str(item["category"]))}</span>' if item["category"] else ""
            st.markdown(f'<div class="quip">{tag}{html.escape(item["text"])}</div>', unsafe_allow_html=True)

        # Category breakdown, only with enough categories behind it
        if analytics.enough_for_breakdown(summary):
            st.markdown("## Where it went")

            rows = [
                (name, row.spent, int(row["count"]))
                for name, row in summary["by_category"].iterrows()
            ]

            render_bars(rows[:6], summary["money_out"])

            if len(rows) > 6:
                rest = rows[6:]
                rest_total = sum(spent for _, spent, _ in rest)
                share = (rest_total / summary["money_out"] * 100) if summary["money_out"] else 0
                with st.expander(f"{len(rest)} smaller categories · {money(rest_total)} ({share:.0f}%)"):
                    render_bars(rest, summary["money_out"])

        # Trends, only with two or more months
        if analytics.enough_for_trend(summary):
            st.markdown("## Month by month")
            trend = analytics.monthly_trend(results_df)
            st.line_chart(trend[["Money in", "Money out"]] if analytics.enough_for_income_view(summary)
                          else trend[["Money out"]])

            category_pivot = analytics.category_trend(results_df)
            if not category_pivot.empty:
                with st.expander("By category over time"):
                    st.bar_chart(category_pivot)
        elif summary["month_count"] == 1:
            st.markdown(
                '<div class="note">Charts over time need at least two months. '
                'Upload another statement and they appear here.</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="note">Money out is every debit on the statement, including '
            'transfers and cash withdrawals. It is not the same as what you consumed.</div>',
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Habits
    # ------------------------------------------------------------------
    with habits_tab:

        worst = habits.worst_offender(leaks)

        if worst:
            st.markdown("## The one to cut")
            repeat = (
                f" We have seen it in {worst['months_seen']} separate months, so this "
                f"is a pattern rather than a one-off."
                if worst.get("is_repeat") else ""
            )
            st.markdown(
                f'<div class="takeaway"><strong>{html.escape(worst["payee"])}</strong> — '
                f'{worst["visits"]} visits, {money(worst["total"])} this period. '
                f'At this pace it costs {money(worst["annual_cost"])} a year.{repeat}</div>',
                unsafe_allow_html=True,
            )

        if leaks:
            st.markdown("## Where the small stuff adds up")
            for leak in leaks:
                with st.expander(f"{leak['payee']} · {money(leak['total'])}"):
                    st.write(
                        f"{leak['visits']} visits, averaging {money(leak['average_ticket'])} each. "
                        f"That is {money(leak['monthly_cost'])} a month, {money(leak['annual_cost'])} a year."
                    )
                    if leak.get("lifetime_total"):
                        st.caption(
                            f"Across every statement you have uploaded: "
                            f"{money(leak['lifetime_total'])} since {leak['first_seen']}."
                        )
        else:
            st.markdown(
                '<div class="note">Nothing repeats often enough in this statement to '
                'call it a habit. Come back with another month.</div>',
                unsafe_allow_html=True,
            )

        subscriptions = [item for item in recurring if item["is_subscription"]]

        if subscriptions:
            st.markdown("## Charging you on a schedule")
            total_monthly = sum(item["monthly_cost"] or 0 for item in subscriptions)
            st.markdown(
                f'<div class="takeaway">{len(subscriptions)} recurring charges, '
                f'{money(total_monthly)} a month, {money(total_monthly * 12)} a year.</div>',
                unsafe_allow_html=True,
            )
            st.dataframe(
                pd.DataFrame([
                    {
                        "Charge": item["payee"],
                        "Every": f"{item['cadence_days']:.0f} days" if item["cadence_days"] else "—",
                        "Amount": money(item["average"]),
                        "Per year": money(item["annual_cost"]),
                    }
                    for item in subscriptions
                ]),
                use_container_width=True, hide_index=True,
            )

    # ------------------------------------------------------------------
    # Investing
    # ------------------------------------------------------------------
    with investing_tab:

        prompt = investments.prompt_text(detection, currency)

        if prompt:
            st.markdown(f'<div class="takeaway">{html.escape(prompt)}</div>', unsafe_allow_html=True)
            st.dataframe(
                pd.DataFrame([
                    {"Platform": name, "Moved in": money(data["contributed"]),
                     "Came back": money(data["withdrawn"]), "Transactions": data["transactions"]}
                    for name, data in detection["platforms"].items()
                ]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.markdown(
                '<div class="note">No investment transfers found in this statement. '
                'The guidance below is general and based only on your cashflow.</div>',
                unsafe_allow_html=True,
            )

        if not st.session_state.wants_guidance:
            if st.button("Show general guidance", type="primary"):
                st.session_state.wants_guidance = True
                st.rerun()
        else:
            st.markdown("## What your cashflow allows")

            if capacity["monthly_spare"] is not None:
                st.markdown(
                    f'<div class="takeaway">Your statement shows about '
                    f'{money(capacity["monthly_spare"])} spare each month after everything '
                    f'that left the account.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="note">No income is visible in this statement, so we '
                    'cannot say what is spare. Upload a statement that includes your '
                    'salary to see this.</div>',
                    unsafe_allow_html=True,
                )

            if capacity["confidence"] == "low":
                st.caption("Based on a single month, so treat it as a rough read.")

            fund = planner.emergency_fund(summary)
            if fund:
                st.markdown("## Cash buffer first")
                st.markdown(
                    f'<div class="takeaway">Your essentials run about '
                    f'{money(fund["monthly_essentials"])} a month, so three to six months '
                    f'of cover is {money(fund["target_low"])} to {money(fund["target_high"])}.</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f'<div class="note">{fund["note"]}</div>', unsafe_allow_html=True)

            st.markdown("## Time changes what makes sense")
            years = st.slider("When would you need this money?", 1, 30, 10, format="%d years")
            band = planner.horizon_guidance(years)

            st.markdown(
                f'<div class="takeaway"><strong>{band["label"]}</strong>. {band["why"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="note">Commonly held for this horizon: {band["typical_mix"]}. '
                f'Historically {band["historical_return"]}. Downside: {band["worst_case"]}</div>',
                unsafe_allow_html=True,
            )

            if capacity["monthly_spare"] and capacity["monthly_spare"] > 0:
                outcomes = planner.scenarios(capacity["monthly_spare"], years)
                st.markdown("## If you set that aside every month")
                st.dataframe(
                    pd.DataFrame([
                        {"Scenario": "You put in", "Value": money(outcomes["contributed"])},
                        {"Scenario": "Weak returns (2%)", "Value": money(outcomes["poor"])},
                        {"Scenario": "Middling returns (5%)", "Value": money(outcomes["middling"])},
                        {"Scenario": "Strong returns (8%)", "Value": money(outcomes["strong"])},
                    ]),
                    use_container_width=True, hide_index=True,
                )
                st.markdown(f'<div class="note">{outcomes["note"]}</div>', unsafe_allow_html=True)

            disclaimer()

    # ------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------
    with goals_tab:

        st.markdown("## Saving for something specific")

        left, right = st.columns(2)
        with left:
            target = st.number_input("What does it cost?", min_value=0.0, value=40000.0, step=1000.0)
        with right:
            years = st.number_input("In how many years?", min_value=0.5, max_value=40.0, value=4.0, step=0.5)

        default_savings = float(capacity["monthly_spare"] or 0) * 0.75
        default_investing = float(capacity["monthly_spare"] or 0) * 0.25

        with st.expander("What you already put aside each month"):
            main_savings = st.number_input("Into savings", min_value=0.0, value=round(max(default_savings, 0.0), 2), step=50.0)
            main_investing = st.number_input("Into investments", min_value=0.0, value=round(max(default_investing, 0.0), 2), step=50.0)
            already = st.number_input("Already saved toward this", min_value=0.0, value=0.0, step=500.0)

        if main_savings + main_investing > 0 and target > 0:

            plan = goals.allocate(target, years, main_savings, main_investing, already)

            st.markdown(
                f'<div class="takeaway">Set aside <strong>{money(plan["goal_monthly"])}</strong> '
                f'a month and this goal is funded in {years:g} years.</div>',
                unsafe_allow_html=True,
            )

            st.dataframe(
                pd.DataFrame([
                    {"Pot": "Goal savings", "Monthly": money(plan["goal_savings"])},
                    {"Pot": "Goal investments", "Monthly": money(plan["goal_investing"])},
                    {"Pot": "Main savings left", "Monthly": money(plan["remaining_savings"])},
                    {"Pot": "Main investments left", "Monthly": money(plan["remaining_investing"])},
                ]),
                use_container_width=True, hide_index=True,
            )

            if not plan["feasible"]:
                st.markdown(
                    f'<div class="flag-note">This does not fit. You would need '
                    f'{money(plan["required_monthly"])} a month and we can only free up '
                    f'{money(plan["goal_monthly"])} without draining your other pots. '
                    f'Stretching the timeline or lowering the target closes the gap.</div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                f'<div class="note">Projected value at the end: '
                f'{money(plan["projected_value"])}, of which {money(plan["contributed_only"])} '
                f'is money you put in. {plan["note"]}</div>',
                unsafe_allow_html=True,
            )

            note = goals.affordability_note(plan, capacity)
            if note:
                st.markdown(f'<div class="note">{note}</div>', unsafe_allow_html=True)

            disclaimer()
        else:
            st.markdown(
                '<div class="note">Enter what you put aside each month to see the split.</div>',
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------
    with table_tab:

        review_mask = results_df["Review Required"].fillna(False).astype(bool)
        review_df = results_df[review_mask].copy()

        if not review_df.empty:
            st.markdown("## Worth a second look")
            st.markdown(
                f'<div class="flag-note">{len(review_df)} transaction'
                f'{"s" if len(review_df) != 1 else ""} we weren\'t confident about. '
                f'Fixing one teaches the classifier for next time.</div>',
                unsafe_allow_html=True,
            )

            categories = list(CATEGORY_TAXONOMY.keys())

            for index, row in review_df.iterrows():
                with st.expander(row["Description"]):
                    merchant = st.text_input(
                        "Merchant",
                        value=row["Merchant"] if pd.notna(row["Merchant"]) else "",
                        key=f"merchant_{index}", placeholder="Who was this?",
                    )
                    left, right = st.columns(2)
                    with left:
                        current = row["Category"] if row["Category"] in categories else categories[0]
                        category = st.selectbox("Category", categories,
                                                index=categories.index(current), key=f"category_{index}")
                    with right:
                        subcategories = CATEGORY_TAXONOMY[category]
                        current_sub = (row["Subcategory"] if row["Subcategory"] in subcategories
                                       else subcategories[0])
                        subcategory = st.selectbox("Subcategory", subcategories,
                                                   index=subcategories.index(current_sub),
                                                   key=f"subcategory_{index}")

                    if st.button("Save", type="primary", key=f"save_{index}"):
                        clean_merchant = merchant.strip() or row["Description"]
                        learning = save_user_correction(
                            description=row["Description"], merchant=clean_merchant,
                            category=category, subcategory=subcategory,
                        )
                        for column, value in {
                            "Merchant": clean_merchant, "Merchant Confidence": 1.0,
                            "Category": category, "Subcategory": subcategory,
                            "Category Confidence": 1.0, "Source": "user_correction",
                            "Review Required": False, "Review Reason": None,
                        }.items():
                            st.session_state.results_df.loc[index, column] = value

                        message = f"Saved. {clean_merchant} is remembered for next time."
                        if learning.get("keywords_promoted"):
                            message += " Learned: " + ", ".join(learning["keywords_promoted"]) + "."
                        st.session_state.flash = message
                        st.rerun()

        st.markdown("## Every transaction")

        filter_options = ["All categories"] + sorted(results_df["Category"].dropna().unique())
        picked = st.selectbox("Show", filter_options, label_visibility="collapsed")

        table_df = (results_df if picked == "All categories"
                    else results_df[results_df["Category"] == picked])

        st.session_state.show_details = st.toggle("Show confidence scores",
                                                  value=st.session_state.show_details)

        simple_columns = ["Date", "Description", "Merchant", "Category", "Amount"]
        detailed_columns = simple_columns + ["Subcategory", "Transaction Type",
                                             "Merchant Confidence", "Category Confidence", "Source"]
        visible = detailed_columns if st.session_state.show_details else simple_columns

        st.dataframe(table_df[[c for c in visible if c in table_df.columns]],
                     use_container_width=True, hide_index=True, height=420)

        st.download_button(
            "Download as CSV",
            data=results_df.to_csv(index=False).encode("utf-8"),
            file_name="classified_transactions.csv",
            mime="text/csv", use_container_width=True,
        )
