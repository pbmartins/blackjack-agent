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
        self.get_prob_query = 'SELECT StateID, Stand, Hit, Defeats ' + \
                'FROM ' + self.table_name + ' WHERE PlayerPoints=? ' + \
                'AND DealerPoints=? AND SoftHand=? AND FirstTurn=? AND PlayerAce=?'
        self.update_prob_query = 'UPDATE ' + self.table_name + \
                ' SET Stand=?, Hit=?, Defeats=? ' + \
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
        self.queries = []
       
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
        self.dealer_hand = dealer.hand

        # Increment turn
        self.turn += 1

        # Get players' total
        self.player_value = card.value(self.player_hand)
        self.dealer_value = card.value(dealer.hand)

        player_ace = len([c for c in self.player_hand if c.is_ace()])
        player_sum = sum([c.value() for c in self.player_hand])
        soft_hand = 0
        if player_ace > 1:
            soft_hand = 1
        elif player_ace == 1:
            soft_hand = int(player_sum == self.player_value)

        self.state = (self.player_value, self.dealer_value, soft_hand, self.turn == 1, player_ace > 0)
        # Access table and search for the best probability based on state-action
        self.states_query = list(self.conn.execute(self.get_prob_query, (self.state)).fetchall()[0])
        wins = self.states_query[1:-1]
        defeats = self.states_query[-1]
        #print(self.state)
        #print(games)
        #print(sum(wins)/games[-1])
        if sum(wins) == 0:
            probs = [0.5, 0.5]
        else:
            probs = [a / sum(wins) for a in wins]
        
        #if self.disable_dd and self.turn == 1:
        #    probs = [(games[i] + games[-1]) / sum(games) if i == 1 else games[i] / sum(games) \
        #            for i in range(games - 1)]

        max_prob = 0
        #if not self.create:
        #    max_prob = max(probs)
        #    max_idx = probs.index(max_prob)
        #    total = []
        #    for i in range(len(probs)):
        #        if max_idx != i and max_prob - probs[i] > self.probs_threshold:
        #            total += [probs[i]]
        #            probs[i] = 0.0
        #    s = sum(total) / (len(probs) - len(total))
        #    probs = [p + s if p != 0 else p for p in probs]
                    

        intervals = [sum(probs[:idx]) for idx in range(1, len(probs) + 1)]
        #print(intervals)
        r = random.random()
        idx = 0
        while intervals[idx] < r:
            idx += 1

        self.action = self.plays[idx]
        self.queries += [(self.states_query, self.action)]
        if not self.create:
            if self.turn == 1 and wins[1] / games[-1] > 0.75:
                #print(self.state)
                #print(games)
                #print(wins[1] / games[-1])
                self.action = 'd'
            if sum(wins) / games[-1] < 0.2:
                #print(games)
                #print(state)
                self.action = 'u'
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
        self.dd += 1 if not self.create and self.action == 'd' else 0
        self.good_dd += 1 if not self.create and self.result == 1 and self.action == 'd' else 0
        
        # Just change the table while learning else read only
        if self.create:
            # Update values on table
            for query, action in self.queries:
                games = self.states_query[1:]
                if self.result == 1:
                    games[self.plays.index(action)] += 1
                elif self.result == 0:
                    games[-1] += 1
                query = games + [self.states_query[0]]
                self.conn.execute(self.update_prob_query, (query))

            print(self.total_games - self.games_left, end='\r')
        
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

