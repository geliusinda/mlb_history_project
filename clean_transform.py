"""
Cleans raw standings CSVs into a normalized table.
Outputs data/clean/standings_clean.csv
Also writes a small 'before_after_sample.csv' showing original vs cleaned for rubric.
"""
from pathlib import Path
import pandas as pd
import glob

RAW_DIR = Path(__file__).resolve().parents[0] / "data" / "raw"
CLEAN_DIR = Path(__file__).resolve().parents[0] / "data" / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

def load_raw():
    files = glob.glob(str(RAW_DIR / "standings_*_*.csv"))
    frames = []
    for f in files:
        df = pd.read_csv(f)
        df["source_file"] = Path(f).name
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def clean(df):
    if "team" in df.columns:
        df = df[df["team"].notna()].copy()
        df["team"] = df["team"].str.strip()
    for col in ["wins","losses","payroll","games_behind","win_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "wins" in df.columns and "losses" in df.columns:
        df["games_played"] = df["wins"] + df["losses"]
        df["win_pct"] = (df["wins"] / df["games_played"]).replace([float("inf"), -float("inf")], pd.NA)
    if "division" in df.columns:
        df["division"] = df["division"].fillna("Unknown").str.title()
    return df

def main():
    raw = load_raw()
    if raw.empty:
        print("No raw files found in data/raw; run the scraper first.")
        return
    before_sample = raw.head(10).copy()
    cleaned = clean(raw)
    cleaned.to_csv(CLEAN_DIR / "standings_clean.csv", index=False)
    after_sample = cleaned.head(10).copy()
    sample = pd.concat({
        "before": before_sample.reset_index(drop=True),
        "after": after_sample.reset_index(drop=True)
    }, axis=1)
    sample.to_csv(CLEAN_DIR / "before_after_sample.csv", index=False)
    print(f"Wrote {len(cleaned)} cleaned rows to data/clean/standings_clean.csv")

if __name__ == "__main__":
    main()
