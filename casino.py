from game import Game
from player import Player
from randomplayer import RandomPlayer
from student import StudentPlayer

def main(n_games=1000, pocket=100, min_bet=1, max_bet=5):
    #players = [StudentPlayer("Pedro Martins", pocket)]
    players = [StudentPlayer("Pedro Martins", pocket), StudentPlayer("Diogo Ferreira", pocket)]
    #players = [Player("Pedro", 100)]
    for i in range(n_games):
        g = Game(players, min_bet=min_bet, max_bet=max_bet, verbose=False) 
        g.run()
    
    print("OVERALL: ", players)

if __name__ == '__main__':
    main()
