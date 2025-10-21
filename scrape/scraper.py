"""
Selenium scraper for Baseball Almanac Year-in-Review (AL/NL) → Team Standings.
Writes CSVs to data/raw and a merged data/raw/standings_all_raw.csv
"""
from pathlib import Path
from time import sleep
from io import StringIO
import re

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import (
    START_YEAR, END_YEAR, LEAGUE_URLS,
    REQUEST_DELAY_SEC, MAX_RETRIES, USER_AGENT
)

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def init_driver(headless: bool = True):
    opts = Options()
    opts.page_load_strategy = "eager"
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(f"--user-agent={USER_AGENT}")
    try:
        opts.add_experimental_option(
            "prefs",
            {"profile.managed_default_content_settings.images": 2}
        )
    except Exception:
        pass

    service = Service() 
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def _norm(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"\s+", "_", s)
    return s


def _normalize_cols(cols):
    return [_norm(c) for c in cols]


def _pick_standings_table(html: str):
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(["h1", "h2", "h3", "b", "strong"]):
        if "team standings" in tag.get_text(strip=True).lower():
            t = tag.find_next("table")
            if t:
                return t

    best, best_score = None, -1
    for t in soup.find_all("table"):
        txt = t.get_text(" ", strip=True).lower()
        score = 0
        if "standings" in txt:
            score += 2
        if " wins " in txt or " w " in txt:
            score += 2
        if " losses " in txt or " l " in txt:
            score += 2
        if " pct" in txt or " w-l%" in txt or " win%" in txt or " wp " in txt:
            score += 1
        if score > best_score:
            best, best_score = t, score
    return best


def parse_standings_html(html: str, league: str) -> pd.DataFrame:
    target = _pick_standings_table(html)
    if target is None:
        raise ValueError("standings table not found")

    df = pd.read_html(StringIO(str(target)))[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            "_".join([str(x) for x in tup if str(x) != "nan"]).strip().lower()
            for tup in df.columns
        ]
    else:
        df.columns = _normalize_cols(df.columns)

    need_header_lift = not any(c in df.columns for c in ("w", "wins")) and not any(c in df.columns for c in ("l", "losses"))
    if need_header_lift and len(df) > 1:
        header_row = [_norm(x) for x in df.iloc[0].tolist()]
        if ("w" in header_row or "wins" in header_row) and ("l" in header_row or "losses" in header_row):
            df = df.iloc[1:].copy()
            header_row = (header_row + [f"col{i}" for i in range(100)])[: df.shape[1]]
            df.columns = header_row

    df.columns = _normalize_cols(df.columns)

    rename = {
        "team_[click_for_roster]": "team",
        "teams": "team",
        "tm": "team",
        "club": "team",
        "franchise": "team",
        "w": "wins",
        "l": "losses",
        "w-l%": "win_pct",
        "wp": "win_pct",
        "pct": "win_pct",
        "win%": "win_pct",
        "win": "win_pct",
        "gb": "games_behind",
    }
    for k, v in rename.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    if "team" not in df.columns and df.shape[1] >= 1:
        df = df.rename(columns={df.columns[0]: "team"})

    keep = [c for c in ["team", "wins", "losses", "win_pct", "games_behind", "payroll", "division"] if c in df.columns]
    df = df[keep].copy()

    # типы
    if "wins" not in df.columns:
        df["wins"] = pd.NA
    if "losses" not in df.columns:
        df["losses"] = pd.NA

    for col in ["wins", "losses"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "win_pct" in df.columns:
        s = (
            df["win_pct"].astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.replace(r"^\.(\d+)$", r"0.\1", regex=True)
        )
        df["win_pct"] = pd.to_numeric(s, errors="coerce")

    if "games_behind" in df.columns:
        s = (
            df["games_behind"].astype(str)
            .str.replace("—", "0", regex=False)
            .str.replace("–", "0", regex=False)
        )
        df["games_behind"] = pd.to_numeric(s, errors="coerce")

    if "payroll" in df.columns:
        s = (
            df["payroll"].astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace("†", "", regex=False)
        )
        df["payroll"] = pd.to_numeric(s, errors="coerce")

    if "division" not in df.columns:
        df.insert(0, "division", None)
    df.insert(0, "league", league)
    return df


def scrape_year(driver, year: int):
    frames = []
    for league, url_tmpl in LEAGUE_URLS.items():
        url = url_tmpl.format(year=year)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                driver.get(url)
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                sleep(REQUEST_DELAY_SEC)
                df = parse_standings_html(driver.page_source, league)
                df.insert(0, "year", year)
                out = RAW_DIR / f"standings_{year}_{league}.csv"
                df.to_csv(out, index=False)
                print(f"[OK] {year} {league}: {out.name} ({len(df)} rows)")
                frames.append(df)
                break
            except Exception as e:
                if attempt >= MAX_RETRIES:
                    print(f"[ERROR] {year} {league}: {e}")
                else:
                    sleep(REQUEST_DELAY_SEC * attempt)
    return pd.concat(frames, ignore_index=True) if frames else None


def main():
    driver = init_driver(headless=True)
    try:
        all_frames = []
        for y in range(START_YEAR, END_YEAR + 1):
            df = scrape_year(driver, y)
            if df is not None:
                all_frames.append(df)
        if all_frames:
            merged = pd.concat(all_frames, ignore_index=True)
            merged.to_csv(RAW_DIR / "standings_all_raw.csv", index=False)
            print(f"[DONE] Wrote merged CSV with {len(merged)} rows")
        else:
            print("[WARN] No data scraped.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
