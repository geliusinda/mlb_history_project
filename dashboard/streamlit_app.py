"""
Streamlit dashboard for MLB standings (from Baseball Almanac scrape).

Run locally:
    streamlit run dashboard/streamlit_app.py

It reads db/baseball_history.db (created by import_csvs.py) and offers interactive views:
- Wins by team over time (select teams)
- League average wins per year (slider year range)
- Wins vs Payroll scatter (by league/year) if payroll available
"""
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().parents[1] / "db" / "baseball_history.db"

st.set_page_config(page_title="MLB History Dashboard", layout="wide")

st.title("⚾ MLB Year-by-Year — Standings Explorer")
st.markdown("Data source: **Baseball Almanac — Year in Review** (scraped for educational use).")

if not DB_PATH.exists():
    st.error("Database not found. Please run the scraper, clean_transform.py, then import_csvs.py.")
    st.stop()

@st.cache_data
def load_df():
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql("SELECT * FROM standings_clean", conn)
    finally:
        conn.close()

df = load_df()
years = st.slider("Select year range", int(df["year"].min()), int(df["year"].max()), (int(df["year"].min()), int(df["year"].max())))
leagues = st.multiselect("Leagues", sorted(df["league"].dropna().unique().tolist()), default=sorted(df["league"].dropna().unique().tolist()))

fdf = df[(df["year"]>=years[0]) & (df["year"]<=years[1]) & (df["league"].isin(leagues))].copy()

tab1, tab2, tab3 = st.tabs(["Team Wins Over Time", "League Averages", "Wins vs Payroll"])

with tab1:
    teams_sel = st.multiselect("Choose teams", sorted(fdf["team"].dropna().unique().tolist())[:20])
    if teams_sel:
        tdf = fdf[fdf["team"].isin(teams_sel)]
        fig = px.line(tdf, x="year", y="wins", color="team", markers=True)
        fig.update_layout(xaxis_title="Year", yaxis_title="Wins")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select at least one team to view trend lines.")

with tab2:
    g = fdf.groupby(["year","league"], as_index=False).agg(avg_wins=("wins","mean"))
    fig2 = px.bar(g, x="year", y="avg_wins", color="league", barmode="group")
    fig2.update_layout(xaxis_title="Year", yaxis_title="Average Wins")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    if "payroll" in fdf.columns and fdf["payroll"].notna().any():
        year_pick = st.select_slider("Pick a year", options=sorted(fdf["year"].unique().tolist()), value=int(fdf["year"].max()))
        sdf = fdf[fdf["year"]==year_pick]
        fig3 = px.scatter(sdf, x="payroll", y="wins", color="league", hover_data=["team","division"])
        fig3.update_layout(xaxis_title="Payroll (USD)", yaxis_title="Wins", title=f"Wins vs Payroll — {year_pick}")
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("Note: Payroll values may be missing or approximate for some seasons on the source site.")
    else:
        st.warning("Payroll data not available in the scraped range. Expand year range or rescrape with more years.")

st.markdown("---")
st.markdown("Built with Streamlit + Plotly. Educational use only.")
