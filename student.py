#encoding: utf8
import card
import random
import numpy
import math
from player import Player
from collections import defaultdict
import sqlite3

class StudentPlayer(Player):
    def __init__(self, name="Meu nome", money=0, table_name='StateAction', n_games='10000000', train=False):
        super(StudentPlayer, self).__init__(name, money)
        self.create = train
        self.total_games = self.games_left = n_games
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
        self.table_name = table_name
        self.conn = sqlite3.connect('tables.sqlite')
        self.get_prob_query = 'SELECT StateID, Action, Probability ' + \
                'FROM ' + self.table_name + ' WHERE PlayerPoints=? ' + \
                'AND DealerPoints=? AND SoftHand=? AND FirstTurn=?'
        self.update_prob_query = 'UPDATE ' + self.table_name + ' SET Probability=?' + \
                ' WHERE StateID=?'
        self.learning_rate = 0.015

        # Ignore rewards
        self.max_treshold = 0.98
        self.min_treshold = 0.02

    def want_to_play(self, rules):
        self.rules = rules
        self.queries = None
        self.action = None
        self.state = None
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

        # Increment turn
        self.turn += 1

        # Get players' total
        self.player_value = card.value(player_hand)
        self.dealer_value = card.value(dealer.hand)
        player_ace = len([c for c in player_hand if c.is_ace()]) >= 1

        state = (self.player_value, self.dealer_value, player_ace, self.turn == 1)

        # Update values on table
        reward = 0
        if self.create and self.turn > 1:
            if self.action == 's':
                reward = 0.015 if state[0] > state[1] else -0.015
            elif self.action == 'h':
                if self.state[0] > self.state[1]:
                    reward += 0.002 if state[0] < 22 else 0
                    reward += 0.013 if state[0] - state[1] > self.state[0] - self.state[1] else 0
                else:
                    reward += 0.002 if state[0] < 22 else 0
                    reward += 0.005 if state[0] - state[1] > self.state[0] - self.state[1] else 0
                    reward += 0.008 if state[0] > state[1] else 0
                reward = -0.015 if reward == 0 else reward
            elif self.action == 'd':
                reward += 0.002 if state[0] < 22 else 0
                reward += 0.013 if state[0] > state[1] else 0
                reward = -0.015 if reward == 0 else reward
            
            # Adjust probabilities with new values based on reward
            self.adjust_probs(reward)
            
        self.state = state
        # Access table and search for the best probability based on state-action
        states_query = self.conn.execute(self.get_prob_query, (self.state)).fetchall()
        self.queries += [states_query]
        probs = [prob for state_id, action, prob in states_query]

        if self.disable_dd and self.turn == 1:
            probs[1] += probs[3]
            probs[-1:] = []

        intervals = [sum(probs[:idx]) for idx in range(1, len(probs) + 1)]
        r = random.uniform(0, 1)
        idx = 0
        while intervals[idx] < r:
            idx += 1

        self.action = self.plays[idx]
        return self.action

    def bet(self, dealer, players): 
        self.disable_dd = False

        if self.create:
            self.bet_value = 2
            return self.bet_value

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
        
        # Bet shouldn't be less than 2 so that we can earn money from surrender
        self.bet_value = 2 if self.bet_value < 2 else self.bet_value

        return self.bet_value
    
    def p_bust(self):
        scenarios = [self.player_value + c for c in list(range(1, 12)) + [10, 10, 10]]
        return len([v for v in scenarios if v > 21]) / len(scenarios)
    
    def adjust_probs(self, reward):
        probs = [prob for state_id, action, prob in self.queries[-1]]
        self.max_threshold = 1.0 - min_threshold * (len(probs) - 1)
        if not any([p > self.max_threshold or p < self.min_threshold\
                for p in probs]):
            up = reward
            down = -reward / len(probs - 1)
            new_values = [(p + up, s) if self.action == a else (p + down, s)\
                for s, a, p in states_query]
        # TODO : put new probs in the self.queries / database based on db schema;
        # CAUTION : need to see the better way to manage double down:
        #   - add it always in self.queries and ignore it if self.turn != 1
        #   - add to queries just the probs that are used (just s,h,u in case of self.turn != 1)


    def payback(self, prize):
        self.result = 0
        if prize > 0:
            self.result = 1
        elif prize < 0:
            self.result = 0 if prize <= -self.bet_value else 0.25
        else:
            self.result = 0.5

        # Update statistics
        self.wins += 1 if self.result == 1 else 0
        self.defeats += 1 if self.result == 0 else 0
        self.draws += 1 if self.result == 0.5 else 0
        self.surrenders += 1 if self.result == 0.25 else 0
        
        # Just change the table while learning else read only
        if self.create:
            # Update values on table
            reward = 0
            if self.action == 's':
                reward = 0.015 if self.result == 1 else -0.015
            elif self.action == 'h' or (self.turn == 1 and self.action == 'd'):
                reward += 0.002 if self.result > 0 else 0
                reward += 0.013 if self.result == 1 else 0
                reward = -0.015 if reward == 0 else reward
            elif self.action == 'u':
                reward += 0.005 if self.state[1] + 7 <= 21 else 0
                reward += 0.005 if self.p_bust() > 0.5 else 0
                reward = -0.010 if reward == 0 else reward
                
                # Adjust probabilities with new values based on reward
                self.adjust_probs(reward)

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

