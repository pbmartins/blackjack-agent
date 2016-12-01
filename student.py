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
        self.create = True
        self.total_games = self.games_left = 10000000 if self.create else 1000
        self.plays = ['s', 'h', 'u', 'd']
     
        # Wallet 
        self.loans = [0.50, 0.25, 0.125]
        self.my_pocket = self.pocket
        self.initial_wallet = self.wallet = int(self.my_pocket * self.loans[0])
        self.my_pocket -= self.initial_wallet
        
        self.disable_dd = False

        # Counting stats
        self.wins = 0
        self.defeats = 0
        self.draws = 0
        self.surrenders = 0
        self.dont_play = 0

        # Create tables to save state-action average rewards
        self.tables = Qtable('tables/qtable_10M_final.npy', create=self.create)

        self.learning_rate = 0.015
        self.damage_rate = 0.5
        self.damage = 1

    def want_to_play(self, rules):
        self.rules = rules
        self.results = []
        self.turn = 0
       
        return True
        if self.create:
            return True

        # Get a loan
        if not self.wallet or self.wallet < (2 * rules.min_bet):
            if len(self.loans) > 1:
                self.initial_wallet = int(self.my_pocket * self.loans[1])
                self.wallet += self.initial_wallet
                self.my_pocket -= self.initial_wallet
                self.loans = self.loans[1:]
                return True
            else:
                self.dont_play += 1 
                self.games_left -= 1
                if self.games_left == 0:
                    self.end()
                return False
        # Transfer founds
        elif self.wallet > (self.initial_wallet * 1.5):
            self.my_pocket += self.wallet - self.initial_wallet
            self.wallet = self.initial_wallet
            return True
        
        return True

    def play(self, dealer, players):
        # Get player hand
        self.players_hand = [p.hand for p in players]
        self.player_hand = [p.hand for p in players if p.player.name == self.name][0]
        self.dealer_hand = dealer.hand

        # Increment turn
        self.turn += 1

        # Get players' totals
        player_value = card.value(self.player_hand)
        player_ace = len([c for c in self.player_hand if c.is_ace()]) >= 1
        dealer_value = card.value(dealer.hand)

        if dealer_value >= 21:
            dealer_value -= 10

        state = (player_value, dealer_value, player_ace, self.turn == 1)
        # Access qtable and search for the best probability based on state-action
        default = 0.25 if self.turn == 1 else 1/3
        dd = 0.25

        probabilities = [self.tables.qtable.get((state, 's'), default), \
                self.tables.qtable.get((state, 'h'), default), \
                self.tables.qtable.get((state, 'u'), default)]
        probabilities += [self.tables.qtable.get((state, 'd'), dd)] \
                if self.turn == 1 else []
        if not self.create and self.turn == 1 and self.disable_dd:
            probabilities = [probabilities[i] + probabilities[3] / 3 \
                    for i in range(0, len(probabilities))]
        intervals = [sum(probabilities[:idx]) for idx in range(1, len(probabilities) + 1)]
        r = random.uniform(0, 1)
        idx = 0
        while intervals[idx] < r:
            idx += 1

        action = self.plays[idx]
        self.results += [(state, action)]
        return action

    def bet(self, dealer, players): 
        self.disable_dd = False
        # Compute bet
        if self.wallet >= (self.initial_wallet * 0.80):
            self.bet_value = int(self.wallet * 0.1)
        elif self.wallet >= (self.initial_wallet * 0.20):
            self.bet_value = int(self.wallet * 0.05)
        else:
            self.bet_value = self.rules.min_bet
            self.disable_dd = True
        
        # Normalize values
        if self.bet_value > self.rules.max_bet:
            self.bet_value = self.rules.max_bet
        elif self.bet_value < self.rules.min_bet:
            self.bet_value = self.rules.min_bet
        
        self.bet_value = 2
        return self.bet_value

    def adjust(self, probs, action, min_threshold, max_threshold, win_prob):
        up, down = self.get_up_down(len(probs) - 1, win_prob)
        if self.result == 1:
            condition = lambda p: p[0] + up > max_threshold
        elif self.result == 0:
            condition = lambda p: p[0] + up < min_threshold
        elif self.result == 0.25:
            if win_prob > 0.6:
                condition = lambda p: p[0] + up < min_threshold
            else:
                condition = lambda p: p[0] + up > max_threshold
        else:
            return False
        return not any([p[1] == action and condition(p) for p in probs])



    def get_probs(self, probs, action, min_threshold, max_threshold, win_prob):
        if len(probs) < 2:
            return None
        surrender_cond = lambda p, up, down: p[0] + down < min_threshold \
                if down < 0 else p[0] + down < max_threshold
        for p in probs:
            if p[1] != action:
                up, down = self.get_up_down(len(probs) - 1, win_prob)
                if self.result == 1 and p[0] + down < min_threshold or \
                        self.result == 0 and p[0] + down > max_threshold or \
                        self.result == 0.25 and surrender_cond(p, up, down):
                    probs.remove(p)
                    max_threshold = 1.0 - min_threshold * (len(probs) - 1)
                    return self.get_probs(probs, action, min_threshold, max_threshold, win_prob)
        return probs

    def get_up_down(self, div, win_prob):
        up = self.learning_rate * self.damage
        down = -self.learning_rate * self.damage / div
        if self.result == 1:
            return up, down
        if self.result == 0:
            return -up, -down
        elif self.result == 0.25:
            return (-up / 2, -down / 2) if win_prob > 0.6 else (up / 2, down / 2)
        else:
            return 0, 0

    def get_win_prob(self):
        if card.value(self.dealer_hand) < 15 or len([c for c in self.dealer_hand if c.is_ace()]) > 0:
            return 1.0
        all_cards = [card.Card(s, r) for r in range(1, 14) for s in range(4)]
        # Remove cards already played
        for hand in self.players_hand + [self.dealer_hand]:
            initial_cards = [c for c in all_cards if c not in hand]

        # Create all possible scenarios
        d_scenarios = [(self.dealer_hand, initial_cards)]
        final_scenarios = []
        while d_scenarios != []:
            d_scenarios = [(s + [c], [x for x in cards if x != c]) \
                    for (s, cards) in d_scenarios for c in cards]
            #print("not filtered = " + str(d_scenarios))
            #print()
            final_scenarios += [s for (s, c) in d_scenarios if card.value(s) >= 17]
            #print("final filtered = " + str(final_scenarios))
            #print()
            d_scenarios = [(s, c) for (s, c) in d_scenarios if s not in final_scenarios]
            #print("scenarios filtered = " + str(d_scenarios))
            #print()

        player_total = card.value(self.player_hand)
        wins = len([s for s in final_scenarios \
                if card.value(s) > 21 or player_total > card.value(s)])
        return wins / len(final_scenarios)
        

    def payback(self, prize):
        self.result = 0
        if prize > 0:
            self.result = 1
        elif prize < 0:
            self.result = 0 if prize <= -self.bet_value else 0.25
        else:
            self.result = 0.5

        self.wins += 1 if self.result == 1 else 0
        self.defeats += 1 if self.result == 0 else 0
        self.draws += 1 if self.result == 0.5 else 0
        self.surrenders += 1 if self.result == 0.25 else 0
        
        # just change the table while learning else read only
        if self.create:
            # Update qtable with the results of the current game
            self.damage = 1
            dd = 0.25
            min_threshold = 0.02
            win_prob = 0.0
            for i in reversed(range(len(self.results))):
                state, action = self.results[i]
                #print(action)
                #print(self.dealer_hand)
                #print("player_total = " + str(card.value(self.player_hand)) \
                #        + ", dealer_total = " + str(card.value(self.dealer_hand)))
                win_prob = self.get_win_prob() if action == 'u' else win_prob
                #print("win_prob = " + str(win_prob))
                
                default = 0.25 if i == 0 else 1/3

                # Get probabilities and filter values between 0.02 and 0.98
                probs = [(self.tables.qtable.get((state, 's'), default), 's'), \
                    (self.tables.qtable.get((state, 'h'), default), 'h'), \
                    (self.tables.qtable.get((state, 'u'), default), 'u')]
                probs += [(self.tables.qtable.get((state, 'd'), dd), 'd')] \
                        if i == 0 else []

                max_threshold = 1.0 - min_threshold * (len(probs) - 1)

                #print("intial probs = " + str(probs))
                #print("action = " + action)
                # Adjust probabilities based on the reward
                # Check if the action to be valued does not surpass the min or max threshold
                adjust = self.adjust(probs, action, min_threshold, max_threshold, win_prob)
                if adjust:
                    # Filter values thar after updating surpass min or max threshold
                    probs = self.get_probs(probs, action, min_threshold, max_threshold, win_prob)
                    #print("filtered probs = " + str(probs))
                    if probs != None:
                        up, down = self.get_up_down(len(probs) - 1, win_prob)

                        new_values = [(p[0] + up, p[1]) if action == p[1] \
                                else (p[0] + down, p[1]) for p in probs]
                        #print("new_values = " + str(new_values))

                        for n in new_values:
                            self.tables.qtable[(state, n[1])] = n[0]

                self.damage *= self.damage_rate
                
            print(self.total_games - self.games_left)
        
        # Update game values
        self.table = 0
        self.pocket += prize
        self.wallet += prize
        self.games_left -= 1

        if self.games_left == 0:
            self.end()

    def end(self):
        self.my_pocket += self.wallet
        self.initial_wallet = self.wallet = 0
        print("Number of victories: " + str(self.wins))
        print("Number of defeats: " + str(self.defeats))
        print("Number of draws: " + str(self.draws))
        print("Number of surrenders: " + str(self.surrenders))
        print("Number of games passed: " + str(self.dont_play))
        if self.create:
            self.tables.save_tables()

