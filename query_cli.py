"""
Simple CLI to run SQL queries against the SQLite database.
Usage examples (PowerShell):
  python query_cli.py "PRAGMA table_info(standings_clean);"
  python query_cli.py "SELECT * FROM standings_clean LIMIT 10;"
  python query_cli.py 'CREATE TABLE standings_fixed AS SELECT year, league, division, [team.1] AS team, source_file FROM standings_clean;'
"""
import sqlite3, sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[0] / "db" / "baseball_history.db"

EXAMPLES = [
    "PRAGMA table_info(standings_clean);",
    "SELECT * FROM standings_clean LIMIT 10;",
    'CREATE TABLE standings_fixed AS SELECT year, league, division, [team.1] AS team, source_file FROM standings_clean;',
    "PRAGMA table_info(standings_fixed);",
    "SELECT year, league, division, team FROM standings_fixed ORDER BY year, league, team LIMIT 20;",
]

def main():
    if not DB_PATH.exists():
        print("DB not found. Run import_csvs.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        if len(sys.argv) > 1:
            q = sys.argv[1]
        else:
            print("No query provided. Try one of these:\n")
            for ex in EXAMPLES:
                print("  ", ex)
            return

        cur = conn.execute(q)

        # Non-SELECT (CREATE/ALTER/INSERT/UPDATE/DELETE) return no rows
        if cur.description is None:
            conn.commit()
            print("OK.")
            return

        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

        from tabulate import tabulate
        print(tabulate(rows, headers=cols, tablefmt="github"))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
