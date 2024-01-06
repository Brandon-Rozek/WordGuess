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
