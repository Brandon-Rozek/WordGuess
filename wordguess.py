"""
Author: Brandon Rozek

Contains common data structures
between WordGuess client and server
"""
from dataclasses import dataclass

class WordGuess:
    RESULTS_LOCATION = "/home/rozek/repo/wordGuess/results.db"
    ADDRESS = "/home/rozek/wordGuess/game.sock"

    @dataclass
    class GuessMessage:
        word: str
        action: str = "guess"
        def __post_init__(self):
            assert self.action == "guess"

    @dataclass
    class GuessResponseMessage:
        guesses_remaining: int
        valid: bool = False
        winner: bool = False
        hint: str = ""
        letters_guessed: str = ""

    @dataclass
    class GameStartMessage:
        is_winner: bool
        num_characters: int
        guesses_remaining: int
        letters_guessed: str
