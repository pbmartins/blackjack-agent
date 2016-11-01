#encoding: utf8
import card
import random
import qtablelib as q
import numpy
from player import Player

class StudentPlayer(Player):
    def __init__(self, name="Meu nome", money=0, eps=1.0, total_games=100000):
        super(StudentPlayer, self).__init__(name, money)
        # Create tables to save state-action average rewards
        self.results = {}
        self.states = q.create_states()
        #self.qtable = q.create_qtable(self.states)
        #self.counting_table = q.create_counting_table(self.qtable)

        # Load tables from files
        # Uncomment to load them
        self.qtable = numpy.load('table_2tuple.npy').item()
        self.counting_table = numpy.load('count_2tuple.npy').item()

        self.total_games = self.games_left = total_games
        self.eps = eps

        # Betting system
        self.bet_pivot = money
        self.bet_value = 1
        self.defeats = 0
        self.max_defeat = 7
        self.result = 0

    def play(self, dealer, players):
        hand = [p.hand for p in players if p.player.name == self.name][0]
        # If player's hand total is under 11, keep hitting
        if(card.value(hand)) < 11:
            return "h"

        player_value = card.value(hand)
        player_ace = len([c for c in hand if c.is_ace()]) >= 1
        dealer_value = card.value(dealer.hand)
        dealer_ace = len([c for c in dealer.hand if c.is_ace()]) >= 1

        # There's something tricky here, example:
        #   Dealer's hand: 2, ace, hidden
        #   card.value(dealer.hand) will return 13 because the sum of the first two cards \
        #       don't go over the 21 limit, even if the third card is a Jack, and then, \
        #       the ace will be considered 1 and not 11, as we thought initially


        if(dealer_value >= 21):
            print("DEALER VALUE: " + str(dealer_value))
            # The ace will be counted as 1, because there's stil a card to show
            dealer_value -= 10
            #return "s"

        #state = (player_value, player_ace, dealer_value, dealer_ace)
        state = (player_value, dealer_value)
        # If random value is less than epsilon, play randomly (0 - stand, 1 - hit)
        # Else access qtable and search for the best probability based on state-action
        if(random.random() < self.eps):
            action = random.randint(0, 1)
        else:
            probabilities = [self.qtable[(state, 0)], self.qtable[(state, 1)]] 
            action = probabilities.index(max(probabilities))
            print("state = {state}, prob = {prob}, action = {action}".format(state=state, prob=probabilities, action=action))

        # Update counting table and create state-action entry on results dict
        state_action = (state, action)
        self.results[state_action] = 0
        self.counting_table[state_action] += 1

        return "h" if action else "s"

    def bet(self, dealer, players):
        # Pivot-base betting system
        #if self.pocket > self.bet_pivot:
        #    self.bet_pivot = self.pocket
        #    self.bet_value = 2
        #elif self.result == 1:
        #    self.bet_value = self.bet_value + 1 if self.bet_value < 5 else 5
        #elif self.result == -1:
        #    self.defeats += 1
        #    if self.defeats == self.max_defeat:
        #        self.defeats = 0
        #        self.bet_pivot = self.pocket
        #        self.bet_value = 2
        #return self.bet_value 

        ##########################
        # Hard-core betting system
        #if self.pocket <= 85:
        #    self.bet_value = 1
        #elif self.pocket >= 120:
        #    self.bet_value = 5
        #else:
        #    self.bet_value = 4
        #return self.bet_value

        ##########################
        # 1-3-2-6 System
        #bets = [1, 3, 2, 6]
        #if self.result:
        #    self.bet_value = (self.bet_value + 1) % len(bets)
        #else:
        #    self.bet_value = 0
        #return bets[self.bet_value]
        
        ##########################
        # Parlay System
        #parlay = lambda n: round(2 * n - 0.85 * n) if n < 5 else 5
        #if self.result:
        #    self.bet_value += 1
        #else:
        #    self.bet_value = 1
        #return parlay(self.bet_value)

        return 1


    def payback(self, prize):
        # After running some tests, I've undestood that the prize gives the result
        self.result = 0
        if prize != 0:
            self.result = -1 if prize < 0 else 1

        # For every state-action in the current game, registry the game final result
        for state_action in self.results:
            self.results[state_action] = self.result
        
        # Update qtable with the results of the current game
        self.qtable = q.update_qtable(self.qtable, self.counting_table, self.results)

        # Save tables to files
        # Uncomment to save
        #numpy.save('table_2tuple.npy', self.qtable)
        #numpy.save('count_2tuple.npy', self.counting_table)

        # Update game values
        self.table = 0
        self.pocket += prize
        self.results = {}
        self.games_left -= 1
        #self.eps = self.games_left / self.total_games
