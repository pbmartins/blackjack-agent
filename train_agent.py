import sqlite3
import json
from casino import main as casino_main

def main():
    conn = sqlite3.connect('tables.sqlite')
    # Read json config file
    with open('settings.json') as data_file:    
        configs = json.load(data_file)

    table_name = configs['table_name']
    conn.execute('DROP TABLE IF EXISTS [' + table_name + ']')
    table_query = 'CREATE TABLE [' + table_name + '] (' + \
        '[StateID]          INTEGER PRIMARY KEY AUTOINCREMENT,' + \
        '[PlayerPoints]     INTEGER NOT NULL,' + \
        '[DealerPoints]     INTEGER NOT NULL,' + \
        '[SoftHand]         INTEGER NOT NULL,' + \
        '[FirstTurn]        INTEGER NOT NULL,' + \
        '[PlayerAce]        INTEGER NOT NULL,' + \
        '[Stand]            INTEGER NOT NULL,' + \
        '[Hit]              INTEGER NOT NULL,' + \
        '[Games]            INTEGER NOT NULL);'
    conn.execute(table_query)
    states = [(pp, dp, sh, ft, pa, 1, 1, 2) for pp in range(3, 22) \
            for dp in range(2, 22) for sh in [0, 1] for ft in [0, 1] for pa in [0, 1]]
    states_query = 'INSERT OR IGNORE INTO ' + table_name + \
        ' (PlayerPoints, DealerPoints, SoftHand, FirstTurn, PlayerAce, Stand, Hit, Games)' + \
        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
    conn.executemany(states_query, states)
    conn.commit()

    n_games = configs['n_games']
    print("Training agent with " + str(n_games)+ ":")
    casino_main(n_games=n_games)


if __name__ == '__main__':
    main()
