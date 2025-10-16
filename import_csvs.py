"""
Imports each CSV in data/raw and data/clean as a separate table in a SQLite DB.
Table name is derived from filename (non-alphanumeric -> underscore).
Ensures datatypes by pandas dtype inference.
"""
import re
import sqlite3
from pathlib import Path
import pandas as pd
import glob

BASE = Path(__file__).resolve().parents[0]
DB_PATH = BASE / "db" / "baseball_history.db"

def tableize(name: str) -> str:
    name = re.sub(r"\.csv$", "", name)
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name).lower()
    return name

def import_folder(folder: Path, conn):
    files = glob.glob(str(folder / "*.csv"))
    for f in files:
        df = pd.read_csv(f)
        tname = tableize(Path(f).name)
        df.to_sql(tname, conn, if_exists="replace", index=False)
        print(f"[OK] Imported {Path(f).name} -> table {tname} ({len(df)} rows)")

def main():
    BASE.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        import_folder(BASE / "data" / "raw", conn)
        import_folder(BASE / "data" / "clean", conn)
        print(f"[DONE] SQLite DB at: {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
