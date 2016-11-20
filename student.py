#encoding: utf8
import card
import random
from qtablelib import Qtable
import numpy
import math
from player import Player
from collections import defaultdict

class StudentPlayer(Player):
    def __init__(self, name="Meu nome", money=0):
        super(StudentPlayer, self).__init__(name, money)
        self.create = False
        self.total_games = self.games_left = 5000000 if self.create else 1000
        self.plays = ['s', 'h', 'u', 'd']
        
        # Counting stats
        self.wins = 0
        self.defeats = 0
        self.draws = 0
        self.surrenders = 0

        # Create tables to save state-action average rewards
        self.tables = Qtable('tables/qtable_5M_sarsa.npy', \
                'tables/ctable_5M_sarsa.npy', create=self.create)


    def want_to_play(self, rules):
        self.etrace = defaultdict(float)
        self.results = {}
        self.turn = 0
        return True

    def play(self, dealer, players):
        # Get player hand
        hand = [p.hand for p in players if p.player.name == self.name][0]
        # If player's hand total is under 11, keep hitting
        if(card.value(hand)) < 11:
            return "h"

        # Increment turn
        self.turn += 1

        # Get players' totals
        player_value = card.value(hand)
        #player_ace = len([c for c in hand if c.is_ace()]) >= 1
        dealer_value = card.value(dealer.hand)
        #dealer_ace = len([c for c in dealer.hand if c.is_ace()]) >= 1

        # There's something tricky here, example:
        #   Dealer's hand: 2, ace, hidden
        #   card.value(dealer.hand) will return 13 because the sum of the first two cards \
        #       don't go over the 21 limit, even if the third card is a Jack, and then, \
        #       the ace will be considered 1 and not 11, as we thought initially

        # The ace will be counted as 1, because there's stil a card to show
        if dealer_value >= 21:
            dealer_value -= 10

        state = (player_value, dealer_value)
        # Access qtable and search for the best probability based on state-action
        probabilities = [self.tables.qtable.get((state, 's'), 0.5), \
                self.tables.qtable.get((state, 'h'), 0.5), \
                self.tables.qtable.get((state, 'u'), 0.3)]
        max_prob = max(probabilities)
        action = self.plays[probabilities.index(max_prob)]

        # Update counting table and create state-action entry on results dict
        self.next_sa = (state, action)
        self.results[self.next_sa] = 0.5
                
        if self.turn > 1:
            self.tables.update_tables(self.current_sa, self.next_sa, \
                    self.results, self.etrace)

        self.tables.ctable[self.next_sa] += 1
        self.current_sa = self.next_sa
        return action

    def bet(self, dealer, players):
        self.bet_value = 2
        return 2


    def payback(self, prize):
        self.result = 0
        if prize > 0:
            self.result = 1
        elif prize < 0:
            self.result = 0 if prize == -self.bet_value else 0.25
        else:
            self.result = 0.5

        self.wins += 1 if self.result == 1 else 0
        self.defeats += 1 if self.result == 0 else 0
        self.draws += 1 if self.result == 0.5 else 0
        self.surrenders += 1 if self.result == 0.25 else 0

        # Update qtable with the results of the current game
        if self.turn > 0:
            self.tables.update_tables(self.current_sa, self.next_sa, \
                    self.results, self.etrace, True)
        
        # Update game values
        self.table = 0
        self.pocket += prize
        self.games_left -= 1
        

        if self.games_left == 0:
            print("Number of victories: " + str(self.wins))
            print("Number of defeats: " + str(self.defeats))
            print("Number of draws: " + str(self.draws))
            print("Number of surrenders: " + str(self.surrenders))


        if self.create:
            print(self.total_games - self.games_left)
            self.tables.save_tables()
