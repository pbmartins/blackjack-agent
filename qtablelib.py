import numpy
# may be eliminated on the future

# state tuple: (player_total, ace_usable_as_11, dealer_total)

# Create all possible states list
def create_states():
    states = []
    for dealer_total in range(1, 21):           # Dealer can have a total between 1 and 20
        for player_total in range(11, 22):      # Player total - we hit until 11
            states[-1:-1] = [(player_total, False, dealer_total), \
                    (player_total, True, dealer_total)]

# Create dictionary of all possible state-actions (state, action) and their values
# and will create Q-value table
def create_qtable(state):
    qtable = {}
    for state in states:
        av[(state, 0)] = av[(state, 1)] = 0.0
    return av

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
        qtable[sa] = qtable[sa] + (results[sa] * qtable[sa]) / counting_table[sa]
    return qtable

