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
        self.total_games = self.games_left = configs['n_games'] \
                if self.create else configs['n_tests']
        self.plays = ['s', 'h', 'u', 'd']
     
        # Wallet 
        self.loans = [0.50, 0.25, 0.125]
        self.my_pocket = self.pocket
        self.initial_wallet = self.wallet = int(self.my_pocket * self.loans[0])
        self.my_pocket -= self.initial_wallet

        self.bet_value = 0
        self.result = 0

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
        self.get_prob_query = 'SELECT StateID, PlayStand, PlayHit, FinalStand, FinalHit, BadPlay ' + \
                'FROM ' + self.table_name + ' WHERE PlayerPoints=? ' + \
                'AND DealerPoints=? AND SoftHand=? AND FirstTurn=? AND PlayerAce=?'
        self.update_prob_query = 'UPDATE ' + self.table_name + \
                ' SET PlayStand=?, PlayHit=?, FinalStand=?, FinalHit=?, BadPlay=? ' + \
                'WHERE StateID=?'
        self.db_counter = 500000
        self.bust_threshold = configs['bust_threshold']
        self.win_threshold = configs['win_threshold']
        self.probs_threshold = configs['probs_threshold']
        self.surrender_threshold = configs['surrender_threshold']
        self.use_dd_threshold = configs['use_dd_threshold']
        self.dd_threshold = configs['dd_threshold']


    def want_to_play(self, rules):
        self.rules = rules
        self.action = None
        self.state = None
        self.turn = 0
        self.queries = []
        self.bet_value = rules.min_bet
      
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

    def prob_dealer_bust(self):
        all_cards = [card.Card(rank=r) for r in range(1, 14)]
        scenarios = [card.value(self.dealer_hand + [c]) for c in all_cards]
        return len([v for v in scenarios \
                if v > 21]) / len(scenarios)


    def play(self, dealer, players):
        # Get player hand
        new_player_hand = [p.hand for p in players if p.player.name == self.name][0]
        new_dealer_hand = dealer.hand
        
        # Get players' total
        new_player_value = card.value(new_player_hand)
        new_dealer_value = card.value(dealer.hand)

        # Increment turn
        self.turn += 1

        # Evaluate older state
        if self.create and self.turn > 1:
            query = self.queries[-1][0]
            wins_defeats = query[1:]
            good_flag = False
            if self.action == 'h':
                # If probably the dealer was on bust
                if self.prob_dealer_bust() > self.bust_threshold:
                    # Maybe we should stand
                    wins_defeats[self.plays.index('s')] += 1
                else:

                    # If the prob of being in advantage over the dealer is low
                    # on the previous play
                    if self.player_value > self.dealer_value:
                        wins_defeats[self.plays.index(self.action)] += 1
                    # If we were in advantage, check if our score hasn't decreased
                    elif new_player_value >= self.player_value:
                        wins_defeats[self.plays.index(self.action)] += 1
                    # If we were in advantage and our score has decreased
                    else:
                        # If we are still in the lead
                        if new_player_value > new_dealer_value:
                            # If out score was above 18, we should have stand
                            if self.player_value > 18:
                                wins_defeats[self.plays.index('s')] += 1
                            # Else the hit was a good option to keep playing
                            else:
                                wins_defeats[self.plays.index(self.action)] += 1
                        # If we lost the lead, then we should have stand
                        else:
                            wins_defeats[self.plays.index('s')] += 1
                    
            elif self.action == 's':
                if new_player_value > 17:
                    wins_defeats[self.plays.index(self.action)] += 1
                else:
                    wins_defeats[self.plays.index('h')] += 1

            query = wins_defeats + [query[0]]
            self.conn.execute(self.update_prob_query, (query))

        self.player_hand = new_player_hand
        self.dealer_hand = new_dealer_hand
        
        # Get players' total
        self.player_value = new_player_value
        self.dealer_value = new_dealer_value

        player_ace = len([c for c in self.player_hand if c.is_ace()])
        player_sum = sum([c.value() for c in self.player_hand])
        soft_hand = player_sum != self.player_value
        
        self.state = (self.player_value, self.dealer_value, \
                soft_hand, self.turn == 1, player_ace > 0)
        # Access table and search for the best probability based on state-action
        self.states_query = list(self.conn.execute(self.get_prob_query, \
                (self.state)).fetchall()[0])
        wins = [self.states_query[1] + self.states_query[3], \
                self.states_query[2] + self.states_query[4]]
        defeats = self.states_query[-1]
        
        probs = [a / sum(wins) for a in wins]
        intervals = [sum(probs[:idx]) for idx in range(1, len(probs) + 1)]
        r = random.random()
        idx = 0
        while intervals[idx] < r:
            idx += 1

        if self.create:
            self.action = self.plays[idx]
        else:
            diff = abs(probs[0] - probs[1])
            self.action = self.plays[idx] if diff < self.probs_threshold \
                    else self.plays[probs.index(max(probs))]
        self.queries += [(self.states_query, self.action)]
        
        if not self.create:
            if self.player_value > 11 \
                    and sum(wins) / (sum(wins) + defeats) < self.surrender_threshold:
                self.action = 'u'
            elif self.turn == 1 and self.player_value > 9 \
                    and sum(self.states_query[3:5]) / sum(wins) > self.use_dd_threshold \
                    and self.states_query[4] / sum(self.states_query[3:5]) > self.dd_threshold:
                self.action = 'd'
        return self.action

    def bet(self, dealer, players): 
        if self.create:
            self.bet_value = 2
            return self.bet_value
        
        # Compute bet
        if self.action == 'd':
            self.bet_value = self.bet_value
        elif self.result < 0:
            self.bet_value = self.rules.min_bet
        else:
            self.bet_value *= 2

        # Normalize values
        if self.bet_value > self.rules.max_bet:
            self.bet_value = self.rules.max_bet
        elif self.bet_value < self.rules.min_bet:
            self.bet_value = self.rules.min_bet
        

        # Bet shouldn't be less than 2 so that we can earn money from surrender
        self.bet_value = 2 if self.bet_value < 2 else self.bet_value

        #self.bet_value = 2
        return self.bet_value
        
    def show(self, players):
        self.last_dealer_hand = players[0].hand
        self.last_dealer_value = card.value(self.last_dealer_hand)
        self.last_player_hand = [p.hand for p in players if p.player.name == self.name][0]
        self.last_player_value = card.value(self.last_player_hand)

    def prob_win(self):
        all_cards = [card.Card(rank=r) for r in range(1, 14)]
        scenarios = [card.value(self.player_hand + [c]) for c in all_cards]
        return len([v for v in scenarios \
                if v < 22 and v > self.last_dealer_value]) / len(scenarios)

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
        if self.create and self.queries != []:
            query = self.queries[-1][0]
            wins_defeats = query[1:]
            if self.action == 'h':
                if self.result == 1:
                    # It's only a good hit if we won because we surpassed the dealer
                    if self.last_dealer_value < 22:
                        wins_defeats[self.plays.index(self.action) + 2] += 1
                    # If we won because the dealer busted, any play is good
                    # But stand is more safe
                elif self.result == 0:
                    # If we were both on bust
                    if self.last_dealer_value > 21:
                        wins_defeats[self.plays.index('s') + 2] += 1
                    # If dealer isn't on bust, but I may be
                    else:
                        # Check if we could have won with a stand
                        if self.player_value > self.last_dealer_value:
                            wins_defeats[self.plays.index('s') + 2] += 1
                        # Check if we had an high chance of winning with a hit
                        elif self.prob_win() > self.win_threshold:
                            wins_defeats[self.plays.index(self.action) + 2] += 1
                        # Else we were going to lose either way
                        else:
                            wins_defeats[-1] += 1
                        
            elif self.action == 's':
                if self.result == 1:
                    wins_defeats[self.plays.index(self.action) + 2] += 1
                elif self.result == 0:
                    if self.prob_win() < self.win_threshold:
                        wins_defeats[-1] += 1
                    else:
                        wins_defeats[self.plays.index('h') + 2] += 1
            query = wins_defeats + [query[0]]
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
        self.dd = 1 if self.dd == 0 else self.dd
        # Print stats
        
        print("Number of victories: " + str(self.wins) + ", " \
                + str(self.wins/(self.total_games-self.dont_play)*100) + "%")
        print("Number of defeats: " + str(self.defeats) + ", " \
                + str(self.defeats/(self.total_games-self.dont_play)*100) + "%")
        print("Number of draws: " + str(self.draws) + ", " \
                + str(self.draws/(self.total_games-self.dont_play)*100) + "%")
        print("Number of surrenders: " + str(self.surrenders) + ", " \
                + str(self.surrenders/(self.total_games-self.dont_play)*100) + "%")
        print("Number of double downs: " + str(self.dd) + ", " \
                + str(self.dd/(self.total_games-self.dont_play)*100) + "%")
        print("Number of good dds: " + str(self.good_dd) + ", " \
                + str(self.good_dd/self.dd*100) + "%")
        print("-------------------------------")
