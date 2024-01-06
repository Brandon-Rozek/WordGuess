"""
WordGuess Leaderboard Viewer
Author: Brandon Rozek
"""
from datetime import datetime
import argparse
import sqlite3

from wordguess import WordGuess

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leaderboard for WordGuess Game")
    parser.add_argument("--date", type=str, help="Filter scores by date listed in YYYY-MM-DD format.")
    args = vars(parser.parse_args())

    # If not specified, then use today's date
    DATE = args.get("date")
    if DATE is None:
        DATE = str(datetime.today().date())

    con = sqlite3.connect(WordGuess.RESULTS_LOCATION)
    try:
        cur = con.cursor()
        res = cur.execute(f"SELECT user, score FROM scores WHERE date = '{DATE}' ORDER BY score DESC")
        print(f"High scores for date '{DATE}'")
        for username, score in res.fetchall():
              print(username, score)
    finally:
        con.close()
