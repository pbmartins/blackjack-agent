import numpy
# may be eliminated on the future
from functools import reduce

# state tuple: (player_total, player_ace_usable_as_11, dealer_total, dealer_ace_usable_as_11)
# sa tuple : (state, action)
#   action: 0 - stand, 1 - hit

# Create all possible states list
def create_states():
    # Versions considering aces
    state_tuple = lambda pt, dt: [(pt, False, dt, False), (pt, True, dt, False), \
            (pt, False, dt, True), (pt, True, dt, True)]
    states = [state_tuple(player_total, dealer_total) \
            for player_total in range(11, 21) for dealer_total in range(1, 21)]
    return reduce(lambda a, b: a + b, states, [])

    #states = []
    #for player_total in range(11, 22):          # Player total - we hit until 11
    #    for dealer_total in range(1, 21):       # Dealer can have a total between 1 and 20
    #        states += [(player_total, False, dealer_total), \
    #                (player_total, True, dealer_total)]
    #return states

    #####################
    #Versions not considering aces since card.value() knows the value in hand

# Create dictionary of all possible state-actions (state, action) and their values
# and will create Q-value table
def create_qtable(states):
    qtable = {}
    for state in states:
        qtable[(state, 0)] = qtable[(state, 1)] = 0.0
    return qtable

# Setup a dictionary of state-actions to record how many times we've experienced
# a given state-action pair. We need this to re-calculate reward averages
def create_counting_table(qtable):
    counting_table = {}
    for state_action in qtable:
        counting_table[state_action] = 0
    return counting_table

# Recalculate the average reward for our Q-value table
def update_qtable(qtable, counting_table, results):
    for sa in results:
        qtable[sa] = qtable[sa] + (results[sa] - qtable[sa]) / counting_table[sa]
    return qtable

