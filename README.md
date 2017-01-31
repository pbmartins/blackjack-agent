# Blackjack Agent

Automated agent to play Blackjack. It was developed for the Introduction to Artificial Intelligence (IIA) final project of the Computers and Telematics Engeneering (ECT) course of Aveiro Universitity (UA).

## Rules of the game

The rules defined are basically the rules of common Blackjack, with some exceptions:

- There's more than one turn per game (instead of playing hit or stand just one time, for the game to end, one of the players must bust or all of them must stand);
- Double-down ends the game for the player who've done it (receives one final card);
- Dealer stands at soft 17.

## Learning how to play

So that the agent can know how to play, it was used a "machine learning" like strategy.
The agent starts with a table of states (PlayerPoints, DealerPoints, FirstTurn, SoftHand, PlayerHand, PlayStand, PlayHit, FinalStand, FinalHit, BadPlay), which are used fer each different play of the game. Next, we use:

    python3 train_agent.py

in order to play a defined number of games so that the agent can learn (all of the settings are in the `settings.json` file.

We'll finish with all the states for all the player points, dealer points, soft hand, player ace and first turn fields combinations, with 5 more important fields:
- [PlayStand] - number of times that a intermediate stand was a good option (this will be likely 1, by default, because, whenever we stand, it'll always be our final play);
- [PlayHit] - number of times that a intermediate hit was a good option;
- [FinalStand] - number of times that a final stand was a good option and won a game;
- [FinalHit] - number of times that a hit stand was a good option and won a game (this is particularly helpful for the choice of when double-down;
- [BadPlay] - number of times that a hit nor stand was a good play.

## The results

To check the results of the games, simply:

    python3 test_results.py

This script will play 10 times with all the thresholds defined in `settings.json` and show all the percentagens associated with each game.

If you have any sugestion, please feel free to contribute!

Diogo Ferreira

Pedro Martins
