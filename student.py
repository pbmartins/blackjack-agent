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
        self.total_games = self.games_left = 1000000 if self.create else 1000
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
        self.tables = Qtable('tables/qtable_2M_final.npy', create=self.create)

        self.learning_rate = 0.015
        self.damage_rate = 0.7
        self.damage = 1

    def want_to_play(self, rules):
        self.rules = rules
        self.results = []
        self.turn = 0
        self.previous_cards = 0
        self.dealer_action = 'h'
       
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
        player_hand = [p.hand for p in players if p.player.name == self.name][0]
        if len(dealer.hand) != self.previous_cards:
            previous_cards = len(dealer.hand)
        else:
            self.dealer_action = 's'

        # Increment turn
        self.turn += 1

        # Get players' total
        self.player_value = card.value(player_hand)
        player_ace = len([c for c in player_hand if c.is_ace()]) >= 1
        self.dealer_value = card.value(dealer.hand)

        #if dealer_value >= 21:
        #    dealer_value -= 10

        state = (self.player_value, self.dealer_value, player_ace, self.turn == 1)
        # Access qtable and search for the best probability based on state-action
        default = 0.25 if self.turn == 1 else 1/3
        dd = 0.25

        probabilities = [self.tables.qtable.get((state, 's'), default), \
                self.tables.qtable.get((state, 'h'), default), \
                self.tables.qtable.get((state, 'u'), default)]
        probabilities += [self.tables.qtable.get((state, 'd'), dd)] \
                if self.turn == 1 else []
        if not self.create and self.turn == 1 and self.disable_dd:
            probabilities[1] += probabilities[3]
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
        if self.wallet >= (self.initial_wallet * 0.50):
            self.bet_value = int(self.wallet * 0.1)
        elif self.wallet >= (self.initial_wallet * 0.10):
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

    def adjust(self, probs, action, min_threshold, max_threshold, good_surr):
        up, down = self.get_up_down(len(probs) - 1, good_surr)
        if self.result == 1:
            condition = lambda p: p[0] + up > max_threshold
        elif self.result == 0:
            condition = lambda p: p[0] + up < min_threshold
        elif self.result == 0.25:
            if not good_surr:
                condition = lambda p: p[0] + up < min_threshold
            else:
                condition = lambda p: p[0] + up > max_threshold
        else:
            return False
        return not any([p[1] == action and condition(p) for p in probs])


    def get_probs(self, probs, action, min_threshold, max_threshold, good_surr):
        if len(probs) < 2:
            return None
        surrender_cond = lambda p, up, down: p[0] + down < min_threshold \
                if down < 0 else p[0] + down < max_threshold
        for p in probs:
            if p[1] != action:
                up, down = self.get_up_down(len(probs) - 1, good_surr)
                if self.result == 1 and p[0] + down < min_threshold or \
                        self.result == 0 and p[0] + down > max_threshold or \
                        self.result == 0.25 and surrender_cond(p, up, down):
                    probs.remove(p)
                    max_threshold = 1.0 - min_threshold * (len(probs) - 1)
                    return self.get_probs(probs, action, min_threshold, max_threshold, good_surr)
        return probs

    def get_up_down(self, div, good_surr):
        up = self.learning_rate * self.damage
        down = -self.learning_rate * self.damage / div
        if self.result == 1:
            return up, down
        if self.result == 0:
            return -up, -down
        elif self.result == 0.25:
            return (-up, -down) if not good_surr else (up / 3, down / 3)
        else:
            return 0, 0

    def good_surrender(self):
        new_dealer_points = self.dealer_value + 7
        if new_dealer_points > 21:
            return 0

        scenarios = [self.player_value + c for c in list(range(1, 12)) + [10, 10, 10]]
        p_bust = len([v for v in scenarios if v > 21]) / len(scenarios)
        threshold = 0.5
        if new_dealer_points > self.player_value:
            return 0 if p_bust > threshold else 1
        else:
            return 0
        #return 1 if new_dealer_points > self.player_value and p_bust > threshold else 0
      

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
            good_surr = 0.0
            for i in reversed(range(len(self.results))):
                state, action = self.results[i]
                good_surr = self.good_surrender() if action == 'u' else good_surr
                
                default = 0.25 if i == 0 else 1/3

                # Get probabilities and filter values between 0.02 and 0.98
                probs = [(self.tables.qtable.get((state, 's'), default), 's'), \
                    (self.tables.qtable.get((state, 'h'), default), 'h'), \
                    (self.tables.qtable.get((state, 'u'), default), 'u')]
                probs += [(self.tables.qtable.get((state, 'd'), dd), 'd')] \
                        if i == 0 else []

                max_threshold = 1.0 - min_threshold * (len(probs) - 1)
                skip = False

                for p, a in probs:
                    if p > max_threshold or p < min_threshold:
                        skip = True
                        break

                if skip:
                    continue

                up, down = self.get_up_down(len(probs) - 1, good_surr)
                new_values = [(p[0] + up, p[1]) if action == p[1] \
                        else (p[0] + down, p[1]) for p in probs]

                for p, a in probs:
                    self.tables.qtable[(state, a)] = p + up if action == a \
                            else p + down

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

