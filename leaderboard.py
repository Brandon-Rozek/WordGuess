"""
Author: Brandon Rozek

View leaderboard information for a particular date

# TODO: argparse
"""

from wordguess import WordGuess
import sqlite3
from datetime import datetime


DATE = str(datetime.today().date())

if __name__ == "__main__":
    con = sqlite3.connect(WordGuess.RESULTS_LOCATION)
    try:
        cur = con.cursor()
        res = cur.execute(f"SELECT user, score FROM scores WHERE date = '{DATE}' ORDER BY score DESC")
        for username, score in res.fetchall():
              print(username, score)
    finally:
        con.close()
