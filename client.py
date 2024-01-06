"""
Author: Brandon Rozek

TODO: Argparse
"""
from datetime import datetime

from pubnix import (
    run_simple_client,
    send_message,
    receive_message
)
from wordguess import WordGuess

WIN_TEXT = lambda score: f"""
Congratulations! You solved the word of the day.
Come back tomorrow! Your score: {score}
"""

GUESSES_REMAINING = lambda gr: f"You have {gr} guesses remaining."

LOSE_TEXT = """
You ran out of guesses for the day. Come back tomorrow!
"""


class WordGuessClient:
    def __init__(self):
        pass


    def start_game(self, client, _):
        message = receive_message(client, WordGuess.GameStartMessage)
        guesses_remaining = message.guesses_remaining
        is_winner = message.is_winner
        today = datetime.today().date()
        print(f"""
Welcome to WordGuess!
              
The goal is to guess the word of the day.
This word is {message.num_characters} characters long.

A * character means a letter was guessed correctly,
but in the incorrect position.
          
Today is {today}.
""")
        if is_winner:
            print(WIN_TEXT(guesses_remaining))
        elif guesses_remaining > 0:
            print(f"You have {guesses_remaining} guesses remaining")
            print("\nTo quit, press CTRL-C.")

        try:
            while not is_winner and guesses_remaining > 0:
                guess = input("Guess: ")
                send_message(client, WordGuess.GuessMessage(guess))

                message = receive_message(client, WordGuess.GuessResponseMessage)
                if not message.valid:
                    print("Not a valid guess, try again.")
                    continue
                
                guesses_remaining = message.guesses_remaining
                is_winner = message.winner
                print(message.hint)
                print(GUESSES_REMAINING(guesses_remaining))
                print("Letters Guessed:", sorted(message.letters_guessed))
                
                if is_winner:
                    print(WIN_TEXT(guesses_remaining))
            
            if not is_winner:
                print(LOSE_TEXT)

        except KeyboardInterrupt:
            pass
        


if __name__ == "__main__":
    w = WordGuessClient()
    run_simple_client(WordGuess.ADDRESS, w.start_game)
