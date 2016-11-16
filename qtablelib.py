import random
from functools import reduce

# state tuple: (player_total, dealer_total, turn)
# sa tuple : (state, action)
#   action: s - stand, h - hit, d - double-down, u - surrender

# Create all possible states list
def create_states():
    states = [[(player_total, dealer_total, turn)] for turn in range (1, 6) \
            for player_total in range(11, 21) for dealer_total in range(1, 21)]
    return reduce(lambda a, b: a + b, states, [])
    

# Create dictionary of all possible state-actions (state, action) and their values
# and will create Q-value table
def create_qtable(states):
    qtable = {}
    for state in states:
        if state[2] == 1:
            qtable[(state, 'd')] = 0.8 if state[1] > 17 else 0.5
        qtable[(state, 'h')] = random.uniform(0.49, 0.51)
        qtable[(state, 's')] = random.uniform(0.49, 0.51)
        qtable[(state, 'u')] = random.uniform(0.49, 0.51)
    return qtable

# Setup a dictionary of state-actions to record how many times we've experienced
# a given state-action pair. We need this to re-calculate reward averages
def create_counting_table(qtable):
    counting_table = {}
    for state_action in qtable:
        counting_table[state_action] = 1
    return counting_table

# Recalculate the average reward for our Q-value table
def update_qtable(qtable, counting_table, results):
    for sa in results:
        qtable[sa] = qtable[sa] + ((results[sa] - qtable[sa]) / counting_table[sa])
    return qtable

