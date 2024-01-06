"""
Author: Brandon Rozek

WordGuess game server

TODO: argparse

TODO: Multiple users trying to access it at same time?

TODO: Fix timeout issue

"""
from datetime import datetime
from functools import lru_cache
from pubnix import (
    run_simple_server,
    receive_message,
    send_message
)
from collections import defaultdict
from wordguess import WordGuess
from typing import List
import os
import pickle
from pathlib import Path
import sqlite3

SEED = 838211
SAVE_LOCATION = "state.pickle"

@lru_cache
def char_positions(word: str):
    """
    Return a dictionary with positions
    of each character within a word.
    Ex: "hello" -> {"h": [0], "e": [1], "l": [2, 3], "o": [4]}
    """
    result = defaultdict(list)
    for i, char in enumerate(word):
        result[char].append(i)
    return result

def make_zero():
    return 0

def make_false():
    return False

def make_default_dict_zero():
    return defaultdict(make_zero)

def make_default_dict_false():
    return defaultdict(make_false)

def make_default_dict_set():
    return defaultdict(set)

class WordGuessServer:
    def __init__(self, seed, word_length = 5, guesses_allowed = 6):
        self.seed = seed
        self.word_length = word_length
        self.guesses_allowed = guesses_allowed
        # date -> user str -> int
        self.guesses_made = defaultdict(make_default_dict_zero)
        # date -> user str -> bool
        self.is_winner = defaultdict(make_default_dict_false)
        # date -> user str -> set[char]
        self.letters_guessed = defaultdict(make_default_dict_set)

    def fix_permissions(self):
        # 33152 = '-rw-------.'
        # 33188 = '-rw-r--r--.'
        os.chmod(__file__, 33152)
        os.chmod("pubnix.py", 33188)
        os.chmod("wordguess.py", 33188)
        os.chmod("words.txt", 33188)
        os.chmod("client.py", 33188)
        Path(WordGuess.RESULTS_LOCATION).touch(33188)
        Path(SAVE_LOCATION).touch(33152)

    @staticmethod
    def save_record(date, username, score):
        con = sqlite3.connect(WordGuess.RESULTS_LOCATION)
        try:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS scores(user TEXT NOT NULL, score INT NOT NULL, date TIMESTAMP NOT NULL, PRIMARY KEY (user, date))"
            )
            cur.execute("INSERT INTO scores VALUES (?, ?, ?)", (username, score, date))
            con.commit()
        except sqlite3.IntegrityError:
            print("Cannot write record:", (date, username, score))
        finally:
            con.close()

    @lru_cache
    def get_words(self):
        words = []
        game_words = "words.txt"
        # guess_words = "words.txt"
        with open(game_words, "r") as file:
            lines = file.read().splitlines()
            words.extend([l for l in lines if len(l) == self.word_length])
        return words

    def get_wotd(self, day):
        words = self.get_words()
        index = (day.year * day.month * day.day * self.seed) % len(words)
        return words[index]

    def valid_guess(self, guess: str):
        if len(guess) != self.word_length:
            return False

        # Guess needs to be part of our
        # dictionary
        if guess not in self.get_words():
            return False

        return True

    @staticmethod
    def compare(expected: str, guess: str) -> List[str]:
        output = ["_"] * len(expected)
        counted_pos = set()

        # (1) Check for letters in correct positions
        for i, (e_char, g_char) in enumerate(zip(expected, guess)):
            if e_char == g_char:
                output[i] = e_char

        gchar_pos = char_positions(expected) 

        for i, g_char in enumerate(guess):
            if g_char in expected and output[i] in ["_", "*"]:
                for pos in gchar_pos[g_char]:
                    if pos not in counted_pos:
                        output[i] = "*"
                        counted_pos.add(pos)
                        break
        
        return output

    def game(self, connection, user):
        # As long as the connection is alive,
        # treat the time the same
        # NOTE: Timeout does exist in pubnix.py
        today = datetime.today().date()
        wotd = self.get_wotd(today)
        
        gr = self.guesses_allowed - self.guesses_made[today][user]
        is_winner = self.is_winner[today][user]
        send_message(connection, WordGuess.GameStartMessage(is_winner, self.word_length, gr, list(self.letters_guessed[today][user])))

        if self.is_winner[today][user]:
            return

        while not self.is_winner[today][user] and self.guesses_made[today][user] < self.guesses_allowed:
            message = receive_message(connection, WordGuess.GuessMessage)
            message.word = message.word.lower()

            if not self.valid_guess(message.word):
                send_message(connection, WordGuess.GuessResponseMessage(gr))
                continue

            self.is_winner[today][user] = message.word == wotd
            if not self.is_winner[today][user]:
                self.guesses_made[today][user] += 1
            gr = self.guesses_allowed - self.guesses_made[today][user]
            result = WordGuessServer.compare(wotd, message.word)

            # Populate letters guessed
            for c in message.word:
                self.letters_guessed[today][user].add(c)

            send_message(
                connection,
                WordGuess.GuessResponseMessage(
                    gr,
                    True,
                    self.is_winner[today][user],
                    result, 
                    list(self.letters_guessed[today][user])
                )
            )
        
        if self.is_winner[today][user]:
            WordGuessServer.save_record(today, user, gr)

if __name__ == "__main__":
    w = WordGuessServer(SEED)

    # Load data structure if existent
    if os.path.exists(SAVE_LOCATION):
        with open(SAVE_LOCATION, "rb") as file:
            w = pickle.load(file)
            print("Successfully loaded game state")

    # Make sure permissions are correct
    # to prevent cheating...
    w.fix_permissions()
    
    try:
        run_simple_server(WordGuess.ADDRESS, w.game)
    finally:
        # Save game data structure
        print("Saving game state... ", end="")
        with open(SAVE_LOCATION, "wb") as file:
            pickle.dump(w, file)
        print("Done.")
