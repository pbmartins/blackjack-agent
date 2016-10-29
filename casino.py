from game import Game
from player import Player
from randomplayer import RandomPlayer
from student import StudentPlayer

if __name__ == '__main__':

    players = [StudentPlayer("Diogo Martins",100)]

    for i in range(1000):
        print(players)
        g = Game(players, min_bet=1, max_bet=5) 
        #g = Game(players, debug=True)
        g.run()

    print("OVERALL: ", players)
