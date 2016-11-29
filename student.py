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
        self.total_games = self.games_left = 10000000 if self.create else 1000
        self.plays = ['s', 'h', 'u', 'd']
     
        # Wallet 
        self.loans = [0.70, 0.50, 0.25]
        self.initial_wallet = self.wallet = int(self.pocket * self.loans[0])
        self.pocket -= self.initial_wallet
        
        # Counting stats
        self.wins = 0
        self.defeats = 0
        self.draws = 0
        self.surrenders = 0
        self.dont_play = 0

        # Create tables to save state-action average rewards
        self.tables = Qtable('tables/qtable_10M_new.npy', create=self.create)

        self.learning_rate = 0.015
        self.damage = 0.5

    def want_to_play(self, rules):
        self.rules = rules
        self.etrace = defaultdict(float)
        self.results = []
        self.turn = 0
        
        # Get a loan
        if not self.wallet or self.wallet < (2 * rules.min_bet):
            if len(self.loans) > 1:
                self.initial_wallet = self.wallet = int(self.pocket * self.loans[1])
                self.pocket -= self.initial_wallet
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
            self.pocket += int(self.wallet - self.initial_wallet)
            self.wallet = self.initial_wallet
            return True
        
        return True

    def play(self, dealer, players):
        
        # Get player hand
        hand = [p.hand for p in players if p.player.name == self.name][0]

        # Increment turn
        self.turn += 1

        # Get players' totals
        player_value = card.value(hand)
        player_ace = len([c for c in hand if c.is_ace()]) >= 1
        dealer_value = card.value(dealer.hand)


        state = (player_value, dealer_value, player_ace, self.turn == 1)
        # Access qtable and search for the best probability based on state-action
        default = 0.25 if self.turn == 1 else 1/3
        dd = 0.25 if self.turn == 1 else 0
        probabilities = [self.tables.qtable.get((state, 's'), default), \
                self.tables.qtable.get((state, 'h'), default), \
                self.tables.qtable.get((state, 'u'), default), \
                self.tables.qtable.get((state, 'd'), dd)]
        intervals = [sum(probabilities[:idx]) for idx in range(1, 5)]
        r = random.uniform(0, 1)
        
        idx = 0
        while intervals[idx] < r:
            idx += 1
            if idx == len(intervals):
                idx -= 2
                break
        
        action = self.plays[idx]
        
        # Update counting table and create state-action entry on results dict
        #self.next_sa = (state, action)
        #self.results[self.next_sa] = 0.5
        #        
        #if self.turn > 1:
        #    self.tables.update_tables(self.current_sa, self.next_sa, \
        #            self.results, self.etrace)
        #
        #self.tables.ctable[self.next_sa] += 1
        #self.current_sa = self.next_sa

        self.results += [(state, action)]
        
        return action

    def bet(self, dealer, players):
        
        # Compute bet
        if self.wallet >= (self.initial_wallet * 0.80):
            self.bet_value = int(self.wallet * 0.1)
        elif self.wallet >= (self.initial_wallet * 0.20):
            self.bet_value = int(self.wallet * 0.05)
        else:
            self.bet_value = self.rules.min_bet
        
        # Normalize values
        if self.bet_value > self.rules.max_bet:
            self.bet_value = self.rules.max_bet
        elif self.bet_value < self.rules.min_bet:
            self.bet_value = self.rules.min_bet
        
        return self.bet_value

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

            
        # just change the table while learning else read only
        if self.create:
            # Update qtable with the results of the current game
            #if self.turn > 0:
            #    self.tables.update_tables(self.current_sa, self.next_sa, \
            #            self.results, self.etrace, True)
            
            damage = 1
            for i in reversed(range(len(self.results))):
                state, action = self.results[i]
                #div = 3 if i == 0 else 2
                default = 0.25 if i == 0 else 1/3
                dd = 0.25 if i == 0 else 0

                # Get probabilities and filter values between 0.02 and 0.98
                probabilities = [self.tables.qtable.get((state, 's'), default), \
                    self.tables.qtable.get((state, 'h'), default), \
                    self.tables.qtable.get((state, 'u'), default)]
                probabilities += [self.tables.qtable.get((state, 'd'), dd)] \
                        if i == 0 else []
                
                probs = [(probabilities[idx], self.plays[idx]) \
                        for idx in range(0, len(probabilities)) \
                        if probabilities[idx] > 0.02 and probabilities[idx] < 0.98]
                div = len(probs) - 1

                print(probs)
                # Adjust probabilities based on the reward
                if len(probs) < 2:
                    continue

                if self.result == 1:
                    up = self.learning_rate * damage
                    down = 0 - self.learning_rate * damage / div
                elif self.result == 0:
                    up = 0 - self.learning_rate * damage
                    down = self.learning_rate * damage / div
                elif self.result == 0.25:
                    up = 0 - self.learning_rate * damage / 1.5
                    down = self.learning_rate * damage / (1.5 * div)
                else:
                    up = 0
                    down = 0

                new_values = [(p[0] + up, p[1]) if action == p[1] \
                        else (p[0] + down, p[1]) for p in probs]


                for n in new_values:
                    self.tables.qtable[(state, n[1])] = n[0]

                damage *= self.damage
               
                # normalize values > 0.98 and < 0.02
                #need = True
                #while(need):
                #    need = False
                #    print(sum(new_values))
                #    print(new_values)
                #    for i in new_values:
                #        if i > 0.98:
                #            red = (i - 0.98) / (div - 1)
                #            val = 0.98
                #        elif i < 0:
                #            red = -((0 - i) / (div - 1))
                #            val = 0
                #        else:
                #            continue
                #        need = True
                #        for j in range(len(new_values)):
                #            new_values[j] = val if new_values[j] == i else new_values[j] + red
                
                #for i in range(0, div+1):
                #    self.tables.qtable[(state, self.plays[i])] = new_values[i]
                
            print(self.total_games - self.games_left)
        
        # Update game values
        self.table = 0
        self.wallet += prize
        self.games_left -= 1

        if self.games_left == 0:
            self.end()

    def end(self):
        self.pocket += self.wallet
        self.initial_wallet = self.wallet = 0
        print("Number of victories: " + str(self.wins))
        print("Number of defeats: " + str(self.defeats))
        print("Number of draws: " + str(self.draws))
        print("Number of surrenders: " + str(self.surrenders))
        print("Number of games passed: " + str(self.dont_play))
        if self.create:
            self.tables.save_tables()

