from collections import defaultdict
import numpy

# state tuple: (player_total, dealer_total, turn)
# sa tuple : (state, action)
#   action: s - stand, h - hit, d - double-down, u - surrender

class Qtable:
    def __init__(self, qtable_fname, ctable_fname, gamma=1, learning_rate=0.9, create=True):
        self.qtable_fname = qtable_fname
        self.ctable_fname = ctable_fname
        self.gamma = gamma
        self.learning_rate = learning_rate
        self.create = create
        if self.create:
            self.qtable = defaultdict(float)
            self.ctable = defaultdict(int)
        else:
            self.qtable = numpy.load(self.qtable_fname).item()
            self.ctable = numpy.load(self.ctable_fname).item()

    # Recalculate the average reward for our Q-value table
    def update_tables(self, current_sa, next_sa, results, etrace, payback=False):
        qtable_next_sa = 0 if payback else self.qtable[next_sa]
        delta = results[next_sa] + self.gamma * qtable_next_sa \
                - self.qtable[current_sa]
        alpha = 1.0 / self.ctable[current_sa]
        etrace[current_sa] += 1

        for sa in results:
            self.qtable[sa] += alpha * delta * etrace[sa]
            etrace[sa] *= self.gamma * self.learning_rate

    # Save tables into their respective files
    def save_tables(self):
        numpy.save(self.qtable_fname, self.qtable)
        numpy.save(self.ctable_fname, self.ctable)

