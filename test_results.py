from casino import main as casino_main
import json

if __name__ == '__main__':
    # Read json config file
    with open('settings.json') as data_file:    
        configs = json.load(data_file)
    for i in range(10):
        print("Game " + str(i) + ":")
        casino_main(n_games=configs['n_tests'], pocket=configs['pocket'])
