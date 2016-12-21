from game import Game
from player import Player
from randomplayer import RandomPlayer
from student import StudentPlayer

def main(n_games=1000, pocket=100):
    players = [RandomPlayer("RP", pocket), StudentPlayer("Diogo Martins", pocket)]
    for i in range(n_games):
        g = Game(players, min_bet=1, max_bet=5, verbose=False) 
        g.run()
    
    print("OVERALL: ", players)

if __name__ == '__main__':
    main()
