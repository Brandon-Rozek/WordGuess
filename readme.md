# WordGuess

Daily pubnix game where you guess the word of the day.
Compare your word chops with other people on the same
server!

## Server

Make sure that the WordGuess folder is accessible
to other users.

This means that if the code lives
in `/home/wg/WordGuess` then the executable permission must
be given to `/home/wg`.

```bash
chmod o+x /home/wg
```

The server code will adjust the permissions of all the other files
to circumvent cheating.


To run the server
```bash
python server.py
```

You should see an output such as
```
Successfully loaded game state
Seed:  701625
Started server at /home/wg/WordGuess/game.sock
```

Don't share the seed with anyone! Otherwise they can
figure out the word for all future days.

You can reset the seed and all game state by removing the file `state.pickle`.

A systemd service file is provided under `wordguess.service` in order to provide another way to run the server.

Copy `wordguess.service` to `~/.config/systemd/user` and then enable and start the service with:

```bash
systemctl --user enable --now wordguess
```

To start on boot-up, your user needs to have `Linger` enabled. If you have root access, you can run:

```bash
sudo loginctl enable-linger $USER
```

## Players

Players can play the game by running the `client.py` python script.
If the game lives under `/home/wg/WordGuess` then the command will be

```bash
python /home/wg/WordGuess/client.py
```

After playing the game, the server will record the users high score.
They can see the leaderboard by running

```bash
python /home/wg/WordGuess/leaderboard.py
```

You can also pass a date with `--date`.


## Notes

Word list from [Morgenstern2573/wordle_clone](https://github.com/Morgenstern2573/wordle_clone/blob/master/build/words.js) on GitHub.
