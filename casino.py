from game import Game
from player import Player
from randomplayer import RandomPlayer
from student import StudentPlayer

def main():
    players = [StudentPlayer("Diogo Martins", 100)]
    #players = [Player("Pedro", 100)]
    for i in range(10000000):
        #print(players)
        g = Game(players, min_bet=1, max_bet=5, verbose=False) 
        #g = Game(players, debug=True)
        g.run()
    
    print("OVERALL: ", players)

if __name__ == '__main__':
    main()
