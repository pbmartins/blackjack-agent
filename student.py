#encoding: utf8
import card
import random
import numpy
import math
from player import Player
from collections import defaultdict
import sqlite3
import json

class StudentPlayer(Player):
    def __init__(self, name="Meu nome", money=0):
        super(StudentPlayer, self).__init__(name, money)
        # Read json config file
        with open('settings.json') as data_file:    
            configs = dict(json.load(data_file))

        self.create = configs['create']
        self.total_games = self.games_left = configs['n_games'] if self.create else configs['n_tests']
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
        self.dd = 0
        self.good_dd = 0

        # Create tables to save state-action average rewards
        self.table_name = configs['table_name']
        self.conn = sqlite3.connect('tables.sqlite')
        self.get_prob_query = 'SELECT StateID, Stand, Hit, Surrender, DoubleDown ' + \
                'FROM ' + self.table_name + ' WHERE PlayerPoints=? ' + \
                'AND DealerPoints=? AND HardHand=? AND FirstTurn=?'
        self.update_prob_query = 'UPDATE ' + self.table_name + \
                ' SET Stand=?, Hit=?, Surrender=?, DoubleDown=? ' + \
                'WHERE StateID=?'
        self.db_counter = 500000
        self.bust_threshold = configs['bust_threshold']
        self.probs_threshold = configs['probs_threshold']

        # Ignore rewards
        self.min_threshold = configs['min_threshold']


    def want_to_play(self, rules):
        self.rules = rules
        self.action = None
        self.state = None
        self.turn = 0
       
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
        self.player_hand = [p.hand for p in players if p.player.name == self.name][0]

        # Increment turn
        self.turn += 1

        # Get players' total
        self.player_value = card.value(self.player_hand)
        self.dealer_value = card.value(dealer.hand)
        player_ace = len([c for c in self.player_hand if c.is_ace()]) >= 1

        state = (self.player_value, self.dealer_value, player_ace, self.turn == 1)

        # Update last query
        reward = 0
        if self.create and self.turn > 1:
            if self.action == 's':
                ### Na primeira jogada, termos 13 e o dealer 3 (3+7=10 < 13), o stand irá ser
                # aceitável na maioria das vezes, mas aqui deveria ser feito alguns double-down
                reward = 0.015 if state[0] > state[1] else -0.015
                #### TEST ####
                #if self.state[0] < 14:
                #    reward += 0.005 if state[0] > state[1] + 7 else 0
                #else:
                #    reward += 0.015 if state[0] > state[1] + 7 else 0
            elif self.action == 'h':
                if self.state[0] > self.state[1]:
                    reward += 0.002 if state[0] < 22 else 0
                    reward += 0.013 if state[0] - (state[1]) > self.state[0] - (self.state[1]) else 0
                else:
                    reward += 0.002 if state[0] < 22 else 0
                    reward += 0.005 if state[0] - (state[1]) > self.state[0] - (self.state[1]) else 0
                    reward += 0.008 if state[0] > state[1] else 0
            reward = -0.015 if reward == 0 else reward
            # Adjust probabilities with new values based on reward
            self.adjust_probs(reward)
            
        self.state = state
        # Access table and search for the best probability based on state-action
        self.states_query = list(self.conn.execute(self.get_prob_query, (self.state)).fetchall()[0])
        probs = self.states_query[1:]
        
        if self.disable_dd and self.turn == 1:
            probs[1] += probs[3]
            probs[-1:] = []

        if not self.create:
            max_prob = max(probs)
            max_idx = probs.index(max_prob)
            total = []
            for i in range(len(probs)):
                if max_idx != i and max_prob - probs[i] > self.probs_threshold:
                    total += [probs[i]]
                    probs[i] = 0
            s = sum(total) / (len(probs) - len(total))
            probs = [p + s if p != 0 else p for p in probs]
                    

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
        all_cards = [card.Card(rank=r) for r in range(1, 14)]
        scenarios = [card.value(self.player_hand + [c]) for c in all_cards]
        return len([v for v in scenarios if v > 21]) / len(scenarios)
    
    def adjust_probs(self, reward):
        probs = self.states_query[1:] if self.states_query[-1] != 0 else self.states_query[1:-1]
        max_threshold = 1.0 - self.min_threshold * (len(probs) - 1)
        if min(probs) >= self.min_threshold and max(probs) <= max_threshold:
            up = reward
            down = -reward / (len(probs) - 1)
            action_idx = self.plays.index(self.action)
            new_values = [probs[i] + up if i == action_idx else probs[i] + down \
                    for i in range(len(probs))]
            new_values += [0, self.states_query[0]] \
                    if len(new_values) < 4 else [self.states_query[0]]
            self.conn.execute(self.update_prob_query, (new_values))
            #self.conn.commit()

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
        if self.create and self.turn > 0:
            # Update values on table
            reward = 0
            if self.action == 's':
                reward = 0.015 if self.result == 1 else -0.015
            elif self.action == 'h' or (self.turn == 1 and self.action == 'd'):
                if self.action == 'd':
                    self.good_dd += 1 if self.result == 1 else 0
                    self.dd += 1
                reward += 0.002 if self.result > 0 else 0
                reward += 0.013 if self.result == 1 else 0
            elif self.action == 'u':
                if self.state[0] > 10:
                    if self.state[1] + 7 <= 21 and self.state[0] < self.state[1] + 7:
                        reward += 0.005 if self.p_bust() > self.bust_threshold else 0
            reward = -0.015 if reward == 0 else reward
                
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
        self.conn.commit()
        self.my_pocket += self.wallet
        self.initial_wallet = self.wallet = 0
        print("Number of victories: " + str(self.wins))
        print("Number of defeats: " + str(self.defeats))
        print("Number of draws: " + str(self.draws))
        print("Number of surrenders: " + str(self.surrenders))
        print("Number of games passed: " + str(self.dont_play))
        print("Number of double downs: " + str(self.dd))
        print("Number of good dds: " + str(self.good_dd))

