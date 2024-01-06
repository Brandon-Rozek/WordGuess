from collections import defaultdict
from datetime import datetime
from typing import List

SEED = 838232

WORDS = []

GAME_WORDS = "gamewords.txt"
GUESS_WORDS = "guesswords.txt"
WORD_LENGTH = 5

with open("words.txt", "r") as file:
    lines = file.read().splitlines()
    WORDS.extend([l for l in lines if len(l) == WORD_LENGTH])

NUMBER_OF_GUESSES = 6

TODAY = datetime.today()
WORD_OF_THE_DAY = WORDS[(TODAY.year * TODAY.month * TODAY.day * SEED) % len(WORDS) ]

def valid_guess(guess: str):
    if len(guess) != len(WORD_OF_THE_DAY):
        return False
    
    # Guess needs to be part of our
    # dictionary
    if guess not in WORDS:
        return False
    
    return True

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


CHAR_POSITIONS = char_positions(WORD_OF_THE_DAY)

def compare(expected: str, guess: str) -> List[str]:
    output = ["_"] * len(expected)
    counted_pos = set()


    # (1) Check for letters in correct positions
    for i, (e_char, g_char) in enumerate(zip(expected, guess)):
        if e_char == g_char:
            output[i] = e_char


    for i, g_char in enumerate(guess):
        if g_char in expected and output[i] in ["_", "-"]:
            for pos in CHAR_POSITIONS[g_char]:
                if pos not in counted_pos:
                    output[i] = "-"
                    counted_pos.add(pos)
                    break
        pass

    return output

if __name__ == "__main__":
    num_guesses = 0
    print("""
Guess words one at a time to guess the game word.

A - character means a letter was guessed correctly,
but in the incorrect position.

To quit, press CTRL-C.
""")
    # start of the user name interaction
    print("_ " * WORD_LENGTH)
    while True:
        guess = input("Guess: ").lower()
        if not valid_guess(guess):
            print("Not a valid guesss")
            continue
        num_guesses += 1

        result = compare(WORD_OF_THE_DAY, guess)
        print(" ".join(result))

        if guess == WORD_OF_THE_DAY:
            print("You won")
            break

        if num_guesses >= NUMBER_OF_GUESSES:
            print("You lost")
            break