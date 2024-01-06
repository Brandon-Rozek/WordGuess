"""
Author: Brandon Rozek
Client for the WordGuess pubnix game.
"""
from datetime import datetime
from pubnix import (
    run_simple_client,
    send_message,
    receive_message
)
from wordguess import WordGuess

## Messages

STARTUP_MESSAGE = lambda nc, td: f"""
Welcome to WordGuess!

The goal is to guess the word of the day.
This word is {nc} characters long.

A * character means a letter was guessed correctly,
but in the incorrect position.

Today is {td}.
"""

WIN_TEXT = lambda score: f"""
Congratulations! You solved the word of the day.
Come back tomorrow! Your score: {score}
"""

GUESSES_REMAINING = lambda gr: f"You have {gr} guesses remaining."

LOSE_TEXT = """
You ran out of guesses for the day. Come back tomorrow!
"""

## Game Client

class WordGuessClient:
    def __init__(self):
        pass

    def start_game(self, client, _):

        # In case the user already played today, we want to get
        # information from the server on the current state
        message = receive_message(client, WordGuess.GameStartMessage)
        guesses_remaining = message.guesses_remaining
        is_winner = message.is_winner
        today = datetime.today().date()

        print(STARTUP_MESSAGE(message.num_characters, today))
        
        if is_winner:
            print(WIN_TEXT(guesses_remaining))
        elif guesses_remaining > 0:
            print(f"You have {guesses_remaining} guesses remaining")
            print("\nTo quit, press CTRL-C.")

        # Core loop if the user has more guesses remaining
        try:
            while not is_winner and guesses_remaining > 0:
                guess = input("Guess: ")
                send_message(client, WordGuess.GuessMessage(guess))

                # Get response from server based on the word provided
                message = receive_message(client, WordGuess.GuessResponseMessage)
                if not message.valid:
                    print("Not a valid guess, try again.")
                    continue

                guesses_remaining = message.guesses_remaining
                is_winner = message.winner

                # Display hints
                print(message.hint)
                print(GUESSES_REMAINING(guesses_remaining))
                print("Letters Guessed:", sorted(message.letters_guessed))

                if is_winner:
                    print(WIN_TEXT(guesses_remaining))

            # Ran out of guesses, present lose text
            if not is_winner:
                print(LOSE_TEXT)

        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    w = WordGuessClient()
    run_simple_client(WordGuess.ADDRESS, w.start_game)
