#encoding: utf8
import card
import random
import qtablelib as q
import numpy
from player import Player

class StudentPlayer(Player):
    def __init__(self, name="Meu nome", money=0, eps=0.1):
        super(StudentPlayer, self).__init__(name, money)
        self.results = {}
        self.states = q.create_states()
        self.qtable = numpy.load('table_f.npy').item()
        #self.qtable = q.create_qtable(self.states)
        #self.counting_table = q.create_counting_table(self.qtable)
        self.counting_table = numpy.load('count_f.npy').item()
        self.eps = eps
        # Betting system
        self.bet_pivot = money
        self.bet_value = 1
        self.defeats = 0
        self.max_defeat = 3
        self.result = 0

    def play(self, dealer, players):
        hand = [p.hand for p in players if p.player.name == self.name][0]
        print(hand)
        if(card.value(hand)) < 11:
            return "h"
        player_value = card.value(hand)
        player_ace = len([c for c in hand if c.is_ace()]) >= 1
        dealer_value = card.value(dealer.hand)
        if(dealer_value >= 21):
            return "s"
        state = (player_value, player_ace, dealer_value)
        if(random.random() < self.eps):
            action = random.randint(0,1)
        else:
            probabilities = [self.qtable[(state, 0)], self.qtable[(state, 1)]] 
            action = probabilities.index(max(probabilities))
        state_action = (state, action)
        self.results[state_action] = 0
        self.counting_table[state_action] += 1
        return "s" if action else "h"

    def bet(self, dealer, players):
        if self.pocket > self.bet_pivot:
            self.bet_pivot = self.pocket
            self.bet_value = 1
        elif self.result == 1:
            self.bet_value = self.bet_value + 1 if self.bet_value < 3 else 3
        elif self.result == -1:
            self.defeats += 1
            if self.defeats == self.max_defeat:
                self.defeats = 0
                self.bet_pivot = self.pocket
                self.bet_value = 1
        
        #return self.bet_value 
        return 1

    def payback(self, prize):
        self.result = -1
        if(prize - self.table > 0):
            self.result = 1
        elif(prize-self.table == 0):
            self.result = 0
        for state_action in self.results:
            self.results[state_action] = self.result
        self.qtable = q.update_qtable(self.qtable, self.counting_table, self.results)
        #numpy.save('table_f.npy', self.qtable)
        #numpy.save('count_f.npy', self.counting_table)
        self.table = 0
        self.pocket += prize
        self.results = {}
